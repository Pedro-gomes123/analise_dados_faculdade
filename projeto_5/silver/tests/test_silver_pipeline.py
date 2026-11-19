"""Testes unitários do pipeline silver."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from bson import json_util

from silver.pipelines._base import _ler_bronze, _ts
from silver.pipelines.meteorologia import _linha_meteorologia, processar_meteorologia
from silver.pipelines.arboviroses import processar_arboviroses
from silver.pipelines.defesa_civil import processar_defesa_civil
from silver.pipelines.animais_peconhentos import processar_animais_peconhentos
from silver.pipelines.estacoes import processar_estacoes
from silver.pipelines.silver_pipeline import silver_pipeline

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
        self.assertEqual(linha[0], "openmeteo")
        self.assertAlmostEqual(linha[5], 28.0)
        self.assertAlmostEqual(linha[8], 1013.0)

    def test_nasa_power_converte_kpa_para_hpa(self):
        p = self._payload_openmeteo()
        p["fonte"] = "nasa_power"
        p["variaveis"] = {
            "temperatura_c": 26.0,
            "precipitacao_mm": 1.0,
            "umidade_pct": 85.0,
            "pressao_kpa": 101.3,
            "vento_ms": 2.0,
        }
        linha = _linha_meteorologia(p, NOW_ISO)
        self.assertIsNotNone(linha)
        self.assertAlmostEqual(linha[8], 1013.0, places=1)

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
        self.assertIsNone(linha[5])
        self.assertIsNone(linha[8])


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
        conn = self._make_conn([(json_util.dumps(payload),)])
        resultado = _ler_bronze(conn, "bronze.openmeteo_horario")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fonte"], "openmeteo")

    def test_ignora_payload_json_invalido(self):
        conn = self._make_conn([("isso nao e json{{{",)])
        self.assertEqual(_ler_bronze(conn, "bronze.tabela"), [])

    def test_tabela_vazia_retorna_lista_vazia(self):
        conn = self._make_conn([])
        self.assertEqual(_ler_bronze(conn, "bronze.tabela"), [])


# ---------------------------------------------------------------------------
# processar_arboviroses
# ---------------------------------------------------------------------------

class ProcessarArbovirosesTests(unittest.TestCase):

    def _conn(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn([{
            "territorio": "Recife", "bairro": "Boa Viagem",
            "indicador": "dengue", "periodo": "2025-W01", "valor": 10,
        }])
        self.assertEqual(processar_arboviroses(conn)["processados"], 1)

    def test_ignora_registro_sem_indicador(self):
        conn = self._conn([{"bairro": "X", "periodo": "2025-W01", "valor": 5}])
        self.assertEqual(processar_arboviroses(conn)["processados"], 0)

    def test_ignora_registro_sem_periodo(self):
        conn = self._conn([{"indicador": "dengue", "bairro": "X", "valor": 5}])
        self.assertEqual(processar_arboviroses(conn)["processados"], 0)


# ---------------------------------------------------------------------------
# processar_defesa_civil
# ---------------------------------------------------------------------------

class ProcessarDefesaCivilTests(unittest.TestCase):

    def _conn(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn([{
            "territorio": "Recife", "bairro": "Afogados",
            "tipo_ocorrencia": "Deslizamento", "periodo": "2025-01", "valor": 3,
        }])
        self.assertEqual(processar_defesa_civil(conn)["processados"], 1)

    def test_ignora_registro_sem_tipo(self):
        conn = self._conn([{"bairro": "X", "periodo": "2025-01", "valor": 1}])
        self.assertEqual(processar_defesa_civil(conn)["processados"], 0)


# ---------------------------------------------------------------------------
# processar_animais_peconhentos
# ---------------------------------------------------------------------------

class ProcessarAnimaisTests(unittest.TestCase):

    def _conn(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn([{
            "territorio": "Pernambuco", "municipio": "Recife",
            "codigo_municipio": "261160", "periodo": "2026-W01", "valor": 7,
        }])
        self.assertEqual(processar_animais_peconhentos(conn)["processados"], 1)

    def test_ignora_registro_sem_periodo(self):
        conn = self._conn([{
            "territorio": "PE", "municipio": "Recife", "codigo_municipio": "261160",
        }])
        self.assertEqual(processar_animais_peconhentos(conn)["processados"], 0)


# ---------------------------------------------------------------------------
# processar_estacoes
# ---------------------------------------------------------------------------

class ProcessarEstacoesTests(unittest.TestCase):

    def _conn(self, payloads):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(json_util.dumps(p),) for p in payloads]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_monta_params_corretos(self):
        conn = self._conn([{
            "fonte": "inmet", "estacao": "A301",
            "nome": "Recife / PE", "municipio": "Recife",
            "latitude": -8.059, "longitude": -34.950, "situacao": "Operante",
        }])
        self.assertEqual(processar_estacoes(conn)["processados"], 1)

    def test_ignora_registro_sem_estacao(self):
        conn = self._conn([{"fonte": "inmet", "nome": "Sem código"}])
        self.assertEqual(processar_estacoes(conn)["processados"], 0)

    def test_usa_fonte_padrao_inmet(self):
        conn = self._conn([{
            "estacao": "A301", "nome": "Recife",
            "municipio": "Recife", "latitude": -8.0, "longitude": -34.9,
        }])
        self.assertEqual(processar_estacoes(conn)["processados"], 1)


# ---------------------------------------------------------------------------
# processar_meteorologia
# ---------------------------------------------------------------------------

class ProcessarMeterologiaTests(unittest.TestCase):

    def _make_conn(self, payloads_por_tabela: dict):
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
        cursors.append(MagicMock())  # cursor do _upsert
        conn = MagicMock()
        conn.cursor.side_effect = cursors
        return conn

    def test_processa_payload_valido(self):
        payload = {
            "fonte": "openmeteo", "estacao": "recife", "territorio": "Recife",
            "lida_em": NOW, "natureza_dado": "historico_modelado",
            "variaveis": {"temperatura_c": 28.0, "precipitacao_mm": 0.0,
                          "umidade_pct": 80.0, "pressao_hpa": 1012.0, "vento_ms": 2.0},
            "latitude": -8.05, "longitude": -34.9,
        }
        conn = self._make_conn({"bronze.openmeteo_horario": [payload]})
        self.assertEqual(processar_meteorologia(conn)["processados"], 1)

    def test_linha_invalida_e_descartada(self):
        conn = self._make_conn({"bronze.openmeteo_horario": [{"lida_em": NOW}]})
        self.assertEqual(processar_meteorologia(conn)["processados"], 0)


# ---------------------------------------------------------------------------
# silver_pipeline — orquestrador
# ---------------------------------------------------------------------------

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

    @patch("silver.pipelines.silver_pipeline._aplicar_ddl")
    def test_chama_todos_os_processadores(self, mock_ddl):
        mocks = [p.start() for p in self._patches()]
        for m in mocks:
            m.return_value = {"tabela": "silver.X", "processados": 1}
        try:
            conn = MagicMock()
            resultados = silver_pipeline(connection=conn, aplicar_ddl=True)
            self.assertEqual(len(resultados), 7)
            mock_ddl.assert_called_once()
            for m in mocks:
                m.assert_called_once_with(conn)
        finally:
            for p in self._patches():
                p.stop()

    @patch("silver.pipelines.silver_pipeline._aplicar_ddl")
    def test_falha_em_uma_fonte_nao_para_as_demais(self, _mock_ddl):
        mocks = [p.start() for p in self._patches()]
        mocks[0].side_effect = RuntimeError("erro simulado")  # meteorologia falha
        for m in mocks[1:]:
            m.return_value = {"tabela": "silver.X", "processados": 2}
        try:
            conn = MagicMock()
            resultados = silver_pipeline(connection=conn, aplicar_ddl=False)
            self.assertEqual(len(resultados), 7)
            self.assertIn("erro", resultados[0])
            total = sum(r.get("processados", 0) for r in resultados)
            self.assertEqual(total, 12)  # 6 fontes × 2
        finally:
            for p in self._patches():
                p.stop()


if __name__ == "__main__":
    unittest.main()
