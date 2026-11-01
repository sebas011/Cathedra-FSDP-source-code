import copy
import json
import sqlite3
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app import shared_workspace as service
from app.api.shared_workspace import report_table
from app.current_grant import current_grant
from app.db import Base
from app.migrations import run_migrations
from app.models import (
    FsdpParticipation,
    LocalUser,
    OfficeLog,
    Program,
    Scholar,
    ScholarEducation,
    ScholarRequirement,
)
from app.product import bind_empty_database
from app.shared_connection import PROTOCOL, SharedError, WorkspaceConnection, fingerprint
from app.shared_merge import merge
from app.shared_records import capture, validate_snapshot
from app.upgrade import upgrade_database

ENDPOINT = "https://script.google.com/macros/s/" + "x" * 30 + "/exec"
USER = SimpleNamespace(id=1, username="TEST ADMIN")


class Vault:
    def __init__(self):
        self.value = {}

    def load(self):
        return copy.deepcopy(self.value)

    def save(self, value):
        self.value = copy.deepcopy(value)


class Bridge:
    def __init__(self):
        self.snapshot = {
            "protocol": PROTOCOL,
            "workspace_id": str(uuid4()),
            "revision": 0,
            "initialized": False,
            "records": [],
        }
        self.receipts = {}
        self.lose_response = False
        self.bad_response = False
        self.error = None
        self.report = None

    def __call__(self, endpoint, body):
        request = json.loads(body)
        command, args = request["command"], request["args"]
        if self.error:
            return {"ok": False, "error": self.error}
        metadata = {
            **{
                key: self.snapshot[key]
                for key in ("protocol", "workspace_id", "revision", "initialized")
            },
            "device_label": "TEST OFFICE",
            "can_initialize": True,
            "storage_url": "https://docs.google.com/spreadsheets/d/teststoragefile/edit",
            "report_url": "https://docs.google.com/spreadsheets/d/testreportfile/edit",
        }
        if command in {"read", "status"}:
            return {
                "ok": True,
                "result": {
                    **metadata,
                    **({"snapshot": copy.deepcopy(self.snapshot)} if command == "read" else {}),
                },
            }
        if command == "report":
            assert args["expected_revision"] == self.snapshot["revision"]
            self.report = args["table"]
            return {"ok": True, "result": {"rows": len(self.report) - 1}}
        receipt = (request["device_id"], args["request_id"])
        digest = fingerprint({"command": command, "args": args})
        replayed = receipt in self.receipts
        if replayed:
            assert self.receipts[receipt] == digest
        else:
            if args["expected_revision"] != self.snapshot["revision"]:
                return {"ok": False, "error": {"code": "conflict", "outcome": "not_committed"}}
            records = {row["key"]: row for row in self.snapshot["records"]}
            changes = args.get("records", args.get("changes", []))
            revision = self.snapshot["revision"] + int(bool(changes) or command == "initialize")
            for change in changes:
                records[change["key"]] = {
                    "key": change["key"],
                    "kind": change["kind"],
                    "value": change["value"],
                    "revision": revision,
                    "origin": {"device_label": "TEST OFFICE", "actor": args["actor"]},
                    "changed_at": "2026-10-31T00:00:00Z",
                }
            candidate = {
                **self.snapshot,
                "revision": revision,
                "initialized": True,
                "records": sorted(records.values(), key=lambda item: item["key"]),
            }
            validate_snapshot(candidate)
            self.snapshot = candidate
            self.receipts[receipt] = digest
        if self.lose_response:
            self.lose_response = False
            raise SharedError("Connection lost", uncertain=True)
        response = {"snapshot": copy.deepcopy(self.snapshot), "replayed": replayed}
        if self.bad_response:
            response["workspace_id"] = str(uuid4())
        return {"ok": True, "result": response}


@pytest.fixture
def computers(tmp_path, monkeypatch):
    databases = []
    for name in ("office", "second"):
        engine = create_engine("sqlite:///" + str(tmp_path / (name + ".db")))
        event.listen(engine, "connect", lambda db, _: db.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            bind_empty_database(conn)
            run_migrations(conn)
        db = Session(engine, expire_on_commit=False, autoflush=False)
        db.add(LocalUser(username=name, password_hash="PRIVATE", role="admin"))
        db.commit()
        databases.append(db)
    monkeypatch.setattr(service, "DB_PATH", tmp_path / "office.db")
    bridge = Bridge()
    connections = [WorkspaceConnection(Vault(), bridge) for _ in databases]
    for connection in connections:
        connection.configure(ENDPOINT)

    def use(index):
        monkeypatch.setattr(service, "connection", connections[index])
        return databases[index]

    yield databases, connections, bridge, use
    service.previews.clear()
    for db in databases:
        db.close()
        db.bind.dispose()


def seed(db):
    program = Program(name="MASTER OF SCIENCE")
    scholar = Scholar(name="ALPHA TEST", profile_remarks="FIRST NOTE", department="CAS")
    scholar.participations = [
        FsdpParticipation(
            program=program,
            application_key="first",
            start_academic_year="2021",
            start_term="Summer",
            status="Incomplete",
            allowed_duration_years=3,
        )
    ]
    scholar.education = [
        ScholarEducation(
            level="Bachelor", degree="BS", graduation_year="2020", graduation_year_manual=True
        )
    ]
    scholar.requirements = [
        ScholarRequirement(
            requirement_name="FORM", is_complete=True, completed_at=datetime(2021, 1, 1)
        )
    ]
    db.add_all([scholar, Scholar(name="BETA TEST")])
    db.flush()
    db.add(
        OfficeLog(
            scholar_id=scholar.id,
            scholar_name=scholar.name,
            user_id=1,
            username="OFFICE",
            entry_type="NOTE",
            note="RECEIVED",
            occurred_on=date(2026, 10, 31),
        )
    )
    db.commit()
    return scholar


def sync(db, mode="sync", choices=None):
    preview = service.previews.create(db, USER, mode)
    return service.apply_preview(db, USER, preview["preview_id"], choices or {})


def test_two_computers_round_trip_and_distinct_edits(computers):
    databases, _, _, use = computers
    office = use(0)
    scholar = seed(office)
    before = capture(office)
    original_ids = (scholar.id, scholar.participations[0].id, scholar.education[0].id)
    sync(office, "initialize")
    assert capture(office) == before
    assert service.local_status(office)["joined"]
    second = use(1)
    sync(second, "join")
    assert capture(second) == before
    assert second.scalar(select(LocalUser)).username == "second"
    office = use(0)
    office.scalar(
        select(Scholar).where(Scholar.name == "ALPHA TEST")
    ).profile_remarks = "OFFICE CHANGE"
    office.commit()
    assert service.local_status(office)["state"] == "dirty"
    sync(office)
    second = use(1)
    second.scalar(select(Scholar).where(Scholar.name == "BETA TEST")).rank = "STAFF NOTE"
    second.commit()
    sync(second)
    office = use(0)
    sync(office)
    assert capture(office) == capture(second)
    office.refresh(scholar)
    assert (scholar.id, scholar.participations[0].id, scholar.education[0].id) == original_ids
    assert service.local_status(office)["state"] == "ready"
    assert len(report_table(service.baseline(service.state_row(office)))[0]) == 16


def test_conflict_choices_and_stale_preview(computers):
    _, _, bridge, use = computers
    office = use(0)
    seed(office)
    sync(office, "initialize")
    second = use(1)
    sync(second, "join")
    second.scalar(select(Scholar).where(Scholar.name == "ALPHA TEST")).profile_remarks = "SECOND"
    second.commit()
    office = use(0)
    office.scalar(select(Scholar).where(Scholar.name == "ALPHA TEST")).profile_remarks = "OFFICE"
    office.commit()
    sync(office)
    second = use(1)
    preview = service.previews.create(second, USER, "sync")
    assert len(preview["conflicts"]) == 1
    with pytest.raises(HTTPException, match="Choose"):
        service.apply_preview(second, USER, preview["preview_id"], {})
    choices = {preview["conflicts"][0]: "shared"}
    service.apply_preview(second, USER, preview["preview_id"], choices)
    assert service.apply_preview(second, USER, preview["preview_id"], choices)["replayed"]
    with pytest.raises(HTTPException, match="different"):
        service.apply_preview(second, USER, preview["preview_id"], {})
    preview = service.previews.create(second, USER, "sync")
    bridge.snapshot["revision"] += 1
    with pytest.raises(SharedError):
        service.apply_preview(second, USER, preview["preview_id"], {})
    assert not service.state_row(second).pending_json


@pytest.mark.parametrize("bad_result", [False, True])
def test_lost_or_malformed_commit_keeps_pending_and_exact_retry(computers, bad_result):
    _, _, bridge, use = computers
    db = use(0)
    seed(db)
    bridge.bad_response = bad_result
    bridge.lose_response = not bad_result
    with pytest.raises(SharedError):
        sync(db, "initialize")
    assert service.state_row(db).pending_json
    with pytest.raises(HTTPException) as blocked:
        service.assert_local_writes_allowed(db, "/api/v1/fsdp/scholars")
    assert blocked.value.status_code == 423
    service.previews.clear()
    bridge.error = {"code": "unauthorized", "outcome": "unknown"}
    with pytest.raises(SharedError):
        service.finish_pending(db, USER)
    assert service.state_row(db).pending_json
    bridge.error = None
    bridge.bad_response = False
    assert service.finish_pending(db, USER)["replayed"]
    assert len(bridge.receipts) == 1
    assert not service.state_row(db).pending_json


def test_restored_checkpoint_requires_join_and_accounts_stay_local(computers):
    _, connections, _, use = computers
    db = use(0)
    seed(db)
    sync(db, "initialize")
    state = service.state_row(db)
    state.cache_id = str(uuid4())
    db.commit()
    assert service.local_status(db)["state"] == "rejoin_required"
    with pytest.raises(HTTPException):
        sync(db)
    sync(db, "join")
    assert service.local_status(db)["joined"]
    assert "PRIVATE" not in json.dumps(capture(db))
    assert "device_key" not in connections[0].public()


def test_local_apply_failure_retains_remote_receipt(computers, monkeypatch):
    _, _, bridge, use = computers
    db = use(0)
    seed(db)
    real = service.apply_snapshot

    def broken(*_):
        raise RuntimeError("simulated local disk failure")

    monkeypatch.setattr(service, "apply_snapshot", broken)
    with pytest.raises(SharedError):
        sync(db, "initialize")
    assert service.state_row(db).pending_json
    monkeypatch.setattr(service, "apply_snapshot", real)
    assert service.finish_pending(db, USER)["replayed"]
    assert len(bridge.receipts) == 1


def test_read_only_capture_validation_and_no_change_idempotence(computers):
    _, _, bridge, use = computers
    db = use(0)
    scholar = seed(db)
    before = capture(db)
    assert not db.new and not db.dirty
    sync(db, "initialize")
    program = db.scalar(select(Program))
    revision = program.revision
    sync(db)
    assert program.revision == revision
    assert capture(db) == before
    invalid = copy.deepcopy(bridge.snapshot)
    next(row for row in invalid["records"] if row["kind"] == "scholar")["value"]["name"] = ""
    with pytest.raises(ValueError):
        validate_snapshot(invalid)
    assert scholar.education[0].graduation_year_manual


def test_delete_scholar_retains_office_log_identity(computers):
    _, _, _, use = computers
    db = use(0)
    scholar = seed(db)
    sync(db, "initialize")
    before = capture(db)
    db.delete(scholar)
    db.commit()
    planned = merge(
        service.baseline(service.state_row(db)),
        capture(db),
        service.baseline(service.state_row(db)),
    )
    assert len(planned["changes"]) == 1
    assert planned["changes"][0]["value"] is None
    sync(db)
    log = next(row for row in before.values() if row["kind"] == "office_log")
    assert next(row for row in capture(db).values() if row["kind"] == "office_log") == log


def test_api_pending_guard_report_and_connection_restrictions(client, monkeypatch, tmp_path):
    bridge = Bridge()
    connection = WorkspaceConnection(Vault(), bridge)
    monkeypatch.setattr(service, "connection", connection)
    monkeypatch.setattr(service, "DB_PATH", tmp_path / "isolated.db")
    root = "/api/v1/shared-workspace"
    assert (
        client.post(
            "/api/v1/fsdp", json={"name": "API TEST", "profile_remarks": "SHARED REMARK"}
        ).status_code
        == 201
    )
    assert not client.get(root).json()["configured"]
    configured = client.post(root + "/configure", json={"endpoint": ENDPOINT})
    assert configured.status_code == 200
    assert "device_key" not in configured.json()
    assert client.get("/api/v1/health").json()["shared_workspace_configured"]
    assert client.post(root + "/check").status_code == 200
    assert (
        client.post("/api/v1/google-sheets/sync", json={"replace_report": True}).status_code == 409
    )
    preview = client.post(root + "/preview", json={"mode": "initialize"}).json()
    bridge.lose_response = True
    result = client.post(
        root + "/apply", json={"preview_id": preview["preview_id"], "choices": {}, "confirm": True}
    )
    assert result.status_code == 503, result.text
    assert client.get(root).json()["state"] == "pending"
    assert client.post("/api/v1/fsdp", json={"name": "BLOCKED"}).status_code == 423
    assert client.delete(root + "/connection").status_code == 409
    assert client.post(root + "/retry").status_code == 200
    assert client.post(root + "/report").status_code == 200
    assert bridge.report[1][7] == "SHARED REMARK"
    assert client.post("/api/v1/fsdp", json={"name": "UNSENT"}).status_code == 201
    assert client.post(root + "/report").status_code == 200
    assert len(bridge.report) == 2
    assert client.delete(root + "/connection").status_code == 200


def test_merge_rejects_unknown_choices_and_invalid_relationship(computers):
    _, _, bridge, use = computers
    db = use(0)
    seed(db)
    sync(db, "initialize")
    local = capture(db)
    with pytest.raises(ValueError, match="choices"):
        merge(bridge.snapshot, local, bridge.snapshot, {str(uuid4()): "local"})
    invalid = copy.deepcopy(local)
    program_key = next(key for key, record in invalid.items() if record["kind"] == "program")
    del invalid[program_key]
    with pytest.raises(ValueError, match="missing program"):
        merge(bridge.snapshot, invalid, bridge.snapshot)


def test_schema18_upgrade_preserves_every_old_field_and_backfills_stable_keys(tmp_path):
    path = tmp_path / "old.db"
    engine = create_engine("sqlite:///" + str(path))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        bind_empty_database(conn)
        run_migrations(conn)
    with Session(engine) as db:
        seed(db)
    tables = (
        "scholars",
        "programs",
        "fsdp_participations",
        "scholar_education",
        "scholar_requirements",
        "office_logs",
    )
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE shared_workspace_state")
        conn.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN shared_order")
        conn.exec_driver_sql("ALTER TABLE scholar_education DROP COLUMN shared_order")
        conn.exec_driver_sql("DELETE FROM schema_migrations WHERE version=19")
        for table in tables:
            conn.exec_driver_sql(f"DROP INDEX uq_{table}_cloud_key")
            conn.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN cloud_key")
        before = {
            table: [
                dict(row)
                for row in conn.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").mappings()
            ]
            for table in tables
        }
    recovery = upgrade_database(engine, path)
    assert recovery and recovery.is_file()
    with sqlite3.connect(recovery) as db:
        assert db.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (18,)
        assert "cloud_key" not in {row[1] for row in db.execute("PRAGMA table_info(scholars)")}
    with engine.connect() as conn:
        after = {
            table: [
                dict(row)
                for row in conn.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").mappings()
            ]
            for table in tables
        }
    for table in tables:
        assert [
            {key: value for key, value in row.items() if key not in {"cloud_key", "shared_order"}}
            for row in after[table]
        ] == before[table]
        assert all(row["cloud_key"] for row in after[table])
    assert upgrade_database(engine, path) is None
    with engine.connect() as conn:
        assert [
            row.cloud_key
            for row in conn.exec_driver_sql("SELECT cloud_key FROM scholars ORDER BY id")
        ] == [row["cloud_key"] for row in after["scholars"]]
    engine.dispose()


def test_same_period_grants_keep_current_status_on_another_computer(computers):
    _, _, _, use = computers
    office = use(0)
    scholar = seed(office)
    scholar.participations[0].cloud_key = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    scholar.participations.append(
        FsdpParticipation(
            program=scholar.participations[0].program,
            cloud_key="00000000-0000-4000-8000-000000000001",
            start_academic_year="2021",
            start_term="Summer",
            status="Completed",
        )
    )
    office.commit()
    assert current_grant(scholar).status == "Completed"
    sync(office, "initialize")
    second = use(1)
    sync(second, "join")
    other = second.scalar(select(Scholar).where(Scholar.name == scholar.name))
    assert current_grant(other).status == "Completed"
    assert capture(office) == capture(second)
