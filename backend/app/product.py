import os

PRODUCT = "fsdp"
PRODUCT_NAME = "Cathedra FSDP"
FSDP_TABLES = frozenset({
    "scholars", "scholar_education", "scholar_requirements", "programs", "fsdp_participations",
    "local_users", "local_sessions", "activity_events", "backup_reviews",
    "cathedra_product", "schema_migrations", "scholar_id_counter",
    "sqlite_sequence", "creation_requests", "education_suppressions", "office_logs",
})
if os.environ.get("CATHEDRA_PRODUCT", PRODUCT) != PRODUCT:
    raise RuntimeError("This codebase supports Cathedra FSDP only.")


def verify_product(database, allow_legacy: bool = False) -> None:
    tables = {
        row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "cathedra_product" not in tables:
        raise ValueError(
            "This database has not been prepared for this Cathedra app. Use the verified split migration, not a combined backup."
        )
    identity = database.execute("SELECT product FROM cathedra_product WHERE id=1").fetchone()
    if identity != (PRODUCT,):
        raise ValueError("This database belongs to a different Cathedra app.")
    if not allow_legacy:
        from app.migrations import MIGRATIONS

        history = (
            database.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()
            if "schema_migrations" in tables
            else []
        )
        expected = [(version, name) for version, name, _ in MIGRATIONS]
        if not history or history != expected[: len(history)]:
            raise ValueError("This backup needs offline FSDP conversion before restore.")
        allowed = FSDP_TABLES if history[-1][0] >= 6 else FSDP_TABLES | {"fsdp_records", "fsdp_legacy_fields"}
        if tables - allowed:
            raise ValueError(
                "This backup still contains other-app tables. Convert it before restore."
            )


def bind_empty_database(connection) -> None:
    tables = set(
        connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars()
    )
    if "cathedra_product" in tables:
        identity = connection.exec_driver_sql(
            "SELECT product FROM cathedra_product WHERE id=1"
        ).scalar()
        if identity != PRODUCT:
            raise RuntimeError("This data directory belongs to another Cathedra app.")
        return
    for table in tables - {"sqlite_sequence", "schema_migrations", "scholar_id_counter"}:
        quoted = table.replace('"', '""')
        if connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{quoted}"').scalar():
            raise RuntimeError(
                "Existing combined records need the verified split migration before startup."
            )
    connection.exec_driver_sql(
        "CREATE TABLE cathedra_product (id INTEGER PRIMARY KEY CHECK(id=1), product TEXT NOT NULL)"
    )
    connection.exec_driver_sql(
        "INSERT INTO cathedra_product (id, product) VALUES (1, ?)", (PRODUCT,)
    )
