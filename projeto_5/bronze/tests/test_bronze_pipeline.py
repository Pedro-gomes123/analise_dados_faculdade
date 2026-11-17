import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from bson import ObjectId, json_util

from bronze.pipeline import COLECOES_BRONZE, _export_collection, pipeline_bronze


class BronzePipelineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 12, 30, tzinfo=timezone.utc)

    # ------------------------------------------------------------------
    # _export_collection
    # ------------------------------------------------------------------

    def test_exports_collection_builds_correct_rows(self):
        """Verifica que _export_collection monta as linhas e chama writer.upsert."""
        document = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "fonte": "openmeteo",
            "tipo_dado": "meteorologia_horaria",
            "municipio": "Recife",
            "ingestao_ts": self.now,
            "payload": {"temperatura_c": 28.5},
        }
        collection = Mock()
        collection.find.return_value = [document]
        db = {"openmeteo_horario": collection}

        writer = Mock()
        writer.upsert.return_value = 1

        result = _export_collection(db, "openmeteo_horario", "bronze.openmeteo_horario", writer, self.now)

        self.assertEqual(result["documentos"], 1)
        self.assertEqual(result["inseridos"], 1)
        self.assertEqual(result["tabela"], "bronze.openmeteo_horario")
        self.assertEqual(result["colecao"], "openmeteo_horario")

        writer.upsert.assert_called_once()
        _, tabela_arg, rows_arg, _ = writer.upsert.call_args.args
        self.assertEqual(tabela_arg, "bronze.openmeteo_horario")
        self.assertEqual(len(rows_arg), 1)

        row = rows_arg[0]
        self.assertEqual(row["_id"], str(document["_id"]))
        self.assertEqual(row["fonte"], "openmeteo")
        self.assertEqual(row["ingestao_ts"], self.now)
        # payload_json deve conter o valor original
        payload = json_util.loads(row["payload_json"])
        self.assertAlmostEqual(payload["temperatura_c"], 28.5)
        # documento_json deve conter o documento completo
        doc_restaurado = json_util.loads(row["documento_json"])
        self.assertEqual(doc_restaurado["_id"], document["_id"])

    def test_empty_collection_skips_upsert(self):
        collection = Mock()
        collection.find.return_value = []
        writer = Mock()

        result = _export_collection(
            {"recife_arboviroses": collection},
            "recife_arboviroses",
            "bronze.recife_arboviroses",
            writer,
            self.now,
        )

        self.assertEqual(result["documentos"], 0)
        self.assertEqual(result["inseridos"], 0)
        writer.upsert.assert_not_called()

    def test_writer_failure_propagates(self):
        collection = Mock()
        collection.find.return_value = [{"_id": "abc", "valor": 1}]
        writer = Mock()
        writer.upsert.side_effect = RuntimeError("falha SQL")

        with self.assertRaisesRegex(RuntimeError, "falha SQL"):
            _export_collection(
                {"recife_defesa_civil": collection},
                "recife_defesa_civil",
                "bronze.recife_defesa_civil",
                writer,
                self.now,
            )

    # ------------------------------------------------------------------
    # pipeline_bronze
    # ------------------------------------------------------------------

    def test_pipeline_iterates_all_configured_collections(self):
        db = Mock()
        collection = Mock()
        collection.find.return_value = []
        db.__getitem__ = Mock(return_value=collection)

        writer = Mock()
        writer.upsert.return_value = 0

        results = pipeline_bronze(db, writer=writer, exported_at=self.now)

        self.assertEqual(len(results), len(COLECOES_BRONZE))
        self.assertEqual(db.__getitem__.call_count, len(COLECOES_BRONZE))

    def test_pipeline_sums_totals_correctly(self):
        """Verifica que o pipeline acumula documentos e inseridos de todas as coleções."""
        db = Mock()
        collection = Mock()
        collection.find.return_value = [{"_id": f"id{i}", "fonte": "test"} for i in range(3)]
        db.__getitem__ = Mock(return_value=collection)

        writer = Mock()
        writer.upsert.return_value = 3

        results = pipeline_bronze(db, writer=writer, exported_at=self.now)

        total_docs = sum(r["documentos"] for r in results)
        total_ins  = sum(r["inseridos"]  for r in results)
        self.assertEqual(total_docs, 3 * len(COLECOES_BRONZE))
        self.assertEqual(total_ins,  3 * len(COLECOES_BRONZE))

    def test_colecoes_bronze_values_are_bronze_schema(self):
        """Todas as tabelas devem estar no schema bronze."""
        for colecao, tabela in COLECOES_BRONZE.items():
            self.assertTrue(
                tabela.startswith("bronze."),
                f"{colecao}: tabela deve começar com 'bronze.' mas é '{tabela}'",
            )


if __name__ == "__main__":
    unittest.main()
