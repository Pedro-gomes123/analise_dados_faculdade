"""Pipeline Silver: lê tabelas bronze, transforma e persiste nas tabelas silver.

Responsabilidades
-----------------
- Ler `payload_json` das tabelas bronze (BSON Extended JSON).
- Desserializar com `json_util.loads` para recuperar tipos Python corretos
  (datetime, Decimal128, etc.) que o JSON nativo não suporta.
- Aplicar regras de limpeza, conversão de unidades e validação por domínio.
- Persistir via MERGE idempotente nas tabelas silver.

Por que BSON Extended JSON (json_util) em vez de JSON nativo?
O payload_json armazenado no bronze foi serializado com `json_util.dumps`, que
codifica tipos BSON/Python não-serializáveis pelo JSON nativo:
  datetime  →  {"$date": "2026-11-15T12:00:00+00:00"}
  ObjectId  →  {"$oid": "507f1f77bcf86cd799439011"}
Usar `json_util.loads` para desserializar garante que os datetimes voltam
como objetos Python `datetime` com timezone UTC — prontos para o SQL Server.

Tabelas geradas
---------------
silver.Meteorologia
    Unifica openmeteo_horario, openmeteo_historico e nasa_power_horario.
    Pressão normalizada para hPa (NASA POWER envia kPa; conversão × 10).
    Chave: (fonte, lida_em).

silver.Arboviroses
    Contagens semanais por bairro de dengue, zika e chikungunya.
    Chave: (territorio, indicador, periodo, bairro).

silver.DefesaCivil
    Atendimentos mensais da Defesa Civil do Recife por tipo e bairro.
    Chave: (territorio, tipo_ocorrencia, periodo, bairro).

silver.AnimaisPerconhentos
    Acidentes semanais com animais peçonhentos em Pernambuco por município.
    Chave: (territorio, municipio, codigo_municipio, periodo).

silver.Estacoes
    Metadados das estações automáticas do INMET em Pernambuco.
    Suporta payload bruto (CD_ESTACAO, VL_LATITUDE …) e normalizado.
    Chave: (fonte, estacao).
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

# json_util do PyMongo: desserializa BSON Extended JSON preservando tipos.
# Necessário porque o bronze armazenou payload_json com json_util.dumps.
from bson import json_util

logger = logging.getLogger(__name__)

# Path para o script DDL silver — calculado dinamicamente.
# parents[2]: silver_pipeline.py → pipelines/ → silver/ → projeto_5/ → sql/silver/
SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "silver" / "001_silver_tables.sql",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _aplicar_ddl(connection, scripts=SQL_SCRIPTS) -> None:
    """Executa os scripts DDL do schema silver de forma idempotente.

    Divide cada arquivo .sql em batches pelo delimitador GO e executa
    um commit por batch. Todos os CREATE TABLE usam `IF OBJECT_ID IS NULL`,
    então re-execuções não falham em tabelas já existentes.

    Por que commit por batch e não um único commit no final?
    DDL no SQL Server tem comportamento transacional limitado — algumas
    operações (CREATE SCHEMA, ALTER TABLE ADD CONSTRAINT) não podem ser
    facilmente desfeitas. Comitar por batch evita deixar o banco em estado
    parcial se um batch falhar no meio.

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.
        scripts: Iterable de paths dos arquivos .sql (padrão: SQL_SCRIPTS).

    Raises:
        Exception: Qualquer erro do driver SQL; faz rollback antes de relançar.
    """
    cursor = connection.cursor()
    try:
        for caminho in scripts:
            script = Path(caminho).read_text(encoding="utf-8")
            # re.split com (?im): case-insensitive + multiline.
            # Aceita "GO", "GO --comentário", "  GO  " como separadores.
            for batch in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script):
                if batch.strip():
                    cursor.execute(batch)
                    connection.commit()
            logger.info("DDL silver aplicado: %s", Path(caminho).name)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _ler_bronze(connection, tabela: str) -> list[dict]:
    """Lê e desserializa os payloads de uma tabela bronze.

    Cada linha da tabela bronze tem uma coluna `payload_json` contendo
    BSON Extended JSON (serializado com `json_util.dumps`). Esta função
    desserializa com `json_util.loads` para recuperar tipos Python corretos,
    inclusive `datetime` com timezone UTC.

    Por que filtramos WHERE payload_json IS NOT NULL?
    Documentos do MongoDB podem não ter campo "payload" — nesse caso,
    o bronze armazena NULL. Sem o filtro, json_util.loads receberia None.

    Payloads inválidos (JSON malformado) são ignorados com aviso em log.

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.
        tabela: Nome completo da tabela bronze (ex.: "bronze.openmeteo_horario").

    Returns:
        Lista de dicts Python, um por documento válido da tabela.
    """
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT payload_json FROM {tabela} WHERE payload_json IS NOT NULL")
        registros = []
        for (payload_json,) in cursor.fetchall():
            try:
                # json_util.loads: converte {"$date": "..."} → datetime Python.
                registros.append(json_util.loads(payload_json))
            except Exception:
                logger.warning("payload_json inválido ignorado em %s", tabela)
        return registros
    finally:
        cursor.close()


# _BATCH_SIZE: tamanho máximo de cada lote para executemany.
# Azure SQL tem timeout em transações com >32k parâmetros em um único executemany.
# Dividir em lotes de 500 resolve o problema observado com sinan_animais_peconhentos
# (que tem ~32.453 documentos no dataset completo de Pernambuco).
_BATCH_SIZE = 500


def _upsert(connection, tabela: str, merge_sql: str, params: list[tuple]) -> int:
    """Insere/atualiza registros em lotes via MERGE idempotente.

    Lotes de _BATCH_SIZE evitam timeout no Azure SQL que ocorre com
    executemany de >32 k linhas em uma única transação (observado em
    sinan_animais_peconhentos com ~32.453 documentos).

    Por que MERGE e não INSERT + UPDATE separados?
    O MERGE é atômico: dentro de uma transação, verifica se a linha existe
    e insere ou atualiza em uma única operação. Sem ele, haveria race condition
    entre o SELECT de verificação e o INSERT subsequente em execuções paralelas.

    Args:
        connection: Conexão pyodbc ativa.
        tabela: Nome da tabela destino (usado apenas para logging).
        merge_sql: Instrução MERGE parametrizada com placeholders `?`.
        params: Lista de tuplas com os valores; uma tupla por linha.

    Returns:
        Número total de linhas processadas em todos os lotes.

    Raises:
        Exception: Erro de banco; faz rollback do lote afetado e relança.
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
    """Converte datetime para string ISO 8601 usada nos parâmetros SQL MERGE.

    Por que converter para string em vez de passar datetime diretamente?
    O mssql-python aceita strings ISO 8601 para colunas DATETIMEOFFSET, mas
    pode não serializar corretamente objetos datetime do PyMongo (que usam
    timezone UTC representado como tzinfo=timezone.utc). Converter explicitamente
    garante o formato correto em qualquer versão do driver.

    Datetimes sem timezone recebem UTC explicitamente antes da conversão,
    pois o SQL Server rejeita strings sem offset para colunas DATETIMEOFFSET.

    Args:
        valor: datetime, str ou None.

    Returns:
        String ISO 8601 com offset (ex.: "2026-11-15T12:00:00+00:00") ou None.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        # Garante timezone UTC para datetimes naive (sem tz).
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.isoformat()
    return str(valor)


# ---------------------------------------------------------------------------
# Meteorologia (openmeteo_horario + openmeteo_historico + nasa_power_horario)
# ---------------------------------------------------------------------------

# Template MERGE para silver.Meteorologia.
# WHEN NOT MATCHED: insere novas leituras.
# WHEN MATCHED UPDATE: atualiza valores se a API corrigiu dados históricos
# (ex: ERA5 republicado com valores corrigidos).
_MERGE_MET = """\
MERGE silver.Meteorologia WITH (HOLDLOCK) AS tgt
USING (VALUES (
    ?, ?, ?,
    CONVERT(datetimeoffset(6), ?),
    ?, ?, ?, ?, ?, ?, ?, ?,
    CONVERT(datetimeoffset(6), ?)
)) AS src (fonte, estacao, territorio, lida_em, natureza_dado,
           temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
           vento_ms, latitude, longitude, atualizado_em)
ON tgt.fonte = src.fonte AND tgt.lida_em = src.lida_em
WHEN NOT MATCHED THEN
    INSERT (fonte, estacao, territorio, lida_em, natureza_dado,
            temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
            vento_ms, latitude, longitude, atualizado_em)
    VALUES (src.fonte, src.estacao, src.territorio, src.lida_em, src.natureza_dado,
            src.temperatura_c, src.precipitacao_mm, src.umidade_pct, src.pressao_hpa,
            src.vento_ms, src.latitude, src.longitude, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    temperatura_c   = src.temperatura_c,
    precipitacao_mm = src.precipitacao_mm,
    umidade_pct     = src.umidade_pct,
    pressao_hpa     = src.pressao_hpa,
    vento_ms        = src.vento_ms,
    atualizado_em   = src.atualizado_em;
"""


def _linha_meteorologia(p: dict, agora: str) -> tuple | None:
    """Extrai e normaliza os campos de um payload de meteorologia.

    Responsabilidade central desta função: conversão de pressão.
    - Open-Meteo e INMET retornam pressão em hPa (hectopascal).
    - NASA POWER retorna em kPa (kilopascal) com campo "pressao_kpa".
    A camada silver normaliza tudo para hPa: pressao_kpa × 10 = pressao_hpa.
    O dado bruto em kPa é preservado no bronze/MongoDB para auditoria.

    Returns:
        Tupla com 13 valores para o MERGE_MET, ou None se fonte/lida_em ausentes.
    """
    variaveis = p.get("variaveis") or {}
    lida_em   = _ts(p.get("lida_em"))
    fonte     = p.get("fonte") or ""

    # Descarta registros sem os campos obrigatórios para a chave de idempotência.
    if not lida_em or not fonte:
        return None

    # Normalização de pressão: hPa tem prioridade; kPa como fallback com conversão.
    pressao = variaveis.get("pressao_hpa")
    if pressao is None and variaveis.get("pressao_kpa") is not None:
        # NASA POWER envia kPa; multiplicar por 10 converte para hPa.
        pressao = variaveis["pressao_kpa"] * 10

    return (
        fonte,
        p.get("estacao") or "",
        p.get("territorio") or "Recife",
        lida_em,
        p.get("natureza_dado"),    # "previsao", "reanalisado_era5", "observado", etc.
        variaveis.get("temperatura_c"),
        variaveis.get("precipitacao_mm"),
        variaveis.get("umidade_pct"),
        pressao,                   # já normalizado para hPa
        variaveis.get("vento_ms"),
        p.get("latitude"),
        p.get("longitude"),
        agora,                     # atualizado_em: timestamp desta execução
    )


def processar_meteorologia(connection) -> dict:
    """Lê as três fontes climáticas do bronze e persiste em silver.Meteorologia.

    Unifica openmeteo_horario, openmeteo_historico e nasa_power_horario em
    uma única tabela silver com schema normalizado. A chave (fonte, lida_em)
    garante que cada horário de cada fonte seja único — sem duplicatas mesmo
    que as janelas de coleta se sobreponham entre execuções.

    Por que uma única tabela para três fontes?
    O app consome dados climáticos de qualquer fonte. Uma tabela unificada
    simplifica queries no app: não precisa de UNION entre três tabelas.
    A coluna `fonte` permite filtrar por origem quando necessário.
    """
    agora = datetime.now(timezone.utc).isoformat()
    # Lê as três fontes bronze — iteração sobre lista de tabelas para DRY.
    tabelas = [
        "bronze.openmeteo_horario",
        "bronze.openmeteo_historico",
        "bronze.nasa_power_horario",
    ]
    params = []
    for tabela in tabelas:
        for p in _ler_bronze(connection, tabela):
            linha = _linha_meteorologia(p, agora)
            if linha:
                params.append(linha)

    inseridos = _upsert(connection, "silver.Meteorologia", _MERGE_MET, params)
    logger.info("silver.Meteorologia: %d linhas processadas", inseridos)
    return {"tabela": "silver.Meteorologia", "processados": inseridos}


# ---------------------------------------------------------------------------
# Arboviroses (recife_arboviroses)
# ---------------------------------------------------------------------------

# MERGE para silver.Arboviroses.
# WHEN MATCHED UPDATE: atualiza contagem se novos registros chegaram do CKAN.
_MERGE_ARB = """\
MERGE silver.Arboviroses WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, indicador, periodo, casos, atualizado_em)
ON  tgt.territorio = src.territorio
AND tgt.indicador  = src.indicador
AND tgt.periodo    = src.periodo
AND tgt.bairro     = src.bairro
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, indicador, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.bairro, src.indicador, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_arboviroses(connection) -> dict:
    """Transforma contagens de arboviroses do bronze para silver.Arboviroses.

    Os dados já chegam agregados do MongoDB (contagem por bairro/semana/agravo)
    — não há transformação de granularidade aqui. A silver apenas:
    - Valida campos obrigatórios (indicador, periodo).
    - Aplica int() em valor para garantir tipo INTEGER no SQL.
    - Registra via MERGE com chave (territorio, indicador, periodo, bairro).
    """
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.recife_arboviroses"):
        indicador = p.get("indicador") or ""
        periodo   = p.get("periodo") or ""
        # Descarta registros sem os campos que compõem a chave de negócio.
        if not indicador or not periodo:
            continue
        params.append((
            p.get("territorio") or "Recife",
            p.get("bairro") or "nao_informado",
            indicador,
            periodo,
            int(p.get("valor") or 0),  # garante INTEGER mesmo se vier como float
            agora,
        ))

    inseridos = _upsert(connection, "silver.Arboviroses", _MERGE_ARB, params)
    logger.info("silver.Arboviroses: %d linhas processadas", inseridos)
    return {"tabela": "silver.Arboviroses", "processados": inseridos}


# ---------------------------------------------------------------------------
# Defesa Civil (recife_defesa_civil)
# ---------------------------------------------------------------------------

_MERGE_DC = """\
MERGE silver.DefesaCivil WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, tipo_ocorrencia, periodo, casos, atualizado_em)
ON  tgt.territorio      = src.territorio
AND tgt.tipo_ocorrencia = src.tipo_ocorrencia
AND tgt.periodo         = src.periodo
AND tgt.bairro          = src.bairro
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, tipo_ocorrencia, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.bairro, src.tipo_ocorrencia, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_defesa_civil(connection) -> dict:
    """Transforma atendimentos da Defesa Civil do bronze para silver.DefesaCivil.

    Mesmo padrão de arboviroses: dados já agregados no MongoDB.
    Chave: (territorio, tipo_ocorrencia, periodo, bairro).
    tipo_ocorrencia representa o tipo de desastre (ex: "Alagamento", "Deslizamento").
    periodo está no formato YYYY-MM (mensal, granularidade do dataset CKAN).
    """
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.recife_defesa_civil"):
        tipo    = p.get("tipo_ocorrencia") or ""
        periodo = p.get("periodo") or ""
        if not tipo or not periodo:
            continue
        params.append((
            p.get("territorio") or "Recife",
            p.get("bairro") or "nao_informado",
            tipo,
            periodo,
            int(p.get("valor") or 0),
            agora,
        ))

    inseridos = _upsert(connection, "silver.DefesaCivil", _MERGE_DC, params)
    logger.info("silver.DefesaCivil: %d linhas processadas", inseridos)
    return {"tabela": "silver.DefesaCivil", "processados": inseridos}


# ---------------------------------------------------------------------------
# Animais Peçonhentos (sinan_animais_peconhentos)
# ---------------------------------------------------------------------------

_MERGE_ANI = """\
MERGE silver.AnimaisPerconhentos WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, municipio, codigo_municipio, periodo, casos, atualizado_em)
ON  tgt.territorio       = src.territorio
AND tgt.municipio        = src.municipio
AND tgt.codigo_municipio = src.codigo_municipio
AND tgt.periodo          = src.periodo
WHEN NOT MATCHED THEN
    INSERT (territorio, municipio, codigo_municipio, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.municipio, src.codigo_municipio, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_animais_peconhentos(connection) -> dict:
    """Transforma acidentes SINAN do bronze para silver.AnimaisPerconhentos.

    Dados já agregados por município/semana. A chave inclui codigo_municipio
    (código IBGE 7 dígitos) além do nome, pois o nome pode ter variações de
    grafia entre versões do SINAN. O código é mais estável para JOINs.
    """
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.sinan_animais_peconhentos"):
        periodo = p.get("periodo") or ""
        if not periodo:
            continue  # registro sem semana epidemiológica é descartado
        params.append((
            p.get("territorio") or "Pernambuco",
            p.get("municipio") or "nao_informado",
            p.get("codigo_municipio") or "nao_informado",
            periodo,
            int(p.get("valor") or 0),
            agora,
        ))

    inseridos = _upsert(connection, "silver.AnimaisPerconhentos", _MERGE_ANI, params)
    logger.info("silver.AnimaisPerconhentos: %d linhas processadas", inseridos)
    return {"tabela": "silver.AnimaisPerconhentos", "processados": inseridos}


# ---------------------------------------------------------------------------
# Estações (inmet_estacoes)
# ---------------------------------------------------------------------------

# MERGE para silver.Estacoes.
# WHEN MATCHED UPDATE: atualiza coordenadas/nome se o INMET corrigir metadados.
_MERGE_EST = """\
MERGE silver.Estacoes WITH (HOLDLOCK) AS tgt
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


def _para_float(valor) -> float | None:
    """Converte string ou número para float, retornando None em caso de falha.

    Necessário porque os payloads brutos do INMET têm VL_LATITUDE como
    string ("-8.0597") e os payloads normalizados têm latitude como float.
    float(str) funciona para ambos; ValueError/TypeError capturam casos inválidos.
    """
    if valor is None:
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def processar_estacoes(connection) -> dict:
    """Transforma metadados de estações INMET do bronze para silver.Estacoes.

    Estratégia de duplo fallback para nomes de campo:
    O INMET mudou os nomes dos campos entre versões da API. Payloads coletados
    antes da normalização usam os nomes originais (CD_ESTACAO, VL_LATITUDE);
    payloads mais recentes usam os aliases normalizados (estacao, latitude).
    A cadeia de or garante compatibilidade com ambos os formatos.

    Por que `_para_float` para lat/lon?
    VL_LATITUDE no payload bruto é string ("-8.0597"). O MERGE SQL precisa de
    FLOAT para a coluna latitude. float("−8.0597") converte corretamente.
    """
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.inmet_estacoes"):
        # Fallback: tenta campo normalizado primeiro, depois campo bruto do INMET.
        estacao = p.get("estacao") or p.get("CD_ESTACAO") or p.get("CD_WSI") or ""
        if not estacao:
            continue  # estação sem código é inidentificável
        nome = p.get("nome") or p.get("DC_NOME")
        municipio = (
            p.get("municipio")
            or p.get("NM_MUNICIPIO")   # payload normalizado
            or p.get("DC_MUNICIPIO")   # payload bruto versão 1
            or p.get("SG_ESTADO")      # fallback para sigla do estado
        )
        # _para_float: suporta tanto float (payload normalizado) como string (bruto).
        lat = _para_float(p.get("latitude") or p.get("VL_LATITUDE"))
        lon = _para_float(p.get("longitude") or p.get("VL_LONGITUDE"))
        situacao = p.get("situacao") or p.get("CD_SITUACAO")
        params.append((
            p.get("fonte") or "inmet",
            estacao,
            nome,
            municipio,
            lat,
            lon,
            situacao,
            agora,
        ))

    inseridos = _upsert(connection, "silver.Estacoes", _MERGE_EST, params)
    logger.info("silver.Estacoes: %d linhas processadas", inseridos)
    return {"tabela": "silver.Estacoes", "processados": inseridos}


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def silver_pipeline(connection=None, aplicar_ddl: bool = True) -> list[dict]:
    """Orquestra a transformação bronze → silver para todas as fontes.

    Falhas em processadores individuais são capturadas e registradas em log;
    as demais fontes continuam sendo processadas. Isso evita que um problema
    pontual (ex.: schema de API alterado em uma fonte) bloqueie toda a pipeline.

    Por que importação local de conectar_sql_server?
    Evita importação circular no nível do módulo: silver_pipeline importaria
    conectar_sql_server, que poderia importar de volta silver.pipelines.

    Args:
        connection: Conexão pyodbc pré-existente; se None, abre e fecha
            automaticamente uma nova conexão via `conectar_sql_server`.
        aplicar_ddl: Se True, executa os scripts DDL do schema silver antes
            de processar (cria tabelas se não existirem).

    Returns:
        Lista de dicts, um por processador, com chaves:
            - "tabela" (str): nome da tabela silver.
            - "processados" (int): linhas inseridas/atualizadas.
            - "erro" (str, opcional): mensagem de erro se o processador falhou.
    """
    from silver.database.sql_server import conectar_sql_server

    # owns: controla se este pipeline fecha a conexão no finally.
    owns = connection is None
    if owns:
        connection = conectar_sql_server()

    try:
        if aplicar_ddl:
            # Cria schema silver e tabelas se ainda não existirem.
            # Idempotente: safe re-executar em cada run.
            _aplicar_ddl(connection)

        # Lista de processadores na ordem de dependência lógica.
        # Meteorologia primeiro (mais linhas, maior chance de lote lento).
        fontes = [
            processar_meteorologia,
            processar_arboviroses,
            processar_defesa_civil,
            processar_animais_peconhentos,
            processar_estacoes,
        ]
        resultados = []
        for fn in fontes:
            try:
                resultados.append(fn(connection))
            except Exception as erro:
                # Captura falha isolada: registra e continua com o próximo processador.
                logger.error("Falha em %s: %s", getattr(fn, "__name__", repr(fn)), type(erro).__name__)
                resultados.append({
                    "tabela":      getattr(fn, "__name__", repr(fn)),
                    "processados": 0,
                    "erro":        str(erro),
                })

        total = sum(r.get("processados", 0) for r in resultados)
        logger.info("Pipeline Silver concluído: %d linhas no total", total)
        return resultados
    finally:
        # Fecha a conexão somente se foi aberta por este pipeline.
        if owns:
            connection.close()
