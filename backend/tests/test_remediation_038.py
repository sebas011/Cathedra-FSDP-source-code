import sqlite3
from contextlib import closing

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine

from app.db import Base
from app.login_limits import LoginLimiter
from app.migrations import run_migrations, validate_migration_history
from app.models import Program, Scholar


def test_failure_bucket_does_not_lock_out_other_loopback_accounts(client):
    for attempt in range(8):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unknown-account", "password": "synthetic-wrong-password"},
        )
        assert response.status_code == 401, attempt
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "unknown-account", "password": "synthetic-wrong-password"},
        ).status_code
        == 429
    )
    for attempt in range(10):
        response = client.post(
            "/api/v1/auth/login", json={"username": "test-admin", "password": "test-password-123"}
        )
        assert response.status_code == 200, attempt


def test_success_releases_only_its_reservation():
    limiter = LoginLimiter(limit=2)
    reservation = limiter.check(" Owner ", "loopback")
    limiter.check("owner", "loopback")
    limiter.release_attempt(reservation)
    assert limiter.entries["account:owner"][1] == 1
    limiter.check("owner", "loopback")
    with pytest.raises(HTTPException) as error:
        limiter.check("owner", "loopback")
    assert error.value.status_code == 429


def test_old_success_cannot_release_new_window_failure(monkeypatch):
    import app.login_limits as limits

    clock = [0.0]
    monkeypatch.setattr(limits.time, "monotonic", lambda: clock[0])
    limiter = LoginLimiter(limit=1, window=5)
    reservation = limiter.check("owner", "loopback")
    clock[0] = 6.0
    limiter.check("owner", "loopback")
    limiter.release_attempt(reservation)
    assert limiter.entries["account:owner"][1] == 1


def test_unknown_username_churn_cannot_displace_registered_accounts():
    limiter = LoginLimiter(limit=1)
    limiter.check("owner", "loopback")
    limiter.check("new-user", "loopback", registered=False)
    for number in range(2100):
        with pytest.raises(HTTPException):
            limiter.check(f"unknown-{number}", "loopback", registered=False)
    with pytest.raises(HTTPException):
        limiter.check("owner", "loopback")
    assert set(limiter.entries) == {"account:owner", "unregistered"}
    reservation = limiter.check("another-owner", "loopback")
    limiter.release_attempt(reservation)
    assert "account:another-owner" not in limiter.entries


def test_hash_workers_are_bounded_and_released():
    limiter = LoginLimiter()
    with limiter.verification(), limiter.verification():
        with pytest.raises(HTTPException) as error, limiter.verification():
            pytest.fail("A third hash worker was admitted")
        assert error.value.status_code == 429
    with limiter.verification():
        pass


def test_legacy_institution_migrates_once_without_new_inheritance(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT, applied_at TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO schema_migrations VALUES (1, 'fsdp-only-baseline', CURRENT_TIMESTAMP)"
        )
        connection.execute(Scholar.__table__.insert().values(id=1, name="Migration scholar"))
        connection.execute(
            Program.__table__.insert().values(
                id=1, name="Reusable", delivering_hei="Legacy institution"
            )
        )
        connection.exec_driver_sql(
            "INSERT INTO fsdp_participations (scholar_id, program_id, status, delivering_hei) VALUES (1, 1, 'On Going', '')"
        )
        run_migrations(connection)
        assert (
            connection.exec_driver_sql("SELECT delivering_hei FROM fsdp_participations").scalar()
            == "Legacy institution"
        )
        connection.exec_driver_sql("UPDATE fsdp_participations SET delivering_hei = NULL")
        run_migrations(connection)
        assert (
            connection.exec_driver_sql("SELECT delivering_hei FROM fsdp_participations").scalar()
            is None
        )
    engine.dispose()


def test_nonstandard_term_is_rejected(client):
    response = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Term test",
            "participations": [
                {
                    "program_name": "Term program",
                    "start_term": "invented",
                    "start_academic_year": "2026-2027",
                    "status": "On Going",
                }
            ],
        },
    )
    assert response.status_code == 422
    assert client.get("/api/v1/fsdp/page").json()["total"] == 0


def test_recovery_required_blocks_records_and_repeat_restore(client):
    from app.main import app

    app.state.restore_request_gate.recovery_required = True
    assert client.get("/api/v1/fsdp/page").status_code == 503
    assert client.post("/api/v1/fsdp", json={"name": "Do not save"}).status_code == 503
    assert (
        client.post("/api/v1/maintenance/restore", json={"filename": "missing.db"}).status_code
        == 503
    )
    assert client.get("/api/v1/health").status_code == 200


def test_missing_migration_prefix_fails_before_schema_changes(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'invalid.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO schema_migrations VALUES (2, 'participation-institution-attribution')"
        )
        with pytest.raises(RuntimeError, match="incomplete"):
            validate_migration_history(connection)
    engine.dispose()
    with closing(sqlite3.connect(tmp_path / "invalid.db")) as database:
        assert (
            database.execute("SELECT name FROM sqlite_master WHERE name='scholars'").fetchone()
            is None
        )


def test_restore_cleanup_failure_requires_restart_before_any_write(client, tmp_path, monkeypatch):
    import app.api.maintenance as maintenance
    from app.restore_recovery import restore_marker_path

    monkeypatch.setattr(maintenance, "DB_PATH", tmp_path / "cathedra.db")
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path / "backups")
    created = client.post("/api/v1/fsdp", json={"name": "Protected original"})
    assert created.status_code == 201
    backup = client.post("/api/v1/maintenance/backups").json()

    def failed_cleanup(_path):
        raise OSError("Synthetic marker removal failure")

    monkeypatch.setattr(maintenance, "finish_restore", failed_cleanup)
    response = client.post("/api/v1/maintenance/restore", json={"filename": backup["filename"]})
    assert response.status_code == 500
    assert restore_marker_path(maintenance.DB_PATH).exists()
    assert client.post("/api/v1/fsdp", json={"name": "Must not be saved"}).status_code == 503
    assert client.get("/api/v1/fsdp/payback").status_code == 503
