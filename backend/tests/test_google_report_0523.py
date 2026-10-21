"""The compact Google report is tested with synthetic in-memory records only."""

import csv
import io
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import event

import app.api.google_sheets as google_api
import app.main as main
from app.google_report import google_report_table
from app.models import FsdpParticipation, Program, Scholar, ScholarEducation

HEADERS = [
    "No.",
    "Name",
    "Age",
    "Tenure",
    "Department",
    "Rank/position",
    "Previous degree",
    "Program",
    "Delivering HEI",
    "Grant type",
    "Date started",
    "Date ended",
    "Extension",
    "Status",
    "Remarks",
]


def report():
    with main.SessionLocal() as db:
        return google_report_table(db)


def seed(*scholars):
    with main.SessionLocal() as db:
        db.add_all(scholars)
        db.commit()


def grant(name, **fields):
    return FsdpParticipation(program=Program(name=name), **fields)


def test_exact_compact_headers_and_no_grant_scholar_preserves_zero_and_profile_notes(client):
    seed(
        Scholar(
            name="SYNTHETIC SCHOLAR",
            age=0,
            tenure_years=0,
            department="IT OFFICE",
            rank="SUPPORT OFFICER",
            previous_degree="HISTORICAL DEGREE",
            profile_remarks="PROFILE NOTE\nSECOND LINE",
            data_source="PRIVATE IMPORT SOURCE",
        )
    )
    headings, rows = report()
    assert headings == HEADERS
    assert rows == [
        [
            1,
            "SYNTHETIC SCHOLAR",
            0,
            0,
            "Staff",
            "SUPPORT OFFICER",
            "HISTORICAL DEGREE",
            *([None] * 7),
            "PROFILE NOTE\nSECOND LINE",
        ]
    ]
    assert "PRIVATE IMPORT SOURCE" not in json.dumps(rows)


def test_each_grant_keeps_its_row_and_education_is_complete_without_legacy_duplicate(client):
    seed(
        Scholar(
            name="SYNTHETIC MULTI GRANT",
            department="coe",
            tenure_years=3.5,
            previous_degree="OUTDATED SINGLE FIELD",
            profile_remarks="PROFILE NOTE",
            education=[
                ScholarEducation(
                    level="Bachelor’s",
                    degree="BS ENGINEERING",
                    institution="SYNTHETIC COLLEGE",
                    graduation_year="2010",
                ),
                ScholarEducation(
                    level="Master’s",
                    degree="MS ENGINEERING",
                    institution="SYNTHETIC UNIVERSITY",
                    graduation_year="2015",
                ),
                ScholarEducation(level="Other", degree="", institution="", graduation_year=None),
            ],
            participations=[
                grant(
                    "SECOND APPLICATION",
                    application_key="separate-application",
                    start_term="Summer",
                    start_academic_year="2023",
                    end_term="2nd",
                    end_academic_year="2024-2025",
                    status="Incomplete",
                    delivering_hei="SYNTHETIC HEI TWO",
                    remarks="SECOND GRANT NOTE",
                ),
                grant(
                    "FIRST APPLICATION",
                    application_key="first-application",
                    start_term="1st",
                    start_academic_year="2021",
                    end_term="2nd",
                    end_academic_year="2022-2023",
                    status="Graduated",
                    delivering_hei=" SYNTHETIC HEI ONE ",
                    grant_type="Other",
                    grant_other="SYNTHETIC SPONSOR",
                    extension="ONE TERM",
                    remarks="FIRST GRANT NOTE",
                    contract_completed_on=date(2022, 1, 1),
                    completion_due_on=date(2022, 2, 1),
                    payback_payment_status="Fully paid",
                ),
            ],
        )
    )
    headings, rows = report()
    assert headings == HEADERS and len(rows) == 2
    first, continuation = rows
    assert first[:7] == [
        1,
        "SYNTHETIC MULTI GRANT",
        None,
        3.5,
        "COE",
        None,
        "Bachelor’s: BS ENGINEERING · SYNTHETIC COLLEGE · 2010\n"
        "Master’s: MS ENGINEERING · SYNTHETIC UNIVERSITY · 2015\nOther",
    ]
    assert first[7:] == [
        "FIRST APPLICATION",
        "SYNTHETIC HEI ONE",
        "Other: SYNTHETIC SPONSOR",
        "1st 2021",
        "2nd 2022-2023",
        "ONE TERM",
        "Completed",
        "Profile: PROFILE NOTE\nGrant: FIRST GRANT NOTE",
    ]
    assert continuation[:7] == [None] * 7
    assert continuation[7:] == [
        "SECOND APPLICATION",
        "SYNTHETIC HEI TWO",
        None,
        "Summer 2023",
        "2nd 2024-2025",
        None,
        "Incomplete",
        "SECOND GRANT NOTE",
    ]
    assert all(len(row) == 15 for row in rows)
    assert "OUTDATED SINGLE FIELD" not in json.dumps(rows)
    assert "Fully paid" not in json.dumps(rows)
    assert "2022-01-01" not in json.dumps(rows)
    assert "2022-02-01" not in json.dumps(rows)


@pytest.mark.parametrize(
    "recorded,term,year,expected",
    [
        (date(2021, 6, 1), "1st", "2020-2021", "2021-06-01"),
        (None, "1st", "2021", "1st 2021"),
        (None, "Summer", "2021", "Summer 2021"),
        (None, "2nd", "2021-2022", "2nd 2021-2022"),
        (None, None, "2021", "2021"),
        (None, "Summer", None, "Summer"),
        (None, " ", "  ", None),
        (None, None, None, None),
    ],
)
def test_dates_use_recorded_actual_dates_or_unexpanded_period_labels(
    client, recorded, term, year, expected
):
    seed(
        Scholar(
            name="SYNTHETIC DATE SCHOLAR",
            participations=[
                grant(
                    "SYNTHETIC SHORT PROGRAM",
                    start_date=recorded,
                    end_date=recorded,
                    start_term=term,
                    end_term=term,
                    start_academic_year=year,
                    end_academic_year=year,
                    contract_completed_on=date(2090, 1, 1),
                    completion_due_on=date(2091, 1, 1),
                )
            ],
        )
    )
    rows = report()[1]
    assert rows[0][10:12] == [expected, expected]


@pytest.mark.parametrize(
    "years,legacy,expected",
    [
        (0, "12 years", 0),
        (1.25, None, 1.25),
        (None, "2 years 6 months", 2.5),
        (None, "unknown", None),
    ],
)
def test_tenure_remains_years_and_unknown_values_are_not_guessed(client, years, legacy, expected):
    seed(Scholar(name="SYNTHETIC TENURE SCHOLAR", tenure_years=years, tenure=legacy))
    assert report()[1][0][3] == expected


def test_unicode_casefold_order_numbers_each_scholar_and_keeps_namesakes_separate(client):
    seed(
        Scholar(id=300, name="zebra"),
        Scholar(id=200, name="ßAME"),
        Scholar(id=101, name="Alice"),
        Scholar(id=100, name=" alice "),
        Scholar(id=201, name="SSAME"),
    )
    rows = report()[1]
    assert [(row[0], row[1]) for row in rows] == [
        (1, " alice "),
        (2, "Alice"),
        (3, "ßAME"),
        (4, "SSAME"),
        (5, "zebra"),
    ]


def test_report_loading_does_not_query_each_scholars_grants_or_education(client):
    counts = []
    for previous, total in [(0, 2), (2, 25)]:
        seed(
            *[
                Scholar(
                    name=f"SYNTHETIC SCHOLAR {number}",
                    education=[
                        ScholarEducation(level="Other", degree="SYNTHETIC DEGREE", institution="")
                    ],
                    participations=[grant(f"SYNTHETIC PROGRAM {number}")],
                )
                for number in range(previous, total)
            ]
        )
        with main.SessionLocal() as db:
            statements = []
            engine = db.get_bind()

            def count(
                _connection, _cursor, statement, _parameters, _context, _many, captured=statements
            ):
                if statement.lstrip().upper().startswith("SELECT"):
                    captured.append(statement)

            event.listen(engine, "before_cursor_execute", count)
            try:
                assert len(google_report_table(db)[1]) == total
            finally:
                event.remove(engine, "before_cursor_execute", count)
        counts.append(len(statements))
    assert counts[1] <= counts[0] + 1
    assert counts[1] <= 5


def test_sync_sends_real_compact_projection_as_literal_text_and_keeps_csv_contract(
    client, monkeypatch
):
    seed(
        Scholar(
            name="=SYNTHETIC NAME()",
            profile_remarks="+SYNTHETIC PROFILE",
            participations=[grant("@SYNTHETIC PROGRAM", remarks="=SYNTHETIC GRANT()")],
        )
    )
    received = []
    monkeypatch.setattr(
        google_api,
        "connection",
        SimpleNamespace(sync=lambda rows: received.append(rows) or {"rows": len(rows) - 1}),
    )
    response = client.post("/api/v1/google-sheets/sync", json={"replace_report": True})
    assert response.status_code == 200 and response.json() == {"rows": 1}
    assert received[0][0] == HEADERS
    assert received[0][1][1] == "=SYNTHETIC NAME()"
    assert received[0][1][7] == "@SYNTHETIC PROGRAM"
    assert received[0][1][-1] == "Profile: +SYNTHETIC PROFILE\nGrant: =SYNTHETIC GRANT()"
    assert all(len(row) == 15 for row in received[0])
    exported = client.get("/api/v1/maintenance/exports/fsdp.csv")
    csv_rows = list(csv.reader(io.StringIO(exported.text.lstrip("\ufeff"))))
    assert csv_rows[0][:2] == ["Scholar ID", "Name"]
    assert "Payback Payment Status" in csv_rows[0] and "Created At" in csv_rows[0]
    assert "Scholar ID" not in HEADERS and "Created At" not in HEADERS


def test_empty_report_still_sends_exact_headers(client):
    assert report() == (HEADERS, [])


def test_published_google_contract_matches_the_actual_projection(client):
    contract = json.loads(
        (
            Path(__file__).resolve().parents[2] / "docs/current/GOOGLE_REPORT_CONTRACT.json"
        ).read_text(encoding="utf-8-sig")
    )
    assert contract["columns"] == report()[0] == HEADERS
    assert contract["path"] == "/api/v1/google-sheets/sync"
    assert contract["worksheet"] == "CATHEDRA REPORT"
