import hashlib
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, selectinload

from app.auth import require_admin, require_signed_in
from app.backups import backup_operations_lock, make_backup, verify_backup_file
from app.college_classification import affiliation, personnel_type
from app.csv_export import SafeCsvWriter, csv_response
from app.current_grant import current_status, grant_order
from app.db import DB_PATH, get_db
from app.diagnostics import maintenance_history, record_maintenance
from app.fsdp_values import effective_hei, has_missing_requirements
from app.migrations import MIGRATIONS, run_migrations
from app.models import BackupReview, FsdpParticipation, LocalUser, Scholar
from app.product import verify_product
from app.record_text import outcome
from app.restore_recovery import begin_restore, finish_restore, restore_marker_path

router = APIRouter(prefix="/maintenance", tags=["Backup & Export"])
BACKUP_DIR = DB_PATH.parent / "backups"


def backup_files() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            *BACKUP_DIR.glob("cathedra-backup-*.db"),
            *BACKUP_DIR.glob("cathedra-protected-before-*.db"),
        ],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def protected_backup_names(backups: list[Path]) -> set[str]:
    protected = {
        item.name
        for item in backups
        if item.name.startswith(("cathedra-backup-before-restore-", "cathedra-protected-before-"))
        or backup_pin_path(item).exists()
    }
    newest_regular = next(
        (
            item
            for item in backups
            if not item.name.startswith(
                ("cathedra-backup-before-restore-", "cathedra-protected-before-")
            )
        ),
        None,
    )
    if newest_regular is not None:
        protected.add(newest_regular.name)
    return protected


def backup_pin_path(backup: Path) -> Path:
    return backup.with_name(f".{backup.name}.protected")


def selected_backup_file(filename: str) -> Path:
    if (
        filename != Path(filename).name
        or not filename.startswith(("cathedra-backup-", "cathedra-protected-before-"))
        or not filename.endswith(".db")
    ):
        raise HTTPException(status_code=404, detail="The selected backup is not available.")
    selected = (BACKUP_DIR / filename).resolve()
    if selected.parent != BACKUP_DIR.resolve() or not selected.is_file():
        raise HTTPException(status_code=404, detail="The selected backup is not available.")
    return selected


def csv_download(filename: str, headings: list[str], rows: list[list[object | None]]) -> Response:
    output = StringIO(newline="")
    writer = SafeCsvWriter(output)
    writer.writerow(headings)
    writer.writerows(rows)
    return csv_response(output, filename)


@router.get("/status")
def maintenance_status(
    db: Session = Depends(get_db), user: LocalUser = Depends(require_signed_in)
) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as caught:
        raise HTTPException(
            status_code=503, detail="Database connection is unavailable."
        ) from caught

    backups = backup_files()
    latest = backups[0] if backups else None
    protected = protected_backup_names(backups)
    free_bytes = shutil.disk_usage(DB_PATH.parent).free
    backup_storage_bytes = sum(item.stat().st_size for item in backups)
    review = db.scalar(select(BackupReview).order_by(BackupReview.id.desc()).limit(1))
    return {
        "database_status": "healthy",
        "database_file": DB_PATH.name,
        "database_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "fsdp_records": db.scalar(select(func.count()).select_from(Scholar)) or 0,
        "backup_count": len(backups),
        "latest_backup_at": datetime.fromtimestamp(latest.stat().st_mtime).astimezone().isoformat()
        if latest
        else None,
        "backup_retention": 14,
        "backup_due": latest is None
        or datetime.now().timestamp() - latest.stat().st_mtime > 7 * 86400,
        "recovery_review": {
            "filename": review.filename,
            "reviewed_at": review.reviewed_at.isoformat(),
            "username": review.username,
            "restore_tested": review.restore_tested,
            "administrator_reported": True,
        }
        if review is not None and user.role == "admin"
        else None,
        "backup_storage_bytes": backup_storage_bytes,
        "free_storage_bytes": free_bytes,
        "storage_warning": free_bytes < max(1024**3, DB_PATH.stat().st_size * 3)
        if DB_PATH.exists()
        else free_bytes < 1024**3,
        "backups": [
            {
                "filename": item.name,
                "created_at": datetime.fromtimestamp(item.stat().st_mtime).astimezone().isoformat(),
                "size_bytes": item.stat().st_size,
                "protected": item.name in protected,
                "pinned": backup_pin_path(item).exists(),
            }
            for item in backups
        ],
    }


class BackupReviewRequest(BaseModel):
    copied_off_device: Literal[True]
    restore_tested: bool = False


@router.post("/backups/{filename}/review", status_code=status.HTTP_201_CREATED)
def record_backup_review(
    filename: str,
    payload: BackupReviewRequest,
    db: Session = Depends(get_db),
    user: LocalUser = Depends(require_admin),
) -> dict[str, object]:
    selected = selected_backup_file(filename)
    try:
        verify_backup_file(selected)
        with selected.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
    except (sqlite3.DatabaseError, OSError, ValueError) as caught:
        raise HTTPException(
            status_code=422, detail="Verify this backup before recording a recovery review."
        ) from caught
    review = BackupReview(
        filename=filename,
        backup_sha256=digest,
        username=user.username,
        copied_off_device=True,
        restore_tested=payload.restore_tested,
    )
    db.add(review)
    db.commit()
    record_maintenance(DB_PATH.parent, "Recovery review recorded", user.username, selected.name)
    return {"recorded": True, "administrator_reported": True}


@router.post("/backups", status_code=status.HTTP_201_CREATED)
def create_database_backup(
    db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)
) -> dict[str, object]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = BACKUP_DIR / f"cathedra-backup-{timestamp}.db"

    try:
        make_backup(db.connection().connection.driver_connection, destination)
    except Exception as caught:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unable to create database backup.") from caught

    record_maintenance(DB_PATH.parent, "Backup created", user.username, destination.name)
    return {
        "filename": destination.name,
        "created_at": datetime.now().astimezone().isoformat(),
        "size_bytes": destination.stat().st_size,
    }


@router.get("/backups/{filename}/download")
def download_database_backup(filename: str, _: LocalUser = Depends(require_admin)) -> FileResponse:
    selected = selected_backup_file(filename)
    try:
        verify_backup_file(selected)
    except (sqlite3.DatabaseError, OSError, ValueError) as caught:
        raise HTTPException(
            status_code=422, detail="The selected backup could not be verified for download."
        ) from caught
    return FileResponse(
        selected,
        media_type="application/octet-stream",
        filename=selected.name,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/backups/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database_backup(filename: str, user: LocalUser = Depends(require_admin)) -> Response:
    with backup_operations_lock:
        selected = selected_backup_file(filename)
        if filename in protected_backup_names(backup_files()):
            raise HTTPException(
                status_code=409,
                detail="This backup is protected. The newest regular backup and restore safety copies cannot be deleted here.",
            )
        selected.unlink()
        record_maintenance(DB_PATH.parent, "Backup deleted", user.username, selected.name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/backups/{filename}/protection", status_code=status.HTTP_204_NO_CONTENT)
def protect_database_backup(filename: str, user: LocalUser = Depends(require_admin)) -> Response:
    with backup_operations_lock:
        selected = selected_backup_file(filename)
        backup_pin_path(selected).touch(exist_ok=True)
        record_maintenance(DB_PATH.parent, "Backup protected", user.username, selected.name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/backups/{filename}/protection", status_code=status.HTTP_204_NO_CONTENT)
def unprotect_database_backup(filename: str, user: LocalUser = Depends(require_admin)) -> Response:
    with backup_operations_lock:
        selected = selected_backup_file(filename)
        if selected.name.startswith("cathedra-backup-before-restore-"):
            raise HTTPException(
                status_code=409, detail="Restore safety backups are always protected."
            )
        backup_pin_path(selected).unlink(missing_ok=True)
        record_maintenance(DB_PATH.parent, "Backup unprotected", user.username, selected.name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


class RestoreRequest(BaseModel):
    filename: str


@router.post("/restore")
def restore_database(
    payload: RestoreRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: LocalUser = Depends(require_admin),
) -> dict[str, object]:
    actor_name = user.username
    selected = selected_backup_file(payload.filename)
    staged = BACKUP_DIR / f".restore-stage-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
    # Older snapshots must not make IDs retired since that snapshot reusable.
    identity_floor = db.execute(
        text("SELECT high_water FROM scholar_id_counter WHERE id = 1")
    ).scalar_one()
    try:
        with closing(sqlite3.connect(selected)) as source:
            try:
                verify_product(source)
            except ValueError as caught:
                raise HTTPException(status_code=422, detail=str(caught)) from caught
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise HTTPException(
                    status_code=422, detail="The selected backup could not be verified."
                )
            if source.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise HTTPException(
                    status_code=422, detail="The selected backup has broken record links."
                )
            tables = {
                row[0]
                for row in source.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            if (
                not {
                    "schema_migrations",
                    "scholars",
                    "fsdp_participations",
                    "programs",
                    "scholar_requirements",
                    "local_users",
                    "local_sessions",
                }
                <= tables
            ):
                raise HTTPException(
                    status_code=422, detail="This is not a supported Cathedra backup."
                )
            version = source.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
            if version is None or version > MIGRATIONS[-1][0]:
                raise HTTPException(
                    status_code=422,
                    detail="The backup schema version is not supported by this Cathedra version.",
                )
            with closing(sqlite3.connect(staged)) as staged_target:
                source.backup(staged_target)
        staged_engine = create_engine(f"sqlite:///{staged.as_posix()}")
        try:
            with staged_engine.begin() as connection:
                run_migrations(connection)
        finally:
            staged_engine.dispose()
        with closing(sqlite3.connect(staged)) as verified:
            if verified.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise HTTPException(
                    status_code=422, detail="The migrated backup could not be verified."
                )
            if verified.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise HTTPException(
                    status_code=422, detail="The migrated backup has broken record links."
                )
            verified.execute("DELETE FROM local_sessions")
            verified.execute(
                "UPDATE scholar_id_counter SET high_water = MAX(high_water, ?) WHERE id = 1",
                (identity_floor,),
            )
            verified.commit()
        pre_restore = (
            BACKUP_DIR / f"cathedra-backup-before-restore-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        )
        target = db.connection().connection.driver_connection
        make_backup(target, pre_restore)
        begin_restore(DB_PATH, pre_restore)
        try:
            with closing(sqlite3.connect(staged)) as source:
                source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("Restored database failed integrity verification.")
            if target.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise sqlite3.DatabaseError("Restored database has broken record links.")
            finish_restore(DB_PATH)
        except Exception:
            with closing(sqlite3.connect(pre_restore)) as recovery:
                recovery.backup(target)
            finish_restore(DB_PATH)
            raise
    except HTTPException:
        raise
    except Exception as caught:
        raise HTTPException(
            status_code=500, detail="Unable to restore the selected backup."
        ) from caught
    finally:
        if restore_marker_path(DB_PATH).exists():
            request.app.state.restore_request_gate.recovery_required = True
        staged.unlink(missing_ok=True)
    record_maintenance(DB_PATH.parent, "Database restored", actor_name, selected.name)
    return {"restored_from": selected.name, "safety_backup": pre_restore.name}


@router.get("/exports/fsdp.csv")
def export_fsdp(db: Session = Depends(get_db)) -> Response:
    scholars = (
        db.scalars(
            select(Scholar)
            .options(
                selectinload(Scholar.participations).selectinload(FsdpParticipation.program),
                selectinload(Scholar.requirements),
                selectinload(Scholar.education),
            )
            .order_by(func.name_sort_key(Scholar.name), Scholar.id)
        )
        .unique()
        .all()
    )
    rows: list[list[object | None]] = []
    for scholar in scholars:
        base = [
            scholar.id,
            scholar.name,
            scholar.age,
            " · ".join(item.degree for item in scholar.education),
            has_missing_requirements(scholar),
            affiliation(scholar.department),
            scholar.rank,
            personnel_type(scholar.department),
            current_status(scholar),
            scholar.tenure_years,
            scholar.created_at,
            scholar.updated_at,
            scholar.profile_remarks,
        ]
        if not scholar.participations:
            rows.append(base + [None] * 14)
            continue
        for index, participation in enumerate(sorted(scholar.participations, key=grant_order)):
            rows.append(
                (base if index == 0 else [None] * len(base))
                + [
                    participation.program.name,
                    effective_hei(participation),
                    participation.start_term,
                    participation.start_academic_year,
                    participation.end_term,
                    participation.end_academic_year,
                    participation.contract_completed_on,
                    participation.grant_type,
                    participation.grant_other,
                    outcome(participation.status),
                    participation.extension,
                    participation.remarks,
                    participation.graduation_date,
                    participation.case_status,
                ]
            )
    return csv_download(
        "cathedra-fsdp.csv",
        [
            "Scholar ID",
            "Name",
            "Age",
            "Education Background",
            "Missing Requirements",
            "Department",
            "Rank / position",
            "Personnel Type",
            "Current Scholar Status",
            "Tenure (years)",
            "Created At",
            "Updated At",
            "Profile Remarks",
            "Program",
            "Delivering HEI",
            "Start Term",
            "Start Academic Year",
            "End Term",
            "End Academic Year",
            "Contract Completion Date",
            "Grant Type",
            "Grant Other",
            "Recorded Grant Status",
            "Extension",
            "Remarks",
            "Graduation Date",
            "Case Status",
        ],
        rows,
    )


@router.get("/exports/education.csv")
def export_education(db: Session = Depends(get_db)) -> Response:
    scholars = db.scalars(
        select(Scholar).options(selectinload(Scholar.education)).order_by(Scholar.id)
    ).all()
    return csv_download(
        "cathedra-education.csv",
        ["Scholar ID", "Name", "Education ID", "Level", "Degree", "Institution", "Graduation Year"],
        [
            [
                scholar.id,
                scholar.name,
                item.id,
                item.level,
                item.degree,
                item.institution,
                item.graduation_year,
            ]
            for scholar in scholars
            for item in scholar.education
        ],
    )


@router.get("/history")
def read_maintenance_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: LocalUser = Depends(require_admin),
) -> dict:
    return maintenance_history(DB_PATH.parent, page, page_size)
