import csv
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.migrations import MIGRATIONS, run_migrations
from app.models import ActivityEvent, LocalUser, OfficeLog
from app.record_text import academic_year
from app.upgrade import upgrade_database


def create(client, **fields):
    response = client.post("/api/v1/fsdp", json={"name": "Office Scholar", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def update(client, row, **fields):
    payload = {**row, "participations": [{**grant, "program_name": grant["name"]} for grant in row["participations"]], **fields}
    response = client.put(f"/api/v1/fsdp/{row['id']}", json=payload, headers={"If-Match": str(row["revision"])})
    assert response.status_code == 200, response.text
    return response.json()


def test_completed_date_education_and_independent_case_status(client):
    row = create(client, participations=[{"program_name": "Master of Science", "status": "Graduated", "graduation_date": "2023-06-01", "case_status": "Closed", "contract_completed_on": "2019-01-01"}])
    grant = row["participations"][0]
    assert grant["status"] == row["current_status"] == "Completed"
    assert grant["case_status"] == "Closed" and grant["payback_attention"] == "Completed"
    assert row["education"][0]["graduation_year"] == "2023"
    assert row["education"][0]["degree"] == "MASTER OF SCIENCE"
    assert client.get("/api/v1/fsdp/page?status=Graduated").json()["total"] == 1
    assert client.get("/api/v1/fsdp/page?status=Completed").json()["total"] == 1
    summary = client.get("/api/v1/fsdp/summary").json()
    assert summary["completed"] == summary["graduated"] == 1
    report = client.get("/api/v1/fsdp/report?status=Completed").json()
    assert report["status_counts"]["Completed"] == 1
    assert report["department_totals"][0]["completed"] == report["department_totals"][0]["graduated"] == 1


def test_closed_does_not_clear_payback_and_copy_resets_dates_outcome_case(client):
    row = create(client, participations=[{"program_name": "Annual", "status": "Payback", "case_status": "Closed", "graduation_date": "2020-06-01", "contract_completed_on": "2019-01-01", "start_date": "2015-01-01", "end_date": "2018-12-01", "extension": "Approved extension", "remarks": "Preserved annual note"}])
    original = row["participations"][0]
    assert original["payback_attention"] == "Recorded Payback"
    copy = client.post(f"/api/v1/fsdp/{row['id']}/grants/{original['id']}/duplicate", headers={"If-Match": "0"})
    assert copy.status_code == 201, copy.text
    copied = copy.json()["participations"][1]
    assert copied["status"] == "On Going" and copied["case_status"] == "Open"
    assert all(copied[key] is None for key in ("start_date", "end_date", "contract_completed_on", "graduation_date"))
    assert copied["extension"] is None
    assert copied["remarks"] == original["remarks"] == "PRESERVED ANNUAL NOTE"
    assert copy.json()["participations"][0] == original


def test_new_unparsed_tenure_fallback_is_uppercase(client):
    row = create(client, tenure="Special appointment")
    assert row["tenure"] == row["tenure_note"] == "SPECIAL APPOINTMENT"
    assert row["tenure_years"] is None


def test_completed_annual_grant_clears_same_program_only_and_closed_remains_review(client):
    row = create(client, participations=[{"program_name": "Annual", "status": "On Going", "contract_completed_on": "2019-01-01"}, {"program_name": "annual", "status": "Completed"}, {"program_name": "Separate", "case_status": "Closed", "contract_completed_on": "2019-01-01"}])
    assert [item["payback_attention"] for item in row["participations"]] == ["Completed", "Completed", "Payback review"]
    assert len(row["education"]) == 1 and row["education"][0]["graduation_year"] is None


def test_old_full_form_preserves_new_fields_and_manual_education_intent(client):
    row = create(client, participations=[{"program_name": "Master of Science", "status": "Completed", "graduation_date": "2023-06-01", "case_status": "Closed"}])
    old = [{key: value for key, value in grant.items() if key not in {"graduation_date", "case_status"}} | {"program_name": grant["name"]} for grant in row["participations"]]
    saved = update(client, row, participations=old)
    assert saved["participations"][0]["graduation_date"] == "2023-06-01"
    assert saved["participations"][0]["case_status"] == "Closed"
    corrected = update(client, saved, education=[{**saved["education"][0], "graduation_year": None}])
    changed = update(client, corrected, participations=[{**corrected["participations"][0], "program_name": "Master of Science", "graduation_date": "2024-06-01"}])
    assert changed["education"][0]["graduation_year"] is None
    removed = update(client, changed, education=[])
    assert removed["education"] == []
    assert update(client, removed)["education"] == []


def test_explicit_date_updates_inferred_year_without_overriding_manual_correction(client):
    row = create(client, participations=[{"program_name": "Master of Science", "status": "Completed", "graduation_date": "2023-06-01"}])
    row = update(client, row, participations=[{**row["participations"][0], "program_name": "Master of Science", "graduation_date": "2024-06-01"}])
    assert row["education"][0]["graduation_year"] == "2024"
    row = update(client, row, education=[{**row["education"][0], "graduation_year": "2022"}])
    row = update(client, row, participations=[{**row["participations"][0], "program_name": "Master of Science", "graduation_date": "2025-06-01"}])
    assert row["education"][0]["graduation_year"] == "2022"


@pytest.mark.parametrize("raw,expected", [("20252026", "2025-2026"), (" 20262027 ", "2026-2027"), ("20252025", "20252025"), ("999910000", "999910000"), ("202", "202"), ("Historical entry", "Historical entry"), (None, None)])
def test_academic_year_format_is_lightweight(raw, expected):
    assert academic_year(raw) == expected


def test_business_text_uppercase_credentials_and_enums_unchanged(client):
    row = create(client, name="Élodie Santos", rank="Assistant professor", tenure_note="Appointment note", profile_remarks="Office remark", education=[{"level": "Master’s", "degree": "Master of Arts", "institution": "University"}], participations=[{"program_name": "Scholarship program", "delivering_hei": "University", "grant_other": "Research", "extension": "Approved", "remarks": "Check transcript", "start_term": "Summer", "start_academic_year": "20252026"}], requirements=[{"requirement_name": "Transcript", "remarks": "Received"}])
    assert row["name"] == "ÉLODIE SANTOS" and row["rank"] == "ASSISTANT PROFESSOR"
    assert row["tenure_note"] == "APPOINTMENT NOTE" and row["profile_remarks"] == "OFFICE REMARK"
    assert row["education"][0]["level"] == "MASTER’S"
    assert row["requirements"][0]["requirement_name"] == "TRANSCRIPT"
    grant = row["participations"][0]
    assert grant["name"] == "SCHOLARSHIP PROGRAM" and grant["remarks"] == "CHECK TRANSCRIPT"
    assert grant["status"] == "On Going" and grant["start_term"] == "Summer" and grant["start_academic_year"] == "2025-2026"
    assert client.get("/api/v1/auth/me").json()["username"] == "test-admin"
    assert client.post("/api/v1/auth/login", json={"username": "test-admin", "password": "test-password-123"}).status_code == 200


def test_office_log_authenticated_actor_append_only_single_activity_and_retry(client):
    scholar = create(client)
    payload = {"scholar_id": scholar["id"], "note": "Transcript received", "entry_type": "Document received", "document_name": "Transcript", "from_department": "Registrar", "username": "forged", "user_id": 999}
    key = {"Idempotency-Key": str(uuid4())}
    response = client.post("/api/v1/office-logs", json=payload, headers=key)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["username"] == "test-admin" and row["user_id"] != 999
    assert row["note"] == "TRANSCRIPT RECEIVED" and row["document_name"] == "TRANSCRIPT"
    assert row["occurred_on"] == date.today().isoformat() and row["scholar_name"] == scholar["name"]
    repeated = client.post("/api/v1/office-logs", json=payload, headers=key)
    assert repeated.status_code == 201 and repeated.json() == row
    assert client.post("/api/v1/office-logs", json={**payload, "note": "Changed"}, headers=key).status_code == 409
    history = client.get(f"/api/v1/activity/scholars/{scholar['id']}").json()["items"]
    assert len([item for item in history if item["record_type"] == "office_logs"]) == 1
    assert client.put(f"/api/v1/office-logs/{row['id']}", json={"note": "Rewrite"}).status_code == 405
    assert client.delete(f"/api/v1/office-logs/{row['id']}").status_code == 405
    assert client.get("/api/v1/office-logs").json()["items"] == [row]
    assert client.post("/api/v1/office-logs", json={"note": " "}).status_code == 422
    assert client.post("/api/v1/office-logs", json={"note": "Valid"}, headers={"Idempotency-Key": "invalid"}).status_code == 422
    assert client.get("/api/v1/office-logs").json()["total"] == 1


def test_office_log_staff_access_paging_filters_csv_and_deleted_scholar_snapshot(client):
    scholar = create(client, name="Logged Scholar")
    client.post("/api/v1/auth/users", json={"username": "log-staff", "password": "temporary-password-123", "role": "staff"})
    token = client.post("/api/v1/auth/login", json={"username": "log-staff", "password": "temporary-password-123"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/change-password", json={"current_password": "temporary-password-123", "new_password": "permanent-password-123"}, headers=headers).status_code == 204
    token = client.post("/api/v1/auth/login", json={"username": "log-staff", "password": "permanent-password-123"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    for payload in [{"note": "Office note"}, {"note": "Transferred form", "entry_type": "Document transferred", "scholar_id": scholar["id"], "to_department": "Registrar"}]:
        assert client.post("/api/v1/office-logs", json=payload, headers=headers).status_code == 201
    listing = client.get("/api/v1/office-logs?page_size=1", headers=headers).json()
    assert listing["total"] == 2 and len(listing["items"]) == 1
    assert client.get(f"/api/v1/office-logs?scholar_id={scholar['id']}", headers=headers).json()["total"] == 1
    assert client.get("/api/v1/office-logs?search=registrar&entry_type=Document%20transferred", headers=headers).json()["total"] == 1
    assert client.get("/api/v1/activity", headers=headers).status_code == 403
    rows = list(csv.reader(io.StringIO(client.get("/api/v1/office-logs/export.csv?search=registrar", headers=headers).text)))
    assert rows[0] == ["ID", "Occurred On", "Created At", "Entry Type", "Scholar ID", "Scholar", "Note", "Document", "From Department", "To Department", "Recorded By"]
    assert len(rows) == 2 and rows[1][-1] == "log-staff"
    assert client.delete(f"/api/v1/fsdp/{scholar['id']}", headers={"If-Match": str(scholar["revision"])}).status_code == 204
    log = client.get("/api/v1/office-logs?search=logged").json()["items"][0]
    assert log["scholar_id"] is None and log["scholar_name"] == "LOGGED SCHOLAR"
    assert client.post("/api/v1/office-logs", json={"note": "Missing", "scholar_id": scholar["id"]}).status_code == 404
    client.headers.clear()
    assert client.get("/api/v1/office-logs").status_code == 401
    assert client.post("/api/v1/office-logs", json={"note": "Anonymous"}).status_code == 401


def test_csv_new_fields_and_no_grant_row_width(client):
    create(client, name="No grant")
    create(client, participations=[{"program_name": "Master", "status": "Completed", "graduation_date": "2023-06-01", "case_status": "Closed"}])
    rows = list(csv.reader(io.StringIO(client.get("/api/v1/maintenance/exports/fsdp.csv").text)))
    assert rows[0][-2:] == ["Graduation Date", "Case Status"]
    assert all(len(item) == len(rows[0]) == 27 for item in rows)
    values = {item[1]: item[-2:] for item in rows[1:]}
    assert values["OFFICE SCHOLAR"] == ["2023-06-01", "Closed"] and values["NO GRANT"] == ["", ""]
    report = list(csv.reader(io.StringIO(client.get("/api/v1/fsdp/report.csv").text)))
    header = next(index for index, row in enumerate(report) if row and row[0] == "Name")
    assert report[header][-2:] == ["Graduation Date", "Case Status"]
    assert all(len(item) == 21 for item in report[header:])


def test_schema_thirteen_is_additive_retains_history_and_is_repeatable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-office.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            run_migrations(connection)
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version=13")
            connection.exec_driver_sql("DROP TABLE office_logs")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN graduation_date")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN case_status")
            connection.exec_driver_sql("INSERT INTO programs(id,name,revision) VALUES(1,'Historical program',4)")
            connection.exec_driver_sql("INSERT INTO scholars(id,name,revision,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Historical scholar',3,0,'Cathedra','2020-01-02','2021-02-03')")
            connection.exec_driver_sql("INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_term,remarks) VALUES(8,1,1,'Graduated','Summer','Exact historical note')")
            run_migrations(connection)
            assert connection.exec_driver_sql("SELECT id,scholar_id,program_id,status,start_term,remarks,graduation_date,case_status FROM fsdp_participations").one() == (8, 1, 1, "Completed", "Summer", "Exact historical note", None, "Open")
            assert connection.exec_driver_sql("SELECT id,name,revision FROM programs").one() == (1, "Historical program", 4)
            assert connection.exec_driver_sql("SELECT name,updated_at FROM scholars").one() == ("Historical scholar", "2021-02-03")
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM office_logs").scalar() == 0
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            before = connection.exec_driver_sql("SELECT * FROM scholars").all()
            run_migrations(connection)
            assert connection.exec_driver_sql("SELECT * FROM scholars").all() == before
            assert connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == MIGRATIONS[-1][0] == 13
    finally:
        engine.dispose()


def test_concurrent_office_log_retries_create_one_entry_and_audit(tmp_path):
    from app.api.office_logs import OfficeLogCreate, create_log

    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", connect_args={"check_same_thread": False})
    barrier = threading.Barrier(2)
    key = str(uuid4())
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            user = LocalUser(username="same-actor", password_hash="synthetic", role="staff")
            db.add(user)
            db.commit()
            identity = user.id

        def submit(_):
            with Session(engine) as db:
                user = db.get(LocalUser, identity)
                db.info["audit_actor"] = (user.id, user.username)
                barrier.wait(timeout=15)
                entry = create_log(OfficeLogCreate(note="Concurrent office note"), db, user, key)
                return entry.id

        with ThreadPoolExecutor(max_workers=2) as workers:
            ids = list(workers.map(submit, range(2)))
        assert ids[0] == ids[1]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(OfficeLog)) == 1
            assert db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.record_type == "office_logs")) == 1
    finally:
        engine.dispose()


def test_office_log_audit_failure_rolls_back_record(tmp_path, monkeypatch):
    import app.api.office_logs as logs

    engine = create_engine(f"sqlite:///{tmp_path / 'rollback.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            actor = LocalUser(username="actor", password_hash="synthetic", role="admin")
            db.add(actor)
            db.commit()
            db.info["audit_actor"] = (actor.id, actor.username)

            def fail_audit(*_, **__):
                raise RuntimeError("Synthetic activity failure")

            monkeypatch.setattr(logs, "add_activity", fail_audit)
            with pytest.raises(RuntimeError, match="Synthetic activity failure"):
                logs.create_log(logs.OfficeLogCreate(note="Rollback note"), db, actor, None)
            db.rollback()
            assert db.scalar(select(func.count()).select_from(OfficeLog)) == 0
            assert db.scalar(select(func.count()).select_from(ActivityEvent)) == 0
    finally:
        engine.dispose()


def test_office_log_unicode_search_and_literal_characters_match_csv(client):
    import app.main as main

    scholar = create(client, name="José Santos")
    first = client.post("/api/v1/office-logs", json={"scholar_id": scholar["id"], "note": "Réception 100%_ received"}).json()
    client.post("/api/v1/office-logs", json={"note": "Unrelated office entry"})
    for search in ("josé", "réception", "%_"):
        records = client.get("/api/v1/office-logs", params={"search": search}).json()
        rows = list(csv.DictReader(io.StringIO(client.get("/api/v1/office-logs/export.csv", params={"search": search}).text)))
        assert records["total"] == len(rows) == 1 and records["items"][0]["id"] == int(rows[0]["ID"]) == first["id"]
    with main.SessionLocal() as db:
        historical = db.get(OfficeLog, first["id"])
        historical.scholar_name = "José Santos"
        historical.note = "Réception 100%_ received"
        db.commit()
    for search in ("JOSÉ", "RÉCEPTION", "%_"):
        assert client.get("/api/v1/office-logs", params={"search": search}).json()["total"] == 1
        assert len(list(csv.DictReader(io.StringIO(client.get("/api/v1/office-logs/export.csv", params={"search": search}).text)))) == 1
    assert client.get("/api/v1/office-logs", params={"search": "%' OR 1=1 --"}).json()["total"] == 0


def test_unrelated_save_preserves_historical_free_text_and_explicit_new_tenure_note(client):
    import app.main as main
    from app.models import Scholar

    row = create(client, participations=[{"program_name": "Historical course", "remarks": "Initial"}])
    with main.SessionLocal() as db:
        scholar = db.get(Scholar, row["id"])
        scholar.name = "Historical Mixed Name"
        scholar.tenure = "  Historic tenure  "
        scholar.tenure_note = "  Exact original tenure note\n"
        scholar.profile_remarks = " Original profile remark\n"
        scholar.participations[0].remarks = " Exact original grant remark\n"
        scholar.participations[0].program.name = "Historical course"
        db.commit()
    old = client.get(f"/api/v1/fsdp/{row['id']}").json()
    payload = {**old, "participations": [{**grant, "program_name": grant["name"], "source_program_id": grant["program_id"]} for grant in old["participations"]]}
    payload.pop("tenure_years")
    payload.pop("tenure_note")
    payload["age"] = 40
    response = client.put(f"/api/v1/fsdp/{old['id']}", json=payload, headers={"If-Match": str(old["revision"])})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["name"] == old["name"] and saved["tenure"] == old["tenure"]
    assert saved["tenure_note"] == old["tenure_note"] and saved["profile_remarks"] == old["profile_remarks"]
    assert saved["participations"][0]["name"] == "Historical course"
    assert saved["participations"][0]["remarks"] == old["participations"][0]["remarks"]
    new = create(client, tenure="Special appointment", tenure_note="Explicit office explanation")
    assert new["tenure_years"] is None and new["tenure_note"] == "EXPLICIT OFFICE EXPLANATION"


def test_schema_thirteen_failure_restores_old_fields_outcome_and_snapshot(tmp_path, monkeypatch):
    import sqlite3

    import app.migrations as migrations

    path = tmp_path / "migration-failure.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        upgrade_database(engine, path)
        with engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version=13")
            connection.exec_driver_sql("DROP TABLE office_logs")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN graduation_date")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN case_status")
            connection.exec_driver_sql("INSERT INTO programs(id,name) VALUES(1,'Old program')")
            connection.exec_driver_sql("INSERT INTO scholars(id,name,revision,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Original scholar',8,0,'Cathedra','2020-01-02','2021-02-03')")
            connection.exec_driver_sql("INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_term,remarks) VALUES(9,1,1,'Graduated','Summer','Exact note')")
            grant_before = connection.exec_driver_sql("SELECT * FROM fsdp_participations").all()
            scholar_before = connection.exec_driver_sql("SELECT * FROM scholars").all()
        original = next(item[2] for item in migrations.MIGRATIONS if item[0] == 13)

        def fail_after_backfill(connection):
            original(connection)
            raise RuntimeError("Synthetic schema13 failure")

        monkeypatch.setattr(migrations, "MIGRATIONS", [(version, label, fail_after_backfill if version == 13 else migration) for version, label, migration in migrations.MIGRATIONS])
        with pytest.raises(RuntimeError, match="Synthetic schema13 failure"):
            upgrade_database(engine, path)
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == 12
            assert connection.exec_driver_sql("SELECT * FROM fsdp_participations").all() == grant_before
            assert connection.exec_driver_sql("SELECT * FROM scholars").all() == scholar_before
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM scholar_education").scalar() == 0
            assert connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='office_logs'").first() is None
        snapshots = list((tmp_path / "backups").glob("*.db"))
        assert len(snapshots) == 1
        with sqlite3.connect(snapshots[0]) as backup:
            assert backup.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (12,)
            assert backup.execute("SELECT status,remarks,start_term FROM fsdp_participations").fetchone() == ("Graduated", "Exact note", "Summer")
    finally:
        engine.dispose()
