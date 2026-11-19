"""Testes unitários do pipeline silver (PySpark).

Os processadores individuais exigem SparkSession + JDBC real, por isso
os testes unitários focam no orquestrador silver_pipeline, mockando cada
processador para verificar coordenação, isolamento de falhas e DDL.
"""

import unittest
from unittest.mock import MagicMock, patch

from silver.pipelines.silver_pipeline import silver_pipeline


class SilverPipelineTests(unittest.TestCase):

    _PROCESSADORES = [
        "processar_meteorologia",
        "processar_arboviroses",
        "processar_defesa_civil",
        "processar_animais_peconhentos",
        "processar_samu",
        "processar_acidentes_transito",
        "processar_estacoes",
    ]

    def _patches(self):
        return [
            patch(f"silver.pipelines.silver_pipeline.{nome}")
            for nome in self._PROCESSADORES
        ]

    def test_chama_todos_os_processadores(self):
        mocks = [p.start() for p in self._patches()]
        for m in mocks:
            m.return_value = {"tabela": "silver.X", "processados": 1}
        try:
            with (
                patch("silver.pipelines.silver_pipeline._aplicar_ddl") as mock_ddl,
                patch(
                    "silver.spark_session.jdbc_url_e_props",
                    return_value=("jdbc:test", {}),
                ),
            ):
                conn  = MagicMock()
                spark = MagicMock()
                resultados = silver_pipeline(connection=conn, spark=spark, aplicar_ddl=True)

                self.assertEqual(len(resultados), 7)
                mock_ddl.assert_called_once()
                for m in mocks:
                    m.assert_called_once_with(spark, conn, "jdbc:test", {})
        finally:
            for p in self._patches():
                p.stop()

    def test_falha_em_uma_fonte_nao_para_as_demais(self):
        mocks = [p.start() for p in self._patches()]
        mocks[0].side_effect = RuntimeError("erro simulado")  # meteorologia falha
        for m in mocks[1:]:
            m.return_value = {"tabela": "silver.X", "processados": 2}
        try:
            with (
                patch("silver.pipelines.silver_pipeline._aplicar_ddl"),
                patch(
                    "silver.spark_session.jdbc_url_e_props",
                    return_value=("jdbc:test", {}),
                ),
            ):
                conn  = MagicMock()
                spark = MagicMock()
                resultados = silver_pipeline(connection=conn, spark=spark, aplicar_ddl=False)

                self.assertEqual(len(resultados), 7)
                self.assertIn("erro", resultados[0])
                total = sum(r.get("processados", 0) for r in resultados)
                self.assertEqual(total, 12)  # 6 fontes × 2
        finally:
            for p in self._patches():
                p.stop()

    def test_sem_ddl_nao_chama_aplicar_ddl(self):
        mocks = [p.start() for p in self._patches()]
        for m in mocks:
            m.return_value = {"tabela": "silver.X", "processados": 0}
        try:
            with (
                patch("silver.pipelines.silver_pipeline._aplicar_ddl") as mock_ddl,
                patch(
                    "silver.spark_session.jdbc_url_e_props",
                    return_value=("jdbc:test", {}),
                ),
            ):
                conn  = MagicMock()
                spark = MagicMock()
                silver_pipeline(connection=conn, spark=spark, aplicar_ddl=False)
                mock_ddl.assert_not_called()
        finally:
            for p in self._patches():
                p.stop()


if __name__ == "__main__":
    unittest.main()
