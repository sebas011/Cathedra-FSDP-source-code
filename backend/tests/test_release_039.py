import importlib.util
from pathlib import Path

import pytest


def load_tool(name):
    path = Path(__file__).resolve().parents[2] / "tools" / f"{name}.py"
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    for relative, content in {
        "Cathedra FSDP.exe": "test binary",
        "VERSION": "0.3.9",
        "APP_PRODUCT": "fsdp",
        "_internal/runtime.dll": "runtime",
        "_internal/frontend/dist/release-version.txt": "0.3.9",
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    source = tmp_path / "source"
    for name in (
        "verify-package.ps1",
        "office-smoke.ps1",
        "protect-local-installation.ps1",
        "update-office.ps1",
    ):
        path = root / "tools" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic tool")
    for relative, content in {
        "VERSION": "0.3.9",
        "backend/constraints-win-py314.txt": "test==1",
        "frontend/package-lock.json": "{}",
    }.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    tool = load_tool("release_manifest")
    import json

    manifest = tool.create_manifest(root, source, "test-python", "test-node")
    (root / "release-manifest.json").write_text(json.dumps(manifest))
    return root, tool


def test_release_inventory_verifies(package):
    root, tool = package
    assert tool.verify_manifest(root)["files"] == 9


@pytest.mark.parametrize("operation", ["modify", "remove", "add"])
def test_release_inventory_rejects_changes(package, operation):
    root, tool = package
    path = root / "_internal/runtime.dll"
    if operation == "modify":
        path.write_text("tampered")
    elif operation == "remove":
        path.unlink()
    else:
        (root / "_internal/extra.dll").write_text("unexpected")
    with pytest.raises(ValueError, match="inventory differs"):
        tool.verify_manifest(root)


def test_windows_resource_metadata():
    tool = load_tool("windows_version")
    assert "filevers=(0, 3, 9, 0)" in tool.version_resource("0.3.9")
    assert "ProductName', 'Cathedra FSDP'" in tool.version_resource("0.3.9")
    with pytest.raises(ValueError):
        tool.version_resource("0.3")
