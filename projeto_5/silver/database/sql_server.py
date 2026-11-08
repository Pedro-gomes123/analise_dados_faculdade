"""Conexão com SQL Server/Azure SQL usando o driver oficial mssql-python."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
AUTH_MODES = {
    "ActiveDirectoryInteractive",
    "ActiveDirectoryServicePrincipal",
    "SqlPassword",
}


def verificar_driver_sql_server() -> str:
    """Verifica o driver Microsoft empacotado, sem depender de ODBC do sistema."""
    try:
        import mssql_python
    except ImportError as error:
        raise RuntimeError(
            "Driver SQL ausente. Instale as dependências com "
            "python3 -m pip install -r silver/requirements.txt."
        ) from error
    return f"mssql-python {getattr(mssql_python, '__version__', '')}".strip()


def _required_config(config: dict[str, str], names: tuple[str, ...]) -> dict[str, str]:
    missing = [name for name in names if not config.get(name)]
    if missing:
        raise RuntimeError("Variáveis SQL ausentes: " + ", ".join(missing))
    return {name: config[name] for name in names}


def _connection_value(value: str) -> str:
    """Escapa valores de connection string com caracteres especiais."""
    return "{" + value.replace("}", "}}") + "}"


def _connection_string(auth_mode: str, config: dict[str, str]) -> str:
    server = config["SQL_SERVER"]
    if "," not in server and "\\" not in server:
        server = f"{server},{config.get('SQL_PORT', '1433')}"

    encrypt = config.get("SQL_ENCRYPT", "yes").lower()
    trust = config.get("SQL_TRUST_SERVER_CERTIFICATE", "no").lower()
    if encrypt not in {"yes", "no"} or trust not in {"yes", "no"}:
        raise RuntimeError("SQL_ENCRYPT e SQL_TRUST_SERVER_CERTIFICATE aceitam yes ou no.")

    parts = [
        f"Server={_connection_value(server)}",
        f"Database={_connection_value(config['SQL_DATABASE'])}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust}",
    ]

    if auth_mode == "SqlPassword":
        credentials = _required_config(config, ("SQL_USERNAME", "SQL_PASSWORD"))
        parts.extend(
            (
                f"UID={_connection_value(credentials['SQL_USERNAME'])}",
                f"PWD={_connection_value(credentials['SQL_PASSWORD'])}",
            )
        )
    elif auth_mode == "ActiveDirectoryInteractive":
        parts.append("Authentication=ActiveDirectoryInteractive")
    elif auth_mode == "ActiveDirectoryServicePrincipal":
        credentials = _required_config(config, ("SQL_CLIENT_ID", "SQL_CLIENT_SECRET"))
        parts.extend(
            (
                "Authentication=ActiveDirectoryServicePrincipal",
                f"UID={_connection_value(credentials['SQL_CLIENT_ID'])}",
                f"PWD={_connection_value(credentials['SQL_CLIENT_SECRET'])}",
            )
        )
    else:
        raise RuntimeError(
            "SQL_AUTH_MODE inválido. Use ActiveDirectoryInteractive, "
            "ActiveDirectoryServicePrincipal ou SqlPassword."
        )
    return ";".join(parts) + ";"


def conectar_sql_server():
    """Abre e valida uma conexão; cabe ao chamador fechar o recurso."""
    load_dotenv(ENV_FILE)
    config = {key: value for key, value in os.environ.items() if key.startswith("SQL_")}
    config.update(_required_config(config, ("SQL_SERVER", "SQL_DATABASE")))

    # Compatibilidade com o .env local que tem SQL_USERNAME/SQL_PASSWORD,
    # mas ainda não define SQL_AUTH_MODE. MFA permanece como fallback seguro.
    auth_mode = config.get("SQL_AUTH_MODE")
    if not auth_mode:
        auth_mode = (
            "SqlPassword"
            if config.get("SQL_USERNAME") and config.get("SQL_PASSWORD")
            else "ActiveDirectoryInteractive"
        )
    if auth_mode not in AUTH_MODES:
        raise RuntimeError(
            "SQL_AUTH_MODE inválido. Use ActiveDirectoryInteractive, "
            "ActiveDirectoryServicePrincipal ou SqlPassword."
        )

    driver_name = verificar_driver_sql_server()
    try:
        import mssql_python

        connection = mssql_python.connect(
            _connection_string(auth_mode, config),
            autocommit=False,
            timeout=60,
        )
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except RuntimeError:
        raise
    except Exception as error:
        error_text = str(error).lower()
        if "timeout" in error_text or "timed out" in error_text:
            message = (
                "A conexão ao SQL Server expirou. Confira o firewall do Azure SQL, "
                "a rede/VPN e se o servidor aceita conexões públicas."
            )
        elif "login failed" in error_text or "authentication" in error_text:
            message = (
                "O SQL Server recusou a autenticação. Confira SQL_AUTH_MODE, "
                "credenciais e permissões do usuário no database."
            )
        else:
            message = (
                "Não foi possível conectar ao SQL Server. Confira autenticação, "
                "permissões, firewall e disponibilidade do servidor."
            )
        logger.error(
            "Falha de conexão SQL Server (driver=%s, tipo=%s).",
            driver_name,
            type(error).__name__,
        )
        raise RuntimeError(message) from None

    logger.info("Conexão com SQL Server validada usando %s.", auth_mode)
    return connection
