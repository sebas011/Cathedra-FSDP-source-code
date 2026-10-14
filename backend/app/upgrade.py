"""Snapshot existing databases before transactional schema changes."""

import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import Engine

from app import models as models
from app.db import Base
from app.migrations import MIGRATIONS, run_migrations, validate_migration_history
from app.product import bind_empty_database, verify_product


def snapshot_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError("Recovery snapshot already exists.")
    if shutil.disk_usage(destination.parent).free < source.stat().st_size * 2 + 1_048_576:
        raise RuntimeError("Free disk space is insufficient for an upgrade recovery snapshot.")
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(destination)) as backup:
                original.backup(backup)
                if backup.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("Recovery snapshot integrity verification failed.")
                if backup.execute("PRAGMA foreign_key_check").fetchone():
                    raise RuntimeError("Recovery snapshot has invalid record relationships.")
                verify_product(backup)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def upgrade_database(engine: Engine, path: Path) -> Path | None:
    """Hold a SQLite write reservation across validation, snapshot and migration."""
    path = path.resolve()
    recovery = None
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            validate_migration_history(connection)
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).scalars()
            )
            applied = (
                set(connection.exec_driver_sql("SELECT version FROM schema_migrations").scalars())
                if "schema_migrations" in tables
                else set()
            )
            if "cathedra_product" in tables:
                with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as database:
                    verify_product(database)
                if applied != {version for version, _, _ in MIGRATIONS}:
                    recovery = (
                        path.parent
                        / "backups"
                        / (
                            "cathedra-protected-before-migration-"
                            + datetime.now().strftime("%Y%m%d-%H%M%S")
                            + "-"
                            + uuid4().hex
                            + ".db"
                        )
                    )
                    snapshot_database(path, recovery)
            bind_empty_database(connection)
            Base.metadata.create_all(bind=connection)
            run_migrations(connection)
            if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError("Upgrade produced invalid record relationships.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return recovery
