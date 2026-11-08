import unittest
from unittest.mock import Mock, patch

from silver import main as silver_main
from silver.pipelines.silver_pipeline import executar_procedure_inmet, silver_pipeline


class SilverPipelineTests(unittest.TestCase):
    def test_executes_idempotent_inmet_procedure_and_reads_counts(self):
        cursor = Mock()
        cursor.fetchone.return_value = (16, 16, 0, "concluido")
        connection = Mock()
        connection.cursor.return_value = cursor

        result = executar_procedure_inmet(connection)

        cursor.execute.assert_called_once_with("EXEC silver.sp_tratar_inmet")
        self.assertEqual(result["registros_lidos"], 16)
        self.assertEqual(result["registros_inseridos"], 16)
        self.assertEqual(result["registros_rejeitados"], 0)
        connection.commit.assert_called_once()

    def test_orchestrates_staging_then_silver_without_owning_injected_clients(self):
        connection = Mock()
        container = Mock()
        with (
            patch(
                "silver.pipelines.silver_pipeline.aplicar_scripts_sql"
            ) as apply_ddl,
            patch(
                "silver.pipelines.silver_pipeline.carregar_inmet_estacoes",
                return_value=[
                    {
                        "status": "concluido",
                        "lidos": 16,
                        "inseridos": 16,
                    }
                ],
            ) as load_staging,
            patch(
                "silver.pipelines.silver_pipeline.executar_procedure_inmet",
                return_value={
                    "registros_lidos": 16,
                    "registros_inseridos": 16,
                    "registros_rejeitados": 0,
                    "status": "concluido",
                },
            ) as run_proc,
        ):
            result = silver_pipeline(connection, container)

        apply_ddl.assert_called_once_with(connection)
        load_staging.assert_called_once_with(connection, container)
        run_proc.assert_called_once_with(connection)
        self.assertEqual(result["fonte"], "INMET_Estacoes")
        self.assertEqual(result["registros_inseridos_staging"], 16)
        connection.close.assert_not_called()

    def test_cli_reports_safe_configuration_error(self):
        with patch(
            "silver.main.silver_pipeline",
            side_effect=RuntimeError(
                "Variáveis SQL ausentes: SQL_SERVER, SQL_DATABASE"
            ),
        ):
            with self.assertLogs("silver.main", level="ERROR") as captured:
                exit_code = silver_main.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("SQL_SERVER, SQL_DATABASE", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
