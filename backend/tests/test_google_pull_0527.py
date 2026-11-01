"""Reconcile fictional reports offline; never read a live sheet or Office database."""

import copy
import sqlite3
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, update
from sqlalchemy.exc import IntegrityError

import app.api.google_sheets as google_api
import app.main as main
from app import clock
from app.models import Scholar

ROOT = "/api/v1/google-sheets/pull"
HEADERS = [
    "No.",
    "Name",
    "Age",
    "Tenure",
    "Department",
    "Rank/position",
    "Previous degree",
    "Profile remarks",
    "Program",
    "Delivering HEI",
    "Grant type",
    "Date started",
    "Date ended",
    "Extension",
    "Status",
    "Remarks",
]


def report_row(name="", program="", **values):
    record = {"Name": name, "Program": program, **values}
    return [record.get(heading, "") for heading in HEADERS]


@pytest.fixture
def report_source(client, monkeypatch):
    google_api.preview_store.clear()
    source = {"values": [HEADERS.copy()], "reads": 0}

    def read_report():
        source["reads"] += 1
        return {
            "spreadsheet_id": "synthetic-sheet",
            "worksheet": "CATHEDRA REPORT",
            "values": copy.deepcopy(source["values"]),
        }

    monkeypatch.setattr(google_api.connection, "read_report", read_report)
    yield source
    google_api.preview_store.clear()


def preview(client, report_source, *rows, headers=None):
    report_source["values"] = [headers or HEADERS.copy(), *rows]
    response = client.post(ROOT + "/preview")
    assert response.status_code == 200, response.text
    return response.json()


def create(client, name, **values):
    response = client.post("/api/v1/fsdp", json={"name": name, **values})
    assert response.status_code == 201, response.text
    return response.json()


def get_scholar(client, scholar_id):
    response = client.get(f"/api/v1/fsdp/{scholar_id}")
    assert response.status_code == 200, response.text
    return response.json()


def selection(profile, scholar=None, grant_targets=None):
    grant_targets = grant_targets or {}
    return {
        "key": profile["key"],
        "scholar_id": scholar["id"] if scholar is not None else None,
        "expected_revision": scholar["revision"] if scholar is not None else None,
        "grants": [
            {"key": grant["key"], "participation_id": grant_targets.get(grant["key"])}
            for grant in profile["grants"]
        ],
    }


def apply(client, proposed, *profiles):
    return client.post(
        ROOT + "/apply", json={"preview_id": proposed["preview_id"], "profiles": list(profiles)}
    )


def snapshot():
    """Include audit/receipt/counter rows so failed batches cannot leave half a save."""
    names = (
        "scholars",
        "programs",
        "fsdp_participations",
        "scholar_education",
        "scholar_requirements",
        "education_suppressions",
        "activity_events",
        "creation_requests",
        "sheet_import_receipts",
        "scholar_id_counter",
    )
    with main.SessionLocal() as db:
        return {
            name: sorted(
                (tuple(row) for row in db.connection().exec_driver_sql(f'SELECT * FROM "{name}"')),
                key=repr,
            )
            for name in names
        }


def editable(record, **changes):
    result = {
        **record,
        "participations": [
            {**grant, "program_name": grant["name"], "source_program_id": grant["program_id"]}
            for grant in record["participations"]
        ],
    }
    result.update(changes)
    return result


def test_preview_is_read_only_and_ordinal_numbers_are_not_record_ids(client, report_source):
    existing = create(client, "SYNTHETIC EXISTING")
    before = snapshot()
    proposed = preview(
        client, report_source, report_row("SYNTHETIC NEW", "NEW PROGRAM", **{"No.": existing["id"]})
    )
    assert snapshot() == before
    assert proposed["preview_id"] and proposed["fetched_at"] and proposed["expires_at"]
    assert proposed["worksheet"] == "CATHEDRA REPORT"
    assert len(proposed["profiles"]) == 1
    profile = proposed["profiles"][0]
    assert profile["row"] == 2 and profile["suggested_scholar_id"] is None
    assert profile["grants"][0]["row"] == 2
    assert profile["grants"][0]["suggested_participation_id"] is None


def test_new_scholars_keep_zero_literal_year_summer_and_independent_annual_rows(
    client, report_source
):
    proposed = preview(
        client,
        report_source,
        report_row(
            "SYNTHETIC ZERO",
            "CERTIFICATION PROGRAM",
            **{
                "No.": 1,
                "Age": 0,
                "Tenure": 0,
                "Department": "CAS",
                "Previous degree": "BACHELOR OF SCIENCE · EXAMPLE COLLEGE · 2010",
                "Profile remarks": "PROFILE NOTE",
                "Date started": "Summer 2021",
                "Date ended": "2nd 2021",
                "Status": "Incomplete",
                "Remarks": "FIRST GRANT NOTE",
            },
        ),
        report_row("", "SECOND PROGRAM", **{"Status": "On Going", "Remarks": "SECOND NOTE"}),
    )
    assert proposed["profiles"][0]["fields"]["age"] == 0
    assert proposed["profiles"][0]["fields"]["tenure_years"] == 0
    assert len(proposed["profiles"]) == 1 and len(proposed["profiles"][0]["grants"]) == 2
    response = apply(client, proposed, selection(proposed["profiles"][0]))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["scholars_created"] == 1 and result["grants_created"] == 2
    assert result["scholars_updated"] == result["grants_updated"] == 0
    saved = get_scholar(client, result["scholar_ids"][0])
    assert saved["name"] == "SYNTHETIC ZERO" and saved["age"] == saved["tenure_years"] == 0
    assert saved["profile_remarks"] == "PROFILE NOTE"
    assert any(
        "BACHELOR OF SCIENCE · EXAMPLE COLLEGE · 2010" in item["degree"]
        for item in saved["education"]
    )
    first, second = saved["participations"]
    assert first["start_term"] == "Summer" and first["start_academic_year"] == "2021"
    assert first["end_term"] == "2nd" and first["end_academic_year"] == "2021"
    assert first["remarks"] == "FIRST GRANT NOTE" and second["remarks"] == "SECOND NOTE"
    assert first["application_key"] and second["application_key"]
    assert first["application_key"] != second["application_key"]


def test_updates_retain_unreported_facts_and_unselected_grants(client, report_source):
    original = create(
        client,
        "SYNTHETIC PRESERVED",
        age=44,
        tenure_years=9,
        has_hard_copy=True,
        has_soft_copy=False,
        profile_remarks="OLD PROFILE NOTE",
        education=[{"level": "Other", "degree": "MANUAL EDUCATION", "institution": "ORIGINAL HEI"}],
        requirements=[{"requirement_name": "KEEP REQUIREMENT", "remarks": "ORIGINAL NOTE"}],
        participations=[
            {
                "program_name": "SELECTED PROGRAM",
                "application_key": "selected-existing-application",
                "program_category": "Certification",
                "start_date": "2020-06-01",
                "completion_due_on": "2023-06-01",
                "allowed_duration_years": 3,
                "case_status": "Closed",
                "payback_payment_status": "Fully paid",
                "status": "Payback",
                "remarks": "OLD GRANT NOTE",
            },
            {"program_name": "UNSELECTED PROGRAM", "application_key": "untouched-application"},
        ],
    )
    targeted = original["participations"][0]
    unselected = original["participations"][1]
    proposed = preview(
        client,
        report_source,
        report_row(
            original["name"],
            targeted["name"],
            **{
                "Age": 44,
                "Tenure": 9,
                "Profile remarks": "NEW PROFILE NOTE",
                "Date started": "2020-06-01",
                "Delivering HEI": "NEW DELIVERING HEI",
                "Status": "Incomplete",
                "Remarks": "NEW GRANT NOTE",
            },
        ),
    )
    profile = proposed["profiles"][0]
    assert profile["suggested_scholar_id"] == original["id"]
    response = apply(
        client,
        proposed,
        selection(profile, original, {profile["grants"][0]["key"]: targeted["id"]}),
    )
    assert response.status_code == 200, response.text
    assert response.json()["scholars_updated"] == response.json()["grants_updated"] == 1
    saved = get_scholar(client, original["id"])
    assert saved["revision"] == original["revision"] + 1
    assert saved["age"] == 44 and saved["tenure_years"] == 9
    assert saved["has_hard_copy"] is True and saved["has_soft_copy"] is False
    assert saved["profile_remarks"] == "NEW PROFILE NOTE"
    assert saved["requirements"] == original["requirements"]
    assert saved["education"] == original["education"]
    grants = {grant["id"]: grant for grant in saved["participations"]}
    assert grants[unselected["id"]] == unselected
    changed = grants[targeted["id"]]
    assert changed["remarks"] == "NEW GRANT NOTE" and changed["status"] == "Incomplete"
    assert changed["delivering_hei"] == "NEW DELIVERING HEI"
    for name in (
        "application_key",
        "program_category",
        "completion_due_on",
        "allowed_duration_years",
        "case_status",
        "payback_payment_status",
    ):
        assert changed[name] == targeted[name]


def test_old_fifteen_column_combined_remarks_cannot_overwrite_separate_notes(client, report_source):
    original = create(
        client,
        "SYNTHETIC OLD REPORT",
        profile_remarks="KEEP PROFILE NOTE",
        participations=[{"program_name": "LEGACY PROGRAM", "remarks": "KEEP GRANT NOTE"}],
    )
    headers = [header for header in HEADERS if header != "Profile remarks"]
    values = report_row(
        original["name"], "LEGACY PROGRAM", **{"Age": 0, "Remarks": "Profile: MIXED\nGrant: MIXED"}
    )
    del values[7]
    proposed = preview(client, report_source, values, headers=headers)
    assert proposed["warnings"]
    profile = proposed["profiles"][0]
    response = apply(
        client,
        proposed,
        selection(
            profile, original, {profile["grants"][0]["key"]: original["participations"][0]["id"]}
        ),
    )
    assert response.status_code == 200, response.text
    saved = get_scholar(client, original["id"])
    assert saved["age"] == 0
    assert saved["profile_remarks"] == "KEEP PROFILE NOTE"
    assert saved["participations"][0]["remarks"] == "KEEP GRANT NOTE"


def test_present_blank_optional_cells_clear_values_but_blank_status_keeps_recorded_outcome(
    client, report_source
):
    original = create(
        client,
        "SYNTHETIC CLEARED CELLS",
        age=44,
        tenure_years=9,
        profile_remarks="CLEAR THIS PROFILE NOTE",
        participations=[
            {
                "program_name": "RECORDED PAYBACK PROGRAM",
                "status": "Payback",
                "remarks": "CLEAR THIS GRANT NOTE",
                "payback_payment_status": "Fully paid",
            }
        ],
    )
    proposed = preview(
        client, report_source, report_row(original["name"], original["participations"][0]["name"])
    )
    profile = proposed["profiles"][0]
    assert profile["fields"]["age"] is None
    assert profile["fields"]["tenure_years"] is None
    assert profile["fields"]["profile_remarks"] is None
    response = apply(
        client,
        proposed,
        selection(
            profile, original, {profile["grants"][0]["key"]: original["participations"][0]["id"]}
        ),
    )
    assert response.status_code == 200, response.text
    saved = get_scholar(client, original["id"])
    assert saved["age"] is saved["tenure_years"] is saved["profile_remarks"] is None
    grant = saved["participations"][0]
    assert grant["remarks"] is None
    assert grant["status"] == "Payback" and grant["payback_payment_status"] == "Fully paid"


@pytest.mark.parametrize("reported_start,reported_end", [("2021-06-01", "2022-05-31"), ("", "")])
def test_exact_or_blank_date_cells_preserve_hidden_terms_years_and_current_status(
    client, report_source, reported_start, reported_end
):
    original = create(
        client,
        "SYNTHETIC HIDDEN PERIODS",
        participations=[
            {
                "program_name": "LATEST BY RECORDED YEAR",
                "start_date": "2021-06-01",
                "end_date": "2022-05-31",
                "start_term": "Summer",
                "start_academic_year": "2030-2031",
                "end_term": "3rd",
                "end_academic_year": "2031-2032",
                "status": "Incomplete",
            },
            {
                "program_name": "OTHER RECORDED YEAR",
                "start_term": "1st",
                "start_academic_year": "2024-2025",
                "status": "On Going",
            },
        ],
    )
    target = original["participations"][0]
    assert original["current_status"] == "Incomplete"
    proposed = preview(
        client,
        report_source,
        report_row(
            original["name"],
            target["name"],
            **{"Date started": reported_start, "Date ended": reported_end},
        ),
    )
    profile = proposed["profiles"][0]
    response = apply(
        client,
        proposed,
        selection(profile, original, {profile["grants"][0]["key"]: target["id"]}),
    )
    assert response.status_code == 200, response.text
    saved = get_scholar(client, original["id"])
    grant = next(item for item in saved["participations"] if item["id"] == target["id"])
    for field in (
        "start_date",
        "end_date",
        "start_term",
        "start_academic_year",
        "end_term",
        "end_academic_year",
        "status",
    ):
        assert grant[field] == target[field]
    assert saved["current_status"] == "Incomplete"


def test_reported_period_labels_update_periods_without_clearing_unreported_exact_dates(
    client, report_source
):
    original = create(
        client,
        "SYNTHETIC TERM ONLY EDIT",
        participations=[
            {
                "program_name": "PERIOD PROGRAM",
                "start_date": "2021-06-01",
                "end_date": "2022-05-31",
                "start_term": "1st",
                "start_academic_year": "2021-2022",
                "end_term": "2nd",
                "end_academic_year": "2022-2023",
                "status": "Payback",
            }
        ],
    )
    target = original["participations"][0]
    proposed = preview(
        client,
        report_source,
        report_row(
            original["name"],
            target["name"],
            **{"Date started": "Summer 2023", "Date ended": "3rd 2024"},
        ),
    )
    profile = proposed["profiles"][0]
    response = apply(
        client,
        proposed,
        selection(profile, original, {profile["grants"][0]["key"]: target["id"]}),
    )
    assert response.status_code == 200, response.text
    saved = get_scholar(client, original["id"])["participations"][0]
    assert saved["start_date"] == target["start_date"] and saved["end_date"] == target["end_date"]
    assert saved["start_term"] == "Summer" and saved["start_academic_year"] == "2023"
    assert saved["end_term"] == "3rd" and saved["end_academic_year"] == "2024"
    assert saved["status"] == "Payback"


@pytest.mark.parametrize("reported", ["1st", "2nd", "3rd", "Summer", "2025"])
def test_partial_period_updates_only_the_fact_represented_in_the_report(
    client, report_source, reported
):
    original = create(
        client,
        "SYNTHETIC PARTIAL PERIOD",
        participations=[
            {
                "program_name": "PARTIAL PERIOD PROGRAM",
                "start_date": "2021-06-01",
                "start_term": "3rd",
                "start_academic_year": "2021-2022",
            }
        ],
    )
    target = original["participations"][0]
    proposed = preview(
        client,
        report_source,
        report_row(original["name"], target["name"], **{"Date started": reported}),
    )
    profile = proposed["profiles"][0]
    result = apply(
        client,
        proposed,
        selection(profile, original, {profile["grants"][0]["key"]: target["id"]}),
    )
    assert result.status_code == 200, result.text
    saved = get_scholar(client, original["id"])["participations"][0]
    assert saved["start_date"] == target["start_date"]
    assert saved["start_term"] == (target["start_term"] if reported == "2025" else reported)
    assert saved["start_academic_year"] == (
        "2025" if reported == "2025" else target["start_academic_year"]
    )


def test_namesakes_and_repeated_program_periods_require_explicit_targets(client, report_source):
    create(client, "SYNTHETIC NAMESAKE")
    chosen = create(
        client,
        "SYNTHETIC NAMESAKE",
        participations=[
            {
                "program_name": "REPEATED PROGRAM",
                "start_academic_year": "2021",
                "application_key": key,
            }
            for key in ("first-application", "second-application")
        ],
    )
    proposed = preview(
        client,
        report_source,
        report_row("synthetic namesake", "REPEATED PROGRAM", **{"Date started": "2021"}),
    )
    profile = proposed["profiles"][0]
    assert profile["suggested_scholar_id"] is None
    assert profile["grants"][0]["suggested_participation_id"] is None
    assert len([item for item in proposed["matches"] if item["name"] == chosen["name"]]) == 2
    target = chosen["participations"][1]
    response = apply(
        client, proposed, selection(profile, chosen, {profile["grants"][0]["key"]: target["id"]})
    )
    assert response.status_code == 200, response.text
    saved = get_scholar(client, chosen["id"])
    assert len(saved["participations"]) == 2
    assert {item["application_key"] for item in saved["participations"]} == {
        "first-application",
        "second-application",
    }


def test_explicit_new_grant_is_an_independent_application(client, report_source):
    original = create(
        client,
        "SYNTHETIC REAPPLICATION",
        participations=[{"program_name": "SAME PROGRAM", "application_key": "old-application"}],
    )
    proposed = preview(client, report_source, report_row(original["name"], "SAME PROGRAM"))
    profile = proposed["profiles"][0]
    response = apply(client, proposed, selection(profile, original))
    assert response.status_code == 200, response.text
    saved = get_scholar(client, original["id"])
    assert len(saved["participations"]) == 2
    new = next(
        grant
        for grant in saved["participations"]
        if grant["id"] != original["participations"][0]["id"]
    )
    assert new["application_key"] and new["application_key"] != "old-application"


def test_apply_uses_the_reviewed_snapshot_without_rereading_changed_source(
    client, report_source, monkeypatch
):
    proposed = preview(client, report_source, report_row("SYNTHETIC REVIEWED", "REVIEWED PROGRAM"))
    report_source["values"] = [HEADERS, report_row("SYNTHETIC CHANGED", "CHANGED PROGRAM")]

    def should_not_read():
        raise AssertionError("Apply must not reread the report after preview")

    monkeypatch.setattr(google_api.connection, "read_report", should_not_read)
    response = apply(client, proposed, selection(proposed["profiles"][0]))
    assert response.status_code == 200, response.text
    saved = get_scholar(client, response.json()["scholar_ids"][0])
    assert saved["name"] == "SYNTHETIC REVIEWED"
    assert saved["participations"][0]["name"] == "REVIEWED PROGRAM"


def test_duplicate_profile_targets_and_cross_scholar_grant_ids_are_rejected_atomically(
    client, report_source
):
    first = create(client, "SYNTHETIC FIRST", participations=[{"program_name": "FIRST PROGRAM"}])
    second = create(client, "SYNTHETIC SECOND", participations=[{"program_name": "SECOND PROGRAM"}])
    proposed = preview(
        client,
        report_source,
        report_row(first["name"], "FIRST PROGRAM"),
        report_row(second["name"], "SECOND PROGRAM"),
    )
    before = snapshot()
    duplicate = apply(
        client,
        proposed,
        selection(proposed["profiles"][0], first),
        selection(proposed["profiles"][1], first),
    )
    assert duplicate.status_code in {409, 422}
    assert snapshot() == before
    profile = proposed["profiles"][0]
    crossed = apply(
        client,
        proposed,
        selection(profile, first, {profile["grants"][0]["key"]: second["participations"][0]["id"]}),
    )
    assert crossed.status_code in {409, 422}
    assert snapshot() == before


def test_stale_target_rejects_the_entire_batch_including_a_new_scholar(client, report_source):
    target = create(client, "SYNTHETIC STALE")
    proposed = preview(
        client, report_source, report_row("SYNTHETIC NEW"), report_row(target["name"])
    )
    changed = client.put(
        f"/api/v1/fsdp/{target['id']}",
        headers={"If-Match": str(target["revision"])},
        json=editable(target, rank="LOCAL CHANGE AFTER PREVIEW"),
    )
    assert changed.status_code == 200
    before = snapshot()
    response = apply(
        client,
        proposed,
        selection(proposed["profiles"][0]),
        selection(proposed["profiles"][1], target),
    )
    assert response.status_code == 409, response.text
    assert snapshot() == before


def test_name_added_after_preview_rejects_new_creation_without_duplicates(client, report_source):
    proposed = preview(client, report_source, report_row("SYNTHETIC NEW NAME"))
    create(client, "SYNTHETIC NEW NAME")
    before = snapshot()
    response = apply(client, proposed, selection(proposed["profiles"][0]))
    assert response.status_code == 409, response.text
    assert snapshot() == before


def test_raw_or_restored_data_change_with_same_revision_also_rejects_snapshot(
    client, report_source
):
    original = create(client, "SYNTHETIC RESTORED", rank="ORIGINAL RANK")
    proposed = preview(client, report_source, report_row(original["name"]))
    with main.SessionLocal() as db:
        db.execute(
            update(Scholar)
            .where(Scholar.id == original["id"])
            .values(rank="DIFFERENT RESTORED RANK")
        )
        db.commit()
    assert get_scholar(client, original["id"])["revision"] == original["revision"]
    before = snapshot()
    response = apply(client, proposed, selection(proposed["profiles"][0], original))
    assert response.status_code == 409, response.text
    assert snapshot() == before


def test_durable_receipt_replays_after_preview_cache_clear_without_new_rows_or_revisions(
    client, report_source
):
    original = create(client, "SYNTHETIC DURABLE")
    proposed = preview(client, report_source, report_row(original["name"], "DURABLE PROGRAM"))
    profile_selection = selection(proposed["profiles"][0], original)
    first = apply(client, proposed, profile_selection)
    assert first.status_code == 200, first.text
    assert first.json()["replayed"] is False
    after = snapshot()
    google_api.preview_store.clear()
    replay = apply(client, proposed, profile_selection)
    assert replay.status_code == 200, replay.text
    assert replay.json() == {**first.json(), "replayed": True}
    assert snapshot() == after
    revised = {**profile_selection, "grants": []}
    rejected = apply(client, proposed, revised)
    assert rejected.status_code == 409, rejected.text
    assert snapshot() == after


def test_late_database_failure_rolls_back_all_records_history_and_receipt(client, report_source):
    proposed = preview(
        client,
        report_source,
        report_row("SYNTHETIC EARLY", "EARLY PROGRAM"),
        report_row("SYNTHETIC LATE", "LATE PROGRAM"),
    )
    before = snapshot()

    def reject_late(_mapper, _connection, record):
        if record.name == "SYNTHETIC LATE":
            raise IntegrityError(
                "synthetic insertion", {}, sqlite3.IntegrityError("synthetic failure")
            )

    event.listen(Scholar, "before_insert", reject_late)
    try:
        response = apply(
            client, proposed, *(selection(profile) for profile in proposed["profiles"])
        )
    finally:
        event.remove(Scholar, "before_insert", reject_late)
    assert response.status_code == 409, response.text
    assert snapshot() == before


@pytest.mark.parametrize(
    "rows",
    [
        [report_row("", "ORPHAN PROGRAM")],
        [report_row("SYNTHETIC MISSING PROGRAM", **{"Status": "Incomplete"})],
    ],
)
def test_missing_essential_profile_or_grant_identifier_never_writes(client, report_source, rows):
    report_source["values"] = [HEADERS, *rows]
    before = snapshot()
    response = client.post(ROOT + "/preview")
    assert response.status_code == 422, response.text
    assert snapshot() == before


@pytest.mark.parametrize(
    "values",
    [{"Age": "not a number"}, {"Date started": "2021-02-30"}, {"Tenure": float("nan")}],
)
def test_unrepresentable_report_values_fail_before_any_database_change(
    client, report_source, values
):
    report_source["values"] = [HEADERS, report_row("SYNTHETIC INVALID", "PROGRAM", **values)]
    before = snapshot()
    response = client.post(ROOT + "/preview")
    assert response.status_code == 422, response.text
    assert snapshot() == before


def test_report_row_limit_is_enforced_before_any_database_change(client, report_source):
    report_source["values"] = [HEADERS] + [
        report_row(f"SYNTHETIC BOUNDED {index}") for index in range(2001)
    ]
    before = snapshot()
    response = client.post(ROOT + "/preview")
    assert response.status_code == 422, response.text
    assert snapshot() == before


def test_expired_preview_cannot_apply(client, report_source, monkeypatch):
    proposed = preview(client, report_source, report_row("SYNTHETIC EXPIRING"))
    deadline = datetime.fromisoformat(proposed["expires_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(clock, "utc_now", lambda: deadline + timedelta(seconds=1))
    before = snapshot()
    response = apply(client, proposed, selection(proposed["profiles"][0]))
    assert response.status_code in {409, 410}
    assert snapshot() == before


def sign_in_as(client, username, role):
    password = "synthetic-pull-password-123"
    created = client.post(
        "/api/v1/auth/users", json={"username": username, "password": password, "role": role}
    )
    assert created.status_code == 201
    signed_in = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    headers = {"Authorization": "Bearer " + signed_in.json()["token"]}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": password, "new_password": "changed-synthetic-pull-password-123"},
    )
    assert changed.status_code == 204
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "changed-synthetic-pull-password-123"},
    )
    return {"Authorization": "Bearer " + signed_in.json()["token"]}


def test_preview_snapshot_belongs_only_to_its_administrator(client, report_source):
    proposed = preview(client, report_source, report_row("SYNTHETIC PRIVATE PREVIEW"))
    headers = sign_in_as(client, "other-pull-admin", "admin")
    before = snapshot()
    response = client.post(
        ROOT + "/apply",
        headers=headers,
        json={
            "preview_id": proposed["preview_id"],
            "profiles": [selection(proposed["profiles"][0])],
        },
    )
    assert response.status_code in {403, 404, 409}
    assert snapshot() == before


def test_pull_routes_require_an_administrator_before_reading_google(client, report_source):
    headers = sign_in_as(client, "pull-staff", "staff")
    response = client.post(ROOT + "/preview", headers=headers)
    assert response.status_code == 403
    denied = client.post(
        ROOT + "/apply",
        headers=headers,
        json={"preview_id": "synthetic-preview", "profiles": []},
    )
    assert denied.status_code == 403
    client.headers.clear()
    assert client.post(ROOT + "/preview").status_code == 401
    assert report_source["reads"] == 0
