"""Orquestra o piloto INMET: Azure Bronze → staging → procedure Silver."""

import logging
import re
import time
from pathlib import Path

from bronze.azure_blob import conectar_azure_blob
from silver.database.sql_server import conectar_sql_server
from silver.pipelines.bronze_to_staging import carregar_inmet_estacoes

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_SCRIPTS = (
    PROJECT_ROOT / "sql" / "staging" / "001_inmet_estacoes.sql",
    PROJECT_ROOT / "sql" / "silver" / "001_inmet_estacoes.sql",
)


def aplicar_scripts_sql(connection, scripts=SQL_SCRIPTS) -> None:
    """Aplica DDL idempotente dividido em batches T-SQL por linhas GO."""
    cursor = connection.cursor()
    current_script = "(desconhecido)"
    batch_number = 0
    try:
        for script_path in scripts:
            current_script = script_path.name
            script = script_path.read_text(encoding="utf-8")
            batches = re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script)
            for batch_number, batch in enumerate(batches, start=1):
                if batch.strip():
                    cursor.execute(batch)
                    connection.commit()
            logger.info("Estruturas SQL verificadas: %s", script_path.name)
    except Exception as error:
        connection.rollback()
        # Os scripts são DDL estático sem valores de dados ou credenciais.
        # Registrar a mensagem SQL facilita identificar permissões e sintaxe.
        logger.error(
            "Falha no DDL arquivo=%s lote=%d tipo=%s erro=%s",
            current_script,
            batch_number,
            type(error).__name__,
            error,
        )
        raise
    finally:
        cursor.close()


def executar_procedure_inmet(connection) -> dict:
    """Executa a procedure idempotente e retorna as contagens da Silver."""
    cursor = connection.cursor()
    try:
        cursor.execute("EXEC silver.sp_tratar_inmet")
        row = cursor.fetchone()
        connection.commit()
        if row is None:
            raise RuntimeError("A procedure INMET não retornou seu resumo.")
        return {
            "registros_lidos": int(row[0]),
            "registros_inseridos": int(row[1]),
            "registros_rejeitados": int(row[2]),
            "status": str(row[3]),
        }
    except Exception:
        connection.rollback()
        logger.error("Falha na procedure silver.sp_tratar_inmet.")
        raise
    finally:
        cursor.close()


def silver_pipeline(connection=None, container=None, aplicar_ddl=True) -> dict:
    """Processa somente INMET estações; outros fontes aguardam o piloto.

    Conexões injetadas são úteis para testes e continuam sob responsabilidade
    do chamador. Conexões criadas aqui são sempre fechadas ao final.
    """
    owns_connection = connection is None
    owns_container = container is None
    started = time.perf_counter()
    try:
        if connection is None:
            connection = conectar_sql_server()
        if container is None:
            container = conectar_azure_blob()
        if aplicar_ddl:
            aplicar_scripts_sql(connection)

        staging_results = carregar_inmet_estacoes(connection, container)
        silver_result = executar_procedure_inmet(connection)
        summary = {
            "fonte": "INMET_Estacoes",
            "arquivos": len(staging_results),
            "arquivos_concluidos": sum(
                result["status"] == "concluido" for result in staging_results
            ),
            "arquivos_ignorados": sum(
                result["status"] == "ignorado" for result in staging_results
            ),
            "registros_lidos": sum(result["lidos"] for result in staging_results),
            "registros_inseridos_staging": sum(
                result["inseridos"] for result in staging_results
            ),
            **silver_result,
            "duracao_segundos": round(time.perf_counter() - started, 3),
        }
        logger.info(
            "Silver piloto: fonte=%s arquivos=%d lidos=%d staging=%d "
            "silver=%d rejeitados=%d duração=%.3fs status=%s",
            summary["fonte"],
            summary["arquivos"],
            summary["registros_lidos"],
            summary["registros_inseridos_staging"],
            summary["registros_inseridos"],
            summary["registros_rejeitados"],
            summary["duracao_segundos"],
            summary["status"],
        )
        return summary
    except Exception:
        logger.error("Pipeline Silver piloto falhou.")
        raise
    finally:
        if owns_connection and connection is not None:
            connection.close()
        if owns_container and container is not None:
            close = getattr(container, "close", None)
            if callable(close):
                close()
