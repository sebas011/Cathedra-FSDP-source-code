"""Optional document tracking, grant categories and one stable scholar order."""

import csv
import sqlite3
from io import StringIO

import pytest
from sqlalchemy import create_engine, select

import app.main as main
from app.migrations import MIGRATIONS
from app.models import Scholar
from app.upgrade import upgrade_database


def create(client, **fields):
    response = client.post("/api/v1/fsdp", json={"name": "Document scholar", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def update(client, scholar, **fields):
    response = client.put(
        f"/api/v1/fsdp/{scholar['id']}",
        json={
            "name": scholar["name"],
            "participations": [
                {**grant, "program_name": grant["name"]} for grant in scholar["participations"]
            ],
            "requirements": [],
            **fields,
        },
        headers={"If-Match": str(scholar["revision"])},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "paper,electronic", [(True, True), (True, False), (False, True), (False, False), (None, None)]
)
def test_document_copies_are_independent_and_omitted_fields_survive(client, paper, electronic):
    scholar = create(client, has_hard_copy=paper, has_soft_copy=electronic)
    assert (scholar["has_hard_copy"], scholar["has_soft_copy"]) == (paper, electronic)
    scholar = update(client, scholar, profile_remarks="Unrelated edit")
    assert (scholar["has_hard_copy"], scholar["has_soft_copy"]) == (paper, electronic)
    # Explicit Unknown clears only the selected flag. It is never a No.
    scholar = update(client, scholar, has_hard_copy=None)
    assert scholar["has_hard_copy"] is None and scholar["has_soft_copy"] is electronic
    with main.SessionLocal() as db:
        stored = db.get(Scholar, scholar["id"])
        assert stored.has_hard_copy is None and stored.has_soft_copy is electronic
    assert client.get(f"/api/v1/fsdp/{scholar['id']}").json()["has_soft_copy"] is electronic


def test_document_copies_default_to_unknown_and_do_not_mark_requirements_missing(client):
    scholar = create(client)
    assert scholar["has_hard_copy"] is None and scholar["has_soft_copy"] is None
    assert scholar["missing_requirements"] is False
    scholar = update(client, scholar, has_hard_copy=False, has_soft_copy=True)
    assert scholar["missing_requirements"] is False
    assert client.get("/api/v1/fsdp/page").json()["items"][0]["has_soft_copy"] is True
    assert client.get("/api/v1/fsdp/report").json()["items"][0]["has_hard_copy"] is False


@pytest.mark.parametrize("category", ["Degree", "Certification", "Enhancement"])
def test_program_category_is_independent_from_funding_and_preserved_when_omitted(client, category):
    scholar = create(
        client,
        participations=[
            {
                "program_name": "Specialized study",
                "program_category": category,
                "grant_type": "Full Scholarship",
                "application_key": "first-application",
            }
        ],
    )
    grant = scholar["participations"][0]
    assert grant["program_category"] == category and grant["grant_type"] == "Full Scholarship"
    assert grant["application_key"] == "first-application"
    old_grant = {
        key: value
        for key, value in grant.items()
        if key not in {"program_category", "application_key"}
    }
    scholar = update(client, scholar, participations=[{**old_grant, "program_name": grant["name"]}])
    saved = scholar["participations"][0]
    assert saved["program_category"] == category and saved["application_key"] == "first-application"
    copied = client.post(
        f"/api/v1/fsdp/{scholar['id']}/grants/{grant['id']}/duplicate",
        headers={"If-Match": str(scholar["revision"])},
    )
    assert copied.status_code == 201, copied.text
    assert copied.json()["participations"][1]["application_key"] == "first-application"
    assert copied.json()["participations"][1]["program_category"] == category
    scholar = update(
        client,
        copied.json(),
        participations=[
            {
                **item,
                "program_name": item["name"],
                "program_category": None,
                "application_key": None,
            }
            for item in copied.json()["participations"]
        ],
    )
    assert all(
        item["program_category"] is None and item["application_key"] is None
        for item in scholar["participations"]
    )


def test_alphabetical_order_ignores_case_and_surrounding_whitespace_before_pagination(client):
    names = [
        "zebra",
        "  alpha  ",
        "BETA",
        "Alpha",
        "charlie",
        "  DELTA",
        "echo",
        "Foxtrot",
        "golf",
        "hotel",
        "india",
        "JULIET",
        "Élodie",
        " éLODIE ",
    ]
    with main.SessionLocal() as db:
        rows = [Scholar(name=name) for name in names]
        db.add_all(rows)
        db.commit()
        expected = [
            item.id
            for item in sorted(rows, key=lambda item: (item.name.strip().casefold(), item.id))
        ]
    listing = client.get("/api/v1/fsdp").json()
    assert [item["id"] for item in listing] == expected
    page_one = client.get("/api/v1/fsdp/page?page_size=10&page=1").json()
    page_two = client.get("/api/v1/fsdp/page?page_size=10&page=2").json()
    assert page_one["total"] == page_two["total"] == len(names)
    assert [item["id"] for item in page_one["items"]] == expected[:10]
    assert [item["id"] for item in page_two["items"]] == expected[10:]
    assert [item["id"] for item in client.get("/api/v1/fsdp/report").json()["items"]] == expected
    directory_rows = list(
        csv.DictReader(
            StringIO(client.get("/api/v1/maintenance/exports/fsdp.csv").text.lstrip("\ufeff"))
        )
    )
    assert [int(item["Scholar ID"]) for item in directory_rows] == expected
    report_rows = list(
        csv.reader(StringIO(client.get("/api/v1/fsdp/report.csv").text.lstrip("\ufeff")))
    )
    start = next(index for index, row in enumerate(report_rows) if row and row[0] == "Name") + 1
    assert [row[0] for row in report_rows[start:]] == [item["name"] for item in listing]
    # Listing and exporting never normalize stored names as a side effect.
    with main.SessionLocal() as db:
        assert list(db.scalars(select(Scholar.name).order_by(Scholar.id))) == names


def test_schema_fourteen_preserves_thirteen_records_ids_and_recovery_snapshot(tmp_path):
    path = tmp_path / "office.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        upgrade_database(engine, path)
        with engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=14")
            for column in ("has_hard_copy", "has_soft_copy"):
                connection.exec_driver_sql(f"ALTER TABLE scholars DROP COLUMN {column}")
            for column in ("program_category", "application_key"):
                connection.exec_driver_sql(f"ALTER TABLE fsdp_participations DROP COLUMN {column}")
            connection.exec_driver_sql(
                "INSERT INTO scholars(id,name,revision,missing_requirements,data_source,created_at,updated_at) VALUES(81,'Historical office scholar',6,0,'Cathedra','2021-01-02','2024-03-04')"
            )
            connection.exec_driver_sql(
                "INSERT INTO programs(id,name,revision,canonical_key) VALUES(23,'Historical study',4,'historical study')"
            )
            connection.exec_driver_sql(
                "INSERT INTO fsdp_participations(id,scholar_id,program_id,status,case_status,start_academic_year,start_term,remarks) VALUES(92,81,23,'Completed','Closed','2021-2022','Summer','ORIGINAL NOTE')"
            )
            before_scholar = tuple(
                connection.exec_driver_sql(
                    "SELECT id,name,revision,created_at,updated_at FROM scholars"
                ).one()
            )
            before_grant = tuple(
                connection.exec_driver_sql(
                    "SELECT id,scholar_id,program_id,status,case_status,start_academic_year,start_term,remarks FROM fsdp_participations"
                ).one()
            )
        snapshot = upgrade_database(engine, path)
        assert snapshot is not None
        with sqlite3.connect(snapshot) as original:
            assert original.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (
                13,
            )
            assert "has_hard_copy" not in {
                row[1] for row in original.execute("PRAGMA table_info(scholars)")
            }
            assert "application_key" not in {
                row[1] for row in original.execute("PRAGMA table_info(fsdp_participations)")
            }
        with engine.connect() as connection:
            assert (
                tuple(
                    connection.exec_driver_sql(
                        "SELECT id,name,revision,created_at,updated_at FROM scholars"
                    ).one()
                )
                == before_scholar
            )
            assert (
                tuple(
                    connection.exec_driver_sql(
                        "SELECT id,scholar_id,program_id,status,case_status,start_academic_year,start_term,remarks FROM fsdp_participations"
                    ).one()
                )
                == before_grant
            )
            assert tuple(
                connection.exec_driver_sql("SELECT has_hard_copy,has_soft_copy FROM scholars").one()
            ) == (None, None)
            assert tuple(
                connection.exec_driver_sql(
                    "SELECT program_category,application_key FROM fsdp_participations"
                ).one()
            ) == (None, None)
            assert (
                connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar()
                == MIGRATIONS[-1][0]
            )
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert upgrade_database(engine, path) is None
    finally:
        engine.dispose()
