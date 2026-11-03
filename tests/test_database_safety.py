import hashlib

import mssql_python
import pytest

from app.config.settings import settings
from app.db import migrate
from app.db.connection import _connection_string


def test_migration_versions_are_ordered_and_checksummed() -> None:
    migrations = migrate.discover_migrations()

    assert [item.version for item in migrations] == ["001"]
    assert migrations[0].checksum == hashlib.sha256(
        (migrate.VERSIONS_DIRECTORY / "v001_products.py").read_bytes()
    ).hexdigest()


def test_migration_database_must_match_config_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sql_database", "ShopEase")
    connection_attempted = False

    def connect() -> mssql_python.Connection:
        nonlocal connection_attempted
        connection_attempted = True
        raise AssertionError("a mismatched target must not connect")

    with pytest.raises(RuntimeError, match="exactly match"):
        migrate.migrate_database("OtherDatabase", connection_factory=connect)

    assert not connection_attempted


def test_master_is_never_a_migration_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sql_database", "master")

    with pytest.raises(RuntimeError, match="non-master"):
        migrate.migrate_database("master")


def test_failed_migration_postcondition_rolls_back_and_never_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sql_database", "ShopEase")

    class Cursor:
        result: tuple[object, ...] | None = None

        def execute(self, query: str, *_parameters: object) -> None:
            if "DB_NAME()" in query:
                self.result = ("ShopEase", 5)
            elif "sp_getapplock" in query:
                self.result = (0,)
            elif "SELECT CASE WHEN" in query:
                self.result = (0,)

        def fetchone(self) -> tuple[object, ...] | None:
            result = self.result
            self.result = None
            return result

        def fetchall(self) -> list[tuple[object, ...]]:
            return []

        def close(self) -> None:
            pass

    class Connection:
        committed = False
        rolled_back = False
        closed = False

        def cursor(self) -> Cursor:
            return Cursor()

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    connection = Connection()

    with pytest.raises(RuntimeError, match="postcondition"):
        migrate.migrate_database(
            "ShopEase",
            connection_factory=lambda: connection,  # type: ignore[arg-type]
        )

    assert connection.rolled_back
    assert not connection.committed
    assert connection.closed


@pytest.mark.parametrize(
    ("database", "engine_edition", "message"),
    [
        ("OtherDatabase", 5, "not the requested"),
        ("ShopEase", 3, "require Azure SQL Database"),
        ("master", 5, "master"),
    ],
)
def test_live_migration_target_is_verified(
    database: str,
    engine_edition: int,
    message: str,
) -> None:
    class Cursor:
        def execute(self, *_args: object) -> None:
            pass

        def fetchone(self) -> tuple[str, int]:
            return database, engine_edition

    with pytest.raises(RuntimeError, match=message):
        migrate._assert_target_database(Cursor(), "ShopEase")  # type: ignore[arg-type]


def test_connection_string_requires_an_explicit_application_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sql_host", "shop.database.windows.net")
    monkeypatch.setattr(settings, "sql_database", "master")

    with pytest.raises(RuntimeError, match="not master"):
        _connection_string()


def test_connection_string_escapes_password_and_keeps_tls_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sql_host", "shop.database.windows.net")
    monkeypatch.setattr(settings, "sql_database", "ShopEase")
    monkeypatch.setattr(settings, "sql_authentication", "SqlPassword")
    monkeypatch.setattr(settings, "sql_user", "app-user")
    monkeypatch.setattr(settings, "sql_password", "p;ass}word")

    connection_string = _connection_string()

    assert "Database={ShopEase}" in connection_string
    assert "PWD={p;ass}}word}" in connection_string
    assert "Encrypt=yes" in connection_string
    assert "TrustServerCertificate=no" in connection_string
