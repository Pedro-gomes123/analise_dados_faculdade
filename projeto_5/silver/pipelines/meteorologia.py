"""Processador silver: bronze → silver.Meteorologia (PySpark).

Unifica openmeteo_horario, openmeteo_historico e nasa_power_horario via
UNION ALL em Spark SQL com get_json_object. Usa UDF para parsear o timestamp
BSON Extended JSON ({"$date": "..."}) presente nos payloads climáticos.
NASA POWER envia pressão em kPa; a conversão ×10 fica no CASE WHEN do SQL.
"""

import datetime
import logging

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import TimestampType

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.Meteorologia"
_FONTES = [
    "bronze.openmeteo_horario",
    "bronze.openmeteo_historico",
    "bronze.nasa_power_horario",
]


@udf(returnType=TimestampType())
def _parse_bson_ts(json_str: str):
    """Extrai datetime de BSON Extended JSON: {"$date": "2026-11-15T12:00:00+00:00"}."""
    if not json_str:
        return None
    try:
        from bson import json_util
        obj = json_util.loads(json_str)
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is not None:
                return obj.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            return obj
    except Exception:
        pass
    return None


def processar_meteorologia(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Lê as três fontes climáticas do bronze e persiste em silver.Meteorologia."""
    spark.udf.register("parse_bson_ts", _parse_bson_ts)

    frames = [
        spark.read.jdbc(
            url=jdbc_url,
            table=f"(SELECT payload_json FROM {t} WHERE payload_json IS NOT NULL) t",
            properties=jdbc_props,
        )
        for t in _FONTES
    ]
    df_raw = frames[0].union(frames[1]).union(frames[2])
    df_raw.createOrReplaceTempView("_brnz_met")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                get_json_object(payload_json, '$.fonte')                              AS fonte,
                COALESCE(get_json_object(payload_json, '$.estacao'), '')              AS estacao,
                COALESCE(get_json_object(payload_json, '$.territorio'), 'Recife')    AS territorio,
                parse_bson_ts(get_json_object(payload_json, '$.lida_em'))             AS lida_em,
                get_json_object(payload_json, '$.natureza_dado')                      AS natureza_dado,
                CAST(get_json_object(payload_json, '$.variaveis.temperatura_c')   AS DOUBLE) AS temperatura_c,
                CAST(get_json_object(payload_json, '$.variaveis.precipitacao_mm') AS DOUBLE) AS precipitacao_mm,
                CAST(get_json_object(payload_json, '$.variaveis.umidade_pct')     AS DOUBLE) AS umidade_pct,
                CASE
                    WHEN get_json_object(payload_json, '$.variaveis.pressao_hpa') IS NOT NULL
                        THEN CAST(get_json_object(payload_json, '$.variaveis.pressao_hpa') AS DOUBLE)
                    ELSE CAST(get_json_object(payload_json, '$.variaveis.pressao_kpa') AS DOUBLE) * 10
                END                                                                   AS pressao_hpa,
                CAST(get_json_object(payload_json, '$.variaveis.vento_ms')        AS DOUBLE) AS vento_ms,
                CAST(get_json_object(payload_json, '$.latitude')                  AS DOUBLE) AS latitude,
                CAST(get_json_object(payload_json, '$.longitude')                 AS DOUBLE) AS longitude,
                current_timestamp()                                                   AS atualizado_em
            FROM _brnz_met
        )
        SELECT fonte, estacao, territorio, lida_em, natureza_dado,
               temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
               vento_ms, latitude, longitude, atualizado_em
        FROM raw
        WHERE fonte IS NOT NULL AND lida_em IS NOT NULL
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
