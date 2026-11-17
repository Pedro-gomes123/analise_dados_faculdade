"""Testes unitários do pipeline silver."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch, call

from bson import json_util

from silver.pipelines.silver_pipeline import (
    _linha_meteorologia,
    _ler_bronze,
    _ts,
    processar_arboviroses,
    processar_defesa_civil,
    processar_animais_peconhentos,
    processar_estacoes,
    processar_meteorologia,
    silver_pipeline,
)

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
NOW_ISO = NOW.isoformat()


# ---------------------------------------------------------------------------
# _ts
# ---------------------------------------------------------------------------

class TsTests(unittest.TestCase):

    def test_datetime_utc_retorna_iso(self):
        dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        self.assertIn("2026-01-01", _ts(dt))

    def test_datetime_naive_recebe_utc(self):
        naive = datetime(2026, 1, 1, 0, 0)
        resultado = _ts(naive)
        self.assertIn("+00:00", resultado)

    def test_none_retorna_none(self):
        self.assertIsNone(_ts(None))


# ---------------------------------------------------------------------------
# _linha_meteorologia
# ---------------------------------------------------------------------------

class LinhaMeterologiaTests(unittest.TestCase):

    def _payload_openmeteo(self, **extra):
        p = {
            "fonte": "openmeteo",
            "estacao": "recife_-8.0500_-34.9000",
            "territorio": "Recife",
            "lida_em": NOW,
            "natureza_dado": "historico_modelado",
            "variaveis": {
                "temperatura_c": 28.0,
                "precipitacao_mm": 0.5,
                "umidade_pct": 80.0,
                "pressao_hpa": 1013.0,
                "vento_ms": 3.2,
            },
            "latitude": -8.05,
            "longitude": -34.9,
        }
        p.update(extra)
        return p

    def test_extrai_campos_openmeteo_corretamente(self):
        linha = _linha_meteorologia(self._payload_openmeteo(), NOW_ISO)
        self.assertIsNotNone(linha)
        self.assertEqual(linha[0], "openmeteo")        # fonte
        self.assertAlmostEqual(linha[5], 28.0)         # temperatura_c
        self.assertAlmostEqual(linha[8], 1013.0)       # pressao_hpa

    def test_nasa_power_converte_kpa_para_hpa(self):
        p = self._payload_openmeteo()
        p["fonte"] = "nasa_power"
        p["variaveis"] = {
            "temperatura_c": 26.0,
            "precipitacao_mm": 1.0,
            "umidade_pct": 85.0,
            "pressao_kpa": 101.3,  # kPa
            "vento_ms": 2.0,
        }
        linha = _linha_meteorologia(p, NOW_ISO)
        self.assertIsNotNone(linha)
        self.assertAlmostEqual(linha[8], 1013.0, places=1)  # pressao_hpa = 101.3 * 10

    def test_sem_lida_em_retorna_none(self):
        p = self._payload_openmeteo()
        p["lida_em"] = None
        self.assertIsNone(_linha_meteorologia(p, NOW_ISO))

    def test_sem_fonte_retorna_none(self):
        p = self._payload_openmeteo()
        p["fonte"] = None
        self.assertIsNone(_linha_meteorologia(p, NOW_ISO))

    def test_variaveis_ausentes_viram_none(self):
        p = self._payload_openmeteo()
        p["variaveis"] = {}
        linha = _linha_meteorologia(p, NOW_ISO)
        self.assertIsNotNone(linha)
        self.assertIsNone(linha[5])   # temperatura_c
        self.assertIsNone(linha[8])   # pressao_hpa


# ---------------------------------------------------------------------------
# _ler_bronze
# ---------------------------------------------------------------------------

class LerBronzeTests(unittest.TestCase):

    def _make_conn(self, rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_desserializa_bson_extended_json(self):
        payload = {"fonte": "openmeteo", "lida_em": NOW, "valor": 1.5}
        payload_json = json_util.dumps(payload)
        conn = self._make_conn([(payload_json,)])

        resultado = _ler_bronze(conn, "bronze.openmeteo_horario")

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fonte"], "openmeteo")
        # datetime deve ser desserializado de volta corretamente
        self.assertIsInstance(resultado[0]["lida_em"], type(NOW))

    def test_ignora_payload_json_invalido(self):
        conn = self._make_conn([("isso nao e json{{{",)])
        resultado = _ler_bronze(conn, "bronze.tabela")
        self.assertEqual(resultado, [])

    def test_tabela_vazia_retorna_lista_vazia(self):
        conn = self._make_conn([])
        resultado = _ler_bronze(conn, "bronze.tabela")
        self.assertEqual(resultado, [])


# ---------------------------------------------------------------------------
# processar_arboviroses
# ---------------------------------------------------------------------------

class ProcessarArbovirosesTests(unittest.TestCase):

    def _conn_com_bronze(self, payloads):
        """Cria mock de conexão que retorna payloads como bronze rows."""
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn_com_bronze([{
            "territorio": "Recife", "bairro": "Boa Viagem",
            "indicador": "dengue", "periodo": "2025-W01", "valor": 10,
        }])
        resultado = processar_arboviroses(conn)
        self.assertEqual(resultado["processados"], 1)
        conn.commit.assert_called()

    def test_ignora_registro_sem_indicador(self):
        conn = self._conn_com_bronze([
            {"bairro": "X", "periodo": "2025-W01", "valor": 5},  # sem indicador
        ])
        resultado = processar_arboviroses(conn)
        self.assertEqual(resultado["processados"], 0)

    def test_ignora_registro_sem_periodo(self):
        conn = self._conn_com_bronze([
            {"indicador": "dengue", "bairro": "X", "valor": 5},  # sem periodo
        ])
        resultado = processar_arboviroses(conn)
        self.assertEqual(resultado["processados"], 0)


# ---------------------------------------------------------------------------
# processar_defesa_civil
# ---------------------------------------------------------------------------

class ProcessarDefesaCivilTests(unittest.TestCase):

    def _conn_com_bronze(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn_com_bronze([{
            "territorio": "Recife", "bairro": "Afogados",
            "tipo_ocorrencia": "Deslizamento", "periodo": "2025-01", "valor": 3,
        }])
        resultado = processar_defesa_civil(conn)
        self.assertEqual(resultado["processados"], 1)

    def test_ignora_registro_sem_tipo(self):
        conn = self._conn_com_bronze([{"bairro": "X", "periodo": "2025-01", "valor": 1}])
        resultado = processar_defesa_civil(conn)
        self.assertEqual(resultado["processados"], 0)


# ---------------------------------------------------------------------------
# processar_animais_peconhentos
# ---------------------------------------------------------------------------

class ProcessarAnimaisTests(unittest.TestCase):

    def _conn_com_bronze(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn_com_bronze([{
            "territorio": "Pernambuco", "municipio": "Recife",
            "codigo_municipio": "261160", "periodo": "2026-W01", "valor": 7,
        }])
        resultado = processar_animais_peconhentos(conn)
        self.assertEqual(resultado["processados"], 1)

    def test_ignora_registro_sem_periodo(self):
        conn = self._conn_com_bronze([{
            "territorio": "PE", "municipio": "Recife", "codigo_municipio": "261160",
        }])
        resultado = processar_animais_peconhentos(conn)
        self.assertEqual(resultado["processados"], 0)


# ---------------------------------------------------------------------------
# processar_estacoes
# ---------------------------------------------------------------------------

class ProcessarEstacoesTests(unittest.TestCase):

    def _conn_com_bronze(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn_com_bronze([{
            "fonte": "inmet", "estacao": "A301",
            "nome": "Recife / PE", "municipio": "Recife",
            "latitude": -8.059, "longitude": -34.950, "situacao": "Operante",
        }])
        resultado = processar_estacoes(conn)
        self.assertEqual(resultado["processados"], 1)
        conn.commit.assert_called()

    def test_ignora_registro_sem_estacao(self):
        conn = self._conn_com_bronze([{"fonte": "inmet", "nome": "Sem código"}])
        resultado = processar_estacoes(conn)
        self.assertEqual(resultado["processados"], 0)

    def test_usa_fonte_padrao_inmet(self):
        conn = self._conn_com_bronze([{
            "estacao": "A301", "nome": "Recife",
            "municipio": "Recife", "latitude": -8.0, "longitude": -34.9,
        }])
        resultado = processar_estacoes(conn)
        # sem "fonte" no payload → usa "inmet" como padrão
        self.assertEqual(resultado["processados"], 1)


# ---------------------------------------------------------------------------
# processar_meteorologia
# ---------------------------------------------------------------------------

class ProcessarMeterologiaTests(unittest.TestCase):

    def _make_conn(self, payloads_por_tabela: dict):
        """payloads_por_tabela: { 'bronze.openmeteo_horario': [...], ... }"""
        tabelas_ordem = [
            "bronze.openmeteo_horario",
            "bronze.openmeteo_historico",
            "bronze.nasa_power_horario",
        ]
        cursors = []
        for tabela in tabelas_ordem:
            payloads = payloads_por_tabela.get(tabela, [])
            cur = MagicMock()
            cur.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
            cursors.append(cur)
        # cursor extra para o _upsert
        cursors.append(MagicMock())

        conn = MagicMock()
        conn.cursor.side_effect = cursors
        return conn

    def test_processa_multiplas_fontes(self):
        payload_base = {
            "fonte": "openmeteo", "estacao": "recife", "territorio": "Recife",
            "lida_em": NOW, "natureza_dado": "historico_modelado",
            "variaveis": {"temperatura_c": 28.0, "precipitacao_mm": 0.0,
                          "umidade_pct": 80.0, "pressao_hpa": 1012.0, "vento_ms": 2.0},
            "latitude": -8.05, "longitude": -34.9,
        }
        conn = self._make_conn({"bronze.openmeteo_horario": [payload_base]})
        resultado = processar_meteorologia(conn)
        self.assertEqual(resultado["processados"], 1)

    def test_linha_invalida_e_descartada(self):
        payload_sem_fonte = {
            "lida_em": NOW, "variaveis": {"temperatura_c": 25.0},
        }
        conn = self._make_conn({"bronze.openmeteo_horario": [payload_sem_fonte]})
        resultado = processar_meteorologia(conn)
        self.assertEqual(resultado["processados"], 0)


# ---------------------------------------------------------------------------
# silver_pipeline — orquestrador
# ---------------------------------------------------------------------------

class SilverPipelineTests(unittest.TestCase):

    @patch("silver.pipelines.silver_pipeline._aplicar_ddl")
    @patch("silver.pipelines.silver_pipeline.processar_estacoes")
    @patch("silver.pipelines.silver_pipeline.processar_animais_peconhentos")
    @patch("silver.pipelines.silver_pipeline.processar_defesa_civil")
    @patch("silver.pipelines.silver_pipeline.processar_arboviroses")
    @patch("silver.pipelines.silver_pipeline.processar_meteorologia")
    def test_chama_todas_as_fontes(self, mock_met, mock_arb, mock_dc, mock_ani, mock_est, mock_ddl):
        for m in (mock_met, mock_arb, mock_dc, mock_ani, mock_est):
            m.return_value = {"tabela": "silver.X", "processados": 1}

        conn = MagicMock()
        resultados = silver_pipeline(connection=conn, aplicar_ddl=True)

        self.assertEqual(len(resultados), 5)
        mock_ddl.assert_called_once()
        mock_met.assert_called_once_with(conn)
        mock_arb.assert_called_once_with(conn)
        mock_dc.assert_called_once_with(conn)
        mock_ani.assert_called_once_with(conn)
        mock_est.assert_called_once_with(conn)

    @patch("silver.pipelines.silver_pipeline._aplicar_ddl")
    @patch("silver.pipelines.silver_pipeline.processar_meteorologia")
    @patch("silver.pipelines.silver_pipeline.processar_arboviroses")
    @patch("silver.pipelines.silver_pipeline.processar_defesa_civil")
    @patch("silver.pipelines.silver_pipeline.processar_animais_peconhentos")
    @patch("silver.pipelines.silver_pipeline.processar_estacoes")
    def test_falha_em_uma_fonte_nao_para_as_demais(
        self, mock_est, mock_ani, mock_dc, mock_arb, mock_met, mock_ddl
    ):
        mock_met.side_effect = RuntimeError("erro simulado")
        for m in (mock_arb, mock_dc, mock_ani, mock_est):
            m.return_value = {"tabela": "silver.X", "processados": 2}

        conn = MagicMock()
        resultados = silver_pipeline(connection=conn, aplicar_ddl=False)

        self.assertEqual(len(resultados), 5)
        self.assertIn("erro", resultados[0])
        total = sum(r.get("processados", 0) for r in resultados)
        self.assertEqual(total, 8)  # 4 fontes × 2


if __name__ == "__main__":
    unittest.main()
