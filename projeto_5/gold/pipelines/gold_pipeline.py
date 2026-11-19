"""Pipeline Gold: transforma silver → gold com PySpark + Spark SQL.

Cada tabela gold é populada por uma query Spark SQL que lê as tabelas
silver como temp views via JDBC. O padrão é: TRUNCATE (pyodbc) + write.jdbc.

Tabelas geradas
---------------
gold.leitura_climatica   — cópia direta de silver.Meteorologia (colunas selecionadas)
gold.estacao             — cópia de silver.Estacoes
gold.indicador_territorio — UNION ALL de Arboviroses, DefesaCivil, AnimaisPerconhentos,
                            SAMU e AcidentesTransito com indicador/fonte normalizados

Ordem de execução
-----------------
    python3 -m mongo.main     # 1. coleta → MongoDB
    python3 -m bronze.main    # 2. MongoDB → bronze SQL Server
    python3 -m silver.main    # 3. bronze → silver SQL Server
    python3 -m gold.main      # 4. silver → gold SQL Server (este arquivo)
"""

import logging
import re
from pathlib import Path

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "gold" / "001_gold_tables.sql",
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _aplicar_ddl(connection, scripts=SQL_SCRIPTS) -> None:
    """Executa os scripts DDL do schema gold de forma idempotente."""
    cursor = connection.cursor()
    try:
        for caminho in scripts:
            script = Path(caminho).read_text(encoding="utf-8")
            for batch in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script):
                if batch.strip():
                    cursor.execute(batch)
                    connection.commit()
            logger.info("DDL gold aplicado: %s", Path(caminho).name)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _truncar(connection, tabela: str) -> None:
    """Trunca a tabela gold antes de recarregar via Spark JDBC."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"TRUNCATE TABLE {tabela}")
        connection.commit()
        logger.debug("Tabela truncada: %s", tabela)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _ler_silver(spark: SparkSession, jdbc_url: str, jdbc_props: dict, tabela: str, view: str) -> None:
    """Lê uma tabela silver via JDBC e registra como temp view."""
    spark.read.jdbc(url=jdbc_url, table=tabela, properties=jdbc_props) \
        .createOrReplaceTempView(view)


# ---------------------------------------------------------------------------
# Processadores gold
# ---------------------------------------------------------------------------

def processar_leitura_climatica(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Copia silver.Meteorologia para gold.leitura_climatica.

    gold.leitura_climatica omite vento_ms, latitude e longitude da silver —
    apenas as quatro variáveis climáticas compõem o componente do app.
    """
    _ler_silver(spark, jdbc_url, jdbc_props, "silver.Meteorologia", "_slvr_met")

    df = spark.sql("""
        SELECT
            fonte, estacao, territorio, lida_em, natureza_dado,
            temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
            current_timestamp() AS atualizado_em
        FROM _slvr_met
    """)

    total = df.count()
    _truncar(connection, "gold.leitura_climatica")
    df.write.jdbc(url=jdbc_url, table="gold.leitura_climatica", mode="append", properties=jdbc_props)
    logger.info("gold.leitura_climatica: %d linhas processadas", total)
    return {"tabela": "gold.leitura_climatica", "processados": total}


def processar_estacao(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Copia metadados de estações de silver.Estacoes para gold.estacao."""
    _ler_silver(spark, jdbc_url, jdbc_props, "silver.Estacoes", "_slvr_est")

    df = spark.sql("""
        SELECT fonte, estacao, nome, municipio, latitude, longitude, situacao,
               current_timestamp() AS atualizado_em
        FROM _slvr_est
    """)

    total = df.count()
    _truncar(connection, "gold.estacao")
    df.write.jdbc(url=jdbc_url, table="gold.estacao", mode="append", properties=jdbc_props)
    logger.info("gold.estacao: %d linhas processadas", total)
    return {"tabela": "gold.estacao", "processados": total}


def processar_indicador_territorio(
    spark: SparkSession, connection, jdbc_url: str, jdbc_props: dict
) -> dict:
    """Unifica cinco fontes silver em gold.indicador_territorio via UNION ALL em Spark SQL.

    Mapeamento de indicador por fonte:
      Arboviroses        → indicador (dengue, zika, etc.)
      DefesaCivil        → tipo_ocorrencia
      AnimaisPerconhentos → 'acidentes_animais_peconhentos' (fixo; bairro = municipio)
      SAMU               → 'samu_' + tipo_emergencia
      AcidentesTransito  → indicador
    """
    for tabela, view in [
        ("silver.Arboviroses",          "_slvr_arb"),
        ("silver.DefesaCivil",          "_slvr_dc"),
        ("silver.AnimaisPerconhentos",  "_slvr_ani"),
        ("silver.SAMU",                 "_slvr_samu"),
        ("silver.AcidentesTransito",    "_slvr_acid"),
    ]:
        _ler_silver(spark, jdbc_url, jdbc_props, tabela, view)

    df = spark.sql("""
        WITH
        arb AS (
            SELECT territorio, bairro, indicador, casos, periodo,
                   'recife_arboviroses' AS fonte
            FROM _slvr_arb
        ),
        dc AS (
            SELECT territorio, bairro, tipo_ocorrencia AS indicador, casos, periodo,
                   'defesa_civil' AS fonte
            FROM _slvr_dc
        ),
        ani AS (
            SELECT territorio, municipio AS bairro,
                   'acidentes_animais_peconhentos' AS indicador,
                   casos, periodo, 'sinan' AS fonte
            FROM _slvr_ani
        ),
        samu AS (
            SELECT territorio, bairro,
                   CONCAT('samu_', tipo_emergencia) AS indicador,
                   casos, periodo, 'recife_samu' AS fonte
            FROM _slvr_samu
        ),
        acid AS (
            SELECT territorio, bairro, indicador, casos, periodo,
                   'recife_acidentes_transito' AS fonte
            FROM _slvr_acid
        ),
        todos AS (
            SELECT * FROM arb
            UNION ALL SELECT * FROM dc
            UNION ALL SELECT * FROM ani
            UNION ALL SELECT * FROM samu
            UNION ALL SELECT * FROM acid
        )
        SELECT territorio, bairro, indicador,
               CAST(casos AS INT) AS valor,
               periodo, fonte,
               current_timestamp() AS atualizado_em
        FROM todos
    """)

    total = df.count()
    _truncar(connection, "gold.indicador_territorio")
    df.write.jdbc(url=jdbc_url, table="gold.indicador_territorio", mode="append", properties=jdbc_props)
    logger.info("gold.indicador_territorio: %d linhas processadas", total)
    return {"tabela": "gold.indicador_territorio", "processados": total}


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def gold_pipeline(connection=None, spark=None, aplicar_ddl: bool = True) -> list[dict]:
    """Orquestra a transformação silver → gold para todas as tabelas.

    Args:
        connection: Conexão pyodbc pré-existente; se None, abre automaticamente.
        spark:      SparkSession pré-existente; se None, cria automaticamente.
        aplicar_ddl: Se True, executa os scripts DDL do schema gold antes de processar.

    Returns:
        Lista de dicts, um por processador, com "tabela", "processados" e "erro" opcional.
    """
    from silver.database.sql_server import conectar_sql_server
    from silver.spark_session import criar_spark_session, jdbc_url_e_props

    owns_conn  = connection is None
    owns_spark = spark is None

    if owns_conn:
        connection = conectar_sql_server()
    if owns_spark:
        spark = criar_spark_session()

    jdbc_url, jdbc_props = jdbc_url_e_props()

    try:
        if aplicar_ddl:
            _aplicar_ddl(connection)

        fontes = [
            processar_leitura_climatica,
            processar_estacao,
            processar_indicador_territorio,
        ]
        resultados = []
        for fn in fontes:
            try:
                resultados.append(fn(spark, connection, jdbc_url, jdbc_props))
            except Exception as erro:
                logger.error(
                    "Falha em %s: %s", getattr(fn, "__name__", repr(fn)), type(erro).__name__
                )
                resultados.append({
                    "tabela":      getattr(fn, "__name__", repr(fn)),
                    "processados": 0,
                    "erro":        str(erro),
                })

        total = sum(r.get("processados", 0) for r in resultados)
        logger.info("Pipeline Gold concluído: %d linhas no total", total)
        return resultados
    finally:
        if owns_conn:
            connection.close()
        if owns_spark:
            spark.stop()
