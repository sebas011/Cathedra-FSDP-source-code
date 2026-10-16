"""Fixed-column education backfill for migrations 11 and 13.

Keep these historical reads and writes independent of mapped model growth.
Only the optional columns introduced in migrations 12/13 are inspected.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy.engine import Connection

from app.graduated_education import graduation_evidence
from app.profile_values import education_level


def sync_historical_education(connection: Connection) -> set[int]:
    """Return changed scholar IDs without altering their revision or timestamps."""
    education_columns = {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scholar_education)")
    }
    grant_columns = {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(fsdp_participations)")
    }
    manual_column = (
        "graduation_year_manual" if "graduation_year_manual" in education_columns else "0"
    )
    date_column = "f.graduation_date" if "graduation_date" in grant_columns else "NULL"
    education = defaultdict(list)
    for row in connection.exec_driver_sql(
        "SELECT id,scholar_id,source_program_id,degree,institution,graduation_year,"
        f"{manual_column} AS graduation_year_manual FROM scholar_education ORDER BY id"
    ).mappings():
        education[row["scholar_id"]].append(dict(row))
    suppressed = set(
        connection.exec_driver_sql("SELECT scholar_id,program_id FROM education_suppressions").all()
    )
    achievements = defaultdict(list)
    for row in connection.exec_driver_sql(
        "SELECT f.id,f.scholar_id,f.program_id,f.status,f.remarks,f.delivering_hei,"
        f"p.name AS program_name,{date_column} AS graduation_date "
        "FROM fsdp_participations f JOIN programs p ON p.id=f.program_id ORDER BY f.id"
    ).mappings():
        evidence, year = graduation_evidence(row["remarks"], row["program_name"])
        if row["graduation_date"] is not None:
            year = str(date.fromisoformat(row["graduation_date"]).year)
        if row["status"].strip().casefold() in {"graduated", "completed"} or evidence:
            achievements[(row["scholar_id"], row["program_id"])].append((row, year))
    changed = set()
    for (scholar_id, program_id), entries in achievements.items():
        if (scholar_id, program_id) in suppressed:
            continue
        latest = max((row for row, _ in entries), key=lambda row: row["id"])
        years = {year for _, year in entries if year}
        year = next(iter(years)) if len(years) == 1 else None
        linked = next(
            (row for row in education[scholar_id] if row["source_program_id"] == program_id), None
        )
        if linked is not None:
            explicit_date = any(row["graduation_date"] is not None for row, _ in entries)
            if (
                not linked["graduation_year_manual"]
                and year
                and (not (linked["graduation_year"] or "").strip() or explicit_date)
                and linked["graduation_year"] != year
            ):
                connection.exec_driver_sql(
                    "UPDATE scholar_education SET graduation_year=? WHERE id=?",
                    (year, linked["id"]),
                )
                linked["graduation_year"] = year
                changed.add(scholar_id)
            continue
        degree = latest["program_name"].strip()
        institution = (latest["delivering_hei"] or "").strip()
        if any(
            row["degree"].strip().casefold() == degree.casefold()
            and row["institution"].strip().casefold() == institution.casefold()
            for row in education[scholar_id]
        ):
            continue
        connection.exec_driver_sql(
            "INSERT INTO scholar_education "
            "(scholar_id,source_program_id,level,degree,institution,graduation_year) "
            "VALUES (?,?,?,?,?,?)",
            (scholar_id, program_id, education_level(degree), degree, institution, year),
        )
        education[scholar_id].append(
            {
                "source_program_id": program_id,
                "degree": degree,
                "institution": institution,
            }
        )
        changed.add(scholar_id)
    return changed
