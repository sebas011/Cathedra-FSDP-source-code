"""Check FSDP read contracts against a private copy, never the live database."""

import argparse
import csv
import json
import os
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from importlib import import_module
from io import StringIO
from pathlib import Path

ENDPOINTS = ("/fsdp/summary", "/fsdp/report", "/fsdp/payback", "/fsdp/report.csv")
SUMMARY_STATUSES = {
    "ongoing": "On Going", "graduated": "Completed", "completed": "Completed", "payback": "Payback",
    "withdrawn": "Withdrawn", "did_not_avail": "Did Not Avail",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, f"{label}: expected a non-negative integer")
    return value


def rows(value: object, label: str) -> list[dict]:
    require(isinstance(value, list) and all(isinstance(item, dict) for item in value),
            f"{label}: expected a list of objects")
    return value


def csv_text(value: str) -> str:
    # Exported values include the required spreadsheet-formula protection.
    return "'" + value if value.lstrip("\ufeff\t\r\n ").startswith(("=", "+", "-", "@")) else value


def database_identity(database: Path) -> tuple[dict[int, str], dict[int, tuple[int, int, str]]]:
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        scholars = dict(connection.execute("SELECT id, name FROM scholars"))
        grants = {
            grant_id: (scholar_id, program_id, program_name)
            for grant_id, scholar_id, program_id, program_name in connection.execute(
                "SELECT fp.id, fp.scholar_id, fp.program_id, p.name "
                "FROM fsdp_participations fp JOIN programs p ON p.id = fp.program_id"
            )
        }
        grant_total = connection.execute("SELECT COUNT(*) FROM fsdp_participations").fetchone()[0]
        require(len(grants) == grant_total, "Source copy has a grant with no matching program")
    return scholars, grants


def validate_records(
    results: dict,
    expected_scholars: dict[int, str],
    expected_grants: dict[int, tuple[int, int, str]],
    export_contracts: dict,
) -> None:
    """Reject successful HTTP responses that omit, duplicate or miscount saved records."""
    for endpoint in ENDPOINTS:
        require(endpoint in results, f"Missing endpoint response: {endpoint}")
    summary, report, payback = (results[endpoint] for endpoint in ENDPOINTS[:3])
    for label, payload in (("Summary", summary), ("Report", report), ("Payback", payback)):
        require(isinstance(payload, dict), f"{label}: expected a JSON object")
    expected_total = len(expected_scholars)
    require(count(summary.get("total"), "Summary total") == expected_total,
            "Summary total differs from the saved scholar identities")
    require(count(report.get("total"), "Report total") == expected_total,
            "Report total differs from the saved scholar identities")
    report_items = rows(report.get("items"), "Report items")
    require(len(report_items) == expected_total, "Full report omits or duplicates scholars")
    actual_scholars, actual_grants = {}, {}
    statuses, departments = Counter(), Counter()
    missing_requirements = 0
    csv_records = Counter()
    for item in report_items:
        scholar_id = item.get("id")
        require(type(scholar_id) is int and scholar_id in expected_scholars,
                "Report contains an unknown scholar identity")
        require(scholar_id not in actual_scholars, "Report duplicates a scholar identity")
        require(item.get("name") == expected_scholars[scholar_id],
                "Report changes a saved scholar name")
        actual_scholars[scholar_id] = item["name"]
        require(type(item.get("missing_requirements")) is bool,
                "Report has malformed requirement follow-up")
        missing_requirements += item["missing_requirements"]
        status = item.get("current_status")
        require(status is None or isinstance(status, str), "Report has malformed current status")
        if status:
            statuses[status] += 1
        department = item.get("department")
        require(department is None or isinstance(department, str), "Report has malformed department")
        departments[department or "Unknown"] += 1
        participations = rows(item.get("participations"), "Report grant records")
        for grant in participations:
            grant_id = grant.get("id")
            require(type(grant_id) is int and grant_id in expected_grants,
                    "Report contains an unknown grant identity")
            require(grant_id not in actual_grants, "Report duplicates a grant identity")
            actual_grants[grant_id] = (scholar_id, grant.get("program_id"), grant.get("name"))
        for grant in participations or [{"name": ""}]:
            require(isinstance(grant.get("name"), str), "Report has a malformed program name")
            csv_records[(csv_text(item["name"]), csv_text(grant["name"]))] += 1
    require(actual_scholars == expected_scholars, "Full report is missing saved scholars")
    require(actual_grants == expected_grants, "Full report changes or omits saved grant records")
    for key, status in SUMMARY_STATUSES.items():
        require(count(summary.get(key), f"Summary {key}") == statuses[status],
                f"Summary {key} differs from the report's current scholar statuses")
    for payload, label in ((summary, "Summary"), (report, "Report")):
        require(count(payload.get("missing_requirements"), f"{label} missing requirements")
                == missing_requirements, f"{label} requirement total differs from its records")
    status_counts = report.get("status_counts")
    require(isinstance(status_counts, dict), "Report status counts are missing or malformed")
    for status, total in status_counts.items():
        require(count(total, f"Report status {status}") == statuses[status],
                f"Report status total differs for {status}")
    require(all(status in status_counts for status in statuses), "Report omits a saved status total")
    department_totals = rows(report.get("department_totals"), "Report department totals")
    actual_departments = {}
    for item in department_totals:
        department = item.get("department")
        require(isinstance(department, str) and department not in actual_departments,
                "Report department totals have missing or duplicate labels")
        actual_departments[department] = count(item.get("scholars"), "Department scholar total")
    require(actual_departments == dict(departments), "Report department totals differ from records")
    actions = rows(report.get("action_items"), "Report action items")
    require(count(report.get("action_total"), "Report action total") == len(actions),
            "Full report action count is truncated or inconsistent")
    require(all(item.get("scholar_id") in expected_scholars for item in actions),
            "Report action references an unknown scholar")
    payback_items = rows(payback.get("items"), "Payback items")
    require(count(payback.get("total"), "Payback total") == len(expected_grants)
            == len(payback_items), "Full payback report omits or duplicates grant records")
    payback_grants, grant_counts, scholar_sets = {}, Counter(), {}
    for item in payback_items:
        grant_id, scholar_id = item.get("participation_id"), item.get("scholar_id")
        require(type(grant_id) is int and grant_id in expected_grants,
                "Payback contains an unknown grant identity")
        require(grant_id not in payback_grants, "Payback duplicates a grant identity")
        require(item.get("scholar_name") == expected_scholars.get(scholar_id),
                "Payback changes a saved scholar name")
        payback_grants[grant_id] = (scholar_id, item.get("program_id"), item.get("program_name"))
        attention = item.get("attention")
        require(isinstance(attention, str) and bool(attention), "Payback has a malformed follow-up")
        grant_counts[attention] += 1
        scholar_sets.setdefault(attention, set()).add(scholar_id)
    require(payback_grants == expected_grants, "Payback changes or omits saved grant records")
    for key, expected_counts in (
        ("grant_counts", grant_counts),
        ("scholar_counts", {group: len(ids) for group, ids in scholar_sets.items()}),
    ):
        actual = payback.get(key)
        require(isinstance(actual, dict), f"Payback {key} are missing or malformed")
        require(all(group in actual for group in expected_counts), f"Payback {key} omit a group")
        require(all(count(total, f"Payback {key} {group}") == expected_counts.get(group, 0)
                    for group, total in actual.items()), f"Payback {key} differ from saved records")
    csv_content = results["/fsdp/report.csv"]
    require(isinstance(csv_content, str), "CSV report is not text")
    csv_rows = list(csv.reader(StringIO(csv_content.lstrip("\ufeff"))))
    require(len(csv_rows) >= 2 and csv_rows[0] == ["Cathedra FSDP Report"],
            "CSV report title is missing or malformed")
    require(csv_rows[1] == ["Scholars", str(expected_total), "Missing requirements",
                            str(missing_requirements)], "CSV report totals differ from saved records")
    sections = export_contracts["report"]["sections"]
    indexes = {}
    for section in ("department_totals", "actions", "records"):
        matches = [index for index, row in enumerate(csv_rows) if row == sections[section]]
        require(len(matches) == 1, f"CSV {section} header is missing, altered or duplicated")
        indexes[section] = matches[0]
    require(indexes["department_totals"] < indexes["actions"] < indexes["records"],
            "CSV report sections are out of order")
    for section, end in (("department_totals", indexes["actions"]),
                         ("actions", indexes["records"]), ("records", len(csv_rows))):
        data = [row for row in csv_rows[indexes[section] + 1:end] if row]
        require(all(len(row) == len(sections[section]) for row in data),
                f"CSV {section} contains malformed rows")
        if section == "records":
            name_index = sections[section].index("Name")
            program_index = sections[section].index("Program applied")
            groups: list[tuple[str, list[list[str]]]] = []
            for row in data:
                if row[name_index]:
                    groups.append((row[name_index], []))
                else:
                    require(bool(groups), "CSV report starts with an orphan grant continuation")
                    require(not any(row[:program_index]),
                            "CSV continuation repeats or changes scholar profile information")
                groups[-1][1].append(row)
            require(len(groups) == len(report_items),
                    "CSV report omits, duplicates or splits a scholar group")
            for (name, group), item in zip(groups, report_items, strict=True):
                require(name == csv_text(item["name"]),
                        "CSV scholar groups are changed or out of order")
                expected_programs = Counter(
                    csv_text(grant["name"])
                    for grant in item["participations"] or [{"name": ""}]
                )
                require(Counter(row[program_index] for row in group) == expected_programs,
                        "CSV scholar group omits, duplicates or moves a grant")
            require(Counter((name, row[program_index]) for name, group in groups for row in group) == csv_records,
                    "CSV report omits, duplicates or changes saved scholar/grant records")
        else:
            expected_count = len(department_totals) if section == "department_totals" else len(actions)
            require(len(data) == expected_count, f"CSV {section} is truncated or inconsistent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    contracts = json.loads((args.app / "docs/current/EXPORT_CONTRACTS.json").read_text("utf-8"))
    args.workspace.mkdir(parents=True, exist_ok=False)
    copied_database = args.workspace / "cathedra.db"
    with closing(sqlite3.connect(f"{args.database.resolve().as_uri()}?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(copied_database)) as destination:
            source.backup(destination)
    original_scholars, original_grants = database_identity(copied_database)
    os.environ["CATHEDRA_DATA_DIR"] = str(args.workspace.resolve())
    os.environ["CATHEDRA_PRODUCT"] = "fsdp"
    sys.path.insert(0, str(args.app.resolve() / "backend"))
    test_client = import_module("fastapi.testclient").TestClient
    require_signed_in = import_module("app.auth").require_signed_in
    app = import_module("app.main").app
    local_user = import_module("app.models").LocalUser
    app.dependency_overrides[require_signed_in] = lambda: local_user(
        id=1, username="isolated-regression-check", role="admin", is_active=True,
        must_change_password=False,
    )
    results = {}
    try:
        with test_client(app) as client:
            scholars, grants = database_identity(copied_database)
            require(scholars == original_scholars, "Private migration changed scholar identities")
            require({key: value[0] for key, value in grants.items()}
                    == {key: value[0] for key, value in original_grants.items()},
                    "Private migration changed grant identities or their scholar ownership")
            for endpoint in ENDPOINTS:
                response = client.get("/api/v1" + endpoint)
                require(response.status_code == 200,
                        f"Read check failed: {endpoint} HTTP {response.status_code}")
                results[endpoint] = response.text if endpoint.endswith(".csv") else response.json()
            validate_records(results, scholars, grants, contracts)
    finally:
        app.dependency_overrides.pop(require_signed_in, None)
    (args.workspace / "responses.json").write_text(
        json.dumps(results, ensure_ascii=False, sort_keys=True), encoding="utf-8",
    )
    print("Four FSDP office-copy endpoint checks passed with record and export consistency checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
