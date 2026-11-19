"""Pipeline Gold: transforma silver → gold (formato para o app VijaClima).

Responsabilidades
-----------------
- Ler tabelas silver já limpas e estruturadas.
- Converter para o formato analítico final consumido pelo app.
- Persistir via MERGE idempotente nas tabelas gold.

Por que uma camada gold separada da silver?
A silver tem um schema normalizado (uma coluna por variável climática). O app
precisa de um formato longo (uma linha por variável) para facilitar consultas
genéricas como "todas as leituras de temperatura_c desta estação".
Esse processo de transformação de largo → longo é chamado de UNPIVOT.

Tabelas geradas
---------------
gold.leitura_climatica
    Formato longo (UNPIVOT): uma linha por variável medida por horário.
    Chave: (fonte, estacao, variavel, lida_em).

gold.estacao
    Metadados das estações meteorológicas (INMET – Pernambuco).
    Chave: (fonte, estacao).

gold.indicador_territorio
    Contagens epidemiológicas e de ocorrências por bairro e período.
    Chave: (territorio, bairro, indicador, periodo, fonte).

gold.fonte_status (VIEW, não gerida por este pipeline)
    Consulta diretamente as tabelas bronze; sempre atualizada.

Ordem de execução
-----------------
    python3 -m mongo.main     # 1. coleta → MongoDB
    python3 -m bronze.main    # 2. MongoDB → bronze SQL Server
    python3 -m silver.main    # 3. bronze → silver SQL Server
    python3 -m gold.main      # 4. silver → gold SQL Server (este arquivo)
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Path para o script DDL gold — calculado dinamicamente.
# parents[2]: gold_pipeline.py → pipelines/ → gold/ → projeto_5/ → sql/gold/
SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "gold" / "001_gold_tables.sql",
)

# _BATCH_SIZE: mesmo limite que a silver (500 linhas por executemany).
# Evita timeout do Azure SQL em volumes grandes. leitura_climatica tem 4× mais
# linhas que a Meteorologia (UNPIVOT multiplica por 4 variáveis).
_BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _aplicar_ddl(connection, scripts=SQL_SCRIPTS) -> None:
    """Executa os scripts DDL do schema gold de forma idempotente.

    Divide cada arquivo em batches separados pelo delimitador GO e executa
    um commit por batch. Em caso de erro, faz rollback e relança a exceção.
    DDL com IF OBJECT_ID IS NULL é seguro para re-execução.

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.
        scripts: Iterable de paths para os arquivos .sql a executar.
    """
    cursor = connection.cursor()
    try:
        for caminho in scripts:
            script = Path(caminho).read_text(encoding="utf-8")
            # re.split (?im): case-insensitive + multiline para o separador GO.
            for batch in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script):
                if batch.strip():
                    cursor.execute(batch)
                    connection.commit()
            logger.info("DDL gold aplicado: %s", Path(caminho).name)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _upsert(connection, tabela: str, merge_sql: str, params: list[tuple]) -> int:
    """Insere/atualiza registros em lotes via MERGE idempotente.

    Quebra `params` em lotes de `_BATCH_SIZE` para evitar timeout do Azure SQL
    em volumes grandes (problema observado com >32 k linhas em único executemany).
    Cada lote é uma transação independente — falha em um lote não desfaz os anteriores.

    Args:
        connection: Conexão pyodbc ativa.
        tabela: Nome da tabela destino (usado apenas para logging).
        merge_sql: Instrução MERGE parametrizada com placeholders `?`.
        params: Lista de tuplas com os valores a inserir; uma tupla por linha.

    Returns:
        Número total de linhas processadas (todos os lotes somados).

    Raises:
        Exception: Qualquer erro de banco; faz rollback do lote afetado.
    """
    if not params:
        return 0
    total = 0
    for i in range(0, len(params), _BATCH_SIZE):
        lote = params[i: i + _BATCH_SIZE]
        cursor = connection.cursor()
        try:
            cursor.executemany(merge_sql, lote)
            connection.commit()
            total += len(lote)
            logger.debug("Lote %d/%d inserido em %s", i + len(lote), len(params), tabela)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    return total


def _ts(valor) -> str | None:
    """Converte datetime (ou qualquer objeto com isoformat) para string ISO 8601.

    Na gold, lemos de silver.Meteorologia via cursor SQL — o pyodbc retorna
    colunas DATETIMEOFFSET como objetos datetime Python. hasattr(isoformat)
    é mais robusto que isinstance(datetime) para cobrir subclasses e tipos
    personalizados do driver.

    Args:
        valor: datetime, date, str ou None.

    Returns:
        String ISO 8601 ou None.
    """
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


# ---------------------------------------------------------------------------
# leitura_climatica — UNPIVOT de silver.Meteorologia
# ---------------------------------------------------------------------------

# Template MERGE para gold.leitura_climatica (formato largo).
# Chave de idempotência: (fonte, estacao, lida_em) — uma linha por horário por fonte.
# Cada variável é uma coluna NULL; a linha existe mesmo que algumas variáveis
# não estejam disponíveis para aquela fonte/horário.
_MERGE_LEITURA = """\
MERGE gold.leitura_climatica WITH (HOLDLOCK) AS tgt
USING (VALUES (
    ?, ?, ?,
    CONVERT(datetimeoffset(6), ?),
    ?, ?, ?, ?, ?,
    CONVERT(datetimeoffset(6), ?)
)) AS src (fonte, estacao, territorio, lida_em, natureza_dado,
           temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa, atualizado_em)
ON  tgt.fonte   = src.fonte
AND tgt.estacao = src.estacao
AND tgt.lida_em = src.lida_em
WHEN NOT MATCHED THEN
    INSERT (fonte, estacao, territorio, lida_em, natureza_dado,
            temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa, atualizado_em)
    VALUES (src.fonte, src.estacao, src.territorio, src.lida_em, src.natureza_dado,
            src.temperatura_c, src.precipitacao_mm, src.umidade_pct, src.pressao_hpa,
            src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    temperatura_c   = src.temperatura_c,
    precipitacao_mm = src.precipitacao_mm,
    umidade_pct     = src.umidade_pct,
    pressao_hpa     = src.pressao_hpa,
    natureza_dado   = src.natureza_dado,
    atualizado_em   = src.atualizado_em;
"""


def processar_leitura_climatica(connection) -> dict:
    """Copia silver.Meteorologia para gold.leitura_climatica no formato largo.

    Formato largo: uma linha por (fonte, estacao, lida_em) com as quatro variáveis
    climáticas como colunas separadas. É o mesmo schema do silver.Meteorologia,
    mas exposto na camada gold para consumo direto pelo app.

    Por que formato largo (e não longo/UNPIVOT)?
    As quatro variáveis (temperatura, precipitação, umidade, pressão) compõem
    juntas uma "leitura" — fazem sentido como um conjunto. O app exibe os quatro
    valores para o mesmo horário em um único card/componente. Com formato largo,
    uma única linha traz tudo que o componente precisa, sem JOIN ou GROUP BY.

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.

    Returns:
        dict com "tabela" (str) e "processados" (int — linhas inseridas ou atualizadas).
    """
    agora = _ts(datetime.now(timezone.utc))
    cursor = connection.cursor()
    try:
        cursor.execute("""\
            SELECT fonte, estacao, territorio, lida_em, natureza_dado,
                   temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa
            FROM silver.Meteorologia
        """)
        rows = cursor.fetchall()
    finally:
        cursor.close()

    # Uma tupla por linha do silver — sem UNPIVOT, cópia direta.
    params = [
        (fonte, estacao, territorio, _ts(lida_em), natureza_dado,
         temp, precip, umid, pressao, agora)
        for fonte, estacao, territorio, lida_em, natureza_dado,
            temp, precip, umid, pressao in rows
    ]

    inseridos = _upsert(connection, "gold.leitura_climatica", _MERGE_LEITURA, params)
    logger.info("gold.leitura_climatica: %d linhas processadas", inseridos)
    return {"tabela": "gold.leitura_climatica", "processados": inseridos}


# ---------------------------------------------------------------------------
# estacao — de silver.Estacoes (INMET)
# ---------------------------------------------------------------------------

# MERGE para gold.estacao.
# WHEN MATCHED UPDATE: atualiza coordenadas/nome se o INMET corrigir metadados.
_MERGE_ESTACAO = """\
MERGE gold.estacao WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (fonte, estacao, nome, municipio, latitude, longitude, situacao, atualizado_em)
ON  tgt.fonte   = src.fonte
AND tgt.estacao = src.estacao
WHEN NOT MATCHED THEN
    INSERT (fonte, estacao, nome, municipio, latitude, longitude, situacao, atualizado_em)
    VALUES (src.fonte, src.estacao, src.nome, src.municipio, src.latitude, src.longitude,
            src.situacao, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    nome          = src.nome,
    municipio     = src.municipio,
    latitude      = src.latitude,
    longitude     = src.longitude,
    situacao      = src.situacao,
    atualizado_em = src.atualizado_em;
"""


def processar_estacao(connection) -> dict:
    """Copia metadados de estações de silver.Estacoes para gold.estacao.

    A tabela silver.Estacoes é populada a partir dos metadados do INMET
    (16 estações automáticas de Pernambuco). O gold.estacao serve como
    catálogo de referência para o app — permite exibir nome, município e
    coordenadas de cada ponto de leitura sem precisar fazer JOIN com o silver.

    Por que copiar do silver em vez de ler direto do silver.Estacoes no app?
    O gold é a única camada exposta ao app. Manter os dados de estação no gold
    simplifica as queries do app: tudo vem de gold.*, não de um JOIN gold.* + silver.*.

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.

    Returns:
        dict com "tabela" (str) e "processados" (int).
    """
    agora = _ts(datetime.now(timezone.utc))
    cursor = connection.cursor()
    try:
        cursor.execute("""\
            SELECT fonte, estacao, nome, municipio, latitude, longitude, situacao
            FROM silver.Estacoes
        """)
        rows = cursor.fetchall()
    finally:
        cursor.close()

    # List comprehension: uma tupla por estação, adicionando o timestamp atual.
    params = [
        (fonte, estacao, nome, municipio, lat, lon, situacao, agora)
        for fonte, estacao, nome, municipio, lat, lon, situacao in rows
    ]

    inseridos = _upsert(connection, "gold.estacao", _MERGE_ESTACAO, params)
    logger.info("gold.estacao: %d linhas processadas", inseridos)
    return {"tabela": "gold.estacao", "processados": inseridos}


# ---------------------------------------------------------------------------
# indicador_territorio — UNION de Arboviroses + DefesaCivil + AnimaisPerconhentos
# ---------------------------------------------------------------------------

# MERGE para gold.indicador_territorio.
# Chave inclui `fonte` para diferenciar a mesma doença em fontes distintas.
_MERGE_INDICADOR = """\
MERGE gold.indicador_territorio WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, indicador, valor, periodo, fonte, atualizado_em)
ON  tgt.territorio = src.territorio
AND tgt.bairro     = src.bairro
AND tgt.indicador  = src.indicador
AND tgt.periodo    = src.periodo
AND tgt.fonte      = src.fonte
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, indicador, valor, periodo, fonte, atualizado_em)
    VALUES (src.territorio, src.bairro, src.indicador, src.valor, src.periodo,
            src.fonte, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    valor         = src.valor,
    atualizado_em = src.atualizado_em;
"""


def processar_indicador_territorio(connection) -> dict:
    """Unifica três fontes silver em gold.indicador_territorio (UNION em Python).

    Por que UNION em Python em vez de UNION em SQL?
    - Mais fácil de depurar: cada SELECT tem seu próprio cursor, erros são isolados.
    - Mais fácil de estender: adicionar uma nova fonte é incluir um bloco.
    - Performance equivalente: o volume é pequeno (centenas de linhas por fonte).

    Mapeamento de campos por fonte:
    - silver.Arboviroses:         indicador = indicador (dengue, zika, etc.)
    - silver.DefesaCivil:         indicador = tipo_ocorrencia (Alagamento, etc.)
    - silver.AnimaisPerconhentos: indicador = "acidentes_animais_peconhentos" (fixo)
                                  bairro    = municipio (SINAN não tem granularidade de bairro)

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.

    Returns:
        dict com "tabela" (str) e "processados" (int).
    """
    agora = _ts(datetime.now(timezone.utc))
    params = []

    # --- Arboviroses (dengue, zika, chikungunya) por bairro/semana -----------
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT territorio, bairro, indicador, casos, periodo FROM silver.Arboviroses"
        )
        for territorio, bairro, indicador, casos, periodo in cursor.fetchall():
            params.append((territorio, bairro, indicador, casos, periodo, "recife_arboviroses", agora))
    finally:
        cursor.close()

    # --- Defesa Civil (tipos de ocorrência) por bairro/mês ------------------
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT territorio, bairro, tipo_ocorrencia, casos, periodo FROM silver.DefesaCivil"
        )
        for territorio, bairro, tipo_ocorrencia, casos, periodo in cursor.fetchall():
            params.append((territorio, bairro, tipo_ocorrencia, casos, periodo, "defesa_civil", agora))
    finally:
        cursor.close()

    # --- Animais Peçonhentos por município/semana ----------------------------
    # municipio assume o papel de bairro — SINAN não tem granularidade de bairro.
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT territorio, municipio, casos, periodo FROM silver.AnimaisPerconhentos"
        )
        for territorio, municipio, casos, periodo in cursor.fetchall():
            params.append((
                territorio,
                municipio,                          # município como "bairro" do indicador
                "acidentes_animais_peconhentos",    # indicador fixo para toda a fonte
                casos,
                periodo,
                "sinan",
                agora,
            ))
    finally:
        cursor.close()

    inseridos = _upsert(connection, "gold.indicador_territorio", _MERGE_INDICADOR, params)
    logger.info("gold.indicador_territorio: %d linhas processadas", inseridos)
    return {"tabela": "gold.indicador_territorio", "processados": inseridos}


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def gold_pipeline(connection=None, aplicar_ddl: bool = True) -> list[dict]:
    """Orquestra a transformação silver → gold para todas as tabelas.

    Executado como último passo da pipeline (após mongo, bronze e silver).
    Cada processador é chamado individualmente; uma falha isolada não para
    os demais — o erro é registrado em log e o dict de resultado inclui
    a chave "erro".

    Por que falha isolada por processador?
    Se processar_leitura_climatica falhar (ex: schema changed), os metadados
    de estação e os indicadores ainda são atualizados. O app degrada com
    dados parciais em vez de não ter dado nenhum.

    Args:
        connection: Conexão pyodbc pré-existente; se None, abre e fecha
            automaticamente uma nova conexão via `conectar_sql_server`.
        aplicar_ddl: Se True, executa os scripts DDL do schema gold antes
            de processar os dados (cria tabelas e view se não existirem).

    Returns:
        Lista de dicts, um por processador, com chaves:
            - "tabela" (str): nome da tabela gold.
            - "processados" (int): linhas inseridas/atualizadas.
            - "erro" (str, opcional): mensagem de erro se o processador falhou.
    """
    # Importação local: evita circular import com silver.database.
    from silver.database.sql_server import conectar_sql_server

    owns = connection is None
    if owns:
        connection = conectar_sql_server()

    try:
        if aplicar_ddl:
            # Cria schema gold, tabelas e view se ainda não existirem.
            _aplicar_ddl(connection)

        # Ordem importa: leitura_climatica (maior volume) antes de estacao e indicadores.
        fontes = [
            processar_leitura_climatica,
            processar_estacao,
            processar_indicador_territorio,
        ]
        resultados = []
        for fn in fontes:
            try:
                resultados.append(fn(connection))
            except Exception as erro:
                # Captura falha isolada sem interromper os demais processadores.
                logger.error(
                    "Falha em %s: %s", getattr(fn, "__name__", repr(fn)), type(erro).__name__
                )
                resultados.append({
                    "tabela":      getattr(fn, "__name__", repr(fn)),
                    "processados": 0,
                    "erro":        str(erro),
                })

        total = sum(r.get("processados", 0) for r in resultados)
        logger.info("Pipeline Gold concluído: %d linhas no total", total)
        return resultados
    finally:
        # Fecha a conexão somente se foi aberta por este pipeline.
        if owns:
            connection.close()
