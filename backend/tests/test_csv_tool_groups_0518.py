import copy
import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def grouped_read_responses(client):
    specification = importlib.util.spec_from_file_location("csv_group_record_check", ROOT / "tools/check_records.py")
    tool = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(tool)
    scholars, grants = {}, {}
    # Equal names must form separate groups; the blank rows retain their own grants.
    for programs in (("=FIRST DEGREE", "SECOND DEGREE"), ("THIRD DEGREE",), ()):
        response = client.post("/api/v1/fsdp", json={
            "name": "=SAME NAME", "department": "CAS",
            "participations": [{"program_name": program, "start_academic_year": f"202{index}-202{index + 1}"}
                               for index, program in enumerate(programs)],
        })
        assert response.status_code == 201, response.text
        item = response.json()
        scholars[item["id"]] = item["name"]
        for grant in item["participations"]:
            grants[grant["id"]] = (item["id"], grant["program_id"], grant["name"])
    results = {}
    for endpoint in tool.ENDPOINTS:
        response = client.get("/api/v1" + endpoint)
        assert response.status_code == 200
        results[endpoint] = response.text if endpoint.endswith(".csv") else response.json()
    contracts = json.loads((ROOT / "docs/current/EXPORT_CONTRACTS.json").read_text("utf-8"))
    return tool, results, scholars, grants, contracts


def test_integrity_check_accepts_grouped_rows_and_name_twins(grouped_read_responses):
    tool, results, scholars, grants, contracts = grouped_read_responses
    tool.validate_records(results, scholars, grants, contracts)


@pytest.mark.parametrize("corruption", ["orphan", "split", "profile_on_continuation", "moved_grant"])
def test_integrity_check_rejects_detached_or_mixed_groups(grouped_read_responses, corruption):
    tool, original, scholars, grants, contracts = grouped_read_responses
    results = copy.deepcopy(original)
    rows = list(csv.reader(StringIO(results["/fsdp/report.csv"])))
    header = contracts["report"]["sections"]["records"]
    start = rows.index(header) + 1
    assert len(rows[start:]) == 4
    assert rows[start + 1][0] == ""
    if corruption == "orphan":
        rows[start][0] = ""
    elif corruption == "split":
        rows[start + 1][0] = rows[start][0]
    elif corruption == "profile_on_continuation":
        rows[start + 1][header.index("Department")] = "CCS"
    else:
        program_index = header.index("Program applied")
        rows[start + 1][program_index], rows[start + 2][program_index] = (
            rows[start + 2][program_index], rows[start + 1][program_index]
        )
    output = StringIO(newline="")
    csv.writer(output).writerows(rows)
    results["/fsdp/report.csv"] = output.getvalue()
    with pytest.raises(ValueError):
        tool.validate_records(results, scholars, grants, contracts)
