from datetime import date

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.migrations import run_migrations
from app.payback import classify_contract, grace_end


@pytest.mark.parametrize("status,completed,graduated,today,expected", [
    ("On Going", "2023-10-07", False, "2026-10-06", "In grace period"),
    ("On Going", "2023-10-07", False, "2026-10-07", "In grace period"),
    ("On Going", "2023-10-07", False, "2026-10-08", "Payback review"),
    ("Withdrawn", "2020-02-29", False, "2023-02-28", "In grace period"),
    ("Withdrawn", "2020-02-29", False, "2023-03-01", "Payback review"),
    ("On Going", None, False, "2026-10-07", "Completion date missing"),
    ("On Going", "2027-01-01", False, "2026-10-07", "Contract not completed"),
    ("On Going", "2020-01-01", True, "2026-10-07", "Completed"),
    ("Payback", None, True, "2026-10-07", "Recorded Payback"),
    (" payBACK ", "2020-01-01", False, "2026-10-07", "Recorded Payback"),
    ("On Going", "9999-01-01", False, "2026-10-07", "Contract not completed"),
])
def test_calendar_grace_rule(status, completed, graduated, today, expected):
    assert classify_contract(status, date.fromisoformat(completed) if completed else None, graduated, date.fromisoformat(today))[0] == expected


def create(client, name, grants, **extra):
    response = client.post("/api/v1/fsdp", json={"name": name, "participations": grants, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_same_program_graduation_outside_year_clears_old_grants_but_not_other_program(client):
    scholar = create(client, "Annual Scholar", [
        {"program_name": "Masters", "contract_completed_on": "2010-01-01", "start_academic_year": "2020-2021"},
        {"program_name": "Masters", "status": "Graduated", "start_academic_year": "2025-2026"},
        {"program_name": "Doctorate", "contract_completed_on": "2010-01-01", "start_academic_year": "2020-2021"},
        {"program_name": "Doctorate", "contract_completed_on": "2011-01-01", "start_academic_year": "2020-2021"},
    ])
    result = client.get("/api/v1/fsdp/payback?start_academic_year=2020-2021").json()
    assert [item["attention"] for item in result["items"]] == ["Payback review", "Payback review", "Completed"]
    assert result["scholar_counts"]["Payback review"] == 1
    assert result["grant_counts"]["Payback review"] == 2
    assert client.get(f"/api/v1/fsdp/{scholar['id']}").json()["revision"] == 0
    assert client.get(f"/api/v1/fsdp/{scholar['id']}").json()["participations"][0]["status"] == "On Going"


def test_optional_date_preserved_on_old_payload_and_explicitly_clearable(client):
    original = create(client, "Date Scholar", [{"program_name": "Course", "contract_completed_on": "2023-02-28"}])
    grant = original["participations"][0]
    payload = {"name": original["name"], "requirements": [], "participations": [{"id": grant["id"], "program_name": grant["name"]}]}
    updated = client.put(f"/api/v1/fsdp/{original['id']}", json=payload, headers={"If-Match": "0"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["participations"][0]["contract_completed_on"] == "2023-02-28"
    payload["participations"][0]["contract_completed_on"] = None
    cleared = client.put(f"/api/v1/fsdp/{original['id']}", json=payload, headers={"If-Match": "1"})
    assert cleared.json()["participations"][0]["contract_completed_on"] is None


def test_annual_copy_resets_outcome_and_contract_without_touching_original(client):
    original = create(client, "Copy Scholar", [{"program_name": "Annual", "status": "Payback", "contract_completed_on": "2020-01-01"}])
    response = client.post(f"/api/v1/fsdp/{original['id']}/grants/{original['participations'][0]['id']}/duplicate", headers={"If-Match": "0"})
    assert response.status_code == 201, response.text
    source, copy = response.json()["participations"]
    assert source["status"] == "Payback" and source["contract_completed_on"] == "2020-01-01"
    assert copy["status"] == "On Going" and copy["contract_completed_on"] is None


def test_payback_export_scope_matches_ui_filter_and_is_csv_safe(client):
    create(client, "=Scholar", [{"program_name": "=Course", "status": "Payback"}], department="CAS")
    create(client, "Unknown date", [{"program_name": "Course"}], department="CAS")
    create(client, "Other department", [{"program_name": "Other", "status": "Payback"}], department="CCS")
    csv = client.get("/api/v1/fsdp/payback.csv?department=CAS&attention=Payback%20action").text
    assert "'=SCHOLAR" in csv and "'=COURSE" in csv
    assert "UNKNOWN DATE" not in csv and "OTHER DEPARTMENT" not in csv
    client.headers.clear()
    assert client.get("/api/v1/fsdp/payback").status_code == 401
    assert client.get("/api/v1/fsdp/payback.csv").status_code == 401


def test_recorded_custom_categories_are_filterable_and_reported(client):
    create(client, "Custom grant", [{"program_name": "Special", "grant_type": "Thesis Grant", "status": "Deferred"}])
    options = client.get("/api/v1/fsdp/report-options").json()
    assert "Thesis Grant" in options["grant_types"] and "Deferred" in options["statuses"]
    report = client.get("/api/v1/fsdp/report?grant_type=Thesis%20Grant&status=Deferred").json()
    assert report["total"] == report["status_counts"]["Deferred"] == report["grant_type_counts"]["Thesis Grant"] == 1


def test_migration_adds_nullable_date_without_inference(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        run_migrations(connection)
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=7")
        connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN contract_completed_on")
        connection.exec_driver_sql("INSERT INTO programs(id,name) VALUES(1,'Course')")
        connection.exec_driver_sql("INSERT INTO scholars(id,name,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Scholar',0,'Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.exec_driver_sql("INSERT INTO fsdp_participations(id,scholar_id,program_id,status,end_date) VALUES(1,1,1,'On Going','2010-01-01')")
        run_migrations(connection)
        run_migrations(connection)
        assert connection.exec_driver_sql("SELECT end_date,contract_completed_on,status FROM fsdp_participations").first() == ("2010-01-01", None, "On Going")
    engine.dispose()


def test_leap_anniversary_is_calendar_years_not_days():
    assert grace_end(date(2024, 2, 29)) == date(2027, 2, 28)


def test_normalized_dashboard_report_scope_matches_older_whitespace_records(client):
    from sqlalchemy import text

    from app.db import get_db
    from app.main import app
    scholar = create(client, "Whitespace", [{"program_name": "Old", "start_academic_year": "2025-2026"}], department="CAS")
    provider = app.dependency_overrides[get_db]()
    db = next(provider)
    try:
        db.execute(text("UPDATE scholars SET department=' CAS ' WHERE id=:id"), {"id":scholar["id"]})
        db.execute(text("UPDATE fsdp_participations SET start_academic_year=' 2025-2026 ' WHERE scholar_id=:id"), {"id":scholar["id"]})
        db.commit()
    finally:
        provider.close()
    query="department=CAS&start_academic_year=2025-2026"
    analytics=client.get("/api/v1/fsdp/analytics?"+query).json()
    report=client.get("/api/v1/fsdp/report?"+query).json()
    assert analytics["scholars"] == report["total"] == 1
    assert len(report["items"][0]["participations"]) == 1
    assert "WHITESPACE" in client.get("/api/v1/fsdp/report.csv?"+query).text
