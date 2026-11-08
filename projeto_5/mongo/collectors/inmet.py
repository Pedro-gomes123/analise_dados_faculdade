"""Coleta estações e observações da API oficial do INMET."""

import logging
from datetime import date, timedelta

from mongo.config import ESTACAO_RECIFE, INMET_BASE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import (
    get,
    para_numero,
    primeiro_valor,
    salvar_json_local,
    utc_datetime,
)

logger = logging.getLogger(__name__)


def _normalizar_estacao(estacao):
    """Mantém todos os campos INMET e inclui os campos comuns da estação."""
    return {
        **estacao,
        "fonte": "inmet",
        "estacao": primeiro_valor(estacao, "CD_ESTACAO", "CD_WSI"),
        "nome": primeiro_valor(estacao, "DC_NOME", "DC_NOME_ESTACAO"),
        "municipio": primeiro_valor(
            estacao, "NM_MUNICIPIO", "DC_MUNICIPIO", "MUNICIPIO", "municipio"
        ),
        "latitude": para_numero(primeiro_valor(estacao, "VL_LATITUDE")),
        "longitude": para_numero(primeiro_valor(estacao, "VL_LONGITUDE")),
        "situacao": primeiro_valor(estacao, "CD_SITUACAO", "situacao"),
    }


def _normalizar_observacao(registro, codigo_estacao):
    """Normaliza data e variáveis, preservando integralmente o retorno do INMET."""
    data_hora = utc_datetime(
        primeiro_valor(registro, "DT_MEDICAO", "data", "data_hora"),
        primeiro_valor(registro, "HR_MEDICAO", "hora"),
    )
    if data_hora is None:
        return None

    variaveis = {
        "precipitacao_mm": para_numero(primeiro_valor(
            registro, "CHUVA", "PRECIPITACAO_TOTAL", "PRECIPITACAO", "precipitacao_mm"
        )),
        "temperatura_c": para_numero(primeiro_valor(
            registro, "TEMP_INS", "TEM_INS", "TEMP_AR", "TEMPERATURA", "temperatura_c"
        )),
        "umidade_pct": para_numero(primeiro_valor(
            registro, "UMD_INS", "UMID_REL", "UMIDADE", "umidade_pct"
        )),
        "pressao_hpa": para_numero(primeiro_valor(
            registro, "PRE_INS", "PRESSAO_ATMOSFERICA", "PRESSAO", "pressao_hpa"
        )),
    }
    return {
        **registro,
        "fonte": "inmet",
        "estacao": primeiro_valor(registro, "CD_ESTACAO") or codigo_estacao,
        "territorio": "Recife",
        "lida_em": data_hora,
        "natureza_dado": "observado",
        "variaveis": variaveis,
    }


def pipeline_inmet(db):
    """Coleta estações de PE e as observações recentes da A301."""
    logger.info("Iniciando pipeline INMET")

    resposta = get(f"{INMET_BASE}/estacoes/T")
    estacoes = resposta.json()
    if not isinstance(estacoes, list):
        raise RuntimeError("A API do INMET não retornou uma lista de estações.")
    estacoes_pe = []
    for estacao in estacoes:
        if not isinstance(estacao, dict):
            continue
        if str(estacao.get("SG_ESTADO", "")).strip().upper() != "PE":
            continue
        normalizada = _normalizar_estacao(estacao)
        if normalizada["estacao"]:
            estacoes_pe.append(normalizada)
    if not estacoes_pe:
        raise RuntimeError("A API do INMET não retornou estações de Pernambuco.")
    salvar_json_local("inmet_estacoes", estacoes_pe)

    carregar_documentos(
        db["inmet_estacoes"],
        "inmet",
        estacoes_pe,
        "estacao_automatica",
        "Pernambuco",
        campos_chave=("estacao",),
    )

    fim = date.today()
    inicio = fim - timedelta(days=2)
    url = (
        f"{INMET_BASE}/estacao/{inicio.isoformat()}/"
        f"{fim.isoformat()}/{ESTACAO_RECIFE}"
    )
    resposta_dados = get(url)
    if resposta_dados.status_code == 204 or not resposta_dados.content:
        logger.warning(
            "INMET sem observações para %s entre %s e %s.",
            ESTACAO_RECIFE,
            inicio,
            fim,
        )
        return

    dados = resposta_dados.json()
    salvar_json_local(f"inmet_{ESTACAO_RECIFE}", dados)
    if isinstance(dados, dict):
        registros = [dados]
    elif isinstance(dados, list):
        registros = dados
    else:
        raise RuntimeError("A API do INMET retornou observações em formato inválido.")

    normalizados = [
        observacao
        for registro in registros
        if isinstance(registro, dict)
        for observacao in [_normalizar_observacao(registro, ESTACAO_RECIFE)]
        if observacao is not None
    ]
    if not normalizados:
        raise RuntimeError(
            f"INMET retornou observações sem data/hora válida para {ESTACAO_RECIFE}."
        )

    carregar_documentos(
        db["inmet_observacoes"],
        "inmet",
        normalizados,
        "observacao_horaria",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline INMET concluído")
