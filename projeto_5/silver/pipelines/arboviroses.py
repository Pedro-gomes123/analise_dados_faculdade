"""Processador silver: bronze.recife_arboviroses → silver.Arboviroses (PySpark)."""

import logging

from pyspark.sql import SparkSession

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.Arboviroses"


def processar_arboviroses(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Transforma contagens de arboviroses do bronze para silver.Arboviroses."""
    df_raw = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT payload_json FROM bronze.recife_arboviroses WHERE payload_json IS NOT NULL) t",
        properties=jdbc_props,
    )
    df_raw.createOrReplaceTempView("_brnz_arb")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                LOWER(COALESCE(get_json_object(payload_json, '$.territorio'), 'Recife'))   AS territorio,
                LOWER(COALESCE(get_json_object(payload_json, '$.bairro'), 'nao_informado')) AS bairro,
                LOWER(get_json_object(payload_json, '$.indicador'))                         AS indicador,
                get_json_object(payload_json, '$.periodo')                                   AS periodo,
                CAST(COALESCE(get_json_object(payload_json, '$.valor'), '0') AS INT)         AS casos
            FROM _brnz_arb
            WHERE get_json_object(payload_json, '$.indicador') IS NOT NULL
              AND get_json_object(payload_json, '$.periodo') IS NOT NULL
        )
        SELECT territorio, bairro, indicador, periodo,
               MAX(casos) AS casos,
               current_timestamp() AS atualizado_em
        FROM raw
        GROUP BY territorio, bairro, indicador, periodo
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
