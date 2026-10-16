import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import auth as account_api
from app.api import fsdp, maintenance
from app.concurrency import advance_revision
from app.db import Base
from app.migrations import run_migrations
from app.models import ActivityEvent, LocalUser, Scholar
from app.schemas import ProgramUpdate, ScholarCreate, ScholarUpdate
from app.scholar_identity import next_scholar_id


def create_engine_with_schema(path):
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    event.listen(
        engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON")
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        run_migrations(connection)
    return engine


def downgrade_to_schema_three(connection):
    connection.exec_driver_sql("DROP TRIGGER track_scholar_identity")
    connection.exec_driver_sql("DROP TABLE scholar_id_counter")
    connection.exec_driver_sql("DROP INDEX uq_local_users_username_lower")
    connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version >= 4")


def test_deleted_identity_cannot_overwrite_replacement_or_mix_history(client):
    old = client.post("/api/v1/fsdp", json={"name": "Original person"}).json()
    old_path = f"/api/v1/fsdp/{old['id']}"
    old_headers = {"If-Match": str(old["revision"])}
    assert client.delete(old_path, headers=old_headers).status_code == 204
    new = client.post("/api/v1/fsdp", json={"name": "Replacement person"}).json()
    assert new["id"] > old["id"]
    stale = {"name": old["name"], "participations": [], "requirements": []}
    assert client.put(old_path, headers=old_headers, json=stale).status_code == 404
    assert client.delete(old_path, headers=old_headers).status_code == 404
    history = client.get(f"/api/v1/activity/scholars/{new['id']}").json()
    assert history["total"] == 1
    assert history["items"][0]["operation"] == "Created"
    assert client.get(f"/api/v1/fsdp/{new['id']}").json()["name"] == new["name"]


def test_failed_scholar_creation_rolls_back_counter_and_rows(client):
    response = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Rejected",
            "participations": [
                {
                    "id": 999,
                    "program_name": "Rejected program",
                    "start_term": "1st",
                    "start_academic_year": "2026-2027",
                }
            ],
        },
    )
    assert response.status_code == 409
    created = client.post("/api/v1/fsdp", json={"name": "Valid"}).json()
    assert created["id"] == 1
    assert client.get("/api/v1/fsdp/programs").json() == []


def test_migration_seeds_historical_ids_and_preserves_records(tmp_path):
    engine = create_engine_with_schema(tmp_path / "migration.db")
    try:
        with engine.begin() as connection:
            downgrade_to_schema_three(connection)
            connection.execute(
                Scholar.__table__.insert().values(
                    id=7, name="Existing", department="CAS", revision=3
                )
            )
            connection.execute(
                ActivityEvent.__table__.insert().values(
                    action="Deleted FSDP #50",
                    area="FSDP",
                    record_type="scholars",
                    record_id=50,
                    subject_scholar_id=None,
                    operation="Deleted",
                )
            )
            connection.execute(
                LocalUser.__table__.insert().values(
                    id=4,
                    username="Owner",
                    password_hash="preserved-hash",
                    role="admin",
                )
            )
            before = {
                table: connection.exec_driver_sql(f"SELECT * FROM {table}").fetchall()
                for table in ("scholars", "activity_events", "local_users")
            }
            run_migrations(connection)
            run_migrations(connection)
            for table, records in before.items():
                after = connection.exec_driver_sql(f"SELECT * FROM {table}").fetchall()
                if table == "scholars":
                    columns = [
                        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")
                    ]
                    for old, new in zip(records, after, strict=True):
                        for field, old_value, new_value in zip(columns, old, new, strict=True):
                            assert new_value == (
                                "Faculty"
                                if field == "personnel_type"
                                else old_value + 1
                                if field == "revision"
                                else old_value
                            )
                else:
                    assert records == after
            assert (
                connection.exec_driver_sql("SELECT high_water FROM scholar_id_counter").scalar_one()
                == 50
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        with Session(engine) as db:
            assert next_scholar_id(db) == 51
    finally:
        engine.dispose()


def test_existing_username_collisions_stop_migration_without_changing_accounts(tmp_path):
    engine = create_engine_with_schema(tmp_path / "collisions.db")
    try:
        with engine.begin() as connection:
            downgrade_to_schema_three(connection)
            for username in ("Owner", "owner"):
                connection.execute(
                    LocalUser.__table__.insert().values(
                        username=username,
                        password_hash="preserved",
                        role="admin",
                    )
                )
        with (
            pytest.raises(RuntimeError, match="offline administrator review"),
            engine.begin() as conn,
        ):
            run_migrations(conn)
        with engine.connect() as connection:
            assert list(
                connection.exec_driver_sql("SELECT username FROM local_users ORDER BY id").scalars()
            ) == ["Owner", "owner"]
            assert (
                connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar()
                == 3
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE name = 'scholar_id_counter'"
                ).first()
                is None
            )
    finally:
        engine.dispose()


def test_counter_survives_explicit_import_delete_and_restart(tmp_path):
    path = tmp_path / "restart.db"
    engine = create_engine_with_schema(path)
    with Session(engine) as db:
        db.add(Scholar(id=80, name="Imported"))
        db.commit()
        db.delete(db.get(Scholar, 80))
        db.commit()
    engine.dispose()
    engine = create_engine_with_schema(path)
    try:
        with Session(engine) as db:
            created = fsdp.create_scholar(ScholarCreate(name="After restart"), db)
            assert created.id == 81
    finally:
        engine.dispose()


def test_concurrent_scholar_creation_allocates_distinct_ids(tmp_path):
    engine = create_engine_with_schema(tmp_path / "allocation.db")
    barrier = threading.Barrier(2)

    def create(name):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return fsdp.create_scholar(ScholarCreate(name=name), db).id

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            ids = list(workers.map(create, ["First", "Second"]))
        assert sorted(ids) == [1, 2]
    finally:
        engine.dispose()


@pytest.mark.parametrize("old_schema", [False, True])
def test_restore_never_lowers_retired_identity_floor(client, tmp_path, monkeypatch, old_schema):
    monkeypatch.setattr(maintenance, "DB_PATH", tmp_path / "cathedra.db")
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path / "backups")
    first = client.post("/api/v1/fsdp", json={"name": "Before backup"}).json()
    backup = client.post("/api/v1/maintenance/backups").json()["filename"]
    if old_schema:
        with closing(sqlite3.connect(tmp_path / "backups" / backup)) as database:
            database.execute("DROP TRIGGER track_scholar_identity")
            database.execute("DROP TABLE scholar_id_counter")
            database.execute("DROP INDEX uq_local_users_username_lower")
            database.execute("DELETE FROM schema_migrations WHERE version >= 4")
            database.commit()
    retired = client.post("/api/v1/fsdp", json={"name": "After backup"}).json()
    assert (
        client.delete(
            f"/api/v1/fsdp/{retired['id']}", headers={"If-Match": str(retired["revision"])}
        ).status_code
        == 204
    )
    assert client.post("/api/v1/maintenance/restore", json={"filename": backup}).status_code == 200
    token = client.post(
        "/api/v1/auth/login",
        json={
            "username": "test-admin",
            "password": "test-password-123",
        },
    ).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    replacement = client.post("/api/v1/fsdp", json={"name": "After restore"}).json()
    assert replacement["id"] > retired["id"] > first["id"]
    assert client.get(f"/api/v1/fsdp/{first['id']}").json()["name"] == first["name"]


def test_program_change_advances_each_scholar_once(client):
    created = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Two grants",
            "participations": [
                {"program_name": "Shared"},
                {"program_name": "Shared"},
            ],
        },
    ).json()
    program_id = created["participations"][0]["program_id"]
    assert (
        client.put(
            f"/api/v1/fsdp/programs/{program_id}",
            json={"name": "Renamed"},
            headers={"If-Match": "0"},
        ).status_code
        == 200
    )
    current = client.get(f"/api/v1/fsdp/{created['id']}").json()
    assert current["revision"] == created["revision"] + 1
    assert all(grant["name"] == "RENAMED" for grant in current["participations"])


def test_program_edit_preserves_concurrent_revision_and_rejects_stale_form(tmp_path):
    engine = create_engine_with_schema(tmp_path / "program-race.db")
    with Session(engine, autoflush=False) as db:
        original = fsdp.create_scholar(
            ScholarCreate(name="Concurrent", participations=[{"program_name": "Original"}]), db
        )
    scholar_id = original.id
    program_id = original.participations[0].program_id
    entered, release = threading.Event(), threading.Event()

    def pause_update(connection, cursor, statement, parameters, context, executemany):
        if connection.info.get("program_test") and statement.startswith("UPDATE programs"):
            entered.set()
            assert release.wait(15)

    def rename():
        with Session(engine) as db:
            connection_info = db.connection().info
            connection_info["program_test"] = True
            try:
                fsdp.update_program(
                    program_id, ProgramUpdate(name="Renamed"), 0, db, LocalUser(role="admin")
                )
            finally:
                connection_info.pop("program_test", None)

    event.listen(engine, "before_cursor_execute", pause_update)
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            pending = workers.submit(rename)
            assert entered.wait(15)
            with Session(engine) as db:
                advance_revision(db, Scholar, scholar_id, 0)
                db.commit()
                before = fsdp.get_scholar(scholar_id, db)
            release.set()
            pending.result(timeout=15)
        with Session(engine) as db:
            current = fsdp.get_scholar(scholar_id, db)
            assert current.revision == before.revision + 1 == 2
            grant = before.participations[0]
            stale = ScholarUpdate(
                name=before.name,
                requirements=[],
                participations=[
                    {"id": grant.id, "program_name": grant.name},
                ],
            )
            with pytest.raises(HTTPException) as caught:
                fsdp.update_scholar(scholar_id, stale, db, before.revision)
            assert caught.value.status_code == 409
            db.rollback()
            assert fsdp.get_scholar(scholar_id, db).participations[0].name == "RENAMED"
    finally:
        release.set()
        event.remove(engine, "before_cursor_execute", pause_update)
        engine.dispose()


@pytest.mark.parametrize("usernames", [("CaseUser", "caseuser"), ("SameUser", "SameUser")])
def test_concurrent_username_creation_returns_one_conflict(tmp_path, monkeypatch, usernames):
    engine = create_engine_with_schema(tmp_path / "users.db")
    barrier = threading.Barrier(2)
    original_hash = account_api.password_hash

    def hash_together(password):
        barrier.wait(timeout=15)
        return original_hash(password)

    monkeypatch.setattr(account_api, "password_hash", hash_together)

    def create(username):
        with Session(engine) as db:
            try:
                account_api.create_user(
                    account_api.UserCreate(
                        username=username,
                        password="synthetic-password-123",
                        role="staff",
                    ),
                    db,
                    LocalUser(role="admin"),
                )
                return 201
            except HTTPException as caught:
                return caught.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(create, usernames)) == [201, 409]
        with Session(engine) as db:
            assert len(db.scalars(select(LocalUser)).all()) == 1
    finally:
        engine.dispose()


def test_database_constraint_rejects_case_equivalent_users(tmp_path):
    engine = create_engine_with_schema(tmp_path / "constraint.db")
    try:
        with Session(engine) as db:
            db.add(LocalUser(username="Owner", password_hash="test", role="admin"))
            db.commit()
            db.add(LocalUser(username="owner", password_hash="test", role="staff"))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
            assert len(db.scalars(select(LocalUser)).all()) == 1
    finally:
        engine.dispose()


def test_username_integrity_error_is_rolled_back_as_conflict(tmp_path, monkeypatch):
    engine = create_engine_with_schema(tmp_path / "conflict.db")
    try:
        with Session(engine) as db:

            def fail_commit():
                raise IntegrityError("synthetic unique violation", {}, Exception())

            monkeypatch.setattr(db, "commit", fail_commit)
            with pytest.raises(HTTPException) as caught:
                account_api.create_user(
                    account_api.UserCreate(
                        username="Owner",
                        password="synthetic-password-123",
                        role="staff",
                    ),
                    db,
                    LocalUser(role="admin"),
                )
            assert caught.value.status_code == 409
            assert db.is_active
            assert db.scalars(select(LocalUser)).all() == []
    finally:
        engine.dispose()


def test_login_uses_database_normalization_on_both_sides(client):
    assert (
        client.post(
            "/api/v1/auth/users",
            json={
                "username": "Élodie",
                "password": "synthetic-password-123",
                "role": "staff",
            },
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "Élodie",
            "password": "synthetic-password-123",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "Élodie"


def test_failed_program_commit_rolls_back_scholar_revision(client, monkeypatch):
    created = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Rollback",
            "participations": [{"program_name": "Original"}],
        },
    ).json()
    existing = client.post("/api/v1/fsdp/programs", json={"name": "Existing"}).json()
    commit = fsdp.commit_record

    def conflict_at_commit(db):
        from app.models import Program

        program = next(item for item in db.dirty if isinstance(item, Program))
        program.name = existing["name"]
        commit(db)

    monkeypatch.setattr(fsdp, "commit_record", conflict_at_commit)
    program_id = created["participations"][0]["program_id"]
    response = client.put(
        f"/api/v1/fsdp/programs/{program_id}", json={"name": "Available"}, headers={"If-Match": "0"}
    )
    assert response.status_code == 409
    after = client.get(f"/api/v1/fsdp/{created['id']}").json()
    assert after["revision"] == created["revision"]
    assert after["participations"][0]["name"] == created["participations"][0]["name"]
