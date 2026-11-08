"""Carga piloto dos Parquets INMET de estações para staging no SQL Server."""

import hashlib
import logging
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

INMET_STATIONS_PREFIX = "inmet/estacoes/"
INMET_STAGING_TABLE = "staging.INMET_Estacoes"
PARQUET_COLUMNS = (
    "_id",
    "fonte",
    "tipo_dado",
    "municipio",
    "ingestao_ts",
    "payload_json",
    "documento_json",
)


def ler_parquet_inmet(conteudo: bytes) -> list[dict]:
    """Lê Parquet INMET e valida o schema real da Bronze antes da carga."""
    table = pq.read_table(pa.BufferReader(conteudo))
    if tuple(table.column_names) != PARQUET_COLUMNS:
        raise ValueError(
            "Schema Parquet inesperado. Esperadas as colunas: "
            + ", ".join(PARQUET_COLUMNS)
        )
    expected_types = {
        "_id": pa.string(),
        "fonte": pa.string(),
        "tipo_dado": pa.string(),
        "municipio": pa.string(),
        "ingestao_ts": pa.timestamp("us", tz="UTC"),
        "payload_json": pa.string(),
        "documento_json": pa.string(),
    }
    for name, expected in expected_types.items():
        if table.schema.field(name).type != expected:
            raise ValueError(
                f"Tipo Parquet inesperado em {name}: "
                f"{table.schema.field(name).type}; esperado {expected}."
            )
    return table.to_pylist()


def fonte_para_blob(blob_name: str) -> str:
    """Aceita apenas o prefixo INMET de estações neste piloto."""
    if blob_name.startswith(INMET_STATIONS_PREFIX) and blob_name.endswith(".parquet"):
        return "INMET_Estacoes"
    raise ValueError(f"Blob fora do escopo do piloto INMET: {blob_name}")


def carregar_arquivo_inmet(connection, container, blob_name: str) -> dict:
    """Carrega um arquivo uma única vez; staging e controle confirmam juntos."""
    fonte = fonte_para_blob(blob_name)
    conteudo = container.get_blob_client(blob_name).download_blob().readall()
    file_hash = hashlib.sha256(conteudo).digest()
    rows = ler_parquet_inmet(conteudo)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT status FROM staging.ArquivosProcessados WHERE file_hash = ?",
        file_hash,
    )
    status = cursor.fetchone()
    if status and status[0] == "concluido":
        logger.info("Arquivo já processado; ignorado: %s", blob_name)
        cursor.close()
        return {
            "arquivo": blob_name,
            "fonte": fonte,
            "lidos": len(rows),
            "inseridos": 0,
            "status": "ignorado",
        }

    now = datetime.now(timezone.utc).isoformat()
    try:
        if status:
            cursor.execute(
                """UPDATE staging.ArquivosProcessados
                   SET blob_name = ?, fonte = ?, processado_em = ?,
                       registros_lidos = ?, registros_inseridos = 0,
                       status = 'processando', mensagem_erro = NULL
                   WHERE file_hash = ?""",
                blob_name,
                fonte,
                now,
                len(rows),
                file_hash,
            )
        else:
            cursor.execute(
                """INSERT INTO staging.ArquivosProcessados
                   (file_hash, blob_name, fonte, processado_em,
                    registros_lidos, registros_inseridos, status, mensagem_erro)
                   VALUES (?, ?, ?, ?, ?, 0, 'processando', NULL)""",
                file_hash,
                blob_name,
                fonte,
                now,
                len(rows),
            )
        connection.commit()

        values = [
            (
                file_hash,
                line_number,
                blob_name,
                row.get("_id"),
                row.get("fonte"),
                row.get("tipo_dado"),
                row.get("municipio"),
                row.get("ingestao_ts").isoformat()
                if row.get("ingestao_ts") is not None
                else None,
                row.get("payload_json"),
                row.get("documento_json"),
            )
            for line_number, row in enumerate(rows, start=1)
        ]
        insert_sql = """INSERT INTO staging.INMET_Estacoes
            (file_hash, linha_arquivo, blob_name, [_id], fonte, tipo_dado,
             municipio, ingestao_ts, payload_json, documento_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?), ?, ?)"""
        if values:
            cursor.executemany(insert_sql, values)

        cursor.execute(
            """UPDATE staging.ArquivosProcessados
               SET processado_em = ?, registros_inseridos = ?,
                   status = 'concluido', mensagem_erro = NULL
               WHERE file_hash = ?""",
            datetime.now(timezone.utc).isoformat(),
            len(values),
            file_hash,
        )
        connection.commit()
        logger.info(
            "Staging concluído: fonte=%s arquivo=%s lidos=%d inseridos=%d",
            fonte,
            blob_name,
            len(rows),
            len(values),
        )
        return {
            "arquivo": blob_name,
            "fonte": fonte,
            "lidos": len(rows),
            "inseridos": len(values),
            "status": "concluido",
        }
    except Exception as error:
        connection.rollback()
        cursor.execute(
            """UPDATE staging.ArquivosProcessados
               SET processado_em = ?, status = 'erro', mensagem_erro = ?
               WHERE file_hash = ?""",
            datetime.now(timezone.utc).isoformat(),
            f"Falha de carga ({type(error).__name__}).",
            file_hash,
        )
        connection.commit()
        logger.error(
            "Falha de staging: fonte=%s arquivo=%s tipo=%s",
            fonte,
            blob_name,
            type(error).__name__,
        )
        raise
    finally:
        cursor.close()


def carregar_inmet_estacoes(connection, container) -> list[dict]:
    """Lista e carrega arquivos Parquet de estações INMET pendentes."""
    blobs = sorted(
        blob.name
        for blob in container.list_blobs(name_starts_with=INMET_STATIONS_PREFIX)
        if blob.name.endswith(".parquet")
    )
    results = []
    for blob_name in blobs:
        results.append(carregar_arquivo_inmet(connection, container, blob_name))
    return results
