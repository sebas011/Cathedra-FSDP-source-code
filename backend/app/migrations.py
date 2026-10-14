import sqlite3

from sqlalchemy.engine import Connection

from app.db import Base


def _baseline(connection) -> None:
    Base.metadata.create_all(bind=connection)


def _participation_institutions(connection) -> None:
    connection.exec_driver_sql(
        "UPDATE fsdp_participations SET delivering_hei = "
        "(SELECT delivering_hei FROM programs WHERE programs.id = fsdp_participations.program_id) "
        "WHERE COALESCE(TRIM(delivering_hei), '') = '' "
        "AND EXISTS (SELECT 1 FROM programs WHERE programs.id = fsdp_participations.program_id "
        "AND COALESCE(TRIM(programs.delivering_hei), '') != '')"
    )


def _record_quality(connection) -> None:
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(activity_events)")}
    if "subject_scholar_id" not in columns:
        connection.exec_driver_sql("ALTER TABLE activity_events ADD COLUMN subject_scholar_id INTEGER")
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_activity_events_subject_scholar_id "
        "ON activity_events(subject_scholar_id)"
    )
    connection.exec_driver_sql(
        "UPDATE activity_events SET subject_scholar_id = record_id "
        "WHERE record_type = 'scholars' AND subject_scholar_id IS NULL"
    )
    for table in ("fsdp_participations", "scholar_requirements"):
        connection.exec_driver_sql(
            f"UPDATE activity_events SET subject_scholar_id = "
            f"(SELECT scholar_id FROM {table} WHERE {table}.id = activity_events.record_id) "
            "WHERE record_type = ? AND subject_scholar_id IS NULL", (table,)
        )
    Base.metadata.tables["backup_reviews"].create(connection, checkfirst=True)


def seed_scholar_counter(connection: Connection | sqlite3.Connection) -> None:
    execute = getattr(connection, "exec_driver_sql", connection.execute)
    execute(
        "UPDATE scholar_id_counter SET high_water = MAX(high_water, "
        "COALESCE((SELECT MAX(id) FROM scholars), 0), "
        "COALESCE((SELECT MAX(subject_scholar_id) FROM activity_events), 0), "
        "COALESCE((SELECT MAX(record_id) FROM activity_events "
        "WHERE record_type = 'scholars'), 0)) WHERE id = 1"
    )


def _integrity_guards(connection: Connection) -> None:
    if connection.exec_driver_sql(
        "SELECT 1 FROM local_users GROUP BY lower(username) HAVING COUNT(*) > 1 LIMIT 1"
    ).first():
        raise RuntimeError(
            "Case-equivalent local usernames require offline administrator review "
            "before upgrading. No accounts have been renamed or merged."
        )
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_local_users_username_lower "
        "ON local_users(lower(username))"
    )
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS scholar_id_counter "
        "(id INTEGER PRIMARY KEY CHECK(id = 1), high_water INTEGER NOT NULL "
        "CHECK(high_water >= 0))"
    )
    connection.exec_driver_sql(
        "INSERT OR IGNORE INTO scholar_id_counter (id, high_water) VALUES (1, 0)"
    )
    seed_scholar_counter(connection)
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS track_scholar_identity AFTER INSERT ON scholars "
        "BEGIN UPDATE scholar_id_counter SET high_water = MAX(high_water, NEW.id) "
        "WHERE id = 1; END"
    )


def _scholar_namesakes(connection: Connection) -> None:
    connection.exec_driver_sql("DROP INDEX IF EXISTS uq_scholars_name")


def _profile_and_dashboard(connection: Connection) -> None:
    from app.models import ScholarEducation
    from app.profile_values import education_level, tenure_in_years
    from app.schemas import normalize_term

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")}
    for name, sql_type in (("tenure_years", "FLOAT"), ("tenure_note", "TEXT")):
        if name not in columns:
            connection.exec_driver_sql(f"ALTER TABLE scholars ADD COLUMN {name} {sql_type}")
    ScholarEducation.__table__.create(connection, checkfirst=True)
    for row in connection.exec_driver_sql("SELECT id, previous_degree, tenure, tenure_years, tenure_note FROM scholars ORDER BY id").mappings().all():
        degree = (row["previous_degree"] or "").strip()
        if degree and not connection.exec_driver_sql("SELECT 1 FROM scholar_education WHERE scholar_id=? LIMIT 1", (row["id"],)).first():
            connection.exec_driver_sql("INSERT INTO scholar_education (scholar_id, level, degree, institution) VALUES (?, ?, ?, '')", (row["id"], education_level(degree), degree))
        if row["tenure_years"] is None:
            years = tenure_in_years(row["tenure"])
            note = row["tenure_note"] or (row["tenure"] if years is None else None)
            connection.exec_driver_sql("UPDATE scholars SET tenure_years=?, tenure_note=? WHERE id=?", (years, note, row["id"]))
    for row in connection.exec_driver_sql("SELECT id, start_term, end_term, remarks FROM fsdp_participations").mappings().all():
        notes = []
        values = []
        for field in ("start_term", "end_term"):
            raw = row[field]
            normalized = normalize_term(raw)
            if raw and raw.strip() and normalized is None:
                notes.append(f"Recorded {field.replace('_', ' ')}: {raw}")
            values.append(normalized)
        remarks = "\n".join([part for part in [row["remarks"], *notes] if part]) or None
        connection.exec_driver_sql("UPDATE fsdp_participations SET start_term=?, end_term=?, remarks=? WHERE id=?", (*values, remarks, row["id"]))
    grant_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")}
    for name in ("legacy_grant_label", "grant_standardized_at", "grant_standardization_note"):
        if name in grant_columns:
            connection.exec_driver_sql(f"ALTER TABLE fsdp_participations DROP COLUMN {name}")
    for table in ("fsdp_records", "fsdp_legacy_fields"):
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")


def _contract_completion(connection: Connection) -> None:
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")}
    if "contract_completed_on" not in columns:
        connection.exec_driver_sql("ALTER TABLE fsdp_participations ADD COLUMN contract_completed_on DATE")


def _explicit_profiles_and_education(connection: Connection) -> None:
    from app.profile_values import education_level
    scholar_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")}
    if "personnel_type" not in scholar_columns:
        connection.exec_driver_sql("ALTER TABLE scholars ADD COLUMN personnel_type VARCHAR(20)")
    education_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholar_education)")}
    if "source_program_id" not in education_columns:
        connection.exec_driver_sql("ALTER TABLE scholar_education ADD COLUMN source_program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL")
    entries = connection.exec_driver_sql("SELECT f.scholar_id, f.program_id, p.name, COALESCE(f.delivering_hei, '') FROM fsdp_participations f JOIN programs p ON p.id=f.program_id WHERE lower(trim(f.status))='graduated' ORDER BY f.id DESC").all()
    for scholar_id, program_id, degree, institution in entries:
        degree, institution = degree.strip(), institution.strip()
        existing = connection.exec_driver_sql("SELECT source_program_id, degree, institution FROM scholar_education WHERE scholar_id=?", (scholar_id,)).all()
        if any(origin == program_id or (stored_degree.strip().casefold() == degree.casefold() and stored_institution.strip().casefold() == institution.casefold()) for origin, stored_degree, stored_institution in existing):
            continue
        connection.exec_driver_sql("INSERT INTO scholar_education (scholar_id, source_program_id, level, degree, institution, graduation_year) VALUES (?,?,?,?,?,NULL)", (scholar_id, program_id, education_level(degree), degree, institution))


def _safe_writes(connection: Connection) -> None:
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(programs)")}
    if "revision" not in columns:
        connection.exec_driver_sql("ALTER TABLE programs ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
    for table in ("creation_requests", "education_suppressions"):
        Base.metadata.tables[table].create(connection, checkfirst=True)


def _profile_remarks_and_colleges(connection: Connection) -> None:
    from app.college_classification import affiliation, previous_affiliation_note

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholars)")}
    if "profile_remarks" not in columns:
        connection.exec_driver_sql("ALTER TABLE scholars ADD COLUMN profile_remarks TEXT")
    for row in connection.exec_driver_sql("SELECT id,department,personnel_type,profile_remarks FROM scholars").mappings().all():
        department = affiliation(row["department"])
        personnel = "Staff" if department == "Staff" else row["personnel_type"]
        if department != row["department"] or personnel != row["personnel_type"]:
            connection.exec_driver_sql(
                "UPDATE scholars SET department=?,personnel_type=?,profile_remarks=?,revision=revision+1 WHERE id=?",
                (department, personnel, previous_affiliation_note(row["department"], row["profile_remarks"]), row["id"]),
            )


def _ensure_identity_columns(connection: Connection) -> None:
    # Migration 11 loads the current ORM. Older databases need its newly mapped
    # additive columns before that historical pass; migration 12 owns backfill.
    program_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(programs)")}
    if "canonical_key" not in program_columns:
        connection.exec_driver_sql("ALTER TABLE programs ADD COLUMN canonical_key TEXT")
    education_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholar_education)")}
    if "graduation_year_manual" not in education_columns:
        connection.exec_driver_sql(
            "ALTER TABLE scholar_education ADD COLUMN graduation_year_manual BOOLEAN NOT NULL DEFAULT 0"
        )
    # Historical ORM passes must also be able to load the current grant model.
    participation_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")}
    if "graduation_date" not in participation_columns:
        connection.exec_driver_sql("ALTER TABLE fsdp_participations ADD COLUMN graduation_date DATE")
    if "case_status" not in participation_columns:
        connection.exec_driver_sql("ALTER TABLE fsdp_participations ADD COLUMN case_status VARCHAR(20) NOT NULL DEFAULT 'Open'")


def _graduation_evidence_and_personnel(connection: Connection) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.college_classification import affiliation, personnel_type, previous_affiliation_note
    from app.fsdp_reporting import options
    from app.graduated_education import sync_graduated_education
    from app.models import Scholar

    _ensure_identity_columns(connection)
    # Join the upgrade's transaction; never commit or replace the office DB here.
    timestamps = dict(connection.exec_driver_sql("SELECT id,updated_at FROM scholars").all())
    changed_ids = []
    with Session(bind=connection, join_transaction_mode="rollback_only") as session:
        for scholar in session.scalars(select(Scholar).options(*options())):
            department = affiliation(scholar.department)
            personnel = personnel_type(department)
            changed = department != scholar.department or personnel != scholar.personnel_type
            scholar.profile_remarks = previous_affiliation_note(scholar.department, scholar.profile_remarks)
            scholar.department, scholar.personnel_type = department, personnel
            education_changed = sync_graduated_education(scholar)
            if changed or education_changed:
                scholar.revision += 1
                changed_ids.append(scholar.id)
        session.flush()
        # Preserve the exact stored timestamp, including historical text formatting.
        if changed_ids:
            connection.exec_driver_sql("UPDATE scholars SET updated_at=? WHERE id=?",
                                       [(timestamps[identity], identity) for identity in changed_ids])


def _program_identity_and_education_intent(connection: Connection) -> None:
    from collections import Counter

    from app.program_identity import program_key

    _ensure_identity_columns(connection)
    rows = connection.exec_driver_sql("SELECT id,name FROM programs ORDER BY id").all()
    keys = {identity: program_key(name) for identity, name in rows}
    counts = Counter(keys.values())
    # No program is renamed, merged or reattached. Ambiguous old groups retain
    # every ID with NULL keys until an administrator explicitly reviews them.
    connection.exec_driver_sql("UPDATE programs SET canonical_key=NULL")
    if rows:
        connection.exec_driver_sql(
            "UPDATE programs SET canonical_key=? WHERE id=?",
            [(key if counts[key] == 1 else None, identity) for identity, key in keys.items()],
        )
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_programs_canonical_key ON programs(canonical_key)"
    )


def _case_completion_and_office_logs(connection: Connection) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.fsdp_reporting import options
    from app.graduated_education import sync_graduated_education
    from app.models import OfficeLog, Scholar

    _ensure_identity_columns(connection)
    OfficeLog.__table__.create(connection, checkfirst=True)
    changed_ids = set(connection.exec_driver_sql(
        "SELECT DISTINCT scholar_id FROM fsdp_participations WHERE lower(trim(status))='graduated'"
    ).scalars())
    connection.exec_driver_sql(
        "UPDATE fsdp_participations SET status='Completed' WHERE lower(trim(status))='graduated'"
    )
    timestamps = dict(connection.exec_driver_sql("SELECT id,updated_at FROM scholars").all())
    with Session(bind=connection, join_transaction_mode="rollback_only") as session:
        for scholar in session.scalars(select(Scholar).options(*options())):
            education_changed = sync_graduated_education(scholar)
            if education_changed or scholar.id in changed_ids:
                scholar.revision += 1
                changed_ids.add(scholar.id)
        session.flush()
        if changed_ids:
            connection.exec_driver_sql("UPDATE scholars SET updated_at=? WHERE id=?",
                                       [(timestamps[identity], identity) for identity in changed_ids])


MIGRATIONS = [
    (1, "fsdp-only-baseline", _baseline),
    (2, "participation-institution-attribution", _participation_institutions),
    (3, "scholar-history-and-backup-reviews", _record_quality),
    (4, "non-reusable-scholar-ids-and-unique-usernames", _integrity_guards),
    (5, "separate-scholars-with-identical-names", _scholar_namesakes),
    (6, "education-tenure-terms-and-dashboard", _profile_and_dashboard),
    (7, "optional-contract-completion", _contract_completion),
    (8, "explicit-personnel-and-graduated-education", _explicit_profiles_and_education),
    (9, "safe-writes-and-education-removal", _safe_writes),
    (10, "profile-remarks-and-college-classification", _profile_remarks_and_colleges),
    (11, "graduation-evidence-and-automatic-personnel", _graduation_evidence_and_personnel),
    (12, "unicode-program-identity-and-education-edit-intent", _program_identity_and_education_intent),
    (13, "completed-outcomes-case-status-and-office-logs", _case_completion_and_office_logs),
]


def validate_migration_history(connection) -> None:
    tables = set(
        connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars()
    )
    if "schema_migrations" not in tables:
        return
    versions = set(connection.exec_driver_sql("SELECT version FROM schema_migrations").scalars())
    if versions and versions != set(range(1, max(versions) + 1)):
        raise RuntimeError("The migration history is incomplete.")
    for version, name in connection.exec_driver_sql("SELECT version, name FROM schema_migrations"):
        if (version, name) not in {(number, label) for number, label, _ in MIGRATIONS}:
            raise RuntimeError(
                "This database needs offline FSDP conversion before startup. Its migration history is not supported."
            )


def run_migrations(connection) -> None:
    validate_migration_history(connection)
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    applied = set(connection.exec_driver_sql("SELECT version FROM schema_migrations").scalars())
    if applied and applied != set(range(1, max(applied) + 1)):
        raise RuntimeError("The migration history is incomplete.")
    for version, name, migration in MIGRATIONS:
        if version not in applied:
            migration(connection)
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (version, name)
            )
