"""Coleta dados de desastres do CKAN federal sem misturar geografias."""

import logging
from io import BytesIO, StringIO

import pandas as pd

from mongo.config import CKAN_GOV
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, get, salvar_json_local

logger = logging.getLogger(__name__)


def _uf_pernambuco(valor):
    texto = str(valor or "").strip().upper()
    return texto in {"PE", "PERNAMBUCO", "26", "26.0"}


def _filtrar_pernambuco(registros):
    if not registros:
        return []
    aliases = {str(chave).strip().casefold(): chave for chave in registros[0]}
    coluna_uf = next(
        (aliases[chave] for chave in ("uf", "estado", "sg_uf", "uf_ocorrencia") if chave in aliases),
        None,
    )
    if coluna_uf is None:
        return []
    return [registro for registro in registros if _uf_pernambuco(registro.get(coluna_uf))]


def _ler_recurso(resposta, formato):
    if formato == "CSV":
        try:
            conteudo = resposta.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            conteudo = resposta.content.decode("latin-1")
        df = pd.read_csv(StringIO(conteudo), sep=None, engine="python")
        return dataframe_para_registros(df)
    if formato == "XLSX":
        df = pd.read_excel(BytesIO(resposta.content))
        return dataframe_para_registros(df)
    conteudo = resposta.json()
    if isinstance(conteudo, list):
        return [item for item in conteudo if isinstance(item, dict)]
    if isinstance(conteudo, dict):
        for chave in ("result", "records", "data"):
            if isinstance(conteudo.get(chave), list):
                return [item for item in conteudo[chave] if isinstance(item, dict)]
        return [conteudo]
    return []


def pipeline_s2id(db):
    """Busca recursos e salva apenas registros com UF explicitamente PE."""
    logger.info("Iniciando pipeline S2ID / dados.gov.br")
    termos = ("s2id desastre", "calamidade publica", "defesa civil emergencia")
    encontrados = {}
    for termo in termos:
        resposta = get(
            f"{CKAN_GOV}/action/package_search",
            params={"q": termo, "rows": 10},
        )
        resultado = resposta.json()
        if not resultado.get("success"):
            logger.warning("CKAN federal não confirmou busca do termo %r", termo)
            continue
        for dataset in resultado.get("result", {}).get("results", []):
            if dataset.get("id"):
                encontrados[dataset["id"]] = dataset

    for dataset in encontrados.values():
        for recurso in dataset.get("resources", []):
            formato = str(recurso.get("format") or "").strip().upper()
            if formato not in {"CSV", "JSON", "XLSX"} or not recurso.get("url"):
                continue
            try:
                linhas = _ler_recurso(get(recurso["url"]), formato)
                registros_pe = _filtrar_pernambuco(linhas)
            except Exception as erro:
                logger.error(
                    "Falha ao ler recurso S2ID dataset=%s recurso=%s tipo=%s",
                    dataset.get("id"), recurso.get("name"), type(erro).__name__,
                )
                continue
            if not registros_pe:
                logger.info(
                    "Recurso S2ID ignorado: sem UF explícita PE ou sem registros PE (%s)",
                    recurso.get("name"),
                )
                continue
            for registro in registros_pe:
                registro["_dataset_id"] = dataset.get("id")
                registro["_dataset_titulo"] = dataset.get("title")
                registro["_recurso_nome"] = recurso.get("name")
            salvar_json_local("s2id_desastres", registros_pe)
            carregar_documentos(
                db["s2id_desastres"],
                "dados_gov_s2id",
                registros_pe,
                "desastres",
                "Pernambuco",
            )
            logger.info("S2ID concluído: %d registros PE", len(registros_pe))
            return

    raise RuntimeError(
        "Não foi encontrado recurso de desastres que permita identificar "
        "explicitamente os registros de Pernambuco. Nenhum dado foi salvo."
    )
