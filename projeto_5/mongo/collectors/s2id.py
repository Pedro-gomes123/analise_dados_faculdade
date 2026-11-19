"""Coleta dados de desastres do CKAN federal (dados.gov.br) via portal S2ID.

Por que este coletor foi substituído pelo defesa_civil.py?
- O portal dados.gov.br/S2ID passou a retornar HTTP 401 (Não Autorizado)
  em 2026, impossibilitando o download dos datasets nacionais de desastres.
- O coletor permanece no código como fallback: se o portal federal voltar
  a funcionar, pode ser reativado em mongo/main.py.
- Para uso ativo, ver defesa_civil.py (Dados Abertos Recife/CKAN local).

Por que filtrar apenas Pernambuco?
O S2ID nacional contém registros de todos os estados do Brasil.
O projeto foca em Recife/PE — importar dados de outros estados
desperdiçaria storage e poluiria análises.

Estratégia de busca por termos múltiplos:
Busca três termos diferentes ("s2id desastre", "calamidade publica", etc.)
e deduplica por ID de dataset. Isso aumenta a chance de encontrar o dataset
correto independentemente de como o CKAN federal o indexou.
"""

import logging
from io import BytesIO, StringIO

# pandas + BytesIO/StringIO: leitura de CSV e XLSX sem salvar em disco.
# XLSX requer BytesIO (binário); CSV requer StringIO (texto).
import pandas as pd

from mongo.config import CKAN_GOV
from mongo.database.mongodb import carregar_documentos
from mongo.utils.http import get
from mongo.utils.storage import dataframe_para_registros, salvar_json_local

logger = logging.getLogger(__name__)


def _uf_pernambuco(valor):
    """Verifica se o valor representa o estado de Pernambuco.

    O CKAN federal usa diferentes formatos para a UF dependendo do dataset:
    sigla "PE", nome "PERNAMBUCO", código IBGE "26" ou "26.0" (com decimal).
    """
    texto = str(valor or "").strip().upper()
    return texto in {"PE", "PERNAMBUCO", "26", "26.0"}


def _filtrar_pernambuco(registros):
    """Filtra registros que pertencem a Pernambuco a partir de uma lista de dicts.

    Estratégia case-insensitive para encontrar a coluna de UF:
    Indexa os nomes de coluna em minúsculo e busca pelos aliases mais comuns.
    Se nenhum alias de UF for encontrado, retorna lista vazia (não conseguimos
    identificar o estado — melhor não importar nada que importar dados errados).

    Args:
        registros: Lista de dicts (linhas do CSV/JSON do CKAN federal).

    Returns:
        Lista filtrada com apenas registros onde UF == PE.
    """
    if not registros:
        return []

    # Indexa as colunas do primeiro registro para busca case-insensitive.
    aliases = {str(chave).strip().casefold(): chave for chave in registros[0]}
    # Tenta encontrar a coluna de UF pelos nomes mais comuns nos datasets federais.
    coluna_uf = next(
        (aliases[chave] for chave in ("uf", "estado", "sg_uf", "uf_ocorrencia") if chave in aliases),
        None,
    )
    if coluna_uf is None:
        # Sem coluna de UF identificável — não podemos garantir que são dados de PE.
        return []
    return [registro for registro in registros if _uf_pernambuco(registro.get(coluna_uf))]


def _ler_recurso(resposta, formato):
    """Parseia a resposta HTTP como CSV, XLSX ou JSON.

    Suporte a três formatos porque o CKAN federal publica os mesmos dados
    em múltiplos formatos dependendo do dataset e do ano.

    CSV: UTF-8-sig (remove BOM do Windows) com fallback para latin-1.
         sep=None: detecta "," ou ";" automaticamente.
    XLSX: BytesIO para leitura binária com pandas (openpyxl).
    JSON: extrai lista de dicts de qualquer estrutura (list, dict com "result"/"records"/"data").

    Args:
        resposta: requests.Response com o conteúdo do recurso.
        formato: "CSV", "XLSX" ou qualquer outro (assume JSON).

    Returns:
        Lista de dicts representando as linhas do recurso.
    """
    if formato == "CSV":
        try:
            conteudo = resposta.content.decode("utf-8-sig")  # remove BOM UTF-8
        except UnicodeDecodeError:
            conteudo = resposta.content.decode("latin-1")    # fallback para ISO-8859-1
        df = pd.read_csv(StringIO(conteudo), sep=None, engine="python")
        return dataframe_para_registros(df)

    if formato == "XLSX":
        # BytesIO: lê o Excel diretamente da memória sem criar arquivo temporário.
        df = pd.read_excel(BytesIO(resposta.content))
        return dataframe_para_registros(df)

    # JSON: extrai registros de diferentes estruturas de resposta CKAN.
    conteudo = resposta.json()
    if isinstance(conteudo, list):
        return [item for item in conteudo if isinstance(item, dict)]
    if isinstance(conteudo, dict):
        # Tenta as chaves mais comuns de containers de resultados CKAN.
        for chave in ("result", "records", "data"):
            if isinstance(conteudo.get(chave), list):
                return [item for item in conteudo[chave] if isinstance(item, dict)]
        return [conteudo]
    return []


def pipeline_s2id(db):
    """Busca dados de desastres do CKAN federal e salva apenas registros de PE.

    NOTA: Este pipeline está desativado em mongo/main.py desde 2026 (HTTP 401).
    Mantido como fallback caso o portal federal reabilite o acesso público.

    Fluxo:
    1. Busca datasets por três termos no CKAN federal, deduplica por ID.
    2. Para cada dataset, itera os recursos CSV/JSON/XLSX.
    3. Lê o recurso, filtra por UF=PE.
    4. Adiciona metadados do CKAN para rastreabilidade.
    5. Persiste no MongoDB e retorna após o primeiro recurso válido.

    Args:
        db: pymongo.Database — banco do MongoDB para persistência.

    Raises:
        RuntimeError: Se nenhum recurso com dados de PE for encontrado.
    """
    logger.info("Iniciando pipeline S2ID / dados.gov.br")

    # Busca por três termos para aumentar a cobertura de datasets.
    # dict encontrados deduplica por ID: o mesmo dataset pode aparecer em
    # múltiplas buscas se corresponder a mais de um termo.
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
                # dict: chave = ID do dataset — deduplicação automática.
                encontrados[dataset["id"]] = dataset

    # Itera todos os datasets encontrados e seus recursos.
    for dataset in encontrados.values():
        for recurso in dataset.get("resources", []):
            formato = str(recurso.get("format") or "").strip().upper()
            # Ignora formatos não suportados (PDF, HTML, ZIP, etc.).
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

            # Adiciona campos de metadados do CKAN para rastreabilidade.
            # Prefixo "_" indica que são metadados do pipeline, não dados originais.
            for registro in registros_pe:
                registro["_dataset_id"]     = dataset.get("id")
                registro["_dataset_titulo"] = dataset.get("title")
                registro["_recurso_nome"]   = recurso.get("name")

            salvar_json_local("s2id_desastres", registros_pe)

            # campos_chave não especificados: carregar_documentos usa os campos
            # do documento para gerar o _id SHA-256 (hash do documento completo).
            carregar_documentos(
                db["s2id_desastres"],
                "dados_gov_s2id",
                registros_pe,
                "desastres",
                "Pernambuco",
            )
            logger.info("S2ID concluído: %d registros PE", len(registros_pe))
            # Retorna após o primeiro recurso válido — não processa datasets duplicados.
            return

    raise RuntimeError(
        "Não foi encontrado recurso de desastres que permita identificar "
        "explicitamente os registros de Pernambuco. Nenhum dado foi salvo."
    )
