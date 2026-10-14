"""User-facing CSV groups retain every grant without repeating profile cells."""

import csv
from datetime import date
from io import StringIO

import pytest
from sqlalchemy import select

import app.main as main
from app.models import FsdpParticipation, Program, Scholar, ScholarEducation

DIRECTORY_HEADERS = [
    "Scholar ID", "Name", "Age", "Education Background", "Missing Requirements",
    "Department", "Rank / position", "Personnel Type", "Current Scholar Status",
    "Tenure (years)", "Created At", "Updated At", "Profile Remarks",
    "Program", "Delivering HEI", "Start Term", "Start Academic Year", "End Term",
    "End Academic Year", "Contract Completion Date", "Grant Type", "Grant Other",
    "Recorded Grant Status", "Extension", "Remarks", "Graduation Date", "Case Status",
]
REPORT_HEADERS = [
    "Name", "Rank / position", "Department", "Age", "Tenure (years)",
    "Education background", "Current scholar status", "Profile Remarks",
    "Program applied", "Delivering HEI", "Type of grant", "Start Term",
    "Start Academic Year", "End Term", "End Academic Year", "Contract Completion Date",
    "Extension", "Remarks", "Recorded grant status", "Graduation Date", "Case Status",
]
PAYBACK_HEADERS = [
    "Scholar", "Scholar ID", "Department", "Program", "Grant ID", "Academic year",
    "Recorded status", "Contract completed", "Grace ends", "Follow-up",
]


def create_scholar(client, name, grants=(), **fields):
    response = client.post("/api/v1/fsdp", json={
        "name": name, "participations": list(grants), **fields,
    })
    assert response.status_code == 201, response.text
    return response.json()


def exported(client, endpoint, headers, **params):
    response = client.get(endpoint, params=params)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(StringIO(response.text)))
    header_index = rows.index(headers)
    details = rows[header_index + 1:]
    assert all(len(row) == len(headers) for row in details)
    return rows, details


def business_snapshot():
    with main.SessionLocal() as db:
        return {
            model.__tablename__: [tuple(row) for row in db.execute(
                select(*model.__table__.columns).order_by(model.id)
            )]
            for model in (Scholar, FsdpParticipation, Program, ScholarEducation)
        }


@pytest.mark.parametrize("endpoint,headers,profile_width,program_column", [
    ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS, 13, "Program"),
    ("/api/v1/fsdp/report.csv", REPORT_HEADERS, 8, "Program applied"),
])
def test_all_grants_contiguous_and_namesakes_start_separate_groups(
    client, endpoint, headers, profile_width, program_column,
):
    # Deliberately save years out of order; the latest grant is still the outcome.
    grants = [
        {"program_name": "Newest", "start_academic_year": "2025-2026", "start_term": "Summer", "status": "Payback", "case_status": "Closed", "contract_completed_on": "2025-07-04"},
        {"program_name": "Oldest", "start_academic_year": "2022-2023", "start_term": "2nd", "end_academic_year": "2023-2024", "end_term": "3rd", "status": "Completed", "case_status": "Closed", "contract_completed_on": "2023-05-20", "graduation_date": "2023-06-14"},
        {"program_name": "Middle", "start_academic_year": "2024-2025", "start_term": "1st", "status": "On Going", "case_status": "Open", "remarks": "Still studying"},
    ]
    first = create_scholar(client, "Same name", grants, department="CAS", age=0,
                           tenure_years=0, profile_remarks="Whole profile")
    second = create_scholar(client, "Same name", [{"program_name": "Different person"}], department="CCS")
    create_scholar(client, "Zebra no grant")
    _, rows = exported(client, endpoint, headers)
    assert len(rows) == 5
    assert [row[headers.index(program_column)] for row in rows] == [
        "OLDEST", "MIDDLE", "NEWEST", "DIFFERENT PERSON", "",
    ]
    assert rows[0][headers.index("Name")] == rows[3][headers.index("Name")] == "SAME NAME"
    assert rows[1][:profile_width] == rows[2][:profile_width] == [""] * profile_width
    assert rows[0][headers.index("Age")] == "0"
    assert rows[0][headers.index("Tenure (years)")] == "0.0"
    assert rows[0][headers.index("Profile Remarks")] == "WHOLE PROFILE"
    assert rows[4][profile_width:] == [""] * (len(headers) - profile_width)
    if "Scholar ID" in headers:
        assert [rows[index][0] for index in (0, 3)] == [str(first["id"]), str(second["id"])]
    recorded_status = "Recorded Grant Status" if "Recorded Grant Status" in headers else "Recorded grant status"
    current_status = "Current Scholar Status" if "Current Scholar Status" in headers else "Current scholar status"
    assert rows[0][headers.index(current_status)] == "Payback"
    assert [row[headers.index(recorded_status)] for row in rows[:3]] == ["Completed", "On Going", "Payback"]
    assert [row[headers.index("Case Status")] for row in rows[:3]] == ["Closed", "Open", "Closed"]
    assert rows[0][headers.index("Graduation Date")] == "2023-06-14"
    assert rows[0][headers.index("Contract Completion Date")] == "2023-05-20"
    assert rows[2][headers.index("Contract Completion Date")] == "2025-07-04"
    assert rows[0][headers.index("Start Term")] == "2nd"
    assert rows[0][headers.index("End Term")] == "3rd"
    assert rows[0][headers.index("End Academic Year")] == "2023-2024"


@pytest.mark.parametrize("endpoint,headers,profile_width,program_column", [
    ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS, 13, "Program"),
    ("/api/v1/fsdp/report.csv", REPORT_HEADERS, 8, "Program applied"),
])
def test_historical_missing_years_terms_and_equal_years_have_stable_order(
    client, endpoint, headers, profile_width, program_column,
):
    create_scholar(client, "Stable history", [
        {"program_name": "Summer", "start_academic_year": "2023-2024", "start_term": "Summer"},
        {"program_name": "Custom year", "start_academic_year": "Historical"},
        {"program_name": "No year"},
        {"program_name": "Second A", "start_academic_year": "2023-2024", "start_term": "2nd"},
        {"program_name": "First", "start_academic_year": "2023-2024", "start_term": "1st"},
        {"program_name": "Second B", "start_academic_year": "2023-2024", "start_term": "2nd"},
    ])
    _, rows = exported(client, endpoint, headers)
    assert [row[headers.index(program_column)] for row in rows] == [
        "CUSTOM YEAR", "NO YEAR", "FIRST", "SECOND A", "SECOND B", "SUMMER",
    ]
    assert all(row[:profile_width] == [""] * profile_width for row in rows[1:])
    assert exported(client, endpoint, headers)[1] == rows


def test_report_filters_grant_subset_without_losing_first_profile_or_totals(client):
    selected = create_scholar(client, "Chosen scholar", [
        {"program_name": "Earlier", "start_academic_year": "2023-2024", "start_term": "1st", "grant_type": "Full Scholarship"},
        {"program_name": "Later", "start_academic_year": "2023-2024", "start_term": "Summer", "grant_type": "Full Scholarship"},
        {"program_name": "Excluded year", "start_academic_year": "2025-2026", "grant_type": "Partial Scholarship", "status": "Payback"},
    ], department="CAS", missing_requirements=True)
    create_scholar(client, "Other college", [{"program_name": "Other", "start_academic_year": "2023-2024", "grant_type": "Full Scholarship"}], department="CCS")
    params = {"department": "CAS", "start_academic_year": "2023-2024", "grant_type": "Full Scholarship", "status": "Payback", "page": 1, "page_size": 1}
    before = client.get("/api/v1/fsdp/report", params=params).json()
    rows, details = exported(client, "/api/v1/fsdp/report.csv", REPORT_HEADERS, **params)
    assert [row[8] for row in details] == ["EARLIER", "LATER"]
    assert details[0][0] == "CHOSEN SCHOLAR" and details[1][:8] == [""] * 8
    assert rows[1] == ["Scholars", "1", "Missing requirements", "1"]
    assert before["total"] == 1 and before["items"][0]["id"] == selected["id"]
    assert len(before["items"][0]["participations"]) == 2
    assert client.get("/api/v1/fsdp/report", params=params).json() == before
    assert any(row and row[0] == "Requirement follow-up" for row in rows)


def test_payback_groups_by_identity_and_keeps_all_filtered_details(client):
    first = create_scholar(client, "Payback namesake", [
        {"program_name": "Recorded newest", "start_academic_year": "2023-2024", "start_term": "Summer", "status": "Payback", "contract_completed_on": "2000-01-03"},
        {"program_name": "Review older", "start_academic_year": "2021-2022", "start_term": "1st", "contract_completed_on": "2000-01-01"},
        {"program_name": "Date not set", "start_academic_year": "2025-2026"},
    ], department="CAS")
    second = create_scholar(client, "Payback namesake", [
        {"program_name": "Another person", "start_academic_year": "2022-2023", "contract_completed_on": "2000-01-02"},
    ], department="CAS")
    params = {"department": "CAS", "attention": "Payback action", "page": 1, "page_size": 1}
    before = client.get("/api/v1/fsdp/payback", params={"department": "CAS", "attention": "Payback action"}).json()
    _, details = exported(client, "/api/v1/fsdp/payback.csv", PAYBACK_HEADERS, **params)
    assert len(details) == before["total"] == 3
    assert [row[3] for row in details] == ["REVIEW OLDER", "RECORDED NEWEST", "ANOTHER PERSON"]
    assert details[0][:3] == ["PAYBACK NAMESAKE", str(first["id"]), "CAS"]
    assert details[1][:3] == [""] * 3
    assert details[2][:3] == ["PAYBACK NAMESAKE", str(second["id"]), "CAS"]
    expected = {str(item["participation_id"]): item for item in before["items"]}
    for row in details:
        item = expected[row[4]]
        assert row[5:] == [item["academic_year"], item["recorded_status"], item["contract_completed_on"], item["grace_ends_on"], item["attention"]]
    assert client.get("/api/v1/fsdp/payback", params={"department": "CAS", "attention": "Payback action"}).json() == before
    # With no attention filter, a third grant remains in its scholar's group.
    _, all_details = exported(client, "/api/v1/fsdp/payback.csv", PAYBACK_HEADERS)
    assert len(all_details) == 4
    assert all_details[2][3] == "DATE NOT SET" and all_details[2][:3] == [""] * 3


def test_exports_remove_provenance_headings_and_legacy_date_fallback_without_db_changes(client):
    saved = create_scholar(client, "Historical scholar", [{
        "program_name": "Master", "start_date": "1998-01-02", "end_date": "1999-03-04",
        "start_term": "Summer", "start_academic_year": "2020-2021",
        "status": "Completed", "graduation_date": "2022-06-14",
    }])
    with main.SessionLocal() as db:
        db.get(Scholar, saved["id"]).data_source = "Legacy imported source"
        db.commit()
    before = business_snapshot()
    for endpoint, headers in [
        ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS),
        ("/api/v1/fsdp/report.csv", REPORT_HEADERS),
    ]:
        rows, details = exported(client, endpoint, headers)
        assert not any("source" in value.casefold() or "legacy" in value.casefold() or "import" in value.casefold() for value in headers)
        assert not any("1998-01-02" in value or "1999-03-04" in value for row in rows for value in row)
        assert details[0][headers.index("Start Term")] == "Summer"
        assert details[0][headers.index("Start Academic Year")] == "2020-2021"
    education_headers = ["Scholar ID", "Name", "Education ID", "Level", "Degree", "Institution", "Graduation Year"]
    _, education = exported(client, "/api/v1/maintenance/exports/education.csv", education_headers)
    assert len(education) == 1 and education[0][-1] == "2022"
    assert business_snapshot() == before
    current = client.get(f"/api/v1/fsdp/{saved['id']}").json()
    assert current["data_source"] == "Legacy imported source"
    assert current["participations"][0]["start_date"] == "1998-01-02"
    assert current["education"][0]["source_program_id"] == saved["participations"][0]["program_id"]


@pytest.mark.parametrize("endpoint,headers,profile_width,program_column", [
    ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS, 13, "Program"),
    ("/api/v1/fsdp/report.csv", REPORT_HEADERS, 8, "Program applied"),
])
def test_continuation_formula_cells_unicode_quotes_and_newlines_are_safe(
    client, endpoint, headers, profile_width, program_column,
):
    create_scholar(client, "=Profile, Résumé", [
        {"program_name": "First safe grant", "start_academic_year": "2021-2022"},
        {"program_name": "@Résumé, \"second\"", "start_academic_year": "2022-2023", "delivering_hei": "+Unicode École", "remarks": "=1+1\nRésumé, \"quoted\"", "extension": "-Extension"},
    ], profile_remarks="@Whole profile")
    _, details = exported(client, endpoint, headers)
    assert len(details) == 2
    assert details[0][headers.index("Name")] == "'=PROFILE, RÉSUMÉ"
    assert details[0][headers.index("Profile Remarks")] == "'@WHOLE PROFILE"
    assert details[1][:profile_width] == [""] * profile_width
    assert details[1][headers.index(program_column)] == "'@RÉSUMÉ, \"SECOND\""
    assert details[1][headers.index("Delivering HEI")] == "'+UNICODE ÉCOLE"
    assert details[1][headers.index("Remarks")] == "'=1+1\nRÉSUMÉ, \"QUOTED\""
    assert details[1][headers.index("Extension")] == "'-EXTENSION"


@pytest.mark.parametrize("endpoint,headers,profile_width", [
    ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS, 13),
    ("/api/v1/fsdp/report.csv", REPORT_HEADERS, 8),
    ("/api/v1/fsdp/payback.csv", PAYBACK_HEADERS, 3),
])
def test_csv_exports_all_groups_beyond_page_size(client, endpoint, headers, profile_width):
    with main.SessionLocal() as db:
        program = Program(name="SYNTHETIC SHARED PROGRAM")
        db.add(program)
        db.flush()
        for index in range(53):
            scholar = Scholar(name=f"SYNTHETIC {index:02d}", department="CAS")
            db.add(scholar)
            db.flush()
            for offset in range(3 if index == 0 else 1):
                db.add(FsdpParticipation(
                    scholar_id=scholar.id, program_id=program.id,
                    start_academic_year=f"{2020 + offset}-{2021 + offset}",
                    contract_completed_on=date(2000, 1, 1),
                ))
        db.commit()
    paged = client.get("/api/v1/fsdp/report", params={"page": 1, "page_size": 1}).json()
    assert paged["total"] == 53 and len(paged["items"]) == 1
    _, details = exported(client, endpoint, headers, page=1, page_size=1)
    assert len(details) == 55
    assert sum(bool(row[0]) for row in details) == 53
    assert details[1][:profile_width] == details[2][:profile_width] == [""] * profile_width
    assert details[-1][headers.index("Name" if "Name" in headers else "Scholar")] == "SYNTHETIC 52"


@pytest.mark.parametrize("endpoint,headers", [
    ("/api/v1/maintenance/exports/fsdp.csv", DIRECTORY_HEADERS),
    ("/api/v1/maintenance/exports/education.csv", ["Scholar ID", "Name", "Education ID", "Level", "Degree", "Institution", "Graduation Year"]),
    ("/api/v1/fsdp/report.csv", REPORT_HEADERS),
    ("/api/v1/fsdp/payback.csv", PAYBACK_HEADERS),
])
def test_empty_csv_has_valid_headers_and_still_requires_sign_in(client, endpoint, headers):
    assert exported(client, endpoint, headers)[1] == []
    client.headers.clear()
    assert client.get(endpoint).status_code == 401
