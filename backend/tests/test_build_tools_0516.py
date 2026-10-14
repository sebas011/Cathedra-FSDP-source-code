import copy
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import FsdpParticipation, Program, Scholar
from create_install_seed import create_install_seed

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name):
    specification = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize("arguments,expected", [
    (((3, 14, 7), "Windows", "AMD64", "v26.8.1", 64), []),
    (((3, 14, 6), "Windows", "AMD64", "v26.8.1", 64), ["Python"]),
    (((3, 14, 7), "Windows", "AMD64", "v26.8.0", 64), ["Node"]),
    (((3, 14, 7), "Linux", "X86_64", "v26.8.1", 64), ["Platform"]),
    (((3, 14, 7), "Windows", "ARM64", "v26.8.1", 64), ["Platform"]),
    (((3, 14, 7), "Windows", "AMD64", "v26.8.1", 32), ["Platform"]),
])
def test_exact_windows_build_runtime(arguments, expected):
    errors = load_tool("verify_build_inputs").verify_runtime(*arguments)
    assert [message.split(":")[0] for message in errors] == expected


def build_environment(monkeypatch, node_version="v26.8.1"):
    tool = load_tool("verify_build_inputs")
    monkeypatch.setattr(tool.sys, "version_info", (3, 14, 7))
    monkeypatch.setattr(tool.platform, "system", lambda: "Windows")
    monkeypatch.setattr(tool.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(tool.struct, "calcsize", lambda _: 8)
    monkeypatch.setattr(tool.subprocess, "run", lambda *_, **__: SimpleNamespace(stdout=node_version))
    return tool


def test_runtime_only_allows_dependency_installation_before_package_check(monkeypatch, tmp_path):
    tool = build_environment(monkeypatch)
    missing_constraints = tmp_path / "not-installed-yet.txt"
    assert tool.main([str(missing_constraints), "--node", "node", "--runtime-only"]) == 0
    assert not missing_constraints.exists()


def test_runtime_mismatch_stops_before_reading_package_constraints(monkeypatch, tmp_path):
    tool = build_environment(monkeypatch, node_version="v24.0.0")
    with pytest.raises(SystemExit, match="Node: expected v26.8.1"):
        tool.main([str(tmp_path / "missing-constraints.txt"), "--node", "node"])


def test_missing_node_is_an_actionable_failure(monkeypatch, tmp_path):
    tool = load_tool("verify_build_inputs")

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("synthetic missing Node")

    monkeypatch.setattr(tool.subprocess, "run", unavailable)
    with pytest.raises(SystemExit, match="Node runtime verification failed"):
        tool.main([str(tmp_path / "constraints.txt"), "--node", "missing-node"])


def test_retired_migration_helper_import_and_cli_never_modify_files(tmp_path):
    tool = load_tool("verify_office_migration")
    source = tmp_path / "source.db"
    destination = tmp_path / "destination.db"
    source.write_bytes(b"synthetic source sentinel")
    destination.write_bytes(b"synthetic destination sentinel")
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, destination)]
    with pytest.raises(RuntimeError, match="retired"):
        tool.verify_migration(source, destination)
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/verify_office_migration.py"),
         str(source), str(destination)], capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "tools/update-office.ps1" in result.stderr
    assert "No files were changed" in result.stderr
    assert before == [hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, destination)]
    missing = tmp_path / "absent.db"
    with pytest.raises(RuntimeError, match="retired"):
        tool.verify_migration(missing, tmp_path / "never-created.db")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["destination.db", "source.db"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 compatibility gate")
@pytest.mark.parametrize("relative,arguments", [
    ("desktop/build-split-release.ps1", []),
    ("desktop/verify-release.ps1", ["-ReleaseFolder", "not-an-installation"]),
    ("tools/check-packaged.ps1", ["-ReleaseFolder", "not-an-installation"]),
])
def test_build_and_packaged_verifiers_reject_unsupported_powershell(relative, arguments):
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(ROOT / relative), *arguments], capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "7.0" in result.stderr and "PowerShell" in result.stderr


@pytest.fixture
def current_read_responses(client):
    scholars, grants = {}, {}
    for index, status in enumerate(("On Going", "Graduated", "Payback pending contract")):
        response = client.post("/api/v1/fsdp", json={
            "name": "=Formula scholar" if index == 0 else f"Synthetic scholar {index}",
            "department": "CAS" if index < 2 else "Staff", "missing_requirements": index == 0,
            "participations": [{"program_name": f"Synthetic program {index}", "status": status,
                                "contract_completed_on": "2020-01-01"}],
        })
        assert response.status_code == 201, response.text
        item = response.json()
        scholars[item["id"]] = item["name"]
        for grant in item["participations"]:
            grants[grant["id"]] = (item["id"], grant["program_id"], grant["name"])
    tool = load_tool("check_records")
    results = {}
    for endpoint in tool.ENDPOINTS:
        response = client.get("/api/v1" + endpoint)
        assert response.status_code == 200, response.text
        results[endpoint] = response.text if endpoint.endswith(".csv") else response.json()
    contracts = json.loads((ROOT / "docs/current/EXPORT_CONTRACTS.json").read_text("utf-8"))
    return tool, results, scholars, grants, contracts


def test_office_copy_checks_actual_records_and_formula_safe_export(current_read_responses):
    tool, results, scholars, grants, contracts = current_read_responses
    tool.validate_records(results, scholars, grants, contracts)


@pytest.mark.parametrize("populated", [False, True])
def test_office_copy_cli_preserves_source_and_checks_private_snapshot(tmp_path, populated):
    source = tmp_path / "synthetic-source.db"
    create_install_seed(source)
    if populated:
        engine = create_engine(f"sqlite:///{source.as_posix()}")
        try:
            with Session(engine) as session:
                session.add(Scholar(
                    name="Synthetic CLI scholar", department="CAS",
                    participations=[FsdpParticipation(program=Program(name="Synthetic CLI program"))],
                ))
                session.commit()
        finally:
            engine.dispose()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    workspace = tmp_path / "private-workspace"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_records.py"), "--app", str(ROOT),
         "--database", str(source), "--workspace", str(workspace)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Four FSDP office-copy endpoint checks passed" in result.stdout
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    responses = json.loads((workspace / "responses.json").read_text("utf-8"))
    assert responses["/fsdp/report"]["total"] == int(populated)
    assert responses["/fsdp/payback"]["total"] == int(populated)


@pytest.mark.parametrize("corruption", [
    "missing_response", "empty_json", "false_summary", "missing_scholar", "duplicate_scholar",
    "missing_grant", "false_action_count", "missing_payback_grant", "false_payback_count",
    "altered_csv_header", "missing_csv_record", "csv_wrong_totals",
])
def test_successful_but_incorrect_read_payloads_are_rejected(current_read_responses, corruption):
    tool, original, scholars, grants, contracts = current_read_responses
    results = copy.deepcopy(original)
    if corruption == "missing_response":
        del results["/fsdp/summary"]
    elif corruption == "empty_json":
        results["/fsdp/report"] = {}
    elif corruption == "false_summary":
        results["/fsdp/summary"]["total"] = 0
    elif corruption == "missing_scholar":
        results["/fsdp/report"]["items"].pop()
    elif corruption == "duplicate_scholar":
        results["/fsdp/report"]["items"][1] = results["/fsdp/report"]["items"][0]
    elif corruption == "missing_grant":
        results["/fsdp/report"]["items"][0]["participations"] = []
    elif corruption == "false_action_count":
        results["/fsdp/report"]["action_total"] += 1
    elif corruption == "missing_payback_grant":
        results["/fsdp/payback"]["items"].pop()
    elif corruption == "false_payback_count":
        group = results["/fsdp/payback"]["items"][0]["attention"]
        results["/fsdp/payback"]["grant_counts"][group] += 1
    else:
        csv_rows = list(csv.reader(StringIO(results["/fsdp/report.csv"])))
        if corruption == "altered_csv_header":
            index = csv_rows.index(contracts["report"]["sections"]["records"])
            csv_rows[index][0] = "Wrong Name Header"
        elif corruption == "missing_csv_record":
            csv_rows.pop()
        else:
            csv_rows[1][1] = "0"
        output = StringIO(newline="")
        csv.writer(output).writerows(csv_rows)
        results["/fsdp/report.csv"] = output.getvalue()
    with pytest.raises(ValueError):
        tool.validate_records(results, scholars, grants, contracts)
