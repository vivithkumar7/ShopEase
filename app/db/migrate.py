import argparse
import hashlib
import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import mssql_python

from app.config.settings import settings
from app.db.connection import connect_database

APP_SCHEMA = "shopease"
MIGRATION_LOCK = f"{APP_SCHEMA}:schema-migrations"
VERSIONS_DIRECTORY = Path(__file__).parent / "migrations" / "versions"
MIGRATION_FILENAME = re.compile(r"v(\d{3})_[a-z][a-z0-9_]*\.py$")


@dataclass(frozen=True)
class Migration:
    version: str
    checksum: str
    up_sql: str
    verify_sql: str


def _migration_from_module(path: Path) -> Migration:
    match = MIGRATION_FILENAME.fullmatch(path.name)
    if match is None:
        raise RuntimeError(f"Invalid migration filename: {path.name}")

    module: ModuleType = importlib.import_module(
        f"app.db.migrations.versions.{path.stem}"
    )
    up_sql = getattr(module, "UP_SQL", None)
    verify_sql = getattr(module, "VERIFY_SQL", None)
    if not isinstance(up_sql, str) or not up_sql.strip():
        raise RuntimeError(f"Migration {path.name} has no UP_SQL")
    if not isinstance(verify_sql, str) or not verify_sql.strip():
        raise RuntimeError(f"Migration {path.name} has no VERIFY_SQL")

    return Migration(
        version=match.group(1),
        checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
        up_sql=up_sql,
        verify_sql=verify_sql,
    )


def discover_migrations() -> list[Migration]:
    files = sorted(
        path
        for path in VERSIONS_DIRECTORY.glob("v*.py")
        if path.name != "__init__.py"
    )
    migrations = [_migration_from_module(path) for path in files]
    versions = [migration.version for migration in migrations]
    expected = [f"{number:03d}" for number in range(1, len(versions) + 1)]
    if versions != expected:
        raise RuntimeError(
            "Migration files must be unique, ordered, and contiguous from v001"
        )
    if not migrations:
        raise RuntimeError("No database migrations were found")
    return migrations


def _assert_target_database(
    cursor: mssql_python.Cursor,
    expected_database: str,
) -> None:
    cursor.execute(
        "SELECT DB_NAME(), CONVERT(int, SERVERPROPERTY('EngineEdition'))"
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Could not verify the connected database")
    actual_database, engine_edition = row
    if actual_database != expected_database:
        raise RuntimeError(
            f"Connected to database {actual_database!r}, "
            f"not the requested application database {expected_database!r}"
        )
    if str(actual_database).casefold() == "master":
        raise RuntimeError("Refusing to run application migrations against master")
    if engine_edition != 5:
        raise RuntimeError(
            "ShopEase migrations require Azure SQL Database "
            f"(EngineEdition 5); connected engine edition is {engine_edition!r}"
        )


def _bootstrap_migration_schema(cursor: mssql_python.Cursor) -> None:
    cursor.execute(
        """
        IF SCHEMA_ID(N'shopease') IS NULL
            EXEC(N'CREATE SCHEMA [shopease] AUTHORIZATION [dbo]');

        IF OBJECT_ID(N'[shopease].[__migration_lock]', N'U') IS NULL
        BEGIN
            CREATE TABLE [shopease].[__migration_lock] (
                [lock_id] tinyint NOT NULL
                    CONSTRAINT [PK___migration_lock] PRIMARY KEY,
                CONSTRAINT [CK___migration_lock_singleton] CHECK ([lock_id] = 1)
            );
        END;

        IF OBJECT_ID(N'[shopease].[__schema_migrations]', N'U') IS NULL
        BEGIN
            CREATE TABLE [shopease].[__schema_migrations] (
                [version] varchar(32) NOT NULL
                    CONSTRAINT [PK___schema_migrations] PRIMARY KEY,
                [checksum] char(64) NOT NULL,
                [applied_at] datetimeoffset(7) NOT NULL
                    CONSTRAINT [DF___schema_migrations_applied_at]
                    DEFAULT SYSUTCDATETIME()
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM [shopease].[__migration_lock] WHERE [lock_id] = 1
        )
            INSERT INTO [shopease].[__migration_lock] ([lock_id]) VALUES (1);

        UPDATE [shopease].[__migration_lock] WITH (UPDLOCK, HOLDLOCK)
        SET [lock_id] = 1
        WHERE [lock_id] = 1;
        """
    )


def _acquire_application_lock(cursor: mssql_python.Cursor) -> None:
    cursor.execute(
        """
        DECLARE @lock_result int;
        EXEC @lock_result = sys.sp_getapplock
            @Resource = ?,
            @LockMode = N'Exclusive',
            @LockOwner = N'Transaction',
            @LockTimeout = 30000;
        SELECT @lock_result;
        """,
        MIGRATION_LOCK,
    )
    row = cursor.fetchone()
    if row is None or row[0] < 0:
        result = None if row is None else row[0]
        raise RuntimeError(
            f"Could not acquire the database migration lock (result {result})"
        )


def _read_applied_migrations(
    cursor: mssql_python.Cursor,
) -> dict[str, str]:
    cursor.execute(
        "SELECT [version], [checksum] "
        "FROM [shopease].[__schema_migrations] ORDER BY [version]"
    )
    return {
        str(version): str(checksum).strip()
        for version, checksum in cursor.fetchall()
    }


def _verify_migration(cursor: mssql_python.Cursor, migration: Migration) -> None:
    cursor.execute(migration.verify_sql)
    row = cursor.fetchone()
    if row is None or row[0] != 1:
        raise RuntimeError(
            f"Migration {migration.version} failed its database postcondition"
        )


def migrate_database(
    expected_database: str,
    connection_factory=connect_database,
) -> list[str]:
    if not expected_database or expected_database.casefold() == "master":
        raise RuntimeError("An explicit non-master application database is required")
    if settings.sql_database != expected_database:
        raise RuntimeError(
            "--database must exactly match the configured SQL_DATABASE"
        )

    migrations = discover_migrations()
    known_versions = {migration.version for migration in migrations}
    connection = connection_factory()
    cursor = connection.cursor()
    applied_now: list[str] = []
    try:
        _assert_target_database(cursor, expected_database)
        cursor.execute(
            """
            SET XACT_ABORT ON;
            SET LOCK_TIMEOUT 15000;
            SET NOCOUNT ON;
            IF @@TRANCOUNT = 0
                THROW 51000, 'Migration runner requires an active transaction', 1;
            """
        )
        _acquire_application_lock(cursor)
        _bootstrap_migration_schema(cursor)

        applied = _read_applied_migrations(cursor)
        unknown_versions = set(applied) - known_versions
        if unknown_versions:
            raise RuntimeError(
                "Database contains migrations missing from this application: "
                + ", ".join(sorted(unknown_versions))
            )

        for migration in migrations:
            previous_checksum = applied.get(migration.version)
            if previous_checksum is not None and previous_checksum != migration.checksum:
                raise RuntimeError(
                    f"Applied migration {migration.version} has changed; "
                    "create a new forward migration instead"
                )
            if previous_checksum is None:
                cursor.execute(migration.up_sql)
                _verify_migration(cursor, migration)
                cursor.execute(
                    """
                    INSERT INTO [shopease].[__schema_migrations]
                        ([version], [checksum])
                    VALUES (?, ?)
                    """,
                    migration.version,
                    migration.checksum,
                )
                applied_now.append(migration.version)

        _verify_migration(cursor, migrations[-1])

        connection.commit()
        return applied_now
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply ordered ShopEase database migrations."
    )
    parser.add_argument(
        "--database",
        required=True,
        help="Must exactly match SQL_DATABASE; master is never a valid target.",
    )
    args = parser.parse_args()
    applied = migrate_database(args.database)
    if applied:
        print(
            f"Applied migration(s) {', '.join(applied)} "
            f"to database {args.database}."
        )
    else:
        print(
            f"Database {args.database} is up to date; "
            "all recorded migrations were verified."
        )


if __name__ == "__main__":
    main()
