"""Coleta SINAN ANIM (acidentes com animais peçonhentos) e persiste somente contagens agregadas.

Por que PySUS/SINAN?
- O SINAN (Sistema de Informação de Agravos de Notificação) é a base oficial
  de dados epidemiológicos do Ministério da Saúde. É a única fonte confiável
  de notificações de acidentes com animais peçonhentos em Pernambuco.
- PySUS é uma biblioteca Python open-source que abstrai o acesso ao FTP do
  DATASUS, evitando manipulação manual de arquivos DBC/DBF binários.

Por que armazenar apenas contagens (agregadas), não registros individuais?
- LGPD (Lei Geral de Proteção de Dados): os dados do SINAN contêm informações
  pessoais de saúde (nome, endereço, CPF). O projeto não precisa de dados
  individuais — apenas contagens por semana e município para análise epidemiológica.
- Agregar antes de persistir é mais seguro e reduz drasticamente o volume
  armazenado (de 275.000 linhas para ~4.400 grupos agregados).
"""

import logging
import re
# defaultdict: acumula contagens sem precisar verificar se a chave existe.
# Mais limpo que verificar "if chave in dict" a cada iteração.
from collections import defaultdict
from datetime import date, datetime

from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, salvar_json_local

logger = logging.getLogger(__name__)


def _texto(valor):
    """Normaliza qualquer valor para string limpa, retornando '' para nulos.

    Lida com os valores especiais que o pandas/NumPy gera ao ler arquivos
    DBC: "nan", "none", "nat" (Not a Time) representam ausência de dado.
    """
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.casefold() in {"", "nan", "none", "nat"} else texto


def _eh_pernambuco(valor):
    """Verifica se o registro pertence ao estado de Pernambuco.

    O campo SG_UF no SINAN pode estar em vários formatos: sigla "PE",
    nome por extenso "PERNAMBUCO", código IBGE "26" ou "26.0".
    Verifica todos para não descartar registros válidos.
    """
    texto = _texto(valor).upper()
    return texto in {"PE", "PERNAMBUCO", "26", "26.0"}


def _periodo_semana(registro):
    """Extrai o período em formato ISO 8601 "YYYY-WNN" a partir de campos SINAN.

    O SINAN usa três campos diferentes para indicar semana:
    - SEM_NOT: semana de notificação (preferencial)
    - SEM_PRI: semana dos primeiros sintomas (fallback)
    - DT_NOTIFIC: data de notificação (fallback final, calculamos a semana ISO)

    O formato "YYYY-WNN" (ex: "2026-W44") é o padrão ISO 8601 e permite
    agrupar e ordenar semanas epidemiológicas de forma consistente.
    """
    semana = _texto(registro.get("SEM_NOT") or registro.get("SEM_PRI"))
    ano = _texto(registro.get("NU_ANO"))
    # re.sub remove qualquer caractere não-numérico do campo de semana,
    # pois o SINAN às vezes inclui prefixos de ano ("202644" = semana 44 de 2026).
    numeros = re.sub(r"\D", "", semana)
    try:
        # Formato "YYYYWW" (6+ dígitos): ex "202644" → "2026-W44"
        if len(numeros) >= 6:
            return f"{numeros[:4]}-W{int(numeros[-2:]):02d}"
        # Formato com ano separado: ex semana="44", ano="2026" → "2026-W44"
        if numeros and ano:
            return f"{int(float(ano)):04d}-W{int(float(numeros)):02d}"
        # Fallback: calcula semana ISO a partir da data de notificação.
        data = _texto(registro.get("DT_NOTIFIC"))
        for formato in ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"):
            try:
                dt = datetime.strptime(data, formato)
                iso = dt.isocalendar()
                return f"{iso.year:04d}-W{iso.week:02d}"
            except ValueError:
                pass
    except (ValueError, OverflowError):
        return None
    return None


def agregar_sinan_pernambuco(registros):
    """Agrega casos por semana epidemiológica e município, descartando dados pessoais.

    Por que usar NU_NOTIFIC para deduplicar?
    O SINAN pode conter duplicatas do mesmo caso (atualizações de ficha).
    Usar o número de notificação como chave de deduplicação conta cada caso
    apenas uma vez por município/semana, mesmo com múltiplas entradas.

    Por que defaultdict com {"ids": set, "sem_id": int}?
    - "ids": conjunto de números de notificação únicos — deduplicação automática.
    - "sem_id": contador de registros sem número de notificação (devem ser contados
      separadamente pois não podem ser deduplicados).
    """
    grupos = defaultdict(lambda: {"ids": set(), "sem_id": 0})
    for registro in registros:
        # Filtra apenas Pernambuco — o dataset nacional tem 300k+ registros.
        # Se o campo UF não existir, interrompemos no pipeline_sinan (guarda de segurança).
        uf = registro.get("SG_UF_NOT") or registro.get("SG_UF")
        if not _eh_pernambuco(uf):
            continue

        periodo = _periodo_semana(registro)
        if not periodo:
            continue  # registro sem data válida é descartado

        # Código IBGE do município (7 dígitos) e nome para identificação.
        codigo = _texto(registro.get("ID_MUNICIP") or registro.get("ID_MN_RESI"))
        nome   = _texto(registro.get("NM_MUNICIP") or registro.get("MUNICIPIO"))
        municipio = nome or (f"codigo:{codigo}" if codigo else "nao_informado")

        chave = (periodo, municipio, codigo)

        # Se tiver número de notificação, adiciona ao set (deduplicação automática).
        # Se não tiver, incrementa o contador separado.
        notificacao = _texto(registro.get("NU_NOTIFIC"))
        if notificacao:
            grupos[chave]["ids"].add(notificacao)
        else:
            grupos[chave]["sem_id"] += 1

    # Contagem final: únicos identificados + registros sem ID.
    return [
        {
            "territorio": "Pernambuco",
            "municipio": municipio,
            "codigo_municipio": codigo or "nao_informado",
            "indicador": "acidentes_animais_peconhentos",
            "periodo": periodo,
            "valor": len(contagem["ids"]) + contagem["sem_id"],
        }
        for (periodo, municipio, codigo), contagem in sorted(grupos.items())
    ]


def pipeline_sinan(db):
    """Baixa o SINAN ANIM do ano mais recente disponível, filtra PE e grava estatísticas.

    Por que tentar o ano corrente primeiro?
    O DATASUS publica arquivos DBC por ano. Em novembro de 2026, o arquivo
    ANIMBR26.parquet já estava disponível com 275.162 registros. Tentar o
    ano corrente primeiro evita trabalhar sempre com dados do ano anterior.

    Guarda de segurança (campo UF obrigatório):
    Se o SINAN retornar dados sem o campo de UF (SG_UF_NOT ou SG_UF), não
    conseguimos filtrar por Pernambuco e correríamos o risco de gravar dados
    nacionais como se fossem estaduais. O pipeline aborta nesse caso.
    """
    logger.info("Iniciando pipeline PySUS / SINAN")

    # pysus: biblioteca Python para acesso a dados do DATASUS via FTP.
    # Importação local para falha clara se não estiver instalada.
    try:
        import pysus
    except ImportError as erro:
        raise RuntimeError(
            "PySUS não está instalado. Instale mongo/requirements.txt."
        ) from erro

    # Tenta o ano corrente; recua para o anterior se o arquivo ainda não
    # foi publicado no FTP do DATASUS (publicação com meses de atraso).
    ano_atual = date.today().year
    df = None
    ano = ano_atual
    for candidato in (ano_atual, ano_atual - 1):
        logger.info("Consultando SINAN ANIM, ano %d", candidato)
        try:
            # pysus.ftp.sinan baixa e converte o arquivo DBC para DataFrame pandas.
            # as_dataframe=True retorna um DataFrame ao invés de um arquivo local.
            resultado = pysus.ftp.sinan(disease="ANIM", year=candidato, as_dataframe=True)
            if resultado is not None and not resultado.empty:
                df = resultado
                ano = candidato
                break
        except Exception as erro:
            logger.warning(
                "SINAN ANIM indisponível para %d (%s), tentando ano anterior.",
                candidato, type(erro).__name__
            )

    if df is None or df.empty:
        raise RuntimeError(
            f"SINAN ANIM não retornou registros para {ano_atual} nem {ano_atual - 1}."
        )

    # Verifica se o campo de UF está presente antes de filtrar.
    # str(col).upper() normaliza nomes de coluna que podem vir em caixa mista.
    colunas = {str(col).upper() for col in df.columns}
    if not ({"SG_UF_NOT", "SG_UF"} & colunas):
        raise RuntimeError(
            "SINAN retornou dados sem campo de UF; interrompido para não gravar "
            "notificações nacionais como se fossem de Pernambuco."
        )

    # dataframe_para_registros: converte DataFrame para lista de dicts normalizados,
    # tratando NaN/NaT do pandas que o MongoDB não aceita diretamente.
    agregados = agregar_sinan_pernambuco(dataframe_para_registros(df))
    if not agregados:
        raise RuntimeError(
            f"SINAN ANIM não retornou contagens agregáveis de Pernambuco para {ano}."
        )

    salvar_json_local("pysus_animais_peconhentos_agregados", agregados)

    # Chave de idempotência: (indicador, periodo, municipio, codigo_municipio).
    # O indicador é fixo ("acidentes_animais_peconhentos"), então a combinação
    # municipio + código + semana identifica unicamente cada contagem.
    carregar_documentos(
        db["sinan_animais_peconhentos"],
        "pysus_sinan",
        agregados,
        "acidentes_animais_peconhentos_agregados_semanais",
        "Pernambuco",
        campos_chave=("indicador", "periodo", "municipio", "codigo_municipio"),
    )
    logger.info(
        "SINAN ANIM concluído: %d grupos agregados de %d linhas recebidas.",
        len(agregados), len(df),
    )
