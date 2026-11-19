"""Testes unitários do pipeline gold."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from gold.pipelines.gold_pipeline import (
    _ts,
    processar_leitura_climatica,
    processar_indicador_territorio,
    gold_pipeline,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
NOW_ISO = NOW.isoformat()


# ---------------------------------------------------------------------------
# _ts
# ---------------------------------------------------------------------------

class TsTests(unittest.TestCase):

    def test_datetime_retorna_iso(self):
        resultado = _ts(NOW)
        self.assertIn("2026-11-15", resultado)

    def test_none_retorna_none(self):
        self.assertIsNone(_ts(None))

    def test_string_retorna_string(self):
        self.assertEqual(_ts("2026-01-01T00:00:00+00:00"), "2026-01-01T00:00:00+00:00")


# ---------------------------------------------------------------------------
# processar_leitura_climatica — formato largo (uma linha por horário)
# ---------------------------------------------------------------------------

class ProcessarLeituraClimaticaTests(unittest.TestCase):

    def _conn_com_silver(self, rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        cursor_upsert = MagicMock()
        conn = MagicMock()
        conn.cursor.side_effect = [cursor, cursor_upsert]
        return conn

    def test_uma_linha_do_silver_gera_uma_linha_no_gold(self):
        # Formato largo: 1 linha do silver → 1 linha no gold (não UNPIVOT)
        row = ("openmeteo", "recife_est", "Recife", NOW, "historico_modelado",
               28.0, 0.5, 80.0, 1013.0)
        conn = self._conn_com_silver([row])
        resultado = processar_leitura_climatica(conn)
        self.assertEqual(resultado["processados"], 1)

    def test_linha_com_nulos_ainda_inserida(self):
        # Variáveis NULL são aceitas — colunas nullable no schema
        row = ("openmeteo", "recife_est", "Recife", NOW, "historico_modelado",
               28.0, None, None, None)
        conn = self._conn_com_silver([row])
        resultado = processar_leitura_climatica(conn)
        self.assertEqual(resultado["processados"], 1)

    def test_silver_vazio_retorna_zero(self):
        conn = self._conn_com_silver([])
        resultado = processar_leitura_climatica(conn)
        self.assertEqual(resultado["processados"], 0)
        conn.commit.assert_not_called()

    def test_multiplas_linhas(self):
        rows = [
            ("openmeteo", "est_a", "Recife", NOW, "previsao", 28.0, 0.5, 80.0, 1013.0),
            ("nasa_power", "est_b", "Recife", NOW, "reanalisado", 27.5, 1.0, 85.0, 1010.0),
        ]
        conn = self._conn_com_silver(rows)
        resultado = processar_leitura_climatica(conn)
        self.assertEqual(resultado["processados"], 2)


# ---------------------------------------------------------------------------
# processar_indicador_territorio
# ---------------------------------------------------------------------------

class ProcessarIndicadorTerritorioTests(unittest.TestCase):

    def _conn_com_silver(self, arb_rows, dc_rows, ani_rows):
        cursors = []
        for rows in (arb_rows, dc_rows, ani_rows):
            cur = MagicMock()
            cur.fetchall.return_value = rows
            cursors.append(cur)
        # cursor do _upsert
        cursors.append(MagicMock())
        conn = MagicMock()
        conn.cursor.side_effect = cursors
        return conn

    def test_une_tres_fontes(self):
        conn = self._conn_com_silver(
            arb_rows=[("Recife", "Boa Viagem", "dengue", 10, "2025-W01")],
            dc_rows=[("Recife", "Afogados", "Deslizamento", 2, "2025-01")],
            ani_rows=[("Pernambuco", "Recife", 5, "2025-W01")],
        )
        resultado = processar_indicador_territorio(conn)
        self.assertEqual(resultado["processados"], 3)

    def test_fontes_vazias_retorna_zero(self):
        conn = self._conn_com_silver([], [], [])
        resultado = processar_indicador_territorio(conn)
        self.assertEqual(resultado["processados"], 0)

    def test_nome_indicador_animais(self):
        conn = self._conn_com_silver(
            arb_rows=[],
            dc_rows=[],
            ani_rows=[("Pernambuco", "Caruaru", 3, "2025-W10")],
        )
        resultado = processar_indicador_territorio(conn)
        self.assertEqual(resultado["processados"], 1)


# ---------------------------------------------------------------------------
# gold_pipeline — orquestrador (processar_estacao removido)
# ---------------------------------------------------------------------------

class GoldPipelineTests(unittest.TestCase):

    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    def test_chama_dois_processadores(self, mock_leitura, mock_ind, mock_ddl):
        for m in (mock_leitura, mock_ind):
            m.return_value = {"tabela": "gold.X", "processados": 5}

        conn = MagicMock()
        resultados = gold_pipeline(connection=conn, aplicar_ddl=True)

        self.assertEqual(len(resultados), 2)
        mock_ddl.assert_called_once()
        mock_leitura.assert_called_once_with(conn)
        mock_ind.assert_called_once_with(conn)

    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    def test_falha_em_uma_fonte_nao_para_as_demais(
        self, mock_leitura, mock_ind, mock_ddl
    ):
        mock_leitura.side_effect = RuntimeError("erro simulado")
        mock_ind.return_value = {"tabela": "gold.indicador_territorio", "processados": 100}

        conn = MagicMock()
        resultados = gold_pipeline(connection=conn, aplicar_ddl=False)

        self.assertEqual(len(resultados), 2)
        self.assertIn("erro", resultados[0])
        total = sum(r.get("processados", 0) for r in resultados)
        self.assertEqual(total, 100)

    @patch("gold.pipelines.gold_pipeline._aplicar_ddl")
    @patch("gold.pipelines.gold_pipeline.processar_indicador_territorio")
    @patch("gold.pipelines.gold_pipeline.processar_leitura_climatica")
    def test_sem_ddl_nao_chama_aplicar_ddl(self, mock_leitura, mock_ind, mock_ddl):
        for m in (mock_leitura, mock_ind):
            m.return_value = {"tabela": "gold.X", "processados": 1}

        conn = MagicMock()
        gold_pipeline(connection=conn, aplicar_ddl=False)
        mock_ddl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
