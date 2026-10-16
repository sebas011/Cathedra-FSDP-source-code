import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_launcher_identity import launcher_module
from test_office_updater import module


@pytest.mark.parametrize("valid", [True, False])
def test_verifier_command_never_selects_data_or_opens_application(monkeypatch, tmp_path, valid):
    launcher = launcher_module()
    selected = tmp_path / "selected package"
    result_path = tmp_path / "result.json"
    arguments = SimpleNamespace(verify_package=str(selected), maintenance_result=str(result_path))
    monkeypatch.setattr(launcher, "parse_arguments", lambda: arguments)

    def forbidden(*_):
        raise AssertionError("Package verification must not select a data folder or open the app")

    monkeypatch.setattr(launcher, "writable_data_directory", forbidden)
    monkeypatch.setattr(launcher, "show_error", forbidden)

    def checked(root, phase):
        assert root == selected
        assert phase == "Selected package"
        if not valid:
            raise module().PackageVerificationError(
                "Package runtime inventory differs: unexpected.dll", selected, phase
            )
        return {"version": "0.5.19", "runtime_files": [1, 2, 3]}, []

    monkeypatch.setitem(sys.modules, "office_update", SimpleNamespace(checked_package=checked))
    if valid:
        launcher.main()
    else:
        with pytest.raises(SystemExit) as stopped:
            launcher.main()
        assert stopped.value.code == 1
    result = json.loads(result_path.read_text())
    assert result["database_accessed"] is False
    assert not selected.exists()
    if valid:
        assert result["verified"] is True
        assert result["runtime_files"] == 3
    else:
        assert result["status"] == "failed"
        assert result["phase"] == "Selected package"
        assert result["package_root"] == str(selected)
        assert "unexpected.dll" in result["detail"]


@pytest.mark.parametrize("failure_phase", ["Existing installation", "Update operation"])
def test_failed_update_receipt_names_phase_without_touching_database(
    monkeypatch, tmp_path, failure_phase
):
    launcher = launcher_module()
    target = tmp_path / "Office installation"
    data = target / "data"
    data.mkdir(parents=True)
    database = data / "cathedra.db"
    database.write_bytes(b"Synthetic Office records must stay intact")
    receipt = data / "result.json"
    arguments = SimpleNamespace(
        verify_package=None,
        data_dir=None,
        update_target=str(target),
        maintenance_result=str(receipt),
        rollback_update=False,
    )
    monkeypatch.setattr(launcher, "parse_arguments", lambda: arguments)
    monkeypatch.setattr(
        launcher, "writable_data_directory", lambda _: tmp_path / "private helper data"
    )
    monkeypatch.setattr(launcher, "bundled_release_version", lambda: "0.5.19")
    monkeypatch.setattr(launcher, "resource_path", lambda *_: tmp_path / "private helper backend")
    monkeypatch.setattr(sys, "path", list(sys.path))
    for name in (
        "CATHEDRA_DATA_DIR",
        "CATHEDRA_PRODUCT",
        "CATHEDRA_FRONTEND_DIST",
        "CATHEDRA_RELEASE_VERSION",
    ):
        monkeypatch.setenv(name, launcher.os.environ.get(name, ""))

    def failed(*_, **__):
        if failure_phase == "Existing installation":
            raise module().PackageVerificationError(
                "Package integrity verification failed: runtime.dll", target, failure_phase
            )
        raise RuntimeError("An interrupted update needs runtime rollback first")

    monkeypatch.setitem(sys.modules, "office_update", SimpleNamespace(update_office=failed))
    with pytest.raises(SystemExit) as stopped:
        launcher.main()
    assert stopped.value.code == 1
    result = json.loads(receipt.read_text())
    assert result["status"] == "failed"
    assert result["phase"] == failure_phase
    assert result["installation"] == str(target)
    assert result["database_replaced"] is False
    assert result["detail"]
    if failure_phase == "Existing installation":
        assert result["package_root"] == str(target)
        assert "runtime.dll" in result["detail"]
    else:
        assert result["package_root"] == str(Path(launcher.__file__).resolve().parents[1])
    assert database.read_bytes() == b"Synthetic Office records must stay intact"
    assert not (data / "update-state.json").exists()
    assert not (data / "backups").exists()
