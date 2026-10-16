import sqlite3
from contextlib import closing

import pytest
from sqlalchemy import create_engine

from app.product import bind_empty_database, verify_product
from create_install_seed import create_install_seed


def test_optional_fields_round_trip_without_business_validation(client):
    payload = {
        "name": "N" * 250,
        "age": 17,
        "department": "D" * 150,
        "participations": [
            {
                "program_name": "Recorded program",
                "start_term": "1st",
                "start_academic_year": "Recorded year",
                "end_term": "3rd",
                "end_date": "2024-01-01",
                "grant_type": "Others",
                "grant_other": "",
            }
        ],
        "requirements": [{"requirement_name": "", "remarks": "R" * 600}],
    }
    response = client.post("/api/v1/fsdp", json=payload)
    assert response.status_code == 201
    record = response.json()
    assert record["age"] == 17
    assert record["department"] == "Staff"
    assert record["profile_remarks"] == "PREVIOUS AFFILIATION: " + "D" * 150
    assert record["requirements"][0]["requirement_name"] == ""
    grant = record["participations"][0]
    assert grant["start_term"] == "1st"
    assert grant["end_date"] == "2024-01-01"
    update = {
        **payload,
        "participations": [
            {
                **payload["participations"][0],
                "id": grant["id"],
                "start_term": "2nd",
                "grant_type": "Historical grant",
                "status": "Historical status",
            }
        ],
        "requirements": [{**payload["requirements"][0], "id": record["requirements"][0]["id"]}],
    }
    saved = client.put(
        f"/api/v1/fsdp/{record['id']}", headers={"If-Match": str(record["revision"])}, json=update
    )
    assert saved.status_code == 200
    reloaded = client.get(f"/api/v1/fsdp/{record['id']}").json()
    assert reloaded["participations"][0]["start_term"] == "2nd"
    assert reloaded["participations"][0]["status"] == "Historical status"
    assert reloaded["participations"][0]["grant_type"] == "Historical grant"
    assert client.get("/api/v1/fsdp/report", params={"department": "D" * 150}).status_code == 200
    assert (
        client.get("/api/v1/fsdp/report.csv", params={"department": "D" * 150}).status_code == 200
    )
    assert client.get("/api/v1/fsdp/page", params={"search": "N" * 250}).json()["total"] == 1
    assert client.get("/api/v1/verification").status_code == 404
    assert client.get("/api/v1/fsdp/monitoring").status_code in {404, 422}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "Essential scholar", "participations": [{"program_name": "   "}]},
    ],
)
def test_essential_fields_reject_blank_values(client, payload):
    assert client.post("/api/v1/fsdp", json=payload).status_code == 422


def test_backup_allowlist_rejects_unrecognized_tables(tmp_path):
    path = tmp_path / "seed.db"
    create_install_seed(path)
    with closing(sqlite3.connect(path)) as database:
        verify_product(database)
        database.execute("CREATE TABLE unrelated_records (id INTEGER PRIMARY KEY)")
        with pytest.raises(ValueError, match="other-app tables"):
            verify_product(database)


def test_unmarked_nonempty_database_is_not_claimed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'unmarked.db'}")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE "other" (id INTEGER PRIMARY KEY)')
            connection.exec_driver_sql('INSERT INTO "other" VALUES (1)')
            with pytest.raises(RuntimeError, match="Existing combined records"):
                bind_empty_database(connection)
            assert "cathedra_product" not in set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).scalars()
            )
    finally:
        engine.dispose()
