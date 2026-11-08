import pyarrow as pa
import pyarrow.parquet as pq
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from bson import ObjectId, json_util

from bronze.pipeline import _export_collection, pipeline_bronze


class BronzePipelineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 12, 30, tzinfo=timezone.utc)

    def test_exports_parquet_table_preserving_full_bson_document(self):
        document = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "fonte": "inmet",
            "tipo_dado": "observacao_horaria",
            "municipio": "Recife",
            "ingestao_ts": self.now,
            "payload": {"created": self.now, "valor": 12.3},
        }
        collection = Mock()
        collection.find.return_value = [document]
        db = {"inmet_observacoes": collection}
        storage = Mock()

        result = _export_collection(
            db, "inmet_observacoes", "inmet/observacoes", storage, self.now
        )

        self.assertEqual(result["documentos"], 1)
        self.assertIn("ano=2026/mes=11/dia=03/", result["blob"])
        self.assertTrue(result["blob"].endswith(".parquet"))
        content = storage.upload.call_args.args[1]
        table = pq.read_table(pa.BufferReader(content))
        self.assertIn("inmet/observacoes/", result["blob"])
        self.assertIn("documento_json", table.column_names)
        restored = json_util.loads(table.column("documento_json")[0].as_py())
        self.assertEqual(restored["_id"], document["_id"])
        self.assertEqual(restored["payload"]["valor"], 12.3)
        self.assertEqual(table.column("fonte")[0].as_py(), "inmet")
        self.assertEqual(table.num_rows, 1)
        collection.find.assert_called_once_with({})

    def test_empty_collection_creates_no_blob(self):
        collection = Mock()
        collection.find.return_value = []
        storage = Mock()

        result = _export_collection(
            {"inmet_estacoes": collection},
            "inmet_estacoes",
            "inmet/estacoes",
            storage,
            self.now,
        )

        self.assertEqual(result["documentos"], 0)
        self.assertIsNone(result["blob"])
        storage.upload.assert_not_called()

    def test_upload_failure_propagates(self):
        collection = Mock()
        collection.find.return_value = [{"valor": 1}]
        storage = Mock()
        storage.upload.side_effect = RuntimeError("upload falhou")

        with self.assertRaisesRegex(RuntimeError, "upload falhou"):
            _export_collection(
                {"inmet_estacoes": collection},
                "inmet_estacoes",
                "inmet/estacoes",
                storage,
                self.now,
            )

    def test_pipeline_iterates_all_configured_collections(self):
        db = Mock()
        collection = Mock()
        collection.find.return_value = []
        db.__getitem__ = Mock(return_value=collection)

        results = pipeline_bronze(db, storage=Mock(), exported_at=self.now)

        self.assertEqual(len(results), 6)
        self.assertEqual(db.__getitem__.call_count, 6)


if __name__ == "__main__":
    unittest.main()
