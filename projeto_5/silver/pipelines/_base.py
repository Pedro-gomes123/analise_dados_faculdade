"""Infraestrutura compartilhada pelos processadores silver.

Contém os helpers de baixo nível usados por todos os processadores:
DDL, leitura do bronze, upsert em lote e conversão de timestamp.
Nenhum processador deve replicar essas funções — importa daqui.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util

logger = logging.getLogger(__name__)

SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "silver" / "001_silver_tables.sql",
)

# Azure SQL tem timeout em transações com >32k parâmetros num único executemany.
# Lotes de 500 resolvem o problema observado com sinan_animais_peconhentos (~32k docs).
_BATCH_SIZE = 500


def _aplicar_ddl(connection, scripts=SQL_SCRIPTS) -> None:
    """Executa os scripts DDL do schema silver de forma idempotente."""
    cursor = connection.cursor()
    try:
        for caminho in scripts:
            script = Path(caminho).read_text(encoding="utf-8")
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
    """Lê e desserializa os payloads de uma tabela bronze."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT payload_json FROM {tabela} WHERE payload_json IS NOT NULL")
        registros = []
        for (payload_json,) in cursor.fetchall():
            try:
                registros.append(json_util.loads(payload_json))
            except Exception:
                logger.warning("payload_json inválido ignorado em %s", tabela)
        return registros
    finally:
        cursor.close()


def _upsert(connection, tabela: str, merge_sql: str, params: list[tuple]) -> int:
    """Insere/atualiza registros em lotes via MERGE idempotente."""
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
    """Converte datetime para string ISO 8601 para os parâmetros SQL MERGE."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.isoformat()
    return str(valor)
