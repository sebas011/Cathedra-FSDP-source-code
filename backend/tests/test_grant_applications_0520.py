from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, aliased

from app.db import Base
from app.grant_applications import (
    application_group_key,
    completed_application_keys,
    has_completed_application_expression,
)
from app.models import FsdpParticipation, Program, Scholar
from app.payback import payback_data

TODAY = date(2026, 10, 15)


@pytest.fixture
def application_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            yield db
    finally:
        engine.dispose()


def add_grant(db, scholar, program, application_key, *, status="On Going", year="2021-2022"):
    grant = FsdpParticipation(
        scholar=scholar,
        program=program,
        application_key=application_key,
        status=status,
        start_academic_year=year,
        contract_completed_on=date(2000, 1, 1),
    )
    db.add(grant)
    db.flush()
    return grant


def attentions(db, **filters):
    return {
        item["participation_id"]: item["attention"]
        for item in payback_data(db, today=TODAY, **filters)["items"]
    }


def test_previous_completed_application_does_not_clear_repeat_or_legacy(application_db):
    db = application_db
    scholar, program = Scholar(name="Repeat scholar"), Program(name="Master of Science")
    completed = add_grant(db, scholar, program, "application-one", status="Completed")
    repeat = add_grant(db, scholar, program, "application-two", year="2023-2024")
    legacy = add_grant(db, scholar, program, None)

    assert attentions(db) == {
        completed.id: "Completed",
        repeat.id: "Payback review",
        legacy.id: "Payback review",
    }
    completed_keys = completed_application_keys(scholar.participations)
    assert application_group_key(completed) in completed_keys
    assert application_group_key(repeat) not in completed_keys
    assert application_group_key(legacy) not in completed_keys
    # The same predicate must work inside another query using an ORM alias.
    candidate = aliased(FsdpParticipation)
    assert dict(
        db.execute(select(candidate.id, has_completed_application_expression(candidate))).all()
    ) == {
        completed.id: True,
        repeat.id: False,
        legacy.id: False,
    }


def test_completion_clears_all_annual_records_in_one_application_even_when_year_filtered(
    application_db,
):
    db = application_db
    scholar, program = Scholar(name="Annual scholar"), Program(name="Master of Arts")
    first_year = add_grant(db, scholar, program, "same-application", year="2021-2022")
    final_year = add_grant(
        db, scholar, program, "same-application", status="Completed", year="2022-2023"
    )
    repeat = add_grant(db, scholar, program, "new-application", year="2023-2024")

    assert attentions(db) == {
        first_year.id: "Completed",
        final_year.id: "Completed",
        repeat.id: "Payback review",
    }
    assert attentions(db, start_academic_year="2021-2022") == {first_year.id: "Completed"}
    totals = payback_data(db, today=TODAY, include_items=False)
    assert totals["items"] == []
    assert totals["grant_counts"]["Completed"] == 2
    assert totals["grant_counts"]["Payback review"] == 1
    assert totals["scholar_counts"]["Completed"] == totals["scholar_counts"]["Payback review"] == 1


def test_legacy_null_records_keep_same_program_completion_without_clearing_new_application(
    application_db,
):
    db = application_db
    scholar, program = Scholar(name="Existing office scholar"), Program(name="Legacy program")
    first = add_grant(db, scholar, program, None)
    completed = add_grant(db, scholar, program, None, status="Graduated")
    repeat = add_grant(db, scholar, program, "explicit-repeat")
    assert attentions(db) == {
        first.id: "Completed",
        completed.id: "Completed",
        repeat.id: "Payback review",
    }


def test_same_application_token_cannot_cross_scholar_or_program(application_db):
    db = application_db
    first, second = Scholar(name="First scholar"), Scholar(name="Second scholar")
    master, certificate = Program(name="Master program"), Program(name="Certification program")
    completed = add_grant(db, first, master, "shared-token", status="Completed")
    different_program = add_grant(db, first, certificate, "shared-token")
    different_scholar = add_grant(db, second, master, "shared-token")
    assert attentions(db) == {
        completed.id: "Completed",
        different_program.id: "Payback review",
        different_scholar.id: "Payback review",
    }
    assert completed_application_keys([completed]) == {application_group_key(completed)}
    assert application_group_key(different_program) != application_group_key(completed)
    assert application_group_key(different_scholar) != application_group_key(completed)


@pytest.mark.parametrize(
    "status,attention",
    [
        ("Payback", "Recorded Payback"),
        ("Payback pending contract", "Payback pending contract"),
        ("Did Not Avail", "Did Not Avail"),
    ],
)
def test_recorded_office_outcome_still_wins_over_application_completion(
    application_db, status, attention
):
    db = application_db
    scholar, program = Scholar(name="Recorded decision"), Program(name="Enhancement program")
    recorded = add_grant(db, scholar, program, "application", status=status)
    add_grant(db, scholar, program, "application", status="Completed")
    assert attentions(db)[recorded.id] == attention


def test_empty_and_null_legacy_keys_have_identical_sql_and_python_scope(application_db):
    db = application_db
    scholar, program = Scholar(name="Historical blank key"), Program(name="Legacy spelling")
    empty = add_grant(db, scholar, program, "")
    completed = add_grant(db, scholar, program, None, status="Completed")
    assert application_group_key(empty) == application_group_key(completed)
    assert attentions(db) == {empty.id: "Completed", completed.id: "Completed"}


def test_application_assessment_agrees_in_profile_reports_dashboard_and_missing_date_filter(client):
    response = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Repeated application office profile",
            "participations": [
                {
                    "program_name": "Master program",
                    "application_key": "old-completed",
                    "status": "Completed",
                },
                {
                    "program_name": "Master program",
                    "application_key": "repeat",
                    "contract_completed_on": "2000-01-01",
                },
                {"program_name": "Master program", "application_key": "repeat"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    scholar = response.json()
    expected = ["Completed", "Payback review", "Completion date missing"]
    assert [grant["payback_attention"] for grant in scholar["participations"]] == expected
    by_id = {
        grant["id"]: attention
        for grant, attention in zip(scholar["participations"], expected, strict=True)
    }

    payback = client.get("/api/v1/fsdp/payback").json()
    assert {item["participation_id"]: item["attention"] for item in payback["items"]} == by_id
    report = client.get("/api/v1/fsdp/report").json()
    assert [
        grant["payback_attention"] for grant in report["items"][0]["participations"]
    ] == expected
    assert len([item for item in report["action_items"] if item["kind"] == "Contract payback"]) == 1
    missing = client.get("/api/v1/fsdp/page?missing=contract_date").json()
    assert missing["total"] == 1 and missing["items"][0]["id"] == scholar["id"]
    analytics = client.get("/api/v1/fsdp/analytics").json()
    assert analytics["payback_summary"]["Payback review"] == 1
