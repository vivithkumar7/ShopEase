import re
import time

import mssql_python

from app.config.settings import settings

mssql_python.pooling(max_size=25, idle_timeout=300)

_TRANSIENT_SQL_ERRORS = {
    20,
    64,
    233,
    40143,
    40197,
    40501,
    40540,
    40613,
    49918,
    49919,
    49920,
    10053,
    10054,
    10060,
    10928,
    10929,
}
_TRANSIENT_SQL_STATES = {"08S01", "08001", "08003", "08007", "08S02", "08S03"}
_ERROR_NUMBER = re.compile(r"\b(?:Msg\s+)?(\d{2,5})\b", re.IGNORECASE)


def _connection_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def _connection_string() -> str:
    host = settings.sql_host
    database = settings.sql_database
    if not host or not database:
        raise RuntimeError("SQL_HOST and SQL_DATABASE must be configured")
    if re.fullmatch(r"[A-Za-z0-9.-]+", host) is None:
        raise RuntimeError("SQL_HOST contains invalid connection-string characters")
    if database.casefold() == "master":
        raise RuntimeError("SQL_DATABASE must name the ShopEase application database, not master")

    parts = [
        f"Server=tcp:{host},1433",
        f"Database={_connection_value(database)}",
        "Encrypt=yes",
        "TrustServerCertificate=no",
        "Connection Timeout=15",
    ]

    if settings.sql_authentication == "ActiveDirectoryDefault":
        parts.append("Authentication=ActiveDirectoryDefault")
    elif settings.sql_authentication == "SqlPassword":
        if not settings.sql_user or settings.sql_password is None:
            raise RuntimeError(
                "SQL_USER and SQL_PASSWORD are required for SQL_PASSWORD authentication"
            )
        parts.extend(
            (
                f"UID={_connection_value(settings.sql_user)}",
                f"PWD={_connection_value(settings.sql_password)}",
            )
        )
    else:
        raise RuntimeError(
            "SQL_AUTHENTICATION must be SqlPassword or ActiveDirectoryDefault"
        )

    return ";".join(parts) + ";"


def _is_transient(error: mssql_python.Error) -> bool:
    message = " ".join(str(argument) for argument in error.args)
    if any(state in message for state in _TRANSIENT_SQL_STATES):
        return True
    return any(
        int(match.group(1)) in _TRANSIENT_SQL_ERRORS
        for match in _ERROR_NUMBER.finditer(message)
    )


def connect_database() -> mssql_python.Connection:
    connection_string = _connection_string()
    attempts = 5

    for attempt in range(attempts):
        try:
            return mssql_python.connect(connection_string)
        except mssql_python.Error as error:
            if not _is_transient(error) or attempt == attempts - 1:
                raise
            time.sleep(min(5 * (2**attempt), 60))

    raise RuntimeError("Database connection retry loop ended unexpectedly")
