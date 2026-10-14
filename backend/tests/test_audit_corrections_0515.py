import csv
import hashlib
import json
import sqlite3
from datetime import date
from io import StringIO
from pathlib import Path

import pytest

from app.education_review import review_education
from app.graduated_education import graduation_evidence

TODAY = date(2026, 10, 9)


@pytest.mark.parametrize(("remarks", "program", "expected"), [
    ("Previously graduated with a Bachelor degree in 2018; now taking doctorate", "Doctor of Education", (False, None)),
    ("Graduated with Bachelor of Science in 2018", "Doctor of Education", (False, None)),
    ("Her daughter graduated in 2022", "Master of Arts", (False, None)),
    ("Graduated with Master of Arts in History in 2022", "Master of Arts in English", (False, None)),
    ("Graduated with Ph.D. in 2022", "Ph.D. Computing", (True, "2022")),
    ("Graduated with Ph.D. in Computing in 2022", "Doctor of Philosophy in Computing", (True, "2022")),
    ("Graduated with Ed.D. in 2022", "Doctor of Education", (True, "2022")),
    ("Graduated with Ph.D. in 2022", "Doctor of Education", (False, None)),
    ("The scholar has graduated from this program in 2022", "Master of Arts", (True, "2022")),
    ("Graduated with Ph.D. in 2022. Contract completed in 2020.", "Ph.D. Computing", (True, "2022")),
    ("Graduated with Ph.D. in 2022. Not graduated from this program.", "Ph.D. Computing", (False, None)),
    ("Graduated on December 31, 2026", "Doctor of Education", (False, None)),
    ("Graduated on 2026-12-31", "Doctor of Education", (False, None)),
    ("Graduated on October 9, 2026", "Doctor of Education", (True, "2026")),
    ("Graduated on 2026-10-08", "Doctor of Education", (True, "2026")),
    ("Graduated on 02/31/2022", "Doctor of Education", (False, None)),
    ("Graduated on February 29, 2023", "Doctor of Education", (False, None)),
    ("Graduated on February 29, 2024", "Doctor of Education", (True, "2024")),
    ("Graduated on 15/06/2022", "Doctor of Education", (True, "2022")),
    ("Graduated on 06/15/2022", "Doctor of Education", (True, "2022")),
    ("Graduated on 06/07/2022", "Doctor of Education", (False, None)),
    ("Graduated on Jun. 15, 2022", "Doctor of Education", (True, "2022")),
    ("Graduated in 2022. Graduated on December 31, 2026", "Doctor of Education", (False, None)),
    ("Graduated in December 2026", "Doctor of Education", (False, None)),
    ("Graduated in June 2022", "Doctor of Education", (True, "2022")),
    ("Graduated in 2026", "Doctor of Education", (True, "2026")),
    ("Graduated in 2027", "Doctor of Education", (False, None)),
    ("Graduated in 2021-2022", "Doctor of Education", (False, None)),
])
def test_current_program_and_calendar_evidence(remarks, program, expected):
    assert graduation_evidence(remarks, program, today=TODAY) == expected


def create(client, name, grants, **fields):
    response = client.post("/api/v1/fsdp", json={"name": name, "participations": grants, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_wrong_degree_save_keeps_remarks_and_existing_manual_education(client):
    remarks = "Previously graduated with a Bachelor degree in 2018; now taking doctorate"
    row = create(client, "Synthetic scholar", [{"program_name": "Doctor of Education", "remarks": remarks}],
                 education=[{"degree": "Bachelor of Science", "institution": "Original HEI", "graduation_year": "2018"}])
    assert [entry["degree"] for entry in row["education"]] == ["BACHELOR OF SCIENCE"]
    assert row["participations"][0]["remarks"] == remarks.upper()
    assert row["participations"][0]["status"] == "On Going"


def test_invalid_remark_is_saveable_and_recorded_graduation_remains_authoritative(client):
    row = create(client, "Recorded scholar", [{"program_name": "Doctor of Education", "remarks": "Graduated on 02/31/2022", "status": "Graduated"}])
    assert len(row["education"]) == 1
    assert row["education"][0]["graduation_year"] is None
    assert row["participations"][0]["status"] == "Completed"


@pytest.mark.parametrize("attention", ["Payback action", "Payback pending contract", "Graduated", "Completion date missing", ""])
def test_payback_paged_unpaged_csv_parity_and_scope_counts(client, attention):
    for name, status in [("Review", "On Going"), ("Recorded", "Payback"), ("Pending", "Payback pending contract"), ("Graduated", "Graduated")]:
        create(client, name, [{"program_name": "Shared", "status": status, "contract_completed_on": "2000-01-01"}], department="CAS")
    create(client, "Missing", [{"program_name": "Shared"}], department="CAS")
    params = {"department": "CAS", "attention": attention}
    unpaged = client.get("/api/v1/fsdp/payback", params=params).json()
    paged = client.get("/api/v1/fsdp/payback", params={**params, "page": 1, "page_size": 2}).json()
    second = client.get("/api/v1/fsdp/payback", params={**params, "page": 2, "page_size": 2}).json()
    third = client.get("/api/v1/fsdp/payback", params={**params, "page": 3, "page_size": 2}).json()
    rows = list(csv.reader(StringIO(client.get("/api/v1/fsdp/payback.csv", params=params).text)))
    # CSV groups grants per scholar; JSON keeps its existing follow-up priority order.
    assert sorted(item["participation_id"] for item in unpaged["items"]) == sorted(int(row[4]) for row in rows[2:])
    assert unpaged["items"] == paged["items"] + second["items"] + third["items"]
    assert paged["total"] == unpaged["total"] == len(rows) - 2
    assert paged["scholar_counts"] == unpaged["scholar_counts"]
    assert unpaged["scholar_counts"]["Completed"] == 1


def test_pending_contract_wins_over_same_program_graduation_and_summer_survives(client):
    row = create(client, "Summer scholar", [
        {"program_name": "Annual", "status": "Payback pending contract", "contract_completed_on": "2000-01-01", "start_term": "Summer"},
        {"program_name": "Annual", "status": "Graduated", "start_term": "Summer"},
    ])
    assert row["participations"][0]["payback_attention"] == "Payback pending contract"
    assert all(grant["start_term"] == "Summer" for grant in row["participations"])


def test_education_review_is_read_only_and_never_marks_manual_entries(tmp_path):
    snapshot = tmp_path / "snapshot.db"
    with sqlite3.connect(snapshot) as connection:
        connection.executescript("""
            CREATE TABLE cathedra_product(id INTEGER,product TEXT);
            INSERT INTO cathedra_product VALUES(1,'fsdp');
            CREATE TABLE programs(id INTEGER,name TEXT);
            INSERT INTO programs VALUES(1,'Doctor of Education');
            CREATE TABLE fsdp_participations(scholar_id INTEGER,program_id INTEGER,status TEXT,remarks TEXT);
            INSERT INTO fsdp_participations VALUES(1,1,'On Going','Previously graduated with a Bachelor degree in 2018');
            INSERT INTO fsdp_participations VALUES(2,1,'Graduated','');
            CREATE TABLE scholar_education(id INTEGER,scholar_id INTEGER,source_program_id INTEGER);
            INSERT INTO scholar_education VALUES(1,1,1),(2,2,1),(3,3,NULL);
        """)
    before = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    result = review_education(snapshot, today=TODAY)
    assert result["linked_entries_checked"] == 2
    assert result["review_candidates"] == 1
    assert result["candidates"][0]["education_id"] == 1
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("export", ["directory", "education", "payback", "report", "office_logs"])
def test_current_documented_export_headers_match_actual_writers(client, export):
    contract = json.loads((Path(__file__).resolve().parents[2] / "docs/current/EXPORT_CONTRACTS.json").read_text())[export]
    create(client, "=Synthetic\nScholar", [{"program_name": "Annual", "status": "Transferred", "remarks": "=Private\nnote"}],
           profile_remarks="=Whole profile", education=[{"degree": "Manual degree", "institution": "Private HEI"}])
    if export == "office_logs":
        assert client.post("/api/v1/office-logs", json={"note": "=Office\nnote"}).status_code == 201
    response = client.get(contract["path"])
    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.text)))
    for header in contract["sections"].values():
        assert rows.count(header) == 1
    if export == "directory":
        header, data = rows[0], rows[1]
        assert len(data) == len(header)
        assert data[header.index("Name")] == "'=SYNTHETIC\nSCHOLAR"
        assert data[header.index("Profile Remarks")] == "'=WHOLE PROFILE"
        assert data[header.index("Remarks")] == "'=PRIVATE\nNOTE"
    elif export == "office_logs":
        assert rows[1][rows[0].index("Note")] == "'=OFFICE\nNOTE"
