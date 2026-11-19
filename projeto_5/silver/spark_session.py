"""SparkSession factory e configuração JDBC para SQL Server.

Centraliza a criação do SparkSession e os parâmetros de conexão JDBC
usados por todos os processadores silver e gold.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def criar_spark_session() -> SparkSession:
    """Cria ou reutiliza um SparkSession local com o driver JDBC SQL Server."""
    return (
        SparkSession.builder
        .appName("vigia_silver_gold")
        .master("local[*]")
        .config(
            "spark.jars.packages",
            "com.microsoft.sqlserver:mssql-jdbc:12.6.1.jre11",
        )
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def jdbc_url_e_props() -> tuple[str, dict]:
    """Retorna (url, props) para leitura/escrita JDBC no SQL Server."""
    load_dotenv(ENV_FILE)
    server   = os.environ["SQL_SERVER"]
    database = os.environ["SQL_DATABASE"]
    user     = os.environ["SQL_USERNAME"]
    password = os.environ["SQL_PASSWORD"]
    trust    = os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "no").lower()
    trust_cert = "true" if trust == "yes" else "false"
    url = (
        f"jdbc:sqlserver://{server}:1433;"
        f"databaseName={database};"
        f"encrypt=true;"
        f"trustServerCertificate={trust_cert};"
    )
    props = {
        "user":     user,
        "password": password,
        "driver":   "com.microsoft.sqlserver.jdbc.SQLServerDriver",
    }
    return url, props
