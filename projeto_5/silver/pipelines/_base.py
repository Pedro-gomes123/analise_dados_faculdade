"""Infraestrutura compartilhada pelos processadores silver.

DDL e TRUNCATE via pyodbc (mssql_python).
Leitura e escrita são feitas via Spark JDBC em cada processador.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "silver" / "001_silver_tables.sql",
)


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


def _truncar(connection, tabela: str) -> None:
    """Trunca a tabela silver antes de recarregar via Spark JDBC."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"TRUNCATE TABLE {tabela}")
        connection.commit()
        logger.debug("Tabela truncada: %s", tabela)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
