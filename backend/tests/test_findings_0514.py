from datetime import date

import pytest

from app.graduated_education import graduation_evidence


@pytest.mark.parametrize(("remarks", "expected"), [
    ("Graduated in 2022", (True, "2022")),
    ("Graduated on June 15, 2022", (True, "2022")),
    ("Graduated on May 15, 2022", (True, "2022")),
    ("Graduation year: 2021", (True, "2021")),
    ("Graduated 06/15/2020", (True, "2020")),
    ("Graduated", (True, None)),
    ("Graduated; Contract completed 2020", (True, None)),
    ("Not graduated in 2022", (False, None)),
    ("Hasn't graduated", (False, None)),
    ("Expected graduation year: 2026", (False, None)),
    ("Will be graduated in 2026", (False, None)),
    ("Graduated?", (False, None)),
    ("Graduation year: unknown", (False, None)),
    ("Graduation requirements submitted 2022", (False, None)),
    ("Graduate student since 2022", (False, None)),
    ("Contract completed on 2020-01-01", (False, None)),
    ("Graduated in 2020; Graduated in 2021", (True, None)),
    (f"Graduated in {date.today().year+1}", (False, None)),
])
def test_conservative_evidence(remarks, expected):
    assert graduation_evidence(remarks) == expected


def create(client, **fields):
    response = client.post("/api/v1/fsdp", json={"name": "Synthetic findings scholar", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def update(client, row, **fields):
    payload = {"name": row["name"], "education": row["education"], "requirements": [],
               "participations": [{**g, "program_name": g["name"]} for g in row["participations"]], **fields}
    response = client.put(f"/api/v1/fsdp/{row['id']}", json=payload, headers={"If-Match":str(row["revision"])})
    assert response.status_code == 200, response.text
    return response.json()


def test_remark_education_corrected_year_and_removal_survive(client):
    row = create(client, participations=[{"program_name":"Ph.D. Computing", "remarks":"Graduated in 2022", "status":"On Going"}])
    assert row["education"][0]["graduation_year"] == "2022"
    assert row["participations"][0]["status"] == "On Going"
    assert row["participations"][0]["payback_attention"] == "Completion date missing"
    row = update(client, row, education=[{**row["education"][0], "graduation_year":"2023"}])
    assert row["education"][0]["graduation_year"] == "2023"
    row = update(client, row, education=[])
    assert not row["education"]
    assert not update(client, row)["education"]


def test_annual_programs_do_not_duplicate_achievements_or_lose_types(client):
    row = create(client, participations=[
        {"program_name":"Master of Science", "grant_type":kind, "start_academic_year":year, "remarks":remarks}
        for kind,year,remarks in [
            ("Full Scholarship","2020-2021",""),
            ("Partial Scholarship","2021-2022",""),
            ("Thesis Aid","2022-2023","Graduated in 2023")]])
    assert len({g["program_id"] for g in row["participations"]}) == 1
    assert len(row["education"]) == 1
    assert len(update(client,row)["participations"]) == 3


def test_unknown_and_automatic_personnel_across_filters_and_csv(client):
    for department,personnel in [("CAS","Faculty"),("IIT","Staff"),("","Unknown"),("Unknown","Unknown")]:
        row = create(client, department=department, personnel_type="Staff")
        assert row["personnel_type"] == personnel
    page = client.get("/api/v1/fsdp/page?missing=personnel_type").json()
    assert page["total"] == 2
    assert {row["department"] for row in page["items"]} == {"Unknown"}
    assert client.get("/api/v1/fsdp/analytics?department=Unknown").json()["scholars"] == 2
    assert "Unknown" in client.get("/api/v1/maintenance/exports/fsdp.csv").text


def test_manual_pending_contract_and_transferred_reporting(client):
    pending = create(client, participations=[{"program_name":"Pending", "status":"Payback pending contract", "contract_completed_on":"2020-01-01"}])
    assert pending["participations"][0]["payback_attention"] == "Payback pending contract"
    assert pending["participations"][0]["status"] == "Payback pending contract"
    create(client, participations=[{"program_name":"Transferred program","status":"Transferred"}])
    queue = client.get("/api/v1/fsdp/payback?page=1&attention=Payback%20action").json()
    assert queue["total"] == 1
    report = client.get("/api/v1/fsdp/report").json()
    assert report["status_counts"]["Transferred"] == 1
    assert report["status_counts"]["Payback pending contract"] == 1
    assert report["department_totals"][0]["payback_pending_contract"] == 1
    assert any(item["attention"] == "Payback pending contract" for item in report["action_items"])
    assert "Transferred" in client.get("/api/v1/fsdp/report.csv").text


def test_backfill_is_idempotent_and_keeps_grants_and_notes(client):
    import app.main as main
    from app.migrations import _graduation_evidence_and_personnel

    row = create(client, department="CAS", profile_remarks="Office note", participations=[{"program_name":"Doctor of Education"}])
    with main.SessionLocal().bind.begin() as connection:
        connection.exec_driver_sql("UPDATE scholars SET personnel_type='Staff',updated_at='2000-01-01 00:00:00' WHERE id=?", (row["id"],))
        connection.exec_driver_sql("UPDATE fsdp_participations SET remarks='Graduated in 2021' WHERE scholar_id=?", (row["id"],))
        _graduation_evidence_and_personnel(connection)
        _graduation_evidence_and_personnel(connection)
    changed = client.get(f"/api/v1/fsdp/{row['id']}").json()
    assert changed["revision"] == row["revision"] + 1
    assert changed["personnel_type"] == "Faculty"
    assert changed["updated_at"].startswith("2000-01-01")
    assert changed["profile_remarks"] == row["profile_remarks"]
    assert changed["participations"][0]["id"] == row["participations"][0]["id"]
    assert changed["education"][0]["graduation_year"] == "2021"

