"""Verified recovery copies; automatic pruning never touches manual backups."""

import os
import sqlite3
import threading
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.migrations import MIGRATIONS
from app.product import verify_product

backup_operations_lock = threading.RLock()


def verify_backup_file(path: Path) -> None:
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as database:
        verify_product(database)
        if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("The backup failed its integrity check.")
        if database.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("The backup has broken record links.")
        tables = {
            row[0]
            for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if (
            not {
                "schema_migrations",
                "scholars",
                "fsdp_participations",
                "programs",
                "scholar_requirements",
                "local_users",
                "local_sessions",
            }
            <= tables
        ):
            raise ValueError("This is not a Cathedra database backup.")
        version = database.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if version is None or version > MIGRATIONS[-1][0]:
            raise ValueError("The backup schema version is not supported.")


def make_backup(source: sqlite3.Connection, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.stem}-{uuid4().hex}.tmp")
    try:
        with closing(sqlite3.connect(temporary)) as target:
            source.backup(target)
        verify_backup_file(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def prune_automatic_copies(
    directory: Path, prefix: str, keep: int, *, preserve: Path | None = None
) -> None:
    with backup_operations_lock:
        # Only our timestamped, non-linked, unpinned automatic files qualify.
        candidates = sorted(
            (
                item
                for item in directory.glob(f"{prefix}*.db")
                if item.is_file()
                and not item.is_symlink()
                and not item.is_junction()
                and not item.with_name(f".{item.name}.protected").exists()
            ),
            key=lambda item: item.name,
            reverse=True,
        )
        # A clock correction must never place the just-verified recovery copy
        # behind older, future-dated filenames and remove it before a deletion.
        if preserve in candidates:
            candidates.remove(preserve)
            candidates.insert(0, preserve)
        for item in candidates[keep:]:
            item.unlink(missing_ok=True)


def daily_backup(database_path: Path, *, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    directory = database_path.parent / "backups"
    destination = directory / f"cathedra-backup-auto-{now:%Y%m%d}.db"
    if destination.exists():
        verify_backup_file(destination)
    else:
        with closing(
            sqlite3.connect(f"{database_path.resolve().as_uri()}?mode=ro", uri=True)
        ) as source:
            make_backup(source, destination)
    prune_automatic_copies(directory, "cathedra-backup-auto-", 14, preserve=destination)
    return destination


def snapshot_before_delete(db: Session) -> Path:
    """Call under BEGIN IMMEDIATE, before changing rows; readers remain available."""
    source = db.connection().connection.driver_connection
    filename = source.execute("PRAGMA database_list").fetchone()[2]
    if filename:
        database_path = Path(filename).resolve()
        directory = database_path.parent / "backups"
        destination = (
            directory
            / f"cathedra-backup-before-delete-{datetime.now():%Y%m%d-%H%M%S-%f}-{uuid4().hex}.db"
        )
        # A separate reader avoids sqlite backup() waiting on its own write lock.
        with closing(sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)) as reader:
            make_backup(reader, destination)
    else:
        # Synthetic/in-memory installations have no disk database to open.
        # Tests must explicitly supply their private data directory.
        root = os.environ.get("CATHEDRA_DATA_DIR")
        if not root:
            raise ValueError("An in-memory recovery directory was not configured.")
        directory = Path(root) / "backups"
        destination = (
            directory
            / f"cathedra-backup-before-delete-{datetime.now():%Y%m%d-%H%M%S-%f}-{uuid4().hex}.db"
        )
        with closing(sqlite3.connect(":memory:")) as reader:
            reader.deserialize(source.serialize())
            make_backup(reader, destination)
    # Retention is best effort after a verified copy exists. A pruning failure
    # must never remove the new recovery copy or permit an unbacked deletion.
    try:
        prune_automatic_copies(
            directory, "cathedra-backup-before-delete-", 30, preserve=destination
        )
    except OSError:
        pass
    return destination
