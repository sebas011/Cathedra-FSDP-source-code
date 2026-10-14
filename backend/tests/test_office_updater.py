import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.upgrade import upgrade_database


def module():
    path = Path(__file__).resolve().parents[2] / "desktop/office_update.py"
    spec = importlib.util.spec_from_file_location("office_update", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def make_package(path, version):
    import hashlib

    path.mkdir()
    values = {
        "Cathedra FSDP.exe": "Synthetic executable",
        "VERSION": version,
        "APP_PRODUCT": "fsdp",
        "_internal/runtime.dll": "Synthetic runtime",
    }
    for name in (
        "verify-package.ps1",
        "office-smoke.ps1",
        "protect-local-installation.ps1",
        "update-office.ps1",
    ):
        values["tools/" + name] = "Synthetic tool"
    entries = []
    for name, content in values.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
        entries.append(
            {
                "path": name,
                "size": destination.stat().st_size,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            }
        )
    (path / "release-manifest.json").write_text(
        json.dumps({"product": "fsdp", "version": version, "runtime_files": entries})
    )


class Lock:
    def close(self):
        pass


@pytest.fixture
def installation(tmp_path):
    incoming = tmp_path / "incoming"
    target = tmp_path / "office"
    make_package(incoming, "0.5.11")
    make_package(target, "0.5.8")
    data = target / "data"
    data.mkdir()
    database = data / "cathedra.db"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    upgrade_database(engine, database)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO scholars (id,name,revision,missing_requirements,data_source,created_at,updated_at) VALUES (987,'New Office scholar',0,0,'Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
        )
    engine.dispose()
    return incoming, target, database


def test_runtime_update_and_rollback_preserve_database(installation):
    incoming, target, database = installation
    before = database.read_bytes()
    updater = module()
    result = updater.update_office(
        incoming, target, lambda _: Lock(), workflow_check=lambda _: None
    )
    assert result["status"] == "verified"
    assert database.read_bytes() == before
    assert (target / "VERSION").read_text() == "0.5.11"
    result = updater.update_office(
        incoming, target, lambda _: Lock(), rollback=True, workflow_check=lambda _: None
    )
    assert result["status"] == "rolled-back"
    assert database.read_bytes() == before
    assert (target / "VERSION").read_text() == "0.5.8"


def test_failed_workflow_restores_runtime_without_replacing_data(installation):
    incoming, target, database = installation
    before = database.read_bytes()

    def failed(_):
        raise RuntimeError("Synthetic verification failure")

    with pytest.raises(RuntimeError):
        module().update_office(incoming, target, lambda _: Lock(), workflow_check=failed)
    assert database.read_bytes() == before
    assert (target / "VERSION").read_text() == "0.5.8"


def test_new_office_edits_prevent_automatic_rollback(installation):
    incoming, target, database = installation
    updater = module()
    updater.update_office(incoming, target, lambda _: Lock(), workflow_check=lambda _: None)
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE scholars SET name='Later Office edit' WHERE id=987")
    before = database.read_bytes()
    with pytest.raises(RuntimeError, match="Office data changed"):
        updater.update_office(
            incoming, target, lambda _: Lock(), rollback=True, workflow_check=lambda _: None
        )
    assert database.read_bytes() == before


def test_corrupt_package_and_active_lock_refused(installation):
    incoming, target, database = installation
    before = database.read_bytes()

    def occupied(_):
        raise RuntimeError("Already open")

    with pytest.raises(RuntimeError, match="Already open"):
        module().update_office(incoming, target, occupied)
    (incoming / "_internal/runtime.dll").write_text("Tampered")
    with pytest.raises(ValueError, match="integrity"):
        module().update_office(incoming, target, lambda _: Lock())
    assert database.read_bytes() == before
