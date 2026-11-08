"""Coleta e agrega notificações de arboviroses do portal Dados Abertos Recife."""

import logging
import re
from collections import defaultdict
from datetime import datetime
from io import StringIO

import pandas as pd

from mongo.config import CKAN_RECIFE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, get, salvar_json_local

logger = logging.getLogger(__name__)


def _valor(registro, *nomes):
    chaves = {str(chave).strip().lower(): chave for chave in registro}
    for nome in nomes:
        chave = chaves.get(nome.lower())
        if chave is not None:
            valor = registro.get(chave)
            if valor is not None and str(valor).strip() not in {"", "nan", "None"}:
                return valor
    return None


def _recife(registro):
    municipio = str(_valor(registro, "MUNICIPIO", "NM_MUNICIP", "municipio") or "").strip()
    codigo = re.sub(r"\D", "", str(_valor(
        registro, "ID_MUNICIP", "CO_MUN_NOT", "COD_MUNICIPIO"
    ) or "").split(".")[0])
    uf = str(_valor(registro, "SG_UF_NOT", "SG_UF", "UF") or "").strip().upper()
    codigo_recife = codigo in {"261160", "2611606"}
    nome_recife = municipio.casefold() in {"recife", "recife - pe"}
    uf_pe = uf in {"PE", "26", "PERNAMBUCO"}
    # O código municipal é suficiente; quando existe UF/texto, ambos devem
    # concordar para evitar aceitar registros homônimos ou códigos malformados.
    return (codigo_recife or nome_recife) and (not uf or uf_pe) and (
        not municipio or nome_recife or codigo_recife
    )


def _agravo(registro):
    codigo = str(_valor(registro, "ID_AGRAVO", "agravo") or "").strip().upper()
    codigo = re.sub(r"\s+", "", codigo)
    mapeamento = {
        "A90": "dengue",
        "A91": "dengue",
        "A92.0": "chikungunya",
        "U06.9": "zika",
    }
    if codigo in mapeamento:
        return mapeamento[codigo]
    texto = codigo.casefold()
    for chave in ("dengue", "zika", "chikungunya", "chik"): 
        if chave in texto:
            return "chikungunya" if chave == "chik" else chave
    return None


def _periodo(registro):
    semana = _valor(registro, "SEM_NOT", "SEMANA_EPIDEMIOLOGICA", "SEM_PRI")
    ano = _valor(registro, "NU_ANO", "ANO", "NU_ANO_NOT")
    if semana is not None:
        digitos = re.sub(r"\D", "", str(semana))
        try:
            if len(digitos) >= 6:
                return f"{digitos[:4]}-W{int(digitos[-2:]):02d}"
            if ano is not None:
                return f"{int(float(ano)):04d}-W{int(float(semana)):02d}"
        except (ValueError, OverflowError):
            return None
    data = _valor(registro, "DT_NOTIFIC", "DT_SIN_PRI", "data")
    if data:
        texto = str(data).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"):
            try:
                dt = datetime.strptime(texto, fmt)
                semana_iso = dt.isocalendar()
                return f"{semana_iso.year:04d}-W{semana_iso.week:02d}"
            except ValueError:
                pass
    return None


def agregar_arboviroses_recife(registros):
    """Retorna apenas contagens semanais por agravo/bairro, sem dados individuais."""
    agregados = defaultdict(lambda: {"ids": set(), "sem_id": 0})
    for registro in registros:
        if not isinstance(registro, dict) or not _recife(registro):
            continue
        agravo = _agravo(registro)
        periodo = _periodo(registro)
        if not agravo or not periodo:
            continue
        bairro = str(_valor(registro, "NM_BAIRRO", "NOBAIINF", "bairro") or "nao_informado").strip()
        chave = (agravo, periodo, bairro)
        notificacao = _valor(registro, "NU_NOTIFIC", "ID_NOTIFICACAO")
        if notificacao is None:
            agregados[chave]["sem_id"] += 1
        else:
            agregados[chave]["ids"].add(str(notificacao).strip())

    return [
        {
            "territorio": "Recife",
            "bairro": bairro,
            "indicador": agravo,
            "periodo": periodo,
            "valor": len(valores["ids"]) + valores["sem_id"],
        }
        for (agravo, periodo, bairro), valores in sorted(agregados.items())
    ]


def _carregar_recurso(url, formato):
    resposta = get(url)
    if formato == "CSV":
        try:
            texto = resposta.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = resposta.content.decode("latin-1")
        quadro = pd.read_csv(StringIO(texto), sep=None, engine="python")
        return dataframe_para_registros(quadro)
    conteudo = resposta.json()
    if isinstance(conteudo, list):
        return [item for item in conteudo if isinstance(item, dict)]
    if isinstance(conteudo, dict):
        for chave in ("result", "records", "data"):
            if isinstance(conteudo.get(chave), list):
                return [item for item in conteudo[chave] if isinstance(item, dict)]
        return [conteudo]
    return []


def pipeline_recife_arboviroses(db):
    """Procura recurso com campos compatíveis e grava contagens de Recife."""
    logger.info("Iniciando pipeline de arboviroses Dados Abertos Recife")
    resposta = get(
        f"{CKAN_RECIFE}/action/package_search",
        params={"q": "dengue zika chikungunya", "rows": 50},
    )
    resultado = resposta.json()
    if not resultado.get("success"):
        raise RuntimeError("O portal CKAN Recife não confirmou a busca.")

    datasets = resultado.get("result", {}).get("results", [])
    if not isinstance(datasets, list):
        raise RuntimeError("CKAN Recife retornou lista de datasets inválida.")

    for dataset in datasets:
        for recurso in dataset.get("resources", []):
            formato = str(recurso.get("format") or "").strip().upper()
            if formato not in {"CSV", "JSON"} or not recurso.get("url"):
                continue
            try:
                linhas = _carregar_recurso(recurso["url"], formato)
                agregados = agregar_arboviroses_recife(linhas)
            except Exception as erro:
                logger.error(
                    "Falha ao baixar/validar recurso CKAN id=%s nome=%s tipo=%s",
                    dataset.get("id"), recurso.get("name"), type(erro).__name__,
                )
                continue
            if not agregados:
                logger.info(
                    "Recurso CKAN sem registros de Recife com agravo e período válidos: %s",
                    recurso.get("name"),
                )
                continue

            for agregado in agregados:
                agregado.update({
                    "dataset_id": dataset.get("id"),
                    "recurso_nome": recurso.get("name"),
                })
            salvar_json_local("dados_abertos_recife_arboviroses", agregados)
            carregar_documentos(
                db["recife_arboviroses"],
                "dados_abertos_recife",
                agregados,
                "arboviroses_agregadas_semanais",
                "Recife",
                campos_chave=("indicador", "periodo", "bairro"),
            )
            logger.info("Arboviroses Recife concluído: %d grupos agregados", len(agregados))
            return

    raise RuntimeError(
        "CKAN Recife não forneceu recurso CSV/JSON com registros identificáveis "
        "de Recife, agravo conhecido, semana e bairro. Nenhum registro foi salvo."
    )
