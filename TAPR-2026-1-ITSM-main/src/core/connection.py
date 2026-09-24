import os
import pyodbc

_DRIVER = "{ODBC Driver 18 for SQL Server}"


def _connect(server: str, database: str, user: str, password: str) -> pyodbc.Connection:
    if not server:
        raise RuntimeError(
            "Variáveis de ambiente de conexão não configuradas. "
            "Verifique SQL_SERVER_SOURCE / SQL_SERVER_TARGET no local.settings.json "
            "ou nas Application Settings da Function App."
        )
    return pyodbc.connect(
        f"DRIVER={_DRIVER};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


def source_connection() -> pyodbc.Connection:
    return _connect(
        os.getenv("SQL_SERVER_SOURCE"),
        os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"),
        os.getenv("SQL_PASSWORD_SOURCE"),
    )


def target_connection() -> pyodbc.Connection:
    return _connect(
        os.getenv("SQL_SERVER_TARGET"),
        os.getenv("SQL_DATABASE_TARGET"),
        os.getenv("SQL_USER_TARGET"),
        os.getenv("SQL_PASSWORD_TARGET"),
    )
