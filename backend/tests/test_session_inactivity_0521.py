"""Idle sessions expire independently of polling and their absolute lifetime."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, delete, func, select
from starlette.requests import Request

import app.auth as authentication
import app.main as main
from app.api import auth as account_api
from app.api import maintenance
from app.migrations import MIGRATIONS, _session_inactivity_lock
from app.models import LocalSession, LocalUser, Scholar


def session_for(client):
    token = client.headers["Authorization"].removeprefix("Bearer ")
    with main.SessionLocal() as database:
        return database.scalar(
            select(LocalSession).where(
                LocalSession.token_hash == authentication.token_digest(token)
            )
        )


@pytest.fixture
def clock(client, monkeypatch, tmp_path):
    monkeypatch.setattr(maintenance, "DB_PATH", tmp_path / "cathedra.db")
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path / "backups")
    current = [session_for(client).last_activity_at]
    monkeypatch.setattr(authentication, "utc_now", lambda: current[0])
    return current


def test_new_session_stores_input_time_and_independent_absolute_deadline(client, clock):
    session = session_for(client)
    assert session.last_activity_at == clock[0]
    assert session.expires_at - session.last_activity_at == timedelta(hours=12)


def test_background_reads_do_not_extend_idle_time_and_exact_boundary_locks(client, clock):
    initial = session_for(client).last_activity_at
    clock[0] = initial + timedelta(minutes=29, seconds=59)
    for path in ("/api/v1/auth/me", "/api/v1/fsdp", "/api/v1/maintenance/status"):
        assert client.get(path).status_code == 200
    assert session_for(client).last_activity_at == initial
    clock[0] = initial + timedelta(minutes=30)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/fsdp").status_code == 401
    assert client.post("/api/v1/auth/activity").status_code == 401
    assert session_for(client).last_activity_at == initial


def test_input_heartbeat_extends_only_idle_deadline_and_cannot_revive_expired_session(
    client, clock
):
    initial = session_for(client)
    clock[0] = initial.last_activity_at + timedelta(minutes=29)
    assert client.post("/api/v1/auth/activity").status_code == 204
    renewed = session_for(client)
    assert renewed.last_activity_at == clock[0]
    assert renewed.expires_at == initial.expires_at
    clock[0] += timedelta(minutes=29, seconds=59)
    assert client.get("/api/v1/auth/me").status_code == 200
    clock[0] += timedelta(seconds=1)
    assert client.post("/api/v1/auth/activity").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert session_for(client).last_activity_at == renewed.last_activity_at


def test_recent_input_cannot_extend_twelve_hour_absolute_expiry(client, clock):
    initial = session_for(client)
    with main.SessionLocal() as database:
        database.get(LocalSession, initial.id).last_activity_at = initial.expires_at - timedelta(
            minutes=1
        )
        database.commit()
    clock[0] = initial.expires_at - timedelta(seconds=1)
    assert client.post("/api/v1/auth/activity").status_code == 204
    assert session_for(client).expires_at == initial.expires_at
    clock[0] = initial.expires_at
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/activity").status_code == 401


def test_activity_rechecks_expiry_after_authentication_before_renewing(client, clock, monkeypatch):
    initial = session_for(client).last_activity_at
    clock[0] = initial + timedelta(minutes=29, seconds=59)
    begin_write = account_api.begin_account_write

    def expire_before_write(database):
        begin_write(database)
        clock[0] = initial + timedelta(minutes=30)

    monkeypatch.setattr(account_api, "begin_account_write", expire_before_write)
    assert client.post("/api/v1/auth/activity").status_code == 401
    assert session_for(client).last_activity_at == initial


def test_stale_activity_cannot_refresh_a_replacement_token_with_reused_session_id(
    client, clock, monkeypatch
):
    initial = session_for(client)
    clock[0] += timedelta(minutes=29)
    replacement = {}
    begin_write = account_api.begin_account_write

    def replace_token_before_write(database):
        database.rollback()
        database.execute(delete(LocalSession).where(LocalSession.id == initial.id))
        database.commit()
        replacement["token"] = authentication.create_session(
            database, database.get(LocalUser, initial.user_id)
        )
        row = database.scalar(
            select(LocalSession).where(
                LocalSession.token_hash == authentication.token_digest(replacement["token"])
            )
        )
        assert row.id == initial.id
        replacement["activity"] = row.last_activity_at
        clock[0] += timedelta(seconds=1)
        begin_write(database)

    monkeypatch.setattr(account_api, "begin_account_write", replace_token_before_write)
    assert client.post("/api/v1/auth/activity").status_code == 401
    with main.SessionLocal() as database:
        row = database.get(LocalSession, initial.id)
        assert row.token_hash == authentication.token_digest(replacement["token"])
        assert row.last_activity_at == replacement["activity"]
    client.headers["Authorization"] = f"Bearer {replacement['token']}"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_legacy_null_activity_requires_sign_in_without_deleting_session_or_scholar(client, clock):
    initial = session_for(client)
    saved = client.post("/api/v1/fsdp", json={"name": "Synthetic retained scholar"})
    assert saved.status_code == 201
    with main.SessionLocal() as database:
        database.get(LocalSession, initial.id).last_activity_at = None
        database.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/activity").status_code == 401
    assert (
        client.put(
            f"/api/v1/fsdp/{saved.json()['id']}", json={"name": "Blocked update"}
        ).status_code
        == 401
    )
    with main.SessionLocal() as database:
        assert database.get(LocalSession, initial.id) is not None
        assert database.get(Scholar, saved.json()["id"]).name == "SYNTHETIC RETAINED SCHOLAR"


def test_activity_requires_authentication_and_refreshes_only_the_current_session(client, clock):
    initial = session_for(client)
    with main.SessionLocal() as database:
        user = database.get(LocalUser, initial.user_id)
        other_token = authentication.create_session(database, user)
    clock[0] += timedelta(minutes=10)
    assert client.post("/api/v1/auth/activity").status_code == 204
    with main.SessionLocal() as database:
        other = database.scalar(
            select(LocalSession).where(
                LocalSession.token_hash == authentication.token_digest(other_token)
            )
        )
        assert other.last_activity_at == initial.last_activity_at
        assert database.get(LocalSession, initial.id).last_activity_at == clock[0]
    client.headers.clear()
    assert client.post("/api/v1/auth/activity").status_code == 401


def test_activity_remains_available_while_temporary_password_must_change(client, clock):
    initial = session_for(client)
    with main.SessionLocal() as database:
        database.get(LocalUser, initial.user_id).must_change_password = True
        database.commit()
    clock[0] += timedelta(minutes=10)
    assert client.get("/api/v1/fsdp").status_code == 403
    assert client.post("/api/v1/auth/activity").status_code == 204
    assert session_for(client).last_activity_at == clock[0]


def test_authorization_reads_do_not_commit_pending_business_records(client, clock):
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/fsdp", "headers": []})
    with main.SessionLocal() as database:
        pending = Scholar(name="Synthetic pending record")
        database.add(pending)
        authentication.require_signed_in(request, client.headers["Authorization"], database)
        assert pending in database.new
        assert pending.id is None
    with main.SessionLocal() as database:
        assert database.scalar(select(func.count()).select_from(Scholar)) == 0


def test_migration_fifteen_adds_nullable_activity_without_deleting_or_rewriting_records():
    assert MIGRATIONS[14][:2] == (15, "session-inactivity-lock")
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE local_sessions (id INTEGER PRIMARY KEY, user_id INTEGER, token_hash TEXT, expires_at DATETIME)"
            )
            connection.exec_driver_sql("CREATE TABLE scholars (id INTEGER PRIMARY KEY, name TEXT)")
            connection.exec_driver_sql(
                "INSERT INTO local_sessions VALUES (8,3,'synthetic-token-digest','2099-01-01')"
            )
            connection.exec_driver_sql(
                "INSERT INTO scholars VALUES (51,'Synthetic historical record')"
            )
            _session_inactivity_lock(connection)
            assert connection.exec_driver_sql("SELECT * FROM local_sessions").one() == (
                8,
                3,
                "synthetic-token-digest",
                "2099-01-01",
                None,
            )
            assert connection.exec_driver_sql("SELECT * FROM scholars").one() == (
                51,
                "Synthetic historical record",
            )
            before = connection.exec_driver_sql("SELECT * FROM local_sessions").all()
            _session_inactivity_lock(connection)
            assert connection.exec_driver_sql("SELECT * FROM local_sessions").all() == before
    finally:
        engine.dispose()
