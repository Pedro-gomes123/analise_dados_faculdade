"""Processador silver: bronze.recife_samu → silver.SAMU (PySpark).

O payload armazena o indicador como "samu_<tipo>". O SUBSTRING(6) remove o
prefixo "samu_" (5 caracteres) para armazenar apenas o tipo na silver.
"""

import logging

from pyspark.sql import SparkSession

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.SAMU"


def processar_samu(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Transforma chamados SAMU do bronze para silver.SAMU."""
    df_raw = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT payload_json FROM bronze.recife_samu WHERE payload_json IS NOT NULL) t",
        properties=jdbc_props,
    )
    df_raw.createOrReplaceTempView("_brnz_samu")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                LOWER(COALESCE(get_json_object(payload_json, '$.territorio'), 'Recife'))    AS territorio,
                LOWER(COALESCE(get_json_object(payload_json, '$.bairro'), 'nao_informado'))  AS bairro,
                LOWER(CASE
                    WHEN get_json_object(payload_json, '$.indicador') LIKE 'samu_%'
                        THEN SUBSTRING(get_json_object(payload_json, '$.indicador'), 6)
                    ELSE get_json_object(payload_json, '$.indicador')
                END)                                                                         AS tipo_emergencia,
                get_json_object(payload_json, '$.periodo')                                   AS periodo,
                CAST(COALESCE(get_json_object(payload_json, '$.valor'), '0') AS INT)         AS casos
            FROM _brnz_samu
            WHERE get_json_object(payload_json, '$.indicador') IS NOT NULL
              AND get_json_object(payload_json, '$.periodo') IS NOT NULL
        )
        SELECT territorio, bairro, tipo_emergencia, periodo,
               MAX(casos) AS casos,
               current_timestamp() AS atualizado_em
        FROM raw
        GROUP BY territorio, bairro, tipo_emergencia, periodo
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
