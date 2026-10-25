import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import clock
from app.activity_audit import add_activity
from app.activity_details import MAX_DETAIL_TEXT
from app.api import maintenance
from app.api.activity import read_event
from app.db import Base
from app.migrations import run_migrations
from app.models import (
    ActivityEvent,
    FsdpParticipation,
    LocalUser,
    OfficeLog,
    Program,
    Scholar,
    ScholarEducation,
    ScholarRequirement,
)
from app.product import bind_empty_database
from app.upgrade import upgrade_database


@pytest.fixture
def audit_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            db.info["audit_actor"] = (1, "history-editor")
            yield db
    finally:
        engine.dispose()


def events(db, operation=None):
    statement = select(ActivityEvent).order_by(ActivityEvent.id)
    if operation:
        statement = statement.where(ActivityEvent.operation == operation)
    return db.scalars(statement).all()


def details(event):
    return {row["field"]: row for row in read_event(event, include_details=True)["change_details"]}


def test_before_after_uses_persisted_values_for_unloaded_fields_and_keeps_null_false(audit_db):
    scholar = Scholar(
        name="Original scholar",
        rank="INSTRUCTOR",
        has_soft_copy=True,
        profile_remarks="Keep this original remark",
    )
    audit_db.add(scholar)
    audit_db.commit()
    audit_db.expire(scholar, ["rank", "has_soft_copy", "profile_remarks"])
    scholar.rank = "ASSOCIATE PROFESSOR"
    scholar.has_soft_copy = False
    scholar.profile_remarks = None
    audit_db.commit()

    changed = details(events(audit_db, "Updated")[-1])
    assert changed["rank"] == {
        "field": "rank",
        "before": "INSTRUCTOR",
        "after": "ASSOCIATE PROFESSOR",
    }
    assert changed["has_soft_copy"] == {"field": "has_soft_copy", "before": True, "after": False}
    assert changed["profile_remarks"] == {
        "field": "profile_remarks",
        "before": "Keep this original remark",
        "after": None,
    }
    assert "revision" not in changed and "data_source" not in changed


def test_created_values_include_database_defaults_and_iso_dates(audit_db):
    scholar = Scholar(name="Created scholar")
    grant = FsdpParticipation(
        scholar=scholar, program=Program(name="Created program"), start_date=date(2021, 6, 1)
    )
    audit_db.add(grant)
    audit_db.commit()
    event = next(
        item for item in events(audit_db, "Created") if item.record_type == "fsdp_participations"
    )
    values = details(event)
    assert event.record_id == grant.id and event.subject_scholar_id == scholar.id
    assert values["start_date"] == {"field": "start_date", "before": None, "after": "2021-06-01"}
    assert values["status"]["after"] == "On Going"
    assert values["case_status"]["after"] == "Open"
    assert not {"application_key", "program_id", "scholar_id"}.intersection(values)


def test_deleted_children_retain_actual_business_values_once(audit_db):
    scholar = Scholar(name="History parent")
    scholar.participations = [
        FsdpParticipation(
            program=Program(name="Program"), status="Incomplete", remarks="Annual note"
        )
    ]
    scholar.education = [ScholarEducation(degree="BACHELOR", institution="COLLEGE")]
    scholar.requirements = [ScholarRequirement(requirement_name="AGREEMENT", is_complete=False)]
    audit_db.add(scholar)
    audit_db.commit()
    identities = {
        type(item): item.id
        for item in [*scholar.participations, *scholar.education, *scholar.requirements]
    }
    scholar.participations = []
    scholar.education = []
    scholar.requirements = []
    audit_db.commit()

    deleted = events(audit_db, "Deleted")
    assert len(deleted) == 3
    assert {item.record_id for item in deleted} == set(identities.values())
    assert all(item.subject_scholar_id == scholar.id for item in deleted)
    by_type = {item.record_type: details(item) for item in deleted}
    assert by_type["fsdp_participations"]["status"] == {
        "field": "status",
        "before": "Incomplete",
        "after": None,
    }
    assert by_type["scholar_education"]["degree"]["before"] == "BACHELOR"
    assert by_type["scholar_requirements"]["is_complete"]["before"] is False


def test_failed_flush_and_rollback_do_not_leave_ghost_history(audit_db):
    audit_db.add(Scholar(name="Rolled back"))
    audit_db.flush()
    audit_db.rollback()
    assert events(audit_db) == []
    audit_db.add(Scholar(name=None))
    with pytest.raises(IntegrityError):
        audit_db.flush()
    audit_db.rollback()
    assert "audit_pending" not in audit_db.info
    audit_db.add(Scholar(name="Committed"))
    audit_db.commit()
    assert len(events(audit_db)) == 1
    assert details(events(audit_db)[0])["name"]["after"] == "Committed"


def test_savepoint_rollback_does_not_publish_cancelled_values(audit_db):
    scholar = Scholar(name="Committed", rank="ORIGINAL")
    audit_db.add(scholar)
    audit_db.commit()
    transaction = audit_db.begin_nested()
    scholar.rank = "CANCELLED VALUE"
    audit_db.flush()
    transaction.rollback()
    scholar.age = 42
    audit_db.commit()
    changed = events(audit_db, "Updated")
    assert len(changed) == 1
    assert details(changed[0]) == {"age": {"field": "age", "before": None, "after": 42}}
    assert scholar.rank == "ORIGINAL"


def test_long_business_text_is_bounded_and_marked_without_changing_record(audit_db):
    scholar = Scholar(name="Text history", profile_remarks="A" * 1500)
    audit_db.add(scholar)
    audit_db.commit()
    scholar.profile_remarks = "B" * 1600
    audit_db.commit()
    note = details(events(audit_db, "Updated")[-1])["profile_remarks"]
    assert note["before"] == "A" * MAX_DETAIL_TEXT
    assert note["after"] == "B" * MAX_DETAIL_TEXT
    assert note["before_truncated"] is note["after_truncated"] is True
    assert scholar.profile_remarks == "B" * 1600


def test_accounts_never_snapshot_values_even_when_details_are_requested(audit_db):
    account = LocalUser(username="history-user", password_hash="secret-password-hash", role="admin")
    audit_db.add(account)
    audit_db.commit()
    account.password_hash = "replacement-secret-hash"
    audit_db.commit()
    add_activity(
        audit_db,
        "Local Accounts",
        "Account change",
        record_type="local_users",
        change_details=[
            {"field": "username", "before": "private-before", "after": "private-after"}
        ],
    )
    audit_db.commit()
    for event in events(audit_db):
        assert not event.change_details or json.loads(event.change_details) == []
        response = read_event(event, include_details=True)
        assert response["change_details"] == []
        assert "secret" not in json.dumps(response, default=str)
    assert "credentials" in json.loads(events(audit_db, "Updated")[-1].changed_fields)


@pytest.mark.parametrize(
    "payload", [None, "not-json", "{}", "[]", '[{"field":"rank"}]', "[" * 1000]
)
def test_legacy_or_corrupt_details_are_safe_without_invented_values(payload):
    event = ActivityEvent(record_type="scholars", changed_fields='["rank"]', change_details=payload)
    assert read_event(event, include_details=True)["change_details"] == []
    assert read_event(event)["changed_fields"] == ["rank"]
    assert "change_details" not in read_event(event)


def test_hostile_details_are_allowlisted_scalar_only_and_bound_on_read():
    event = ActivityEvent(
        record_type="scholars",
        changed_fields='["rank"]',
        change_details=json.dumps(
            [
                {"field": "password_hash", "before": "secret-old", "after": "secret-new"},
                {"field": "token_hash", "before": "secret-token", "after": "secret-token2"},
                {"field": "revision", "before": 1, "after": 2},
                {"field": "rank", "before": "OLD", "after": "NEW", "password": "secret-extra"},
                {"field": "rank", "before": "DUPLICATE", "after": "DUPLICATE"},
                {"field": "name", "before": {"nested": "secret-nested"}, "after": "text"},
                {"field": "age", "before": 20, "after": float("inf")},
                {"field": "profile_remarks", "before": None, "after": "X" * 2000},
            ]
        ),
    )
    safe = read_event(event, include_details=True)["change_details"]
    assert safe == [
        {"field": "rank", "before": "OLD", "after": "NEW"},
        {
            "field": "profile_remarks",
            "before": None,
            "after": "X" * MAX_DETAIL_TEXT,
            "after_truncated": True,
        },
    ]
    assert "secret" not in json.dumps(safe)
    event.change_details = " " * 512_001
    assert read_event(event, include_details=True)["change_details"] == []


def test_scholar_details_are_admin_only_and_global_activity_stays_metadata(client):
    scholar = client.post(
        "/api/v1/fsdp", json={"name": "HISTORY SCHOLAR", "rank": "ORIGINAL"}
    ).json()
    updated = client.put(
        f"/api/v1/fsdp/{scholar['id']}",
        json={"name": scholar["name"], "rank": "UPDATED", "participations": [], "requirements": []},
        headers={"If-Match": str(scholar["revision"])},
    )
    assert updated.status_code == 200
    history = client.get(f"/api/v1/activity/scholars/{scholar['id']}").json()
    assert any(
        {"field": "rank", "before": "ORIGINAL", "after": "UPDATED"} in row["change_details"]
        for row in history["items"]
    )
    assert all("change_details" not in row for row in client.get("/api/v1/activity").json())
    assert (
        client.post(
            "/api/v1/auth/users",
            json={"username": "history-staff", "password": "staff-password-123", "role": "staff"},
        ).status_code
        == 201
    )
    token = client.post(
        "/api/v1/auth/login", json={"username": "history-staff", "password": "staff-password-123"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "staff-password-123",
                "new_password": "changed-staff-password-123",
            },
            headers=headers,
        ).status_code
        == 204
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "history-staff", "password": "changed-staff-password-123"},
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.get(f"/api/v1/activity/scholars/{scholar['id']}", headers=headers).status_code == 403
    )
    assert client.get("/api/v1/activity", headers=headers).status_code == 403


def historical_database(path):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        bind_empty_database(connection)
        run_migrations(connection)
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>16")
        connection.exec_driver_sql("ALTER TABLE activity_events DROP COLUMN change_details")
        connection.exec_driver_sql(
            "INSERT INTO scholars(id,name,revision,rank,missing_requirements,data_source,created_at,updated_at) VALUES(51,'Mixed Case Historical Scholar',7,'Original rank',0,'Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql("INSERT INTO programs(id,name) VALUES(52,'Historical program')")
        connection.exec_driver_sql(
            "INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_term,start_academic_year,remarks) VALUES(53,51,52,'Custom historic outcome','Summer','2021','Exact old remarks')"
        )
        connection.exec_driver_sql(
            "INSERT INTO local_users(id,username,password_hash,role,must_change_password,created_at) VALUES(3,'historical-admin','synthetic-password-hash','admin',0,CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO local_sessions(id,user_id,token_hash,expires_at) VALUES(42,3,'synthetic-token-hash','2027-01-01 12:00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO activity_events(id,user_id,username,action,area,record_type,record_id,operation,changed_fields,subject_scholar_id,created_at) VALUES(54,3,'historical-admin','Old update','FSDP','scholars',51,'Updated','[\"rank\"]',51,'2021-01-01 08:00:00')"
        )
        connection.exec_driver_sql("UPDATE scholar_id_counter SET high_water=51 WHERE id=1")
        before = {
            table: [
                dict(row)
                for row in connection.exec_driver_sql(
                    f'SELECT * FROM "{table}" ORDER BY rowid'
                ).mappings()
            ]
            for table in (
                "scholars",
                "programs",
                "fsdp_participations",
                "local_users",
                "local_sessions",
                "activity_events",
                "schema_migrations",
            )
        }
    engine.dispose()
    return before


def test_schema16_upgrade_has_protected_copy_preserves_rows_and_never_backfills_details(tmp_path):
    path = tmp_path / "cathedra.db"
    before = historical_database(path)
    engine = create_engine(f"sqlite:///{path}")
    try:
        recovery = upgrade_database(engine, path)
        assert recovery and recovery.is_file()
        with closing(sqlite3.connect(path)) as db:
            db.row_factory = sqlite3.Row
            for table, original in before.items():
                query = f'SELECT * FROM "{table}" ORDER BY rowid'
                after = [dict(row) for row in db.execute(query)]
                if table == "schema_migrations":
                    assert after[: len(original)] == original and after[-1]["version"] == 17
                else:
                    assert [
                        {name: row[name] for name in original[index]}
                        for index, row in enumerate(after)
                    ] == original
            assert db.execute("SELECT change_details FROM activity_events").fetchone()[0] is None
        with closing(sqlite3.connect(recovery)) as snapshot:
            assert "change_details" not in {
                row[1] for row in snapshot.execute("PRAGMA table_info(activity_events)")
            }
            assert (
                snapshot.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 16
            )
        assert upgrade_database(engine, path) is None
        assert len(list((tmp_path / "backups").glob("cathedra-protected-before-*.db"))) == 1
    finally:
        engine.dispose()


def test_schema16_backup_restores_through_supported_handler_with_history_and_revoked_sessions(
    tmp_path, monkeypatch
):
    directory = tmp_path / "backups"
    directory.mkdir()
    old = directory / "cathedra-backup-schema16.db"
    original = historical_database(old)
    old_hash = hashlib.sha256(old.read_bytes()).hexdigest()
    current = tmp_path / "cathedra.db"
    engine = create_engine(f"sqlite:///{current}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        bind_empty_database(connection)
        run_migrations(connection)
        connection.exec_driver_sql("UPDATE scholar_id_counter SET high_water=99 WHERE id=1")
    monkeypatch.setattr(maintenance, "DB_PATH", current)
    monkeypatch.setattr(maintenance, "BACKUP_DIR", directory)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(restore_request_gate=SimpleNamespace(recovery_required=False))
        )
    )
    try:
        with Session(engine) as db:
            restored = maintenance.restore_database(
                maintenance.RestoreRequest(filename=old.name),
                request,
                db,
                LocalUser(username="restore-admin"),
            )
        assert restored["restored_from"] == old.name
        assert (directory / restored["safety_backup"]).is_file()
        with closing(sqlite3.connect(current)) as db:
            db.row_factory = sqlite3.Row
            assert db.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 17
            assert db.execute("SELECT COUNT(*) FROM local_sessions").fetchone()[0] == 0
            assert db.execute("SELECT high_water FROM scholar_id_counter").fetchone()[0] == 99
            for table in (
                "scholars",
                "programs",
                "fsdp_participations",
                "local_users",
                "activity_events",
            ):
                after = [dict(row) for row in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
                assert [
                    {name: row[name] for name in original[table][index]}
                    for index, row in enumerate(after)
                ] == original[table]
            assert db.execute("SELECT change_details FROM activity_events").fetchone()[0] is None
        assert hashlib.sha256(old.read_bytes()).hexdigest() == old_hash
    finally:
        engine.dispose()


def test_office_log_model_default_uses_philippine_business_day(audit_db, monkeypatch):
    monkeypatch.setattr(
        clock, "utc_now", lambda: datetime(2026, 10, 25, 16, 1, tzinfo=timezone.utc)
    )
    record = OfficeLog(
        user_id=1, username="test-editor", entry_type="Document", note="Model default"
    )
    audit_db.add(record)
    audit_db.commit()
    assert record.occurred_on == date(2026, 10, 26)
