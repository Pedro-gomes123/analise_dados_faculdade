"""Testes unitários do pipeline gold (PySpark).

Os processadores individuais exigem SparkSession + JDBC real, por isso
os testes unitários focam no orquestrador gold_pipeline, mockando cada
processador para verificar coordenação, isolamento de falhas e DDL.
"""

import unittest
from unittest.mock import MagicMock, patch

from gold.pipelines.gold_pipeline import gold_pipeline


class GoldPipelineTests(unittest.TestCase):

    @patch("gold.pipelines.gold_pipeline.processar_estacao")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    def test_chama_tres_processadores(
        self, mock_ddl, mock_leitura, mock_ind, mock_estacao
    ):
        for m in (mock_leitura, mock_ind, mock_estacao):
            m.return_value = {"tabela": "gold.X", "processados": 5}

        with patch(
            "silver.spark_session.jdbc_url_e_props",
            return_value=("jdbc:test", {}),
        ):
            conn  = MagicMock()
            spark = MagicMock()
            resultados = gold_pipeline(connection=conn, spark=spark, aplicar_ddl=True)

        self.assertEqual(len(resultados), 3)
        mock_ddl.assert_called_once()
        for m in (mock_leitura, mock_ind, mock_estacao):
            m.assert_called_once_with(spark, conn, "jdbc:test", {})

    @patch("gold.pipelines.gold_pipeline.processar_estacao")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    def test_falha_em_uma_fonte_nao_para_as_demais(
        self, mock_ddl, mock_leitura, mock_ind, mock_estacao
    ):
        mock_leitura.side_effect = RuntimeError("erro simulado")
        mock_ind.return_value     = {"tabela": "gold.indicador_territorio", "processados": 100}
        mock_estacao.return_value = {"tabela": "gold.estacao", "processados": 16}

        with patch(
            "silver.spark_session.jdbc_url_e_props",
            return_value=("jdbc:test", {}),
        ):
            conn  = MagicMock()
            spark = MagicMock()
            resultados = gold_pipeline(connection=conn, spark=spark, aplicar_ddl=False)

        self.assertEqual(len(resultados), 3)
        self.assertIn("erro", resultados[0])
        total = sum(r.get("processados", 0) for r in resultados)
        self.assertEqual(total, 116)

    @patch("gold.pipelines.gold_pipeline.processar_estacao")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    def test_sem_ddl_nao_chama_aplicar_ddl(
        self, mock_ddl, mock_leitura, mock_ind, mock_estacao
    ):
        for m in (mock_leitura, mock_ind, mock_estacao):
            m.return_value = {"tabela": "gold.X", "processados": 1}

        with patch(
            "silver.spark_session.jdbc_url_e_props",
            return_value=("jdbc:test", {}),
        ):
            conn  = MagicMock()
            spark = MagicMock()
            gold_pipeline(connection=conn, spark=spark, aplicar_ddl=False)

        mock_ddl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
