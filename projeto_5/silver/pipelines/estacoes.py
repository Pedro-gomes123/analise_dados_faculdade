"""Processador silver: bronze.inmet_estacoes → silver.Estacoes (PySpark).

Suporta dois formatos de payload: normalizado (estacao, latitude) e
bruto INMET (CD_ESTACAO, VL_LATITUDE). O COALESCE cobre ambos.
"""

import logging

from pyspark.sql import SparkSession

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.Estacoes"


def processar_estacoes(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Transforma metadados de estações INMET do bronze para silver.Estacoes."""
    df_raw = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT payload_json FROM bronze.inmet_estacoes WHERE payload_json IS NOT NULL) t",
        properties=jdbc_props,
    )
    df_raw.createOrReplaceTempView("_brnz_est")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                COALESCE(get_json_object(payload_json, '$.fonte'), 'inmet')             AS fonte,
                COALESCE(
                    get_json_object(payload_json, '$.estacao'),
                    get_json_object(payload_json, '$.CD_ESTACAO'),
                    get_json_object(payload_json, '$.CD_WSI')
                )                                                                        AS estacao,
                COALESCE(
                    get_json_object(payload_json, '$.nome'),
                    get_json_object(payload_json, '$.DC_NOME')
                )                                                                        AS nome,
                COALESCE(
                    get_json_object(payload_json, '$.municipio'),
                    get_json_object(payload_json, '$.NM_MUNICIPIO'),
                    get_json_object(payload_json, '$.DC_MUNICIPIO'),
                    get_json_object(payload_json, '$.SG_ESTADO')
                )                                                                        AS municipio,
                CAST(COALESCE(
                    get_json_object(payload_json, '$.latitude'),
                    get_json_object(payload_json, '$.VL_LATITUDE')
                ) AS DOUBLE)                                                             AS latitude,
                CAST(COALESCE(
                    get_json_object(payload_json, '$.longitude'),
                    get_json_object(payload_json, '$.VL_LONGITUDE')
                ) AS DOUBLE)                                                             AS longitude,
                COALESCE(
                    get_json_object(payload_json, '$.situacao'),
                    get_json_object(payload_json, '$.CD_SITUACAO')
                )                                                                        AS situacao,
                current_timestamp()                                                      AS atualizado_em
            FROM _brnz_est
        )
        SELECT fonte, estacao, nome, municipio, latitude, longitude, situacao, atualizado_em
        FROM raw
        WHERE estacao IS NOT NULL
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
