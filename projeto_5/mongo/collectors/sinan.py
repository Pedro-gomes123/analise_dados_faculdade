"""Coleta SINAN ANIM e persiste somente contagens agregadas de Pernambuco."""

import logging
import re
from collections import defaultdict
from datetime import date, datetime

from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, salvar_json_local

logger = logging.getLogger(__name__)


def _texto(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.casefold() in {"", "nan", "none", "nat"} else texto


def _eh_pernambuco(valor):
    texto = _texto(valor).upper()
    return texto in {"PE", "PERNAMBUCO", "26", "26.0"}


def _periodo_semana(registro):
    semana = _texto(registro.get("SEM_NOT") or registro.get("SEM_PRI"))
    ano = _texto(registro.get("NU_ANO"))
    numeros = re.sub(r"\D", "", semana)
    try:
        if len(numeros) >= 6:
            return f"{numeros[:4]}-W{int(numeros[-2:]):02d}"
        if numeros and ano:
            return f"{int(float(ano)):04d}-W{int(float(numeros)):02d}"
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
    """Agrega casos por semana e município, descartando campos individuais."""
    grupos = defaultdict(lambda: {"ids": set(), "sem_id": 0})
    for registro in registros:
        uf = registro.get("SG_UF_NOT") or registro.get("SG_UF")
        if not _eh_pernambuco(uf):
            continue
        periodo = _periodo_semana(registro)
        if not periodo:
            continue
        codigo = _texto(registro.get("ID_MUNICIP") or registro.get("ID_MN_RESI"))
        nome = _texto(registro.get("NM_MUNICIP") or registro.get("MUNICIPIO"))
        municipio = nome or (f"codigo:{codigo}" if codigo else "nao_informado")
        chave = (periodo, municipio, codigo)
        notificacao = _texto(registro.get("NU_NOTIFIC"))
        if notificacao:
            grupos[chave]["ids"].add(notificacao)
        else:
            grupos[chave]["sem_id"] += 1

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
    """Baixa o ano anterior, filtra PE e grava estatísticas sem notificações pessoais."""
    logger.info("Iniciando pipeline PySUS / SINAN")
    try:
        import pysus
    except ImportError as erro:
        raise RuntimeError(
            "PySUS não está instalado. Instale mongo/requirements.txt."
        ) from erro

    ano = date.today().year - 1
    logger.info("Consultando SINAN ANIM, ano %d", ano)
    try:
        df = pysus.ftp.sinan(disease="ANIM", year=ano, as_dataframe=True)
    except Exception as erro:
        raise RuntimeError(f"Falha na consulta PySUS SINAN ANIM: {type(erro).__name__}") from erro
    if df is None or df.empty:
        raise RuntimeError(f"SINAN ANIM não retornou registros para {ano}.")

    colunas = {str(col).upper() for col in df.columns}
    if not ({"SG_UF_NOT", "SG_UF"} & colunas):
        raise RuntimeError(
            "SINAN retornou dados sem campo de UF; interrompido para não gravar "
            "notificações nacionais como se fossem de Pernambuco."
        )
    agregados = agregar_sinan_pernambuco(dataframe_para_registros(df))
    if not agregados:
        raise RuntimeError(
            f"SINAN ANIM não retornou contagens agregáveis de Pernambuco para {ano}."
        )

    salvar_json_local("pysus_animais_peconhentos_agregados", agregados)
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
