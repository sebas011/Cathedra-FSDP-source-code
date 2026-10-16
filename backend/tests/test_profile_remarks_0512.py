import csv
import sqlite3
from io import StringIO

from sqlalchemy import create_engine

from app.upgrade import upgrade_database


def test_profile_remarks_separate_from_grant_and_omitted_update_preserves(client):
    payload = {
        "name": "Synthetic remarks",
        "profile_remarks": "Office note\nSecond line",
        "participations": [{"program_name": "Synthetic course", "remarks": "Grant note"}],
        "requirements": [],
    }
    response = client.post("/api/v1/fsdp", json=payload)
    assert response.status_code == 201
    scholar = response.json()
    url = f"/api/v1/fsdp/{scholar['id']}"
    assert client.get(url).json()["profile_remarks"] == "OFFICE NOTE\nSECOND LINE"
    assert scholar["participations"][0]["remarks"] == "GRANT NOTE"
    payload["participations"][0]["id"] = scholar["participations"][0]["id"]
    payload.pop("profile_remarks")
    response = client.put(url, json=payload, headers={"If-Match": str(scholar["revision"])})
    assert response.status_code == 200
    scholar = response.json()
    assert scholar["profile_remarks"] == "OFFICE NOTE\nSECOND LINE"
    for note in ["=private note", ""]:
        response = client.put(
            url,
            json={**payload, "profile_remarks": note},
            headers={"If-Match": str(scholar["revision"])},
        )
        assert response.status_code == 200
        scholar = response.json()
        assert scholar["profile_remarks"] == note.upper()
        assert scholar["participations"][0]["remarks"] == "GRANT NOTE"
        exported = next(
            csv.DictReader(
                StringIO(client.get("/api/v1/maintenance/exports/fsdp.csv").text.lstrip("\ufeff"))
            )
        )
        assert exported["Remarks"] == "GRANT NOTE"
        assert exported["Profile Remarks"].lstrip("'") == note.upper()
        rows = list(
            csv.reader(StringIO(client.get("/api/v1/fsdp/report.csv").text.lstrip("\ufeff")))
        )
        header = next(row for row in rows if "Profile Remarks" in row)
        assert rows[-1][header.index("Profile Remarks")].lstrip("'") == note.upper()


def test_migration_adds_remarks_and_retains_recovery_snapshot(tmp_path):
    path = tmp_path / "cathedra.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    upgrade_database(engine, path)
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=10")
        connection.exec_driver_sql("ALTER TABLE scholars DROP COLUMN profile_remarks")
        connection.exec_driver_sql(
            "INSERT INTO scholars(id,name,department,missing_requirements,data_source,created_at,updated_at,revision) VALUES(1,'Synthetic old profile','CAS',0,'Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,4)"
        )
    snapshot = upgrade_database(engine, path)
    assert snapshot
    with sqlite3.connect(snapshot) as before:
        assert before.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (9,)
        assert "profile_remarks" not in {
            row[1] for row in before.execute("PRAGMA table_info(scholars)")
        }
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT name,profile_remarks,revision FROM scholars"
        ).first() == ("Synthetic old profile", None, 5)
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
    assert upgrade_database(engine, path) is None
    engine.dispose()
