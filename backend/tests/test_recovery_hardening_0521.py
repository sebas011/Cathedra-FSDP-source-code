import hashlib
import importlib.util
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import backups
from app.api import fsdp, maintenance
from app.contract_rules import classify_contract
from app.db import Base
from app.migrations import run_migrations
from app.models import Scholar
from app.product import bind_empty_database


def create_database(path):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        bind_empty_database(connection)
        run_migrations(connection)
    with Session(engine) as db:
        db.add(Scholar(name="RECOVERY TEST"))
        db.commit()
    engine.dispose()


def test_daily_verified_copy_retention_and_manual_pin_preservation(tmp_path):
    source = tmp_path / "cathedra.db"
    create_database(source)
    directory = tmp_path / "backups"
    for offset in range(18):
        backups.daily_backup(source, now=datetime(2026, 1, 1) + timedelta(days=offset))
    assert len(list(directory.glob("cathedra-backup-auto-*.db"))) == 14
    pinned = directory / "cathedra-backup-auto-20260105.db"
    pinned.with_name(f".{pinned.name}.protected").touch()
    manual = directory / "cathedra-backup-manual.db"
    manual.write_bytes(b"manual")
    for offset in range(18, 22):
        backups.daily_backup(source, now=datetime(2026, 1, 1) + timedelta(days=offset))
    assert pinned.exists() and manual.read_bytes() == b"manual"
    with closing(sqlite3.connect(directory / "cathedra-backup-auto-20260122.db")) as db:
        assert db.execute("SELECT name FROM scholars").fetchone()[0] == "RECOVERY TEST"


def test_failed_copy_does_not_prune_existing_copies(tmp_path, monkeypatch):
    source = tmp_path / "cathedra.db"
    create_database(source)
    previous = backups.daily_backup(source, now=datetime(2026, 1, 1))

    def fail(*args):
        raise OSError("no space")

    monkeypatch.setattr(backups, "make_backup", fail)
    with pytest.raises(OSError):
        backups.daily_backup(source, now=datetime(2026, 1, 2))
    assert previous.exists()


@pytest.mark.parametrize("kind,keep", [("auto", 14), ("before-delete", 30)])
def test_new_verified_copy_survives_retention_after_clock_rollback(tmp_path, kind, keep):
    source = tmp_path / "cathedra.db"
    create_database(source)
    directory = tmp_path / "backups"
    directory.mkdir()
    for index in range(keep):
        (directory / f"cathedra-backup-{kind}-29990101-{index:03}.db").write_bytes(b"old copy")
    if kind == "auto":
        copied = backups.daily_backup(source, now=datetime(2026, 1, 1))
    else:
        engine = create_engine(f"sqlite:///{source}")
        try:
            with Session(engine) as db:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                copied = backups.snapshot_before_delete(db)
        finally:
            engine.dispose()
    assert copied.exists()
    backups.verify_backup_file(copied)
    assert len(list(directory.glob(f"cathedra-backup-{kind}-*.db"))) == keep


def test_file_snapshot_under_write_reservation_captures_predelete_state(tmp_path):
    source = tmp_path / "cathedra.db"
    create_database(source)
    engine = create_engine(f"sqlite:///{source}")
    with Session(engine) as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        copied = backups.snapshot_before_delete(db)
        scholar = db.query(Scholar).one()
        db.delete(scholar)
        db.commit()
    with closing(sqlite3.connect(copied)) as snapshot:
        assert snapshot.execute("SELECT COUNT(*) FROM scholars").fetchone()[0] == 1
    with closing(sqlite3.connect(source)) as current:
        assert current.execute("SELECT COUNT(*) FROM scholars").fetchone()[0] == 0
    engine.dispose()


def test_delete_fails_closed_if_snapshot_fails_and_stale_requests_do_not_copy(client, monkeypatch):
    created = client.post("/api/v1/fsdp", json={"name": "PRESERVE ME"}).json()
    calls = []

    def fail(db):
        calls.append(True)
        raise OSError("private disk path")

    monkeypatch.setattr(fsdp, "snapshot_before_delete", fail)
    url = f"/api/v1/fsdp/{created['id']}"
    assert client.delete(url).status_code == 428
    assert client.delete(url, headers={"If-Match": "999"}).status_code == 409
    assert not calls
    failed = client.delete(url, headers={"If-Match": str(created["revision"])})
    assert failed.status_code == 503
    assert "private disk path" not in failed.text
    assert client.get(url).json()["name"] == "PRESERVE ME"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "filename", ["other.db", "../cathedra-backup-a.db", "cathedra-backup-a.txt"]
)
def test_restore_reuses_strict_selection(client, tmp_path, monkeypatch, filename):
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path)
    (tmp_path / "other.db").touch()
    result = client.post("/api/v1/maintenance/restore", json={"filename": filename})
    assert result.status_code == 404


@pytest.mark.parametrize("status", ["Transferred", "Withdrawn"])
def test_transferred_withdrawn_remain_eligible_for_review(status):
    result, deadline = classify_contract(status, date(2020, 6, 1), False, date(2023, 6, 2))
    assert result == "Payback review" and deadline == date(2023, 6, 1)
    assert classify_contract(status, date(2020, 6, 1), True, date(2026, 1, 1))[0] == "Completed"


def test_updater_hashes_stream_without_read_bytes(tmp_path, monkeypatch):
    module_path = Path(__file__).resolve().parents[2] / "desktop" / "office_update.py"
    spec = importlib.util.spec_from_file_location("streamed_updater", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = tmp_path / "runtime.bin"
    content = b"runtime contents" * 10000
    candidate.write_bytes(content)

    def forbidden(*args):
        raise AssertionError("whole-file read")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert module.file_sha256(candidate) == hashlib.sha256(content).hexdigest()
