from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

import app.main as main
from app import clock
from app.contract_rules import assess_contract, classify_contract
from app.fsdp_reporting import fsdp_report_data, options, read_scholar
from app.graduated_education import graduation_evidence
from app.models import Scholar


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-06-01T15:59:59+00:00", "2026-06-01"),
        ("2026-06-01T16:00:00+00:00", "2026-06-02"),
        ("2026-06-02T00:00:00+08:00", "2026-06-02"),
        ("2026-06-01T16:00:00", "2026-06-02"),
        ("2026-12-31T16:00:00+00:00", "2027-01-01"),
    ],
)
def test_office_business_date_uses_manila_even_for_naive_utc_instants(instant, expected):
    assert clock.business_today(datetime.fromisoformat(instant)) == date.fromisoformat(expected)


@pytest.mark.parametrize(
    "status,completed,graduated,today,attention,rule,fragment",
    [
        (
            "Payback",
            None,
            True,
            "2026-06-02",
            "Recorded Payback",
            "CONTRACT_RECORDED_PAYBACK",
            "recorded by the office",
        ),
        (
            "Payback pending contract",
            "2000-01-01",
            True,
            "2026-06-02",
            "Payback pending contract",
            "CONTRACT_RECORDED_PENDING",
            "pending repayment contract",
        ),
        (
            "Did Not Avail",
            "2000-01-01",
            True,
            "2026-06-02",
            "Did Not Avail",
            "CONTRACT_NOT_AVAILED",
            "does not apply",
        ),
        (
            "Completed",
            None,
            True,
            "2026-06-02",
            "Completed",
            "CONTRACT_COMPLETED_RECORDED",
            "This grant has",
        ),
        (
            "On Going",
            "2000-01-01",
            True,
            "2026-06-02",
            "Completed",
            "CONTRACT_COMPLETED_APPLICATION",
            "same recorded application group",
        ),
        (
            "Incomplete",
            None,
            False,
            "2026-06-02",
            "Completion date missing",
            "CONTRACT_DEADLINE_MISSING",
            "No usable completion deadline",
        ),
        (
            "Incomplete",
            "9999-01-01",
            False,
            "2026-06-02",
            "Contract not completed",
            "CONTRACT_DEADLINE_UNUSABLE",
            "outside the supported",
        ),
        (
            "Withdrawn",
            "2027-06-01",
            False,
            "2026-06-02",
            "Contract not completed",
            "CONTRACT_BEFORE_DEADLINE",
            "2027-06-01",
        ),
        (
            "Transferred",
            "2023-06-01",
            False,
            "2026-06-01",
            "In grace period",
            "CONTRACT_IN_GRACE",
            "includes 2026-06-01",
        ),
        (
            "Incomplete",
            "2023-06-01",
            False,
            "2026-06-02",
            "Payback review",
            "CONTRACT_REVIEW_DUE",
            "ended 2026-06-01",
        ),
    ],
)
def test_assessment_explains_the_same_existing_classification(
    status, completed, graduated, today, attention, rule, fragment
):
    completed = date.fromisoformat(completed) if completed else None
    today = date.fromisoformat(today)
    decision = assess_contract(status, completed, graduated, today)
    assert decision.attention == attention
    assert decision.rule_code == rule
    assert fragment in decision.reason
    assert decision.as_of == today
    assert classify_contract(status, completed, graduated, today) == (
        decision.attention,
        decision.grace_ends_on,
    )


def create(client, name="Assessment sample"):
    response = client.post(
        "/api/v1/fsdp",
        json={
            "name": name,
            "participations": [
                {
                    "program_name": "Program",
                    "application_key": "first",
                    "status": "On Going",
                    "completion_due_on": "2000-01-01",
                },
                {"program_name": "Program", "application_key": "first", "status": "Completed"},
                {
                    "program_name": "Program",
                    "application_key": "first",
                    "status": "Payback",
                    "case_status": "Closed",
                    "payback_payment_status": "Fully paid",
                },
                {
                    "program_name": "Program",
                    "application_key": "second",
                    "status": "Withdrawn",
                    "completion_due_on": "2000-01-01",
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_profile_payback_and_report_explanations_agree_without_overwriting_recorded_facts(
    client, monkeypatch
):
    created = create(client)
    monkeypatch.setattr(clock, "utc_now", lambda: datetime(2026, 6, 1, 16, tzinfo=timezone.utc))
    profile = client.get(f"/api/v1/fsdp/{created['id']}").json()
    follow_up = client.get("/api/v1/fsdp/payback").json()
    report = client.get("/api/v1/fsdp/report").json()
    profile_rows = profile["participations"]
    assert [item["assessment_rule"] for item in profile_rows] == [
        "CONTRACT_COMPLETED_APPLICATION",
        "CONTRACT_COMPLETED_RECORDED",
        "CONTRACT_RECORDED_PAYBACK",
        "CONTRACT_REVIEW_DUE",
    ]
    by_id = {item["participation_id"]: item for item in follow_up["items"]}
    report_by_id = {item["id"]: item for item in report["items"][0]["participations"]}
    for item in profile_rows:
        for key in ("assessment_rule", "assessment_reason", "assessment_as_of"):
            assert item[key] == by_id[item["id"]][key] == report_by_id[item["id"]][key]
        assert item["assessment_as_of"] == "2026-06-02"
    recorded = profile_rows[2]
    assert recorded["status"] == "Payback"
    assert recorded["payback_attention"] == "Recorded Payback"
    assert recorded["payback_payment_status"] == "Fully paid"
    assert recorded["case_status"] == "Closed"
    assert report["as_of"] == follow_up["as_of"] == "2026-06-02"


def test_report_and_profile_take_one_business_date_per_snapshot(client, monkeypatch):
    create(client, "First sample")
    create(client, "Second sample")
    calls = []

    def crossing_midnight():
        calls.append(1)
        return datetime(2026, 6, 1, 15 if len(calls) == 1 else 16, 59, tzinfo=timezone.utc)

    monkeypatch.setattr(clock, "utc_now", crossing_midnight)
    with main.SessionLocal() as db:
        report = fsdp_report_data(db)
        assert len(calls) == 1
        assert report["as_of"] == "2026-06-01"
        assert {
            item.assessment_as_of for row in report["items"] for item in row.participations
        } == {date(2026, 6, 1)}
        calls.clear()
        row = db.scalars(select(Scholar).options(*options())).first()
        rendered = read_scholar(row)
        assert len(calls) == 1
        assert {item.assessment_as_of for item in rendered.participations} == {date(2026, 6, 1)}


def test_graduation_evidence_uses_the_same_office_business_date(monkeypatch):
    monkeypatch.setattr(clock, "utc_now", lambda: datetime(2026, 6, 1, 16, tzinfo=timezone.utc))
    assert graduation_evidence("Graduation date: 2026-06-02") == (True, "2026")
    assert graduation_evidence("Graduation date: 2026-06-03") == (False, None)
