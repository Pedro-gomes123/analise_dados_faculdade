"""Verifica driver Microsoft, autenticação e consulta simples no SQL Server.

Execute da raiz de projeto_5:
    python3 -m silver.test_sql_connection
"""

import logging
import sys

from silver.database.sql_server import conectar_sql_server, verificar_driver_sql_server


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    connection = None
    try:
        driver = verificar_driver_sql_server()
        print(f"Driver SQL encontrado: {driver}")
        print("Abrindo conexão usando o modo de autenticação configurado…")
        connection = conectar_sql_server()
        cursor = connection.cursor()
        cursor.execute(
            """SELECT
                   DB_NAME() AS banco,
                   SUSER_SNAME() AS usuario,
                   GETDATE() AS data_conexao;"""
        )
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            raise RuntimeError("A consulta de validação não retornou resultado.")
        print("Conexão SQL Server estabelecida:")
        print(f"  Banco: {row[0]}")
        print(f"  Usuário: {row[1]}")
        print(f"  Data da conexão: {row[2]}")
        return 0
    except Exception as error:
        print(f"Falha no teste SQL Server: {error}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
