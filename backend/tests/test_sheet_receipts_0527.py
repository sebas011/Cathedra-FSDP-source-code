"""Additive import-receipt upgrades use only synthetic local databases."""

import hashlib
import sqlite3
from contextlib import closing

from conftest import remove_shared_schema
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.db import Base
from app.migrations import MIGRATIONS, run_migrations
from app.models import LocalUser, Scholar, SheetImportReceipt
from app.product import bind_empty_database, verify_product
from app.upgrade import upgrade_database
from create_install_seed import PERSONNEL_TABLES, create_install_seed


def test_schema17_receipt_upgrade_preserves_existing_values_history_and_snapshot(tmp_path):
    path = tmp_path / "cathedra.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        bind_empty_database(connection)
        run_migrations(connection)
        remove_shared_schema(connection)
        connection.exec_driver_sql("DROP TABLE sheet_import_receipts")
        connection.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=18")
        connection.exec_driver_sql(
            "INSERT INTO scholars(id,name,revision,missing_requirements,data_source,created_at,updated_at) "
            "VALUES(91,'Mixed Case Existing Scholar',4,0,'Cathedra','2021-01-01','2021-02-01')"
        )
        connection.exec_driver_sql(
            "INSERT INTO activity_events(id,action,area,record_type,record_id,operation,"
            "changed_fields,change_details,subject_scholar_id,created_at) "
            "VALUES(72,'Historical activity','FSDP','scholars',91,'Updated','[\"name\"]',"
            '\'[ {"field":"name","before":"Old","after":"New"} ]\',91,\'2021-02-01\')'
        )
        connection.exec_driver_sql("UPDATE scholar_id_counter SET high_water=91 WHERE id=1")
        names = set(
            connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")
            .scalars()
            .all()
        )
        before = {
            name: connection.exec_driver_sql(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
            for name in names
        }
        columns = {
            name: ",".join(
                row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{name}")')
            )
            for name in names
        }
    try:
        recovery = upgrade_database(engine, path)
        assert recovery and recovery.is_file()
        with closing(sqlite3.connect(path)) as upgraded:
            assert upgraded.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (
                MIGRATIONS[-1][0],
            )
            assert upgraded.execute(
                "SELECT name FROM schema_migrations WHERE version=18"
            ).fetchone() == ("google-sheet-import-receipts",)
            after_names = {
                row[0]
                for row in upgraded.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert after_names == names | {"sheet_import_receipts", "shared_workspace_state"}
            for name, rows in before.items():
                actual = upgraded.execute(
                    f'SELECT {columns[name]} FROM "{name}" ORDER BY rowid'
                ).fetchall()
                if name == "schema_migrations":
                    actual = actual[: len(rows)]
                assert actual == [tuple(row) for row in rows]
            assert upgraded.execute("SELECT COUNT(*) FROM sheet_import_receipts").fetchone() == (0,)
            assert upgraded.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert not upgraded.execute("PRAGMA foreign_key_check").fetchall()
            verify_product(upgraded)
        with closing(sqlite3.connect(recovery)) as snapshot:
            assert snapshot.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (
                17,
            )
            assert not snapshot.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sheet_import_receipts'"
            ).fetchone()
            verify_product(snapshot)
        first_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        assert upgrade_database(engine, path) is None
        assert hashlib.sha256(path.read_bytes()).hexdigest() == first_hash
    finally:
        engine.dispose()


def test_import_receipt_identity_is_scoped_to_account_and_cascades_on_account_removal(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'receipts.db').as_posix()}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            first = LocalUser(
                username="first-import-admin", password_hash="synthetic", role="admin"
            )
            second = LocalUser(
                username="other-import-admin", password_hash="synthetic", role="admin"
            )
            db.add_all([first, second])
            db.flush()
            for user in (first, second):
                db.add(
                    SheetImportReceipt(
                        user_id=user.id,
                        request_key="same-request-key",
                        payload_digest="a" * 64,
                        result_json='{"created":1}',
                    )
                )
            db.add(Scholar(name="Unrelated existing scholar"))
            db.commit()
            assert len(db.scalars(select(SheetImportReceipt)).all()) == 2
            db.execute(delete(LocalUser).where(LocalUser.id == second.id))
            db.commit()
            remaining = db.scalars(select(SheetImportReceipt)).all()
            assert len(remaining) == 1 and remaining[0].user_id == first.id
            assert remaining[0].result_json == '{"created":1}'
            assert db.scalar(select(Scholar.name)) == "Unrelated existing scholar"
    finally:
        engine.dispose()


def test_clean_install_seed_has_empty_import_receipts(tmp_path):
    path = tmp_path / "cathedra-seed.db"
    create_install_seed(path)
    assert "sheet_import_receipts" in PERSONNEL_TABLES
    with closing(sqlite3.connect(path)) as seed:
        assert seed.execute("SELECT COUNT(*) FROM sheet_import_receipts").fetchone() == (0,)
        assert seed.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (
            MIGRATIONS[-1][0],
        )
        verify_product(seed)
