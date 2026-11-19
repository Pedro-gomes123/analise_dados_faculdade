"""Processador silver: bronze.sinan_animais_peconhentos → silver.AnimaisPerconhentos (PySpark)."""

import logging

from pyspark.sql import SparkSession

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.AnimaisPerconhentos"


def processar_animais_peconhentos(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Transforma acidentes SINAN do bronze para silver.AnimaisPerconhentos."""
    df_raw = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT payload_json FROM bronze.sinan_animais_peconhentos WHERE payload_json IS NOT NULL) t",
        properties=jdbc_props,
    )
    df_raw.createOrReplaceTempView("_brnz_ani")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                LOWER(COALESCE(get_json_object(payload_json, '$.territorio'), 'Pernambuco'))         AS territorio,
                LOWER(COALESCE(get_json_object(payload_json, '$.municipio'), 'nao_informado'))         AS municipio,
                LOWER(COALESCE(get_json_object(payload_json, '$.codigo_municipio'), 'nao_informado'))  AS codigo_municipio,
                get_json_object(payload_json, '$.periodo')                                             AS periodo,
                CAST(COALESCE(get_json_object(payload_json, '$.valor'), '0') AS INT)                   AS casos
            FROM _brnz_ani
            WHERE get_json_object(payload_json, '$.periodo') IS NOT NULL
        )
        SELECT territorio, municipio, codigo_municipio, periodo,
               MAX(casos) AS casos,
               current_timestamp() AS atualizado_em
        FROM raw
        GROUP BY territorio, municipio, codigo_municipio, periodo
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
