"""Conexão com SQL Server/Azure SQL usando o driver oficial mssql-python.

Por que mssql-python e não pyodbc + ODBC Driver?
- pyodbc exige que o ODBC Driver (libmsodbcsql) seja instalado separadamente
  no sistema operacional — processo trabalhoso em Linux e CI/CD.
- mssql-python é um driver Python puro que empacota o cliente TDS sem
  dependências externas de sistema. pip install é suficiente.
- API compatível com pyodbc: o restante do código usa cursor.execute(),
  cursor.fetchall() e connection.commit() sem nenhuma mudança.

Modos de autenticação suportados (SQL_AUTH_MODE no .env):
  SqlPassword                    → usuário/senha SQL (SQL_USERNAME + SQL_PASSWORD)
  ActiveDirectoryInteractive     → autenticação MFA via browser (desenvolvimento)
  ActiveDirectoryServicePrincipal → Service Principal Azure AD (CI/CD)

Segurança da connection string:
Nenhum erro relançado expõe a string de conexão (que contém senha). Os
blocos except convertem o erro em RuntimeError com mensagem genérica.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Path para o .env na raiz do projeto, calculado dinamicamente.
# parents[2]: sql_server.py → database/ → silver/ → projeto_5/ → .env
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Conjunto de modos de autenticação válidos — usado para validação explícita
# antes de tentar a conexão (falha clara antes de erro obscuro do driver).
AUTH_MODES = {
    "ActiveDirectoryInteractive",
    "ActiveDirectoryServicePrincipal",
    "SqlPassword",
}


def verificar_driver_sql_server() -> str:
    """Verifica se o driver mssql-python está instalado e retorna sua versão.

    Por que verificar antes de conectar?
    Se o driver não estiver instalado, o ImportError gerado pelo connect()
    seria confuso (pode aparecer como AttributeError no pyodbc). Esta função
    fornece uma mensagem de erro clara com instruções de instalação.

    Returns:
        String "mssql-python X.Y.Z" para logging.

    Raises:
        RuntimeError: Se mssql_python não estiver instalado.
    """
    try:
        import mssql_python
    except ImportError as error:
        raise RuntimeError(
            "Driver SQL ausente. Instale as dependências com "
            "python3 -m pip install -r silver/requirements.txt."
        ) from error
    # getattr com default: versão pode não existir em builds de desenvolvimento.
    return f"mssql-python {getattr(mssql_python, '__version__', '')}".strip()


def _required_config(config: dict[str, str], names: tuple[str, ...]) -> dict[str, str]:
    """Valida que as variáveis de configuração obrigatórias estão presentes.

    Por que validar antes de construir a connection string?
    Uma variável ausente geraria um KeyError interno com mensagem confusa.
    Esta função fornece uma mensagem clara listando TODAS as variáveis
    ausentes de uma vez, não apenas a primeira.

    Raises:
        RuntimeError: Lista de variáveis ausentes ou vazias.
    """
    missing = [name for name in names if not config.get(name)]
    if missing:
        raise RuntimeError("Variáveis SQL ausentes: " + ", ".join(missing))
    return {name: config[name] for name in names}


def _connection_value(value: str) -> str:
    """Escapa valores da connection string com chaves para suportar caracteres especiais.

    O formato da connection string T-SQL usa {} para valores com caracteres
    especiais (;, =, espaços). Senhas como "P@ss;word=1" precisam ser escapadas
    como "{P@ss;word=1}" — o único caractere a escapar dentro das chaves é "}"
    duplicado como "}}".

    Returns:
        String no formato "{valor}".
    """
    return "{" + value.replace("}", "}}") + "}"


def _connection_string(auth_mode: str, config: dict[str, str]) -> str:
    """Monta a connection string para o mssql-python a partir das variáveis de ambiente.

    Formato: "Server={...};Database={...};Encrypt=yes;UID={...};PWD={...};"

    Por que adicionar porta se não estiver na string do servidor?
    Azure SQL aceita "{servidor},{porta}" como formato de Server.
    Se o usuário forneceu apenas o FQDN (sem ",1433"), adicionamos a porta
    padrão para evitar timeout de DNS em redes corporativas que bloqueiam 1433.

    Args:
        auth_mode: Modo de autenticação ("SqlPassword", "ActiveDirectoryInteractive",
                   "ActiveDirectoryServicePrincipal").
        config: Dict com variáveis SQL_* do ambiente.

    Returns:
        Connection string formatada para o mssql-python.

    Raises:
        RuntimeError: auth_mode inválido ou variáveis obrigatórias ausentes.
    """
    server = config["SQL_SERVER"]
    # Adiciona porta padrão se o servidor não especificou "host,porta" ou "host\instância".
    if "," not in server and "\\" not in server:
        server = f"{server},{config.get('SQL_PORT', '1433')}"

    # Validação explícita dos valores booleanos — evita enviar strings inválidas ao driver.
    encrypt = config.get("SQL_ENCRYPT", "yes").lower()
    trust   = config.get("SQL_TRUST_SERVER_CERTIFICATE", "no").lower()
    if encrypt not in {"yes", "no"} or trust not in {"yes", "no"}:
        raise RuntimeError("SQL_ENCRYPT e SQL_TRUST_SERVER_CERTIFICATE aceitam yes ou no.")

    # Partes comuns a todos os modos de autenticação.
    parts = [
        f"Server={_connection_value(server)}",
        f"Database={_connection_value(config['SQL_DATABASE'])}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust}",
    ]

    if auth_mode == "SqlPassword":
        # Autenticação SQL clássica: usuário + senha no banco de dados.
        credentials = _required_config(config, ("SQL_USERNAME", "SQL_PASSWORD"))
        parts.extend(
            (
                f"UID={_connection_value(credentials['SQL_USERNAME'])}",
                f"PWD={_connection_value(credentials['SQL_PASSWORD'])}",
            )
        )
    elif auth_mode == "ActiveDirectoryInteractive":
        # MFA via browser: o driver abre uma janela de autenticação Azure AD.
        # Útil em desenvolvimento, não funciona em CI/CD sem display.
        parts.append("Authentication=ActiveDirectoryInteractive")
    elif auth_mode == "ActiveDirectoryServicePrincipal":
        # Service Principal: client_id (UID) + client_secret (PWD) do Azure AD.
        # Ideal para CI/CD e ambientes serverless sem interação humana.
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
    # Termina com ";" — requerido pelo formato de connection string T-SQL.
    return ";".join(parts) + ";"


def conectar_sql_server():
    """Abre, valida e retorna uma conexão ao SQL Server/Azure SQL.

    Carrega as variáveis do .env, seleciona o modo de autenticação, monta a
    connection string e executa SELECT 1 para confirmar que a conexão funciona.
    Retorna a conexão ao chamador — cabe ao chamador fechá-la com connection.close().

    Por que autocommit=False (padrão)?
    Com autocommit=False, cada executemany é uma transação explícita.
    O código usa connection.commit() / connection.rollback() explicitamente,
    garantindo que falhas parciais não deixem dados em estado inconsistente.

    Por que timeout=60?
    Azure SQL pode levar até 30s para "acordar" em tier serverless.
    60s dá margem sem bloquear indefinidamente em problemas de rede.

    Returns:
        mssql_python.Connection: conexão validada, pronta para uso.

    Raises:
        RuntimeError: Falha de autenticação, timeout ou erro de rede —
            com mensagem em português sem expor credenciais.
    """
    # load_dotenv: lê o .env sem sobrescrever variáveis já definidas no ambiente
    # (variáveis de CI/CD têm prioridade sobre o arquivo local).
    load_dotenv(ENV_FILE)

    # Filtra apenas variáveis SQL_* para não passar variáveis desnecessárias.
    config = {key: value for key, value in os.environ.items() if key.startswith("SQL_")}
    config.update(_required_config(config, ("SQL_SERVER", "SQL_DATABASE")))

    # Autodetecção do modo de autenticação:
    # - Se SQL_AUTH_MODE está no .env, usa ele.
    # - Se SQL_USERNAME + SQL_PASSWORD estão presentes, assume SqlPassword.
    # - Caso contrário, cai em ActiveDirectoryInteractive (MFA).
    # Isso mantém compatibilidade com .env criados antes de SQL_AUTH_MODE existir.
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

    # Verifica o driver antes de tentar conectar para erro mais claro.
    driver_name = verificar_driver_sql_server()
    try:
        import mssql_python

        # connect(): abre a conexão TCP + handshake TLS + login SQL.
        connection = mssql_python.connect(
            _connection_string(auth_mode, config),
            autocommit=False,  # transações explícitas via commit()/rollback()
            timeout=60,        # segundos de espera antes de TimeoutError
        )
        # Prova de vida: SELECT 1 falha imediatamente se a conexão não funcionar.
        # Detecta problemas de firewall/rede antes de tentar o primeiro DDL.
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except RuntimeError:
        # RuntimeError vem de verificar_driver_sql_server ou _required_config — relança diretamente.
        raise
    except Exception as error:
        # Categoriza o erro para mensagem clara sem expor a connection string.
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
        # raise ... from None: suprime o "During handling of the above exception..."
        # que poderia expor detalhes internos da connection string no traceback.
        raise RuntimeError(message) from None

    logger.info("Conexão com SQL Server validada usando %s.", auth_mode)
    return connection
