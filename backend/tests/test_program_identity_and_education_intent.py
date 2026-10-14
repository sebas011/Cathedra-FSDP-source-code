from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.fsdp import create_program
from app.db import Base, get_db
from app.graduated_education import graduation_evidence
from app.main import app
from app.migrations import run_migrations
from app.models import Program
from app.program_identity import program_key
from app.schemas import ProgramCreate
from app.upgrade import upgrade_database


def create(client, **fields):
    response = client.post("/api/v1/fsdp", json={"name": "Synthetic scholar", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def update(client, row, **fields):
    grants = [{**grant, "program_name": grant["name"]} for grant in row["participations"]]
    return client.put(f"/api/v1/fsdp/{row['id']}", headers={"If-Match": str(row["revision"])},
                      json={"name": row["name"], "participations": grants,
                            "requirements": row["requirements"], **fields})


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_explicit_year_clear_survives_current_and_future_sync(client, cleared):
    row = create(client, participations=[{"program_name": "Doctor of Education", "remarks": "Graduated in 2022"}])
    entry = row["education"][0]
    assert entry["graduation_year"] == "2022"
    saved = update(client, row, education=[{**entry, "graduation_year": cleared}])
    assert saved.status_code == 200, saved.text
    assert not saved.json()["education"][0]["graduation_year"]
    saved_again = update(client, saved.json(), profile_remarks="An unrelated correction")
    assert saved_again.status_code == 200
    assert not saved_again.json()["education"][0]["graduation_year"]
    assert saved_again.json()["education"][0]["source_program_id"] == entry["source_program_id"]
    current = saved_again.json()
    changed_remarks = [{**grant, "program_name": grant["name"], "remarks": "Graduated in 2023"}
                       for grant in current["participations"]]
    resubmitted = update(client, current, education=current["education"], participations=changed_remarks)
    assert resubmitted.status_code == 200, resubmitted.text
    assert not resubmitted.json()["education"][0]["graduation_year"]


@pytest.mark.parametrize("unchanged_blank", [None, "", "   "])
def test_unchanged_inferred_blank_accepts_new_evidence_on_full_form_resubmission(client, unchanged_blank):
    row = create(client, participations=[{"program_name": "Doctor of Education", "status": "Graduated"}])
    entry = row["education"][0]
    assert entry["graduation_year"] is None
    dated_grants = [{**grant, "program_name": grant["name"], "remarks": "Graduated in 2022"}
                    for grant in row["participations"]]
    saved = update(client, row, education=[{**entry, "graduation_year": unchanged_blank}],
                   participations=dated_grants)
    assert saved.status_code == 200, saved.text
    assert saved.json()["education"][0]["graduation_year"] == "2022"


def test_omitted_year_preserved_and_manual_nonblank_correction_survives(client):
    row = create(client, participations=[{"program_name": "Doctor of Education", "remarks": "Graduated in 2022"}])
    entry = row["education"][0]
    omitted = {key: value for key, value in entry.items() if key != "graduation_year"}
    saved = update(client, row, education=[omitted])
    assert saved.status_code == 200
    assert saved.json()["education"][0]["graduation_year"] == "2022"
    corrected = update(client, saved.json(), education=[{**entry, "graduation_year": "Unknown year"}])
    assert corrected.status_code == 200
    assert update(client, corrected.json()).json()["education"][0]["graduation_year"] == "UNKNOWN YEAR"


def test_education_removal_restore_still_regenerates_evidence(client):
    row = create(client, participations=[{"program_name": "Doctor of Education", "remarks": "Graduated in 2022"}])
    program_id = row["participations"][0]["program_id"]
    removed = update(client, row, education=[]).json()
    assert removed["education"] == []
    assert update(client, removed).json()["education"] == []
    current = client.get(f"/api/v1/fsdp/{row['id']}").json()
    restored = update(client, current, restore_education_program_ids=[program_id])
    assert restored.status_code == 200
    assert restored.json()["education"][0]["graduation_year"] == "2022"


@pytest.mark.parametrize("equivalent", ["Master of Éducation", "master OF éducation", "Master of E\u0301ducation"])
def test_unicode_program_resolution_reuses_identity(client, equivalent):
    original = client.post("/api/v1/fsdp/programs", json={"name": "Master of Éducation"}).json()
    row = create(client, participations=[{"program_name": equivalent, "start_term": "Summer"}])
    assert row["participations"][0]["program_id"] == original["id"]
    assert row["participations"][0]["start_term"] == "Summer"
    assert len(client.get("/api/v1/fsdp/programs").json()) == 1
    assert client.post("/api/v1/fsdp/programs", json={"name": equivalent}).status_code == 409


def test_unicode_key_uses_compatibility_casefold_and_whitespace():
    assert program_key("  Ｍａｓｔｅｒ\tOF  Éducation ") == program_key("master of e\u0301ducation")
    assert program_key("Straße") == program_key("STRASSE")
    assert program_key("Education") != program_key("Éducation")


def test_catalog_race_returns_one_identity_and_clean_conflict(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}", connect_args={"timeout": 10})
    Base.metadata.create_all(engine)
    gate = Barrier(2)

    class ConcurrentSession(Session):
        def commit(self):
            gate.wait(timeout=5)
            return super().commit()

    def submit(name):
        with ConcurrentSession(engine, autoflush=False) as db:
            try:
                program = create_program(ProgramCreate(name=name), db, None)
                return 201, program.id
            except HTTPException as error:
                return error.status_code, error.detail

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = list(workers.map(submit, ["Master of Éducation", "master of éducation"]))
        assert sorted(status for status, _ in responses) == [201, 409]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Program)) == 1
    finally:
        engine.dispose()


def test_implicit_insert_conflict_rolls_back_scholar_instead_of_server_error(client, monkeypatch):
    client.post("/api/v1/fsdp/programs", json={"name": "Shared"})
    # Another request can commit after the lookup. Force precisely that stale
    # lookup while leaving the real unique constraint and save path in place.
    monkeypatch.setattr("app.api.fsdp.matching_programs", lambda db, name: [])
    response = client.post("/api/v1/fsdp", json={"name": "Not committed", "participations": [{"program_name": "shared"}]})
    assert response.status_code == 409
    assert "another request" in response.json()["detail"]
    assert client.get("/api/v1/fsdp").json() == []


def test_conflicting_program_insert_rolls_back_education_and_revision(client, monkeypatch):
    row = create(client, participations=[{"program_name": "Doctor of Education", "remarks": "Graduated in 2022"}])
    client.post("/api/v1/fsdp/programs", json={"name": "Shared"})
    monkeypatch.setattr("app.api.fsdp.matching_programs", lambda db, name: [])
    response = update(client, row,
                      education=[{**row["education"][0], "graduation_year": None}],
                      participations=[{"program_name": "shared"}])
    assert response.status_code == 409
    current = client.get(f"/api/v1/fsdp/{row['id']}").json()
    assert current["revision"] == row["revision"]
    assert current["education"] == row["education"]
    assert current["participations"] == row["participations"]


def test_migration_preserves_colliding_ids_names_history_and_years(tmp_path, monkeypatch):
    import app.migrations as migrations

    # Exercise migration 12 independently; the following migration deliberately
    # changes the legacy Graduated outcome to Completed.
    monkeypatch.setattr(migrations, "MIGRATIONS", [item for item in migrations.MIGRATIONS if item[0] <= 12])
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            run_migrations(connection)
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version=12")
            connection.exec_driver_sql("DROP INDEX uq_programs_canonical_key")
            connection.exec_driver_sql("ALTER TABLE programs DROP COLUMN canonical_key")
            connection.exec_driver_sql("ALTER TABLE scholar_education DROP COLUMN graduation_year_manual")
            connection.exec_driver_sql("INSERT INTO programs(id,name,revision) VALUES(1,'Shared',7),(2,'shared',4),(3,'Master of Éducation',2)")
            connection.exec_driver_sql("INSERT INTO scholars(id,name,revision,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Old scholar',9,0,'Cathedra','2020-01-02','2021-02-03')")
            connection.exec_driver_sql("INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_term,remarks) VALUES(1,1,2,'Graduated','Summer','Private historical note')")
            connection.exec_driver_sql("INSERT INTO scholar_education(id,scholar_id,source_program_id,level,degree,institution,graduation_year) VALUES(1,1,2,'Master’s','Manual correction','Original HEI',NULL)")
            before = connection.exec_driver_sql("SELECT id,name,revision FROM programs ORDER BY id").all()
            grant_before = connection.exec_driver_sql("SELECT * FROM fsdp_participations").all()
            scholar_before = connection.exec_driver_sql("SELECT * FROM scholars").all()
            run_migrations(connection)
            assert connection.exec_driver_sql("SELECT id,name,revision FROM programs ORDER BY id").all() == before
            assert connection.exec_driver_sql("SELECT * FROM fsdp_participations").all() == grant_before
            assert connection.exec_driver_sql("SELECT * FROM scholars").all() == scholar_before
            assert connection.exec_driver_sql("SELECT canonical_key FROM programs ORDER BY id").all() == [(None,), (None,), (program_key("Master of Éducation"),)]
            assert connection.exec_driver_sql("SELECT degree,institution,graduation_year,graduation_year_manual FROM scholar_education").one() == ("Manual correction", "Original HEI", None, 0)
            run_migrations(connection)
            assert connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == 12
    finally:
        engine.dispose()


@pytest.mark.parametrize("previous_version", [5, 10, 11])
def test_populated_old_schema_upgrades_through_current_orm_and_retains_snapshot(tmp_path, previous_version):
    import sqlite3

    path = tmp_path / "old-office.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        upgrade_database(engine, path)
        with engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>?", (previous_version,))
            connection.exec_driver_sql("DROP INDEX uq_programs_canonical_key")
            connection.exec_driver_sql("ALTER TABLE programs DROP COLUMN canonical_key")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN graduation_date")
            connection.exec_driver_sql("ALTER TABLE fsdp_participations DROP COLUMN case_status")
            if previous_version == 5:
                connection.exec_driver_sql("DROP TABLE scholar_education")
            else:
                connection.exec_driver_sql("ALTER TABLE scholar_education DROP COLUMN graduation_year_manual")
            connection.exec_driver_sql("INSERT INTO programs(id,name,revision) VALUES(1,'Master of Arts in Education',3)")
            connection.exec_driver_sql("INSERT INTO scholars(id,name,revision,department,personnel_type,previous_degree,missing_requirements,data_source,created_at,updated_at) VALUES(1,'Old scholar',8,'CAS','Faculty','Bachelor of Arts',0,'Cathedra','2000-01-02','2001-02-03')")
            connection.exec_driver_sql("INSERT INTO fsdp_participations(id,scholar_id,program_id,status,start_term,remarks) VALUES(1,1,1,'On Going','Summer','Graduated with Master of Arts in Education in 2022')")
            grant_columns = ",".join(row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)"))
            grant_before = connection.exec_driver_sql(f"SELECT {grant_columns} FROM fsdp_participations").one()
        snapshot = upgrade_database(engine, path)
        assert snapshot and snapshot.is_file()
        with sqlite3.connect(snapshot) as database:
            assert database.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (previous_version,)
            assert "canonical_key" not in {row[1] for row in database.execute("PRAGMA table_info(programs)")}
        with engine.connect() as connection:
            assert connection.exec_driver_sql(f"SELECT {grant_columns} FROM fsdp_participations").one() == grant_before
            assert connection.exec_driver_sql("SELECT graduation_date,case_status FROM fsdp_participations").one() == (None, "Open")
            assert connection.exec_driver_sql("SELECT id,name,revision,canonical_key FROM programs").one() == (
                1, "Master of Arts in Education", 3, program_key("Master of Arts in Education"))
            assert connection.exec_driver_sql("SELECT name,updated_at FROM scholars").one() == ("Old scholar", "2001-02-03")
            assert connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == 13
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            if previous_version < 11:
                assert connection.exec_driver_sql("SELECT graduation_year FROM scholar_education WHERE source_program_id=1").scalar() == "2022"
        assert upgrade_database(engine, path) is None
    finally:
        engine.dispose()


def test_schema_twelve_failure_rolls_back_columns_identity_and_records(tmp_path, monkeypatch):
    import sqlite3

    import app.migrations as migrations

    path = tmp_path / "rollback-office.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        upgrade_database(engine, path)
        with engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=12")
            connection.exec_driver_sql("DROP INDEX uq_programs_canonical_key")
            connection.exec_driver_sql("ALTER TABLE programs DROP COLUMN canonical_key")
            connection.exec_driver_sql("ALTER TABLE scholar_education DROP COLUMN graduation_year_manual")
            connection.exec_driver_sql("INSERT INTO programs(id,name,revision) VALUES(1,'Existing',4)")
            before = connection.exec_driver_sql("SELECT * FROM programs").all()
        version_twelve = next(item for item in migrations.MIGRATIONS if item[0] == 12)
        original = version_twelve[2]

        def fail_after_backfill(connection):
            original(connection)
            raise RuntimeError("Synthetic migration failure")

        monkeypatch.setattr(migrations, "MIGRATIONS", [
            (version, label, fail_after_backfill if version == 12 else migration)
            for version, label, migration in migrations.MIGRATIONS
        ])
        with pytest.raises(RuntimeError, match="Synthetic migration failure"):
            upgrade_database(engine, path)
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT * FROM programs").all() == before
            assert connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar() == 11
            assert "canonical_key" not in {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(programs)")}
            assert "graduation_year_manual" not in {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholar_education)")}
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
        snapshots = list((tmp_path / "backups").glob("*.db"))
        assert len(snapshots) == 1
        with sqlite3.connect(snapshots[0]) as database:
            assert database.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (11,)
            assert database.execute("SELECT name,revision FROM programs").fetchone() == ("Existing", 4)
    finally:
        engine.dispose()


def test_historical_collision_requires_identity_for_new_grants_but_preserves_old_edits(client):
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        db.connection().exec_driver_sql("INSERT INTO programs(name,canonical_key,revision) VALUES('Shared',NULL,0),('shared',NULL,0)")
        db.commit()
    finally:
        generator.close()
    catalog = client.get("/api/v1/fsdp/programs").json()
    assert all(program["identity_conflict"] for program in catalog)
    rejected = client.post("/api/v1/fsdp", json={"name": "Choose identity", "participations": [{"program_name": "SHARED"}]})
    assert rejected.status_code == 409
    selected = catalog[1]
    row = create(client, participations=[{"program_name": selected["name"], "source_program_id": selected["id"]}])
    assert row["participations"][0]["program_id"] == selected["id"]
    assert update(client, row, profile_remarks="Existing grant correction").json()["participations"][0]["program_id"] == selected["id"]
    assert client.post("/api/v1/fsdp/programs", json={"name": "SHARED"}).status_code == 409
    renamed = client.put(f"/api/v1/fsdp/programs/{selected['id']}", headers={"If-Match": "0"}, json={"name": "Reviewed distinct program"})
    assert renamed.status_code == 200
    assert renamed.json()["identity_conflict"] is False
    assert client.get(f"/api/v1/fsdp/{row['id']}").json()["revision"] == row["revision"] + 2


def test_explicit_program_selection_must_match_and_catalog_edit_is_revision_guarded(client):
    program = client.post("/api/v1/fsdp/programs", json={"name": "Existing"}).json()
    response = client.post("/api/v1/fsdp", json={"name": "Wrong selection", "participations": [{"program_name": "Different", "source_program_id": program["id"]}]})
    assert response.status_code == 409
    assert client.put(f"/api/v1/fsdp/programs/{program['id']}", json={"name": "Existing"}).status_code == 428
    assert client.put(f"/api/v1/fsdp/programs/{program['id']}", headers={"If-Match": "0"}, json={"name": "Renamed"}).status_code == 200
    assert client.put(f"/api/v1/fsdp/programs/{program['id']}", headers={"If-Match": "0"}, json={"name": "Stale"}).status_code == 409


@pytest.mark.parametrize(("remarks", "program", "expected"), [
    ("Graduated with Master of Arts in Education", "Master of Arts in Education", (True, None)),
    ("Graduated with Master of Arts in Education in 2022", "Master of Arts in Education", (True, "2022")),
    ("Graduated with Master of Arts in Education", "Master of Arts in History", (False, None)),
    ("Graduated with Master of Arts in Education in 2027", "Master of Arts in Education", (False, None)),
    ("Graduated with Master of Arts in Education on 02/31/2022", "Master of Arts in Education", (False, None)),
    ("Expected to graduate with Master of Arts in Education", "Master of Arts in Education", (False, None)),
])
def test_qualification_prepositions_are_not_assumed_to_be_dates(remarks, program, expected):
    assert graduation_evidence(remarks, program, today=date(2026, 10, 10)) == expected
