import unittest
from unittest.mock import Mock, patch

from silver.database.sql_server import (
    _connection_string,
    conectar_sql_server,
    verificar_driver_sql_server,
)


class SqlServerTests(unittest.TestCase):
    def test_reports_missing_configuration_without_exposing_values(self):
        env = {
            "SQL_SERVER": "",
            "SQL_DATABASE": "",
            "SQL_USERNAME": "",
            "SQL_PASSWORD": "",
            "SQL_AUTH_MODE": "",
        }
        with (
            patch("silver.database.sql_server.load_dotenv"),
            patch.dict("os.environ", env, clear=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "Variáveis SQL ausentes"):
                conectar_sql_server()

    def test_sql_password_connection_string_escapes_credentials_and_uses_tls(self):
        config = {
            "SQL_SERVER": "srv-proj5-dev.database.windows.net",
            "SQL_DATABASE": "db_monitoramento",
            "SQL_PORT": "1433",
            "SQL_USERNAME": "vigia_operator",
            "SQL_PASSWORD": "one;two}three",
            "SQL_ENCRYPT": "yes",
            "SQL_TRUST_SERVER_CERTIFICATE": "no",
        }
        value = _connection_string("SqlPassword", config)
        self.assertIn("Server={srv-proj5-dev.database.windows.net,1433}", value)
        self.assertIn("Encrypt=yes", value)
        self.assertIn("TrustServerCertificate=no", value)
        self.assertIn("PWD={one;two}}three}", value)

    def test_interactive_connection_string_does_not_include_password(self):
        config = {
            "SQL_SERVER": "srv-proj5-dev.database.windows.net",
            "SQL_DATABASE": "db_monitoramento",
            "SQL_USERNAME": "pcg@example.invalid",
            "SQL_PASSWORD": "must-not-be-used",
        }
        value = _connection_string("ActiveDirectoryInteractive", config)
        self.assertIn("Authentication=ActiveDirectoryInteractive", value)
        self.assertNotIn("UID=", value)
        self.assertNotIn("PWD=", value)
        self.assertNotIn("must-not-be-used", value)

    def test_connects_with_mssql_python_driver_and_validates_connection(self):
        fake_driver = Mock()
        fake_driver.__version__ = "test"
        fake_driver.connect.return_value.cursor.return_value.fetchone.return_value = (1,)
        env = {
            "SQL_SERVER": "srv-proj5-dev.database.windows.net",
            "SQL_DATABASE": "db_monitoramento",
            "SQL_USERNAME": "vigia_operator",
            "SQL_PASSWORD": "example-only-test-value",
            "SQL_AUTH_MODE": "SqlPassword",
        }
        with (
            patch("silver.database.sql_server.load_dotenv"),
            patch("silver.database.sql_server.verificar_driver_sql_server", return_value="mssql-python test"),
            patch.dict("os.environ", env, clear=False),
            patch.dict("sys.modules", {"mssql_python": fake_driver}),
        ):
            connection = conectar_sql_server()

        self.assertIs(connection, fake_driver.connect.return_value)
        args, kwargs = fake_driver.connect.call_args
        self.assertIn("UID={vigia_operator}", args[0])
        self.assertIn("PWD={example-only-test-value}", args[0])
        self.assertEqual(kwargs, {"autocommit": False, "timeout": 60})
        fake_driver.connect.return_value.cursor.return_value.execute.assert_called_once_with("SELECT 1")

    def test_driver_validation_uses_official_microsoft_package(self):
        fake_driver = Mock()
        fake_driver.__version__ = "1.16.0"
        with patch.dict("sys.modules", {"mssql_python": fake_driver}):
            self.assertEqual(verificar_driver_sql_server(), "mssql-python 1.16.0")


if __name__ == "__main__":
    unittest.main()
