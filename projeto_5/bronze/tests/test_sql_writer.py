"""Testes unitários do BronzeSqlWriter e casos extremos do pipeline bronze."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, call, patch

from bson import ObjectId

from bronze.pipeline import COLECOES_BRONZE, _export_collection
from bronze.sql_writer import BronzeSqlWriter, _validar_tabela


NOW = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# _validar_tabela
# ---------------------------------------------------------------------------

class ValidarTabelaTests(unittest.TestCase):

    def test_aceita_nomes_validos(self):
        for nome in ("bronze.openmeteo_horario", "bronze.nasa_power_horario", "schema.tabela_123"):
            with self.subTest(nome=nome):
                _validar_tabela(nome)  # não deve lançar

    def test_rejeita_nome_com_espacos(self):
        with self.assertRaises(ValueError):
            _validar_tabela("bronze. openmeteo")

    def test_rejeita_injecao_sql_ponto_virgula(self):
        with self.assertRaises(ValueError):
            _validar_tabela("bronze.tabela; DROP TABLE bronze.tabela--")

    def test_rejeita_injecao_sql_aspas(self):
        with self.assertRaises(ValueError):
            _validar_tabela("bronze.tabela'--")

    def test_rejeita_string_vazia(self):
        with self.assertRaises(ValueError):
            _validar_tabela("")

    def test_rejeita_nome_com_traco(self):
        with self.assertRaises(ValueError):
            _validar_tabela("bronze.minha-tabela")


# ---------------------------------------------------------------------------
# BronzeSqlWriter.upsert
# ---------------------------------------------------------------------------

class BronzeSqlWriterUpsertTests(unittest.TestCase):

    def _make_writer(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return BronzeSqlWriter(conn), conn, cursor

    def test_upsert_vazio_nao_chama_executemany(self):
        writer, conn, cursor = self._make_writer()
        writer._registrar_log = Mock()

        result = writer.upsert("colecao", "bronze.tabela", [], NOW)

        self.assertEqual(result, 0)
        cursor.executemany.assert_not_called()
        writer._registrar_log.assert_called_once_with("colecao", "bronze.tabela", NOW, 0, 0)

    def test_upsert_chama_executemany_com_parametros_corretos(self):
        writer, conn, cursor = self._make_writer()
        writer._registrar_log = Mock()

        rows = [
            {
                "_id": "abc123",
                "fonte": "openmeteo",
                "tipo_dado": "meteorologia",
                "municipio": "Recife",
                "ingestao_ts": NOW,
                "payload_json": '{"t": 28}',
                "documento_json": '{"_id": "abc123"}',
            }
        ]
        result = writer.upsert("colecao", "bronze.openmeteo_horario", rows, NOW)

        self.assertEqual(result, 1)
        cursor.executemany.assert_called_once()
        sql_arg, params_arg = cursor.executemany.call_args.args
        self.assertIn("bronze.openmeteo_horario", sql_arg)
        self.assertIn("MERGE", sql_arg.upper())
        self.assertEqual(len(params_arg), 1)
        p = params_arg[0]
        self.assertEqual(p[0], "abc123")           # _id
        self.assertEqual(p[1], "openmeteo")        # fonte
        self.assertEqual(p[4], NOW.isoformat())    # ingestao_ts
        self.assertEqual(p[7], NOW.isoformat())    # exportado_em
        conn.commit.assert_called()

    def test_upsert_rollback_em_falha(self):
        writer, conn, cursor = self._make_writer()
        cursor.executemany.side_effect = RuntimeError("erro SQL")

        with self.assertRaises(RuntimeError):
            writer.upsert("col", "bronze.tabela", [{"_id": "x"}], NOW)

        conn.rollback.assert_called_once()

    def test_upsert_rejeita_tabela_invalida(self):
        writer, conn, cursor = self._make_writer()
        with self.assertRaises(ValueError):
            writer.upsert("col", "bronze.tabela'; DROP TABLE x--", [{"_id": "x"}], NOW)
        cursor.executemany.assert_not_called()

    def test_upsert_linha_sem_ingestao_ts_usa_none(self):
        writer, conn, cursor = self._make_writer()
        writer._registrar_log = Mock()

        rows = [{"_id": "sem_ts", "fonte": "teste"}]
        writer.upsert("col", "bronze.tabela", rows, NOW)

        _, params_arg = cursor.executemany.call_args.args
        self.assertIsNone(params_arg[0][4])  # ingestao_ts deve ser None


# ---------------------------------------------------------------------------
# BronzeSqlWriter.aplicar_ddl
# ---------------------------------------------------------------------------

class BronzeSqlWriterDdlTests(unittest.TestCase):

    def test_aplicar_ddl_divide_em_batches_por_go(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        writer = BronzeSqlWriter(conn)

        script_fake = "CREATE SCHEMA bronze;\nGO\nCREATE TABLE bronze.t (id INT);\nGO\n"
        fake_path = Mock()
        fake_path.read_text.return_value = script_fake

        with patch("bronze.sql_writer.Path") as MockPath:
            MockPath.return_value = fake_path
            writer.aplicar_ddl(scripts=["dummy.sql"])

        # 2 batches não vazios → 2 execute + 2 commit
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertEqual(conn.commit.call_count, 2)

    def test_aplicar_ddl_rollback_em_falha(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = RuntimeError("erro DDL")
        writer = BronzeSqlWriter(conn)

        fake_path = Mock()
        fake_path.read_text.return_value = "CREATE SCHEMA bronze;\n"

        with patch("bronze.sql_writer.Path") as MockPath:
            MockPath.return_value = fake_path
            with self.assertRaises(RuntimeError):
                writer.aplicar_ddl(scripts=["dummy.sql"])

        conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# _export_collection — edge cases de dados
# ---------------------------------------------------------------------------

class ExportCollectionEdgeCaseTests(unittest.TestCase):

    def _make_writer(self, return_value=1):
        w = Mock()
        w.upsert.return_value = return_value
        return w

    def test_ingestao_ts_naive_e_convertido_para_utc(self):
        """datetime sem fuso deve receber UTC antes de serializar."""
        naive_ts = datetime(2026, 1, 15, 8, 30)  # sem tzinfo
        doc = {"_id": "id1", "ingestao_ts": naive_ts, "fonte": "teste"}
        collection = Mock()
        collection.find.return_value = [doc]
        writer = self._make_writer()

        _export_collection({"col": collection}, "col", "bronze.col", writer, NOW)

        _, _, rows, _ = writer.upsert.call_args.args
        # Deve ter tzinfo UTC
        self.assertIsNotNone(rows[0]["ingestao_ts"].tzinfo)
        self.assertEqual(rows[0]["ingestao_ts"], naive_ts.replace(tzinfo=timezone.utc))

    def test_documento_sem_payload_usa_none(self):
        """Documentos sem campo 'payload' devem gerar payload_json = None."""
        doc = {"_id": "id2", "fonte": "sinan"}
        collection = Mock()
        collection.find.return_value = [doc]
        writer = self._make_writer()

        _export_collection({"col": collection}, "col", "bronze.col", writer, NOW)

        _, _, rows, _ = writer.upsert.call_args.args
        self.assertIsNone(rows[0]["payload_json"])

    def test_documento_com_objectid_serializado_como_string(self):
        """_id do tipo ObjectId deve virar string no row."""
        oid = ObjectId("507f1f77bcf86cd799439011")
        doc = {"_id": oid, "fonte": "mongo"}
        collection = Mock()
        collection.find.return_value = [doc]
        writer = self._make_writer()

        _export_collection({"col": collection}, "col", "bronze.col", writer, NOW)

        _, _, rows, _ = writer.upsert.call_args.args
        self.assertIsInstance(rows[0]["_id"], str)
        self.assertEqual(rows[0]["_id"], str(oid))

    def test_multiplos_documentos_geram_multiplas_linhas(self):
        docs = [{"_id": f"id{i}", "fonte": "openmeteo"} for i in range(5)]
        collection = Mock()
        collection.find.return_value = docs
        writer = self._make_writer(return_value=5)

        result = _export_collection({"col": collection}, "col", "bronze.col", writer, NOW)

        _, _, rows, _ = writer.upsert.call_args.args
        self.assertEqual(len(rows), 5)
        self.assertEqual(result["documentos"], 5)
        self.assertEqual(result["inseridos"], 5)


# ---------------------------------------------------------------------------
# COLECOES_BRONZE — integridade do mapeamento
# ---------------------------------------------------------------------------

class ColecoesBronzeTests(unittest.TestCase):

    def test_sem_duplicatas_de_tabela(self):
        tabelas = list(COLECOES_BRONZE.values())
        self.assertEqual(len(tabelas), len(set(tabelas)), "Tabelas duplicadas em COLECOES_BRONZE")

    def test_todas_no_schema_bronze(self):
        for colecao, tabela in COLECOES_BRONZE.items():
            self.assertTrue(tabela.startswith("bronze."), f"{colecao} → {tabela}")

    def test_nome_tabela_bate_com_nome_colecao(self):
        for colecao, tabela in COLECOES_BRONZE.items():
            sufixo = tabela.split(".", 1)[1]
            self.assertEqual(sufixo, colecao, f"Tabela '{tabela}' deveria ter sufixo '{colecao}'")


if __name__ == "__main__":
    unittest.main()
