"""Historical upgrades use their own columns, independent of future ORM mappings."""

import pytest
from sqlalchemy import Column, Integer, MetaData, create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import registry

import app.migrations as migrations
import app.models as models


@pytest.fixture
def historical_connection():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            for statement in (
                "CREATE TABLE scholars (id INTEGER PRIMARY KEY, name TEXT, revision INTEGER "
                "NOT NULL, department TEXT, personnel_type TEXT, profile_remarks TEXT, updated_at TEXT)",
                "CREATE TABLE programs (id INTEGER PRIMARY KEY, name TEXT, revision INTEGER)",
                "CREATE TABLE fsdp_participations (id INTEGER PRIMARY KEY, scholar_id INTEGER, "
                "program_id INTEGER, status TEXT, remarks TEXT, delivering_hei TEXT, start_term TEXT)",
                "CREATE TABLE scholar_education (id INTEGER PRIMARY KEY, scholar_id INTEGER, "
                "source_program_id INTEGER, level TEXT, degree TEXT, institution TEXT, graduation_year TEXT)",
                "CREATE TABLE education_suppressions (scholar_id INTEGER, program_id INTEGER)",
            ):
                connection.exec_driver_sql(statement)
            connection.exec_driver_sql(
                "INSERT INTO scholars VALUES (1,'Historical scholar',7,'CAS','Staff',"
                "'Original note','2001-02-03 04:05:06.123')"
            )
            connection.exec_driver_sql("INSERT INTO programs VALUES (1,'Master of Science',4)")
            connection.exec_driver_sql(
                "INSERT INTO fsdp_participations VALUES "
                "(8,1,1,'Graduated','Graduated in 2022','Original HEI','Summer')"
            )
            yield connection
    finally:
        engine.dispose()


@pytest.mark.parametrize("version", [11, 13])
def test_historical_backfills_do_not_query_future_scholar_mapping(
    historical_connection, monkeypatch, version
):
    connection = historical_connection
    future_table = models.Scholar.__table__.to_metadata(MetaData())
    future_table.append_column(Column("future_profile_marker", Integer))
    mapper_registry = registry()

    class FutureScholar:
        pass

    mapper_registry.map_imperatively(FutureScholar, future_table)
    monkeypatch.setattr(models, "Scholar", FutureScholar)
    monkeypatch.setattr("app.fsdp_reporting.options", lambda: [])
    try:
        # A full mapped SELECT demonstrably requires columns absent in this snapshot.
        with pytest.raises(OperationalError):
            connection.execute(select(FutureScholar)).all()
        migration = next(item[2] for item in migrations.MIGRATIONS if item[0] == version)
        migration(connection)
        assert connection.exec_driver_sql(
            "SELECT name,revision,updated_at FROM scholars"
        ).one() == ("Historical scholar", 8, "2001-02-03 04:05:06.123")
        assert connection.exec_driver_sql(
            "SELECT source_program_id,degree,institution,graduation_year FROM scholar_education"
        ).one() == (1, "Master of Science", "Original HEI", "2022")
        assert connection.exec_driver_sql("SELECT id,revision FROM programs").one() == (1, 4)
        assert connection.exec_driver_sql(
            "SELECT id,start_term FROM fsdp_participations"
        ).one() == (8, "Summer")
        before = connection.exec_driver_sql("SELECT * FROM scholars").all()
        migration(connection)
        assert connection.exec_driver_sql("SELECT * FROM scholars").all() == before
        assert "future_profile_marker" not in {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")
        }
    finally:
        mapper_registry.dispose()


def test_historical_migrations_add_only_their_owned_columns(historical_connection):
    connection = historical_connection
    migrations._graduation_evidence_and_personnel(connection)
    assert "has_hard_copy" not in {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")
    }
    assert "graduation_date" not in {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")
    }
    assert "canonical_key" not in {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(programs)")
    }
    migrations._program_identity_and_education_intent(connection)
    assert "graduation_year_manual" in {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholar_education)")
    }
    migrations._case_completion_and_office_logs(connection)
    grant_columns = {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")
    }
    assert {"graduation_date", "case_status"} <= grant_columns
    assert not {"program_category", "application_key"} & grant_columns
    assert connection.exec_driver_sql(
        "SELECT status,case_status FROM fsdp_participations"
    ).one() == ("Completed", "Open")
    assert connection.exec_driver_sql("SELECT COUNT(*) FROM office_logs").scalar_one() == 0


@pytest.mark.parametrize("previous_version", [10, 12])
def test_fixed_historical_snapshot_runs_ledger_through_fourteen(
    historical_connection, monkeypatch, previous_version
):
    connection = historical_connection
    historical = [item for item in migrations.MIGRATIONS if item[0] <= 14]
    monkeypatch.setattr(migrations, "MIGRATIONS", historical)
    if previous_version == 12:
        migrations._graduation_evidence_and_personnel(connection)
        migrations._program_identity_and_education_intent(connection)
    connection.exec_driver_sql(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY,name TEXT NOT NULL)"
    )
    connection.exec_driver_sql(
        "INSERT INTO schema_migrations (version,name) VALUES (?,?)",
        [(version, name) for version, name, _ in historical if version <= previous_version],
    )
    migrations.run_migrations(connection)
    assert (
        connection.exec_driver_sql("SELECT MAX(version) FROM schema_migrations").scalar_one() == 14
    )
    assert connection.exec_driver_sql(
        "SELECT id,name,revision,updated_at,has_hard_copy,has_soft_copy FROM scholars"
    ).one() == (1, "Historical scholar", 9, "2001-02-03 04:05:06.123", None, None)
    assert connection.exec_driver_sql(
        "SELECT id,scholar_id,program_id,status,remarks,delivering_hei,start_term,"
        "graduation_date,case_status,program_category,application_key FROM fsdp_participations"
    ).one() == (
        8,
        1,
        1,
        "Completed",
        "Graduated in 2022",
        "Original HEI",
        "Summer",
        None,
        "Open",
        None,
        None,
    )
    before = connection.exec_driver_sql("SELECT * FROM scholars").all()
    migrations.run_migrations(connection)
    assert connection.exec_driver_sql("SELECT * FROM scholars").all() == before


def test_office_log_historical_ddl_does_not_follow_future_model(historical_connection, monkeypatch):
    class FutureOfficeLog:
        __table__ = None

    monkeypatch.setattr(models, "OfficeLog", FutureOfficeLog)
    connection = historical_connection
    migrations._case_completion_and_office_logs(connection)
    assert {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(office_logs)")} == {
        "id",
        "scholar_id",
        "scholar_name",
        "user_id",
        "username",
        "request_key",
        "payload_digest",
        "occurred_on",
        "created_at",
        "entry_type",
        "note",
        "document_name",
        "from_department",
        "to_department",
    }
    assert {row[1] for row in connection.exec_driver_sql("PRAGMA index_list(office_logs)")} == {
        "ix_office_logs_scholar_id",
        "ix_office_logs_occurred_id",
        "uq_office_logs_user_request",
    }


@pytest.mark.parametrize(
    "manual,stored,explicit,expected",
    [
        (0, None, None, "2022"),
        (0, "2020", None, "2020"),
        (0, "2020", "2024-06-01", "2024"),
        (1, None, "2024-06-01", None),
        (1, "Corrected year", "2024-06-01", "Corrected year"),
    ],
)
def test_frozen_education_preserves_manual_year_intent(
    historical_connection, manual, stored, explicit, expected
):
    from app.historical_education import sync_historical_education

    connection = historical_connection
    connection.exec_driver_sql(
        "ALTER TABLE scholar_education ADD COLUMN graduation_year_manual BOOLEAN NOT NULL DEFAULT 0"
    )
    connection.exec_driver_sql("ALTER TABLE fsdp_participations ADD COLUMN graduation_date DATE")
    connection.exec_driver_sql("UPDATE fsdp_participations SET graduation_date=?", (explicit,))
    connection.exec_driver_sql(
        "INSERT INTO scholar_education VALUES (20,1,1,'Manual level','Manual degree',"
        "'Manual institution',?,?)",
        (stored, manual),
    )
    before = connection.exec_driver_sql("SELECT * FROM scholars").all()
    changed = sync_historical_education(connection)
    assert changed == ({1} if expected != stored else set())
    assert connection.exec_driver_sql("SELECT * FROM scholar_education").one() == (
        20,
        1,
        1,
        "Manual level",
        "Manual degree",
        "Manual institution",
        expected,
        manual,
    )
    assert connection.exec_driver_sql("SELECT * FROM scholars").all() == before
    assert sync_historical_education(connection) == set()


def test_frozen_education_repeated_programs_suppressions_and_deduplication(historical_connection):
    from app.historical_education import sync_historical_education

    connection = historical_connection
    connection.exec_driver_sql(
        "INSERT INTO programs VALUES (2,'Suppressed',0),(3,'Existing manual degree',0),(4,'Uncertain',0)"
    )
    connection.exec_driver_sql(
        "INSERT INTO fsdp_participations VALUES "
        "(9,1,1,'Completed','Graduated in 2023','Latest HEI','Summer'),"
        "(10,1,2,'Completed','Graduated in 2021','HEI','Summer'),"
        "(11,1,3,'Completed',NULL,' Same HEI ','Summer'),"
        "(12,1,4,'On Going','Expected graduation year: 2022','HEI','Summer')"
    )
    connection.exec_driver_sql("INSERT INTO education_suppressions VALUES (1,2)")
    connection.exec_driver_sql(
        "INSERT INTO scholar_education VALUES (50,1,NULL,'Manual level',"
        "' existing MANUAL degree ','same hei','Manual year')"
    )
    assert sync_historical_education(connection) == {1}
    assert connection.exec_driver_sql(
        "SELECT source_program_id,degree,institution,graduation_year FROM scholar_education ORDER BY id"
    ).all() == [
        (None, " existing MANUAL degree ", "same hei", "Manual year"),
        (1, "Master of Science", "Latest HEI", None),
    ]
    assert sync_historical_education(connection) == set()
