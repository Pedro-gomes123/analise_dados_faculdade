import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pyarrow as pa
import pyarrow.parquet as pq

from silver.pipelines.bronze_to_staging import (
    carregar_arquivo_inmet,
    fonte_para_blob,
    ler_parquet_inmet,
)


def make_parquet() -> bytes:
    schema = pa.schema(
        [
            pa.field("_id", pa.string()),
            pa.field("fonte", pa.string()),
            pa.field("tipo_dado", pa.string()),
            pa.field("municipio", pa.string()),
            pa.field("ingestao_ts", pa.timestamp("us", tz="UTC")),
            pa.field("payload_json", pa.string()),
            pa.field("documento_json", pa.string()),
        ]
    )
    rows = [
        {
            "_id": "a" * 64,
            "fonte": "inmet",
            "tipo_dado": "estacao_automatica",
            "municipio": "Pernambuco",
            "ingestao_ts": datetime(2026, 11, 3, tzinfo=timezone.utc),
            "payload_json": '{"CD_ESTACAO":"A388"}',
            "documento_json": '{"_id":"' + "a" * 64 + '"}',
        }
    ]
    output = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), output)
    return output.getvalue().to_pybytes()


class FakeCursor:
    def __init__(self, processed=None, fail_insert=False):
        self.processed = processed
        self.fail_insert = fail_insert
        self.executed = []
        self.inserted = []
        self.fast_executemany = False
        self.closed = False

    def execute(self, sql, *params):
        self.executed.append((sql, params))
        return self

    def fetchone(self):
        return self.processed

    def executemany(self, sql, values):
        if self.fail_insert:
            raise RuntimeError("insert failure")
        self.inserted.extend(values)

    def close(self):
        self.closed = True


class BronzeToStagingTests(unittest.TestCase):
    def test_reads_real_bronze_schema_shape_and_types(self):
        rows = ler_parquet_inmet(make_parquet())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fonte"], "inmet")
        self.assertEqual(rows[0]["ingestao_ts"].utcoffset().total_seconds(), 0)

    def test_rejects_unmapped_blob_source(self):
        with self.assertRaises(ValueError):
            fonte_para_blob("s2id/desastres/arquivo.parquet")

    def test_loads_file_and_tracks_idempotency_metadata(self):
        cursor = FakeCursor()
        connection = Mock()
        connection.cursor.return_value = cursor
        blob_name = "inmet/estacoes/ano=2026/mes=11/dia=03/test.parquet"
        blob = Mock()
        blob.download_blob.return_value.readall.return_value = make_parquet()
        container = Mock()
        container.get_blob_client.return_value = blob

        result = carregar_arquivo_inmet(connection, container, blob_name)

        self.assertEqual(result["lidos"], 1)
        self.assertEqual(result["inseridos"], 1)
        self.assertEqual(result["status"], "concluido")
        self.assertEqual(len(cursor.inserted), 1)
        self.assertEqual(len(cursor.inserted[0][0]), 32)
        self.assertGreaterEqual(connection.commit.call_count, 2)

    def test_skips_a_completed_file(self):
        cursor = FakeCursor(processed=("concluido",))
        connection = Mock()
        connection.cursor.return_value = cursor
        blob = Mock()
        blob.download_blob.return_value.readall.return_value = make_parquet()
        container = Mock()
        container.get_blob_client.return_value = blob

        result = carregar_arquivo_inmet(
            connection,
            container,
            "inmet/estacoes/ano=2026/mes=11/dia=03/test.parquet",
        )

        self.assertEqual(result["status"], "ignorado")
        self.assertEqual(result["inseridos"], 0)
        self.assertFalse(cursor.inserted)
        connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
