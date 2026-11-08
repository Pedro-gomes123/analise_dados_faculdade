"""Exporta snapshots imutáveis das coleções MongoDB para a camada Bronze."""

import logging
import uuid
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from bson import json_util

from bronze.azure_blob import AzureBlobStorage

logger = logging.getLogger(__name__)

# Nomes confirmados nos coletores do projeto.
COLECOES_BRONZE = {
    "inmet_estacoes": "inmet/estacoes",
    "inmet_observacoes": "inmet/observacoes",
    "openmeteo_horario": "openmeteo/horario",
    "recife_arboviroses": "recife/arboviroses",
    "s2id_desastres": "s2id/desastres",
    "sinan_animais_peconhentos": "sinan/animais_peconhentos",
}


def _export_collection(db, collection_name, destination, storage, exported_at):
    """Grava uma coleção como tabela Parquet, preservando o documento BSON bruto.

    Cada coleção vira uma tabela lógica no prefixo de destino. Os campos comuns
    ficam em colunas próprias; `payload_json` e `documento_json` usam Extended
    JSON para preservar estruturas aninhadas e tipos BSON sem perda.
    """
    collection = db[collection_name]
    documents = list(collection.find({}))
    if not documents:
        logger.info("Coleção vazia, sem arquivo: %s", collection_name)
        return {"colecao": collection_name, "documentos": 0, "blob": None}

    rows = []
    for document in documents:
        ingestao_ts = document.get("ingestao_ts")
        if isinstance(ingestao_ts, datetime) and ingestao_ts.tzinfo is None:
            ingestao_ts = ingestao_ts.replace(tzinfo=timezone.utc)
        elif isinstance(ingestao_ts, datetime):
            ingestao_ts = ingestao_ts.astimezone(timezone.utc)
        else:
            ingestao_ts = None

        payload = document.get("payload")
        rows.append(
            {
                "_id": str(document.get("_id", "")),
                "fonte": document.get("fonte"),
                "tipo_dado": document.get("tipo_dado"),
                "municipio": document.get("municipio"),
                "ingestao_ts": ingestao_ts,
                "payload_json": (
                    json_util.dumps(payload, ensure_ascii=False)
                    if "payload" in document
                    else None
                ),
                # Snapshot Extended JSON do documento original completo.
                "documento_json": json_util.dumps(document, ensure_ascii=False),
            }
        )

    schema = pa.schema(
        [
            pa.field("_id", pa.string()),
            pa.field("fonte", pa.string()),
            pa.field("tipo_dado", pa.string()),
            pa.field("municipio", pa.string()),
            pa.field("ingestao_ts", pa.timestamp("us", tz="UTC")),
            pa.field("payload_json", pa.string()),
            pa.field("documento_json", pa.string()),
        ]
    )
    table = pa.Table.from_pylist(rows, schema=schema)
    output = pa.BufferOutputStream()
    pq.write_table(table, output, compression="snappy")
    parquet_bytes = output.getvalue().to_pybytes()
    blob_name = (
        f"{destination}/ano={exported_at:%Y}/mes={exported_at:%m}/"
        f"dia={exported_at:%d}/{exported_at:%H%M%S%f}Z-{uuid.uuid4().hex}.parquet"
    )
    storage.upload(blob_name, parquet_bytes)
    logger.info(
        "Exportação concluída: coleção=%s documentos=%d blob=%s",
        collection_name,
        len(documents),
        blob_name,
    )
    return {"colecao": collection_name, "documentos": len(documents), "blob": blob_name}


def pipeline_bronze(db, storage=None, exported_at=None):
    """Exporta as coleções configuradas; qualquer falha de upload propaga erro."""
    exported_at = exported_at or datetime.now(timezone.utc)
    if exported_at.tzinfo is None:
        exported_at = exported_at.replace(tzinfo=timezone.utc)
    exported_at = exported_at.astimezone(timezone.utc)
    storage = storage or AzureBlobStorage()

    logger.info("Início da exportação Bronze em %s", exported_at.isoformat())
    results = []
    for collection_name, destination in COLECOES_BRONZE.items():
        results.append(
            _export_collection(db, collection_name, destination, storage, exported_at)
        )
    total = sum(result["documentos"] for result in results)
    logger.info(
        "Resumo Bronze: coleções=%d documentos=%d arquivos=%d horário=%s",
        len(results),
        total,
        sum(result["blob"] is not None for result in results),
        exported_at.isoformat(),
    )
    return results
