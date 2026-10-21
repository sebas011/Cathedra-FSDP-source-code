import csv
from datetime import date
from io import StringIO

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine

from app.contract_rules import classify_contract, completion_deadline
from app.db import Base
from app.migrations import run_migrations
from app.schemas import ParticipationInput


@pytest.mark.parametrize(
    "start,years,explicit,legacy,expected,basis",
    [
        ("2021-06-01", 3, None, None, "2024-06-01", "Program start and allowed duration"),
        ("2020-02-29", 1, None, None, "2021-02-28", "Program start and allowed duration"),
        ("2020-02-29", 4, None, None, "2024-02-29", "Program start and allowed duration"),
        ("2021-06-01", 3, "2022-03-01", "2000-01-01", "2022-03-01", "Explicit deadline"),
        (None, 3, None, "2000-01-01", "2000-01-01", "Previously recorded completion date"),
        ("2021-06-01", None, None, None, None, None),
        ("9999-06-01", 1, None, None, None, None),
    ],
)
def test_deadline_uses_recorded_priority_and_calendar_anniversaries(
    start, years, explicit, legacy, expected, basis
):
    def parse(value):
        return date.fromisoformat(value) if value else None

    assert completion_deadline(parse(start), years, parse(explicit), parse(legacy)) == (
        parse(expected),
        basis,
    )


@pytest.mark.parametrize("status", ["On Going", "Incomplete", "Transferred", "Withdrawn"])
def test_grace_begins_at_allowed_deadline_and_includes_third_anniversary(status):
    deadline, _ = completion_deadline(date(2021, 6, 1), 3)
    assert (
        classify_contract(status, deadline, False, date(2024, 5, 31))[0] == "Contract not completed"
    )
    assert classify_contract(status, deadline, False, date(2024, 6, 1))[0] == "In grace period"
    assert classify_contract(status, deadline, False, date(2027, 6, 1))[0] == "In grace period"
    assert classify_contract(status, deadline, False, date(2027, 6, 2))[0] == "Payback review"
    assert classify_contract(status, deadline, True, date(2027, 6, 2))[0] == "Completed"


@pytest.mark.parametrize("duration", [0, -1, 101, 1.5])
def test_optional_duration_requires_whole_positive_years(duration):
    with pytest.raises(ValidationError):
        ParticipationInput(program_name="Course", allowed_duration_years=duration)


def create(client, grants):
    response = client.post(
        "/api/v1/fsdp", json={"name": "Deadline and payment profile", "participations": grants}
    )
    assert response.status_code == 201, response.text
    return response.json()


def update(client, scholar, grant):
    return client.put(
        f"/api/v1/fsdp/{scholar['id']}",
        headers={"If-Match": str(scholar["revision"])},
        json={"name": scholar["name"], "requirements": [], "participations": [grant]},
    )


def test_new_facts_round_trip_old_payload_preserves_them_and_explicit_null_clears(client):
    scholar = create(
        client,
        [
            {
                "program_name": "Program",
                "start_date": "1990-06-01",
                "allowed_duration_years": 3,
                "completion_due_on": "1994-06-01",
                "contract_completed_on": "1980-01-01",
                "status": "Payback",
                "payback_payment_status": "Partially paid",
            }
        ],
    )
    grant = scholar["participations"][0]
    assert grant["completion_deadline_on"] == "1994-06-01"
    assert grant["completion_deadline_source"] == "Explicit deadline"
    assert grant["payback_payment_status"] == "Partially paid"
    older_payload = {"id": grant["id"], "program_name": grant["name"], "status": "Payback"}
    response = update(client, scholar, older_payload)
    assert response.status_code == 200, response.text
    scholar = response.json()
    retained = scholar["participations"][0]
    for key in (
        "start_date",
        "allowed_duration_years",
        "completion_due_on",
        "payback_payment_status",
    ):
        assert retained[key] == grant[key]
    response = update(
        client,
        scholar,
        {**older_payload, "completion_due_on": None, "payback_payment_status": "Fully paid"},
    )
    assert response.status_code == 200, response.text
    scholar = response.json()
    paid = scholar["participations"][0]
    assert paid["completion_deadline_on"] == "1993-06-01"
    assert paid["payback_payment_status"] == "Fully paid"
    assert paid["payback_attention"] == "Recorded Payback"
    response = update(
        client,
        scholar,
        {**older_payload, "allowed_duration_years": None, "payback_payment_status": None},
    )
    assert response.status_code == 200, response.text
    fallback = response.json()["participations"][0]
    assert fallback["completion_deadline_on"] == "1980-01-01"
    assert fallback["payback_payment_status"] is None


def test_deadline_payback_and_incomplete_match_profile_dashboard_report_and_csv(client):
    scholar = create(
        client,
        [
            {
                "program_name": "Short certification",
                "status": " incomplete ",
                "start_academic_year": "2021",
                "start_date": "2021-01-04",
                "completion_due_on": "2021-10-01",
                "payback_payment_status": "Unpaid",
            }
        ],
    )
    grant = scholar["participations"][0]
    assert grant["start_academic_year"] == "2021"
    assert grant["status"] == scholar["current_status"] == "Incomplete"
    assert grant["payback_attention"] == "Payback review"
    followup = client.get("/api/v1/fsdp/payback").json()["items"][0]
    assert followup["completion_deadline_on"] == "2021-10-01"
    assert followup["payback_payment_status"] == "Unpaid"
    assert client.get("/api/v1/fsdp/summary").json()["incomplete"] == 1
    assert client.get("/api/v1/fsdp/page?status=Incomplete").json()["total"] == 1
    assert client.get("/api/v1/fsdp/page?missing=contract_date").json()["total"] == 0
    report = client.get("/api/v1/fsdp/report").json()
    assert report["status_counts"]["Incomplete"] == 1
    assert report["department_totals"][0]["incomplete"] == 1
    assert report["items"][0]["participations"][0]["payback_attention"] == "Payback review"
    assert client.get("/api/v1/fsdp/analytics").json()["statuses"] == [
        {"label": "Incomplete", "count": 1}
    ]
    for endpoint in (
        "/api/v1/fsdp/payback.csv",
        "/api/v1/fsdp/report.csv",
        "/api/v1/maintenance/exports/fsdp.csv",
    ):
        content = client.get(endpoint).text
        rows = list(csv.reader(StringIO(content.removeprefix("\ufeff"))))
        header = next(row for row in rows if "Payback Payment Status" in row)
        detail = next(row for row in rows if "Unpaid" in row)
        assert detail[header.index("Payback Payment Status")] == "Unpaid"
        assert detail[header.index("Effective Completion Deadline")] == "2021-10-01"
        assert len(detail) == len(header)


@pytest.mark.parametrize(
    "completion_facts",
    [
        {"allowed_duration_years": 3},
        {"completion_due_on": "1993-06-01"},
        {"allowed_duration_years": 3, "completion_due_on": "1993-06-01"},
    ],
)
def test_annual_copy_preserves_application_deadline_and_clears_outcome_and_payment(
    client, completion_facts
):
    scholar = create(
        client,
        [
            {
                "program_name": "Annual",
                "application_key": "application-one",
                "status": "Payback",
                "start_date": "1990-06-01",
                "contract_completed_on": "1980-01-01",
                "end_date": "1993-05-31",
                "graduation_date": "1993-06-01",
                "payback_payment_status": "Fully paid",
                "case_status": "Closed",
                "extension": "Historical extension",
                **completion_facts,
            }
        ],
    )
    original = scholar["participations"][0]
    response = client.post(
        f"/api/v1/fsdp/{scholar['id']}/grants/{original['id']}/duplicate",
        headers={"If-Match": "0"},
    )
    assert response.status_code == 201, response.text
    source, copied = response.json()["participations"]
    assert source == original
    assert copied["allowed_duration_years"] == original["allowed_duration_years"]
    assert copied["application_key"] == original["application_key"]
    assert copied["start_date"] == original["start_date"]
    assert copied["completion_due_on"] == original["completion_due_on"]
    assert copied["completion_deadline_on"] == original["completion_deadline_on"]
    assert copied["payback_attention"] == "Payback review"
    assert (
        copied["contract_completed_on"]
        is copied["end_date"]
        is copied["graduation_date"]
        is copied["payback_payment_status"]
        is copied["extension"]
        is None
    )
    assert copied["status"] == "On Going"
    assert copied["case_status"] == "Open"


def test_annual_copy_without_new_completion_rules_keeps_legacy_date_reset(client):
    scholar = create(
        client,
        [
            {
                "program_name": "Historical annual grant",
                "start_date": "1990-06-01",
                "contract_completed_on": "1993-06-01",
            }
        ],
    )
    original = scholar["participations"][0]
    response = client.post(
        f"/api/v1/fsdp/{scholar['id']}/grants/{original['id']}/duplicate",
        headers={"If-Match": "0"},
    )
    assert response.status_code == 201, response.text
    copied = response.json()["participations"][1]
    assert copied["start_date"] is copied["contract_completed_on"] is None
    assert copied["completion_deadline_on"] is None
    assert copied["payback_attention"] == "Completion date missing"


def test_application_completion_and_payment_are_independent_from_payback_review(client):
    scholar = create(
        client,
        [
            {
                "program_name": "Repeated course",
                "application_key": "finished-application",
                "status": "Completed",
                "completion_due_on": "1993-02-28",
            },
            {
                "program_name": "Repeated course",
                "application_key": "finished-application",
                "status": "Incomplete",
                "completion_due_on": "1993-02-28",
            },
            {
                "program_name": "Repeated course",
                "application_key": "separate-application",
                "status": "Incomplete",
                "completion_due_on": "1993-02-28",
                "payback_payment_status": "Fully paid",
            },
            {
                "program_name": "Repeated course",
                "application_key": "separate-application",
                "status": "Transferred",
                "completion_due_on": "1993-02-28",
            },
            {
                "program_name": "Repeated course",
                "application_key": "separate-application",
                "status": "Withdrawn",
                "completion_due_on": "1993-02-28",
            },
            {
                "program_name": "Repeated course",
                "application_key": "finished-application",
                "status": "Payback",
                "completion_due_on": "1993-02-28",
                "payback_payment_status": "Fully paid",
            },
        ],
    )
    expected = [
        "Completed",
        "Completed",
        "Payback review",
        "Payback review",
        "Payback review",
        "Recorded Payback",
    ]
    assert [grant["payback_attention"] for grant in scholar["participations"]] == expected
    followups = client.get("/api/v1/fsdp/payback").json()
    groups = {item["participation_id"]: item["attention"] for item in followups["items"]}
    assert [groups[grant["id"]] for grant in scholar["participations"]] == expected
    assert followups["grant_counts"]["Payback review"] == 3
    assert followups["grant_counts"]["Recorded Payback"] == 1
    assert followups["scholar_counts"]["Payback review"] == 1
    actions = client.get("/api/v1/fsdp/report").json()["action_items"]
    paid_actions = [item for item in actions if item["detail"].endswith(" · Payment: Fully paid")]
    assert len(paid_actions) == 2
    assert {item["attention"] for item in paid_actions} == {"Recorded Payback", "Payback review"}
    assert all(item["priority"] == 0 for item in paid_actions)


def test_leap_day_deadline_grace_is_inclusive_and_extreme_dates_do_not_overflow():
    deadline, _ = completion_deadline(date(2020, 2, 29), 4)
    assert deadline == date(2024, 2, 29)
    assert classify_contract("Incomplete", deadline, False, date(2027, 2, 28)) == (
        "In grace period",
        date(2027, 2, 28),
    )
    assert classify_contract("Incomplete", deadline, False, date(2027, 3, 1)) == (
        "Payback review",
        date(2027, 2, 28),
    )
    assert classify_contract("Incomplete", date.max, False, date.max) == (
        "Contract not completed",
        None,
    )


@pytest.mark.parametrize("previous_version", [13, 14, 15])
def test_migration16_adds_nullable_facts_without_altering_existing_records(
    tmp_path, previous_version
):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-office.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            run_migrations(connection)
            connection.exec_driver_sql(
                "DELETE FROM schema_migrations WHERE version>?", (previous_version,)
            )
            for column in ("allowed_duration_years", "completion_due_on", "payback_payment_status"):
                connection.exec_driver_sql(f"ALTER TABLE fsdp_participations DROP COLUMN {column}")
            if previous_version < 15:
                connection.exec_driver_sql(
                    "ALTER TABLE local_sessions DROP COLUMN last_activity_at"
                )
            if previous_version < 14:
                for column in ("has_hard_copy", "has_soft_copy"):
                    connection.exec_driver_sql(f"ALTER TABLE scholars DROP COLUMN {column}")
                for column in ("program_category", "application_key"):
                    connection.exec_driver_sql(
                        f"ALTER TABLE fsdp_participations DROP COLUMN {column}"
                    )
            connection.exec_driver_sql("INSERT INTO programs(id,name) VALUES(1,'Program')")
            connection.exec_driver_sql(
                "INSERT INTO scholars(id,name,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Historical scholar',0,'Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            )
            connection.exec_driver_sql(
                "INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_date,contract_completed_on,remarks) VALUES(1,1,1,'Payback','2021-01-04','2021-10-01','Keep exact historical text')"
            )
            # Retain historical/custom outcomes and note casing byte for byte.
            connection.exec_driver_sql(
                "INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_academic_year,start_term,remarks) VALUES(2,1,1,'Historical custom outcome','2021','Summer','Untouched historical note')"
            )
            connection.exec_driver_sql(
                "INSERT INTO local_users(id,username,password_hash,role,created_at) "
                "VALUES(1,'existing-office-user','synthetic-password-hash','admin',"
                "'2021-01-04 12:00:00')"
            )
            connection.exec_driver_sql(
                "INSERT INTO local_sessions(id,user_id,token_hash,expires_at) "
                "VALUES(1,1,'synthetic-token-hash','2027-01-04 12:00:00')"
            )
            connection.exec_driver_sql(
                "INSERT INTO office_logs(id,scholar_id,scholar_name,user_id,username,"
                "occurred_on,created_at,entry_type,note) "
                "VALUES(1,1,'Historical scholar',1,'existing-office-user','2021-01-04',"
                "'2021-01-04 12:00:00','DOCUMENT','Unchanged office log note')"
            )
            protected_before = {
                table: list(connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id"))
                for table in ("programs", "local_users", "office_logs")
            }
            session_before = dict(
                connection.exec_driver_sql("SELECT * FROM local_sessions").mappings().one()
            )
            before = [
                dict(row)
                for row in connection.exec_driver_sql(
                    "SELECT * FROM fsdp_participations ORDER BY id"
                ).mappings()
            ]
            scholar_before = dict(
                connection.exec_driver_sql("SELECT * FROM scholars").mappings().one()
            )
            revision = connection.exec_driver_sql("SELECT revision FROM scholars").scalar()
            run_migrations(connection)
            run_migrations(connection)
            after = list(
                connection.exec_driver_sql(
                    "SELECT * FROM fsdp_participations ORDER BY id"
                ).mappings()
            )
            assert len(after) == len(before)
            for old_row, new_row in zip(before, after, strict=True):
                assert {column: new_row[column] for column in old_row} == old_row
                assert all(
                    new_row[column] is None
                    for column in (
                        "allowed_duration_years",
                        "completion_due_on",
                        "payback_payment_status",
                    )
                )
            scholar_after = connection.exec_driver_sql("SELECT * FROM scholars").mappings().one()
            assert {column: scholar_after[column] for column in scholar_before} == scholar_before
            for table, rows in protected_before.items():
                assert (
                    list(connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id")) == rows
                )
            session_after = (
                connection.exec_driver_sql("SELECT * FROM local_sessions").mappings().one()
            )
            assert {column: session_after[column] for column in session_before} == session_before
            assert connection.exec_driver_sql("SELECT revision FROM scholars").scalar() == revision
            assert (
                connection.exec_driver_sql("SELECT max(version) FROM schema_migrations").scalar()
                == 16
            )
    finally:
        engine.dispose()
