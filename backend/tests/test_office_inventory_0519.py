"""Runtime inventory parity and closed-app update preflight protections."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_office_updater import Lock, make_package, module
from test_office_updater import installation as installation

WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="Windows path and PowerShell parity")


def complete_package(path: Path, release: str = "0.5.19") -> dict:
    """Add the frontend identity required by the real PowerShell verifier."""
    make_package(path, release)
    identity = path / "_internal/frontend/dist/release-version.txt"
    identity.parent.mkdir(parents=True)
    identity.write_text(release, encoding="utf-8")
    manifest = json.loads((path / "release-manifest.json").read_text())
    manifest["runtime_files"].append(
        {
            "path": identity.relative_to(path).as_posix(),
            "size": identity.stat().st_size,
            "sha256": hashlib.sha256(identity.read_bytes()).hexdigest(),
        }
    )
    save_manifest(path, manifest)
    return manifest


def save_manifest(path: Path, manifest: dict) -> None:
    (path / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def powershell_verifies(path: Path) -> dict:
    script = Path(__file__).resolve().parents[2] / "tools/verify-package.ps1"
    shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    environment = {**os.environ, "PSModulePath": str(shell.parent / "Modules")}
    result = subprocess.run(
        [
            str(shell),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Package",
            str(path),
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["verified"] is True
    return receipt


@WINDOWS_ONLY
def test_uppercase_physical_tool_names_match_powershell_inventory(tmp_path):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    for tool in (package / "tools").iterdir():
        temporary = tool.with_name("case-rename-" + tool.name)
        tool.rename(temporary)
        temporary.rename(tool.with_name(tool.name.upper()))
    assert powershell_verifies(package)["runtime_files"] == len(manifest["runtime_files"])
    assert module().verify_package(package) == manifest


@WINDOWS_ONLY
@pytest.mark.parametrize("separator", ["/", "\\"])
def test_equivalent_manifest_case_and_slashes_match_powershell(tmp_path, separator):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    for entry in manifest["runtime_files"]:
        entry["path"] = entry["path"].upper().replace("/", separator)
    save_manifest(package, manifest)
    assert powershell_verifies(package)["runtime_files"] == len(manifest["runtime_files"])
    assert module().verify_package(package) == manifest


@WINDOWS_ONLY
def test_uppercase_physical_internal_tree_matches_powershell(tmp_path):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    runtime = package / "_internal/runtime.dll"
    runtime.rename(runtime.with_name("case-rename-runtime.dll"))
    (package / "_internal/case-rename-runtime.dll").rename(
        package / "_internal/RUNTIME.DLL"
    )
    (package / "_internal").rename(package / "case-rename-internal")
    (package / "case-rename-internal").rename(package / "_INTERNAL")
    assert powershell_verifies(package)["runtime_files"] == len(manifest["runtime_files"])
    assert module().verify_package(package) == manifest


@pytest.mark.parametrize("relative", ["tools/update-office.ps1", "_internal/runtime.dll"])
def test_duplicate_case_alias_is_refused(tmp_path, relative):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    original = next(item for item in manifest["runtime_files"] if item["path"] == relative)
    manifest["runtime_files"].append({**original, "path": relative.upper()})
    save_manifest(package, manifest)
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        module().verify_package(package)


@WINDOWS_ONLY
def test_nested_tool_basename_does_not_expand_runtime_inventory(tmp_path):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    nested = package / "tools/notes/update-office.ps1"
    nested.parent.mkdir()
    nested.write_text("An unrelated support copy", encoding="utf-8")
    assert powershell_verifies(package)["runtime_files"] == len(manifest["runtime_files"])
    assert module().verify_package(package) == manifest


def test_nested_tool_cannot_replace_required_tool_omitted_from_manifest(tmp_path):
    package = tmp_path / "incoming"
    manifest = complete_package(package)
    relative = "tools/update-office.ps1"
    manifest["runtime_files"] = [
        entry for entry in manifest["runtime_files"] if entry["path"] != relative
    ]
    save_manifest(package, manifest)
    nested = package / "tools/notes/update-office.ps1"
    nested.parent.mkdir()
    (package / relative).rename(nested)
    with pytest.raises(ValueError) as failure:
        module().verify_package(package)
    assert_inventory_diagnostic(failure.value, package, relative)


def assert_inventory_diagnostic(error: Exception, package: Path, *relative_paths: str) -> None:
    message = str(error).replace("\\", "/").casefold()
    assert "package runtime inventory differs" in message
    assert package.as_posix().casefold() in message
    for relative in relative_paths:
        assert relative.casefold() in message


def test_unknown_internal_file_has_actionable_inventory_diagnostic(tmp_path):
    package = tmp_path / "incoming"
    complete_package(package)
    (package / "_internal/unexpected.dll").write_bytes(b"Unlisted runtime")
    with pytest.raises(ValueError) as failure:
        module().verify_package(package)
    assert_inventory_diagnostic(failure.value, package, "_internal/unexpected.dll")


@pytest.mark.parametrize("relative", ["tools/update-office.ps1", "_internal/runtime.dll"])
def test_missing_runtime_has_actionable_inventory_diagnostic(tmp_path, relative):
    package = tmp_path / "incoming"
    complete_package(package)
    (package / relative).unlink()
    with pytest.raises(ValueError) as failure:
        module().verify_package(package)
    assert_inventory_diagnostic(failure.value, package, relative)


def test_missing_and_unexpected_runtime_are_both_reported(tmp_path):
    package = tmp_path / "incoming"
    complete_package(package)
    (package / "_internal/runtime.dll").rename(package / "_internal/renamed.dll")
    with pytest.raises(ValueError) as failure:
        module().verify_package(package)
    assert_inventory_diagnostic(
        failure.value, package, "_internal/runtime.dll", "_internal/renamed.dll"
    )


def test_corrupted_manifested_runtime_is_refused(tmp_path):
    package = tmp_path / "incoming"
    complete_package(package)
    (package / "_internal/runtime.dll").write_text("Corrupted runtime", encoding="utf-8")
    with pytest.raises(ValueError, match="[Ii]ntegrity"):
        module().verify_package(package)


def test_linked_runtime_is_refused(tmp_path):
    package = tmp_path / "incoming"
    complete_package(package)
    runtime = package / "_internal/runtime.dll"
    external = tmp_path / "external.dll"
    external.write_bytes(runtime.read_bytes())
    runtime.unlink()
    try:
        runtime.symlink_to(external)
    except OSError as error:
        pytest.skip(f"This host cannot create synthetic symbolic links: {error}")
    with pytest.raises(ValueError, match="[Ll]inked"):
        module().verify_package(package)


def deny_internal_enumeration(
    monkeypatch, updater, package: Path, relative: str = "_internal"
) -> None:
    original = updater.os.scandir

    def denied(path):
        if Path(path) == package / relative:
            raise PermissionError("Synthetic runtime inventory access denied")
        return original(path)

    monkeypatch.setattr(updater.os, "scandir", denied)


def test_runtime_enumeration_error_fails_closed(tmp_path, monkeypatch):
    package = tmp_path / "incoming"
    complete_package(package)
    updater = module()
    deny_internal_enumeration(monkeypatch, updater, package)
    with pytest.raises((OSError, ValueError), match="[Aa]ccess denied"):
        updater.verify_package(package)


def test_partial_enumeration_error_cannot_hide_unlisted_runtime(tmp_path, monkeypatch):
    package = tmp_path / "incoming"
    complete_package(package)
    hidden = package / "_internal/unreadable/unlisted.dll"
    hidden.parent.mkdir()
    hidden.write_bytes(b"Unlisted runtime behind an unreadable folder")
    updater = module()
    deny_internal_enumeration(monkeypatch, updater, package, "_internal/unreadable")
    with pytest.raises((OSError, ValueError), match="[Aa]ccess denied"):
        updater.verify_package(package)


def data_inventory(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in path.rglob("*")
        if item.is_file()
    }


@pytest.mark.parametrize(
    ("location", "defect"),
    [
        ("incoming", "missing"),
        ("incoming", "unexpected"),
        ("incoming", "corrupt"),
        ("installed", "missing"),
        ("installed", "corrupt"),
    ],
)
def test_invalid_inventory_preflight_preserves_office_data(installation, location, defect):
    incoming, target, database = installation
    package = incoming if location == "incoming" else target
    runtime = package / "_internal/runtime.dll"
    if defect == "missing":
        runtime.unlink()
    elif defect == "unexpected":
        (package / "_internal/unexpected.dll").write_bytes(b"Unlisted runtime")
    else:
        runtime.write_bytes(b"Corrupt runtime")
    before_database = database.read_bytes()
    before_data = data_inventory(target / "data")
    with pytest.raises(ValueError):
        module().update_office(
            incoming, target, lambda _: Lock(), workflow_check=lambda _: None
        )
    assert database.read_bytes() == before_database
    assert data_inventory(target / "data") == before_data
    assert not (target / "data/update-state.json").exists()
    assert not (target / "data/updates").exists()


def test_existing_residue_is_archived_and_runtime_repair_can_roll_back(installation):
    incoming, target, database = installation
    residue = {
        "_internal/old-frontend/unexpected.js": b"Old unlisted frontend chunk",
        "tools/notes/old.txt": b"Existing tool support file",
    }
    for relative, content in residue.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    before_database = database.read_bytes()
    updater = module()
    result = updater.update_office(
        incoming, target, lambda _: Lock(), workflow_check=lambda _: None
    )
    assert result["status"] == "verified"
    assert result["database_replaced"] is False
    assert result["existing_runtime_residue_repaired"] is True
    assert result["runtime_residue_files"] == len(residue)
    archive = Path(result["runtime_residue_archive"])
    assert archive.is_relative_to(target / "data/updates")
    old_runtime = Path(result["old_runtime"])
    assert updater.verify_package(old_runtime)["version"] == "0.5.8"
    assert updater.verify_package(target)["version"] == "0.5.11"
    for relative, content in residue.items():
        assert (archive / relative).read_bytes() == content
        assert not (target / relative).exists()
        assert not (old_runtime / relative).exists()
    assert database.read_bytes() == before_database
    rolled_back = updater.update_office(
        incoming, target, lambda _: Lock(), rollback=True, workflow_check=lambda _: None
    )
    assert rolled_back["status"] == "rolled-back"
    assert updater.verify_package(target)["version"] == "0.5.8"
    assert database.read_bytes() == before_database
    for relative, content in residue.items():
        assert (archive / relative).read_bytes() == content
        assert not (target / relative).exists()


@pytest.mark.parametrize("location", ["incoming", "installed"])
def test_unlisted_link_preflight_preserves_office_data(installation, location, tmp_path):
    incoming, target, database = installation
    selected = incoming if location == "incoming" else target
    external = tmp_path / "external-unlisted.dll"
    external.write_bytes(b"Runtime link must not be followed or archived")
    linked = selected / "_internal/unlisted-link.dll"
    try:
        linked.symlink_to(external)
    except OSError as error:
        pytest.skip(f"This host cannot create synthetic symbolic links: {error}")
    before_database = database.read_bytes()
    before_data = data_inventory(target / "data")
    with pytest.raises(ValueError, match="[Ll]inked"):
        module().update_office(
            incoming, target, lambda _: Lock(), workflow_check=lambda _: None
        )
    assert database.read_bytes() == before_database
    assert data_inventory(target / "data") == before_data
    assert not (target / "data/update-state.json").exists()
    assert not (target / "data/updates").exists()


@pytest.mark.parametrize("location", ["incoming", "installed"])
def test_enumeration_preflight_preserves_office_data(installation, location, monkeypatch):
    incoming, target, database = installation
    updater = module()
    selected = incoming if location == "incoming" else target
    before_database = database.read_bytes()
    before_data = data_inventory(target / "data")
    deny_internal_enumeration(monkeypatch, updater, selected)
    with pytest.raises((OSError, ValueError), match="[Aa]ccess denied"):
        updater.update_office(
            incoming, target, lambda _: Lock(), workflow_check=lambda _: None
        )
    assert database.read_bytes() == before_database
    assert data_inventory(target / "data") == before_data
    assert not (target / "data/update-state.json").exists()
    assert not (target / "data/updates").exists()
