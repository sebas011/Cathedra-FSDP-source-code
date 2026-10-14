from uuid import uuid4

from sqlalchemy import create_engine

from app.profile_values import education_level
from app.upgrade import upgrade_database


def payload():
    return {
        "name": "Safe retry",
        "participations": [{"program_name": "BS Computing", "status": "Graduated"}],
        "requirements": [],
    }


def test_creation_replay_and_deleted_result(client):
    headers = {"Idempotency-Key": str(uuid4())}
    first = client.post("/api/v1/fsdp", json=payload(), headers=headers)
    second = client.post("/api/v1/fsdp", json=payload(), headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert client.get("/api/v1/fsdp/page").json()["total"] == 1
    assert (
        client.post(
            "/api/v1/fsdp", json={**payload(), "name": "Changed"}, headers=headers
        ).status_code
        == 409
    )
    client.delete(
        f"/api/v1/fsdp/{first.json()['id']}", headers={"If-Match": str(first.json()["revision"])}
    )
    assert client.post("/api/v1/fsdp", json=payload(), headers=headers).status_code == 409


def test_program_stale_writer(client):
    program = client.post("/api/v1/fsdp/programs", json={"name": "Original"}).json()
    url = f"/api/v1/fsdp/programs/{program['id']}"
    assert client.put(url, json={"name": "First"}).status_code == 428
    headers = {"If-Match": str(program["revision"])}
    assert client.put(url, json={"name": "First"}, headers=headers).status_code == 200
    assert client.put(url, json={"name": "Stale"}, headers=headers).status_code == 409
    assert client.get("/api/v1/fsdp/programs").json()[0]["name"] == "FIRST"


def test_generated_education_removal_and_restore(client):
    scholar = client.post("/api/v1/fsdp", json=payload()).json()
    program_id = scholar["education"][0]["source_program_id"]
    update = {
        **payload(),
        "education": [],
        "participations": [
            {**payload()["participations"][0], "id": scholar["participations"][0]["id"]}
        ],
    }
    url = f"/api/v1/fsdp/{scholar['id']}"
    removed = client.put(url, json=update, headers={"If-Match": str(scholar["revision"])}).json()
    assert removed["education"] == []
    assert removed["suppressed_education_program_ids"] == [program_id]
    again = client.put(url, json=update, headers={"If-Match": str(removed["revision"])}).json()
    assert again["education"] == []
    restored = client.put(
        url,
        json={**update, "restore_education_program_ids": [program_id]},
        headers={"If-Match": str(again["revision"])},
    ).json()
    assert len(restored["education"]) == 1
    assert restored["suppressed_education_program_ids"] == []


def test_bachelor_abbreviations():
    for degree in ["BS Computing", "BA History", "B.S. Biology", "Bachelor of Arts"]:
        assert education_level(degree) == "Bachelor’s"
    assert education_level("Basic Training") == "Other"


def test_upgrade_snapshot_precedes_changes_and_current_skips(tmp_path):
    import sqlite3
    from contextlib import closing

    path = tmp_path / "cathedra.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    assert upgrade_database(engine, path) is None
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=9")
        connection.exec_driver_sql("ALTER TABLE programs DROP COLUMN revision")
        connection.exec_driver_sql("DROP TABLE creation_requests")
        connection.exec_driver_sql("DROP TABLE education_suppressions")
    snapshot = upgrade_database(engine, path)
    assert snapshot and snapshot.is_file()
    with closing(sqlite3.connect(snapshot)) as database:
        assert database.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (8,)
        assert "revision" not in {row[1] for row in database.execute("PRAGMA table_info(programs)")}
    assert upgrade_database(engine, path) is None
    engine.dispose()


def test_snapshot_failure_prevents_schema_writes(tmp_path, monkeypatch):
    import app.upgrade as upgrade

    path = tmp_path / "cathedra.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    upgrade_database(engine, path)
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=9")
        connection.exec_driver_sql("ALTER TABLE programs DROP COLUMN revision")

    def fail(*args):
        raise OSError("Synthetic full disk")

    monkeypatch.setattr(upgrade, "snapshot_database", fail)
    import pytest

    with pytest.raises(OSError):
        upgrade_database(engine, path)
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == 8
        )
        assert "revision" not in {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(programs)")
        }
    engine.dispose()
