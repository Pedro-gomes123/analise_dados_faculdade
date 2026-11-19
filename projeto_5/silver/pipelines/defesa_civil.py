"""Processador silver: bronze.recife_defesa_civil → silver.DefesaCivil (PySpark)."""

import logging

from pyspark.sql import SparkSession

from silver.pipelines._base import _truncar

logger = logging.getLogger(__name__)

_TABELA = "silver.DefesaCivil"


def processar_defesa_civil(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Transforma atendimentos da Defesa Civil do bronze para silver.DefesaCivil."""
    df_raw = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT payload_json FROM bronze.recife_defesa_civil WHERE payload_json IS NOT NULL) t",
        properties=jdbc_props,
    )
    df_raw.createOrReplaceTempView("_brnz_dc")

    df = spark.sql("""
        WITH raw AS (
            SELECT
                LOWER(COALESCE(get_json_object(payload_json, '$.territorio'), 'Recife'))        AS territorio,
                LOWER(COALESCE(get_json_object(payload_json, '$.bairro'), 'nao_informado'))      AS bairro,
                LOWER(get_json_object(payload_json, '$.tipo_ocorrencia'))                        AS tipo_ocorrencia,
                get_json_object(payload_json, '$.periodo')                                        AS periodo,
                CAST(COALESCE(get_json_object(payload_json, '$.valor'), '0') AS INT)              AS casos
            FROM _brnz_dc
            WHERE get_json_object(payload_json, '$.tipo_ocorrencia') IS NOT NULL
              AND get_json_object(payload_json, '$.periodo') IS NOT NULL
        )
        SELECT territorio, bairro, tipo_ocorrencia, periodo,
               MAX(casos) AS casos,
               current_timestamp() AS atualizado_em
        FROM raw
        GROUP BY territorio, bairro, tipo_ocorrencia, periodo
    """)

    total = df.count()
    _truncar(connection, _TABELA)
    df.write.jdbc(url=jdbc_url, table=_TABELA, mode="append", properties=jdbc_props)
    logger.info("%s: %d linhas processadas", _TABELA, total)
    return {"tabela": _TABELA, "processados": total}
