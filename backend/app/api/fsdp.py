import hashlib
import json
from datetime import datetime
from io import StringIO
from types import SimpleNamespace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity_audit import add_activity
from app.auth import require_admin, require_signed_in
from app.backups import snapshot_before_delete
from app.college_classification import (
    affiliation,
    affiliation_expression,
    personnel_type,
    previous_affiliation_note,
)
from app.concurrency import advance_revision
from app.contract_rules import matches_attention
from app.csv_export import SafeCsvWriter, csv_response
from app.current_grant import current_status_expression, grant_order
from app.db import get_db
from app.fsdp_reporting import (
    fsdp_report_data,
    options,
    read_scholar,
    registration_series,
)
from app.graduated_education import sync_graduated_education
from app.grant_applications import has_completed_application_expression
from app.models import (
    CreationRequest,
    EducationSuppression,
    FsdpParticipation,
    LocalUser,
    Program,
    Scholar,
    ScholarEducation,
    ScholarRequirement,
)
from app.name_matches import name_similarity
from app.payback import payback_data
from app.profile_values import education_level, tenure_in_years
from app.program_identity import matching_programs, program_entry_keys, program_key
from app.record_text import edited_text, outcome, uppercase_text
from app.schemas import (
    FsdpSummary,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    ScholarCreate,
    ScholarRead,
    ScholarUpdate,
)
from app.scholar_identity import next_scholar_id

router = APIRouter(prefix="/fsdp", tags=["FSDP"])


@router.get("/name-matches")
def similar_scholars(
    name: str = Query(min_length=3, max_length=200),
    exclude_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    matches = []
    statement = select(Scholar.id, Scholar.name, Scholar.department)
    if exclude_id is not None:
        statement = statement.where(Scholar.id != exclude_id)
    for scholar_id, existing_name, department in db.execute(statement):
        score, reason = name_similarity(name, existing_name)
        if score:
            matches.append(
                {
                    "id": scholar_id,
                    "name": existing_name,
                    "department": affiliation(department),
                    "reason": reason,
                    "score": score,
                }
            )
    return sorted(matches, key=lambda item: (-item["score"], item["id"]))[:8]


def scholar_statement(search: str, status_filter: str, missing: str = ""):
    statement = select(Scholar).options(*options()).distinct()
    if search.strip():
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        term = f"%{escaped}%"
        statement = (
            statement.outerjoin(Scholar.participations)
            .outerjoin(FsdpParticipation.program)
            .where(
                or_(
                    func.name_prefix_matches(Scholar.name, search.strip()) == 1,
                    Scholar.department.ilike(term, escape="\\"),
                    Scholar.rank.ilike(term, escape="\\"),
                    Program.name.ilike(term, escape="\\"),
                    FsdpParticipation.delivering_hei.ilike(term, escape="\\"),
                )
            )
        )
    if status_filter.strip():
        statement = statement.where(current_status_expression() == outcome(status_filter))
    if missing == "personnel_type":
        statement = statement.where(affiliation_expression(Scholar.department) == "Unknown")
    elif missing == "starting_year":
        statement = statement.where(
            Scholar.participations.any(
                or_(
                    FsdpParticipation.start_academic_year.is_(None),
                    func.trim(FsdpParticipation.start_academic_year) == "",
                )
            )
        )
    elif missing == "contract_date":
        statement = statement.where(
            Scholar.participations.any(
                FsdpParticipation.contract_completed_on.is_(None)
                & FsdpParticipation.completion_due_on.is_(None)
                & or_(
                    FsdpParticipation.start_date.is_(None),
                    FsdpParticipation.allowed_duration_years.is_(None),
                )
                & ~func.lower(func.trim(FsdpParticipation.status)).in_(
                    ["graduated", "completed", "did not avail"]
                )
                & ~has_completed_application_expression(FsdpParticipation)
            )
        )
    return statement


def commit_record(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as caught:
        db.rollback()
        import sqlite3

        from app.diagnostics import log_private_exception

        reference = log_private_exception(caught)
        code = getattr(caught.orig, "sqlite_errorcode", None)
        program_conflict = code == sqlite3.SQLITE_CONSTRAINT_UNIQUE and str(caught.orig) in {
            "UNIQUE constraint failed: programs.name",
            "UNIQUE constraint failed: programs.canonical_key",
        }
        detail = (
            "A program with this name already exists. Review the existing program."
            if program_conflict
            else "A linked record changed or no longer exists. Reload the record before saving."
            if code == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY
            else "The record could not be saved because some details conflict with stored data. Reload and review the details before saving."
        )
        raise HTTPException(
            status_code=409,
            detail=f"{detail} Reference: {reference}",
        ) from None


def resolve_program(
    db: Session,
    program_name: str,
    source_program_id: int | None = None,
    existing_program: Program | None = None,
) -> Program:
    normalized_name = program_name.strip()
    if source_program_id is not None:
        selected = db.get(Program, source_program_id)
        if selected is None or not program_entry_keys(selected.name) & program_entry_keys(
            normalized_name
        ):
            raise HTTPException(
                status_code=409,
                detail="The selected program changed. Select it from the catalog again.",
            )
        return selected
    # Old clients editing a historical grant retain its explicit identity when
    # its name is unchanged, even if another old program has an equivalent name.
    if existing_program is not None and program_key(existing_program.name) == program_key(
        normalized_name
    ):
        return existing_program
    matches = matching_programs(db, normalized_name)
    if (
        existing_program is not None
        and program_entry_keys(existing_program.name) & program_entry_keys(normalized_name)
        and all(item.id != existing_program.id for item in matches)
    ):
        # A grant already identifies its historical program. Preserve that
        # identity for its uppercase display spelling, but require selection
        # if that spelling could also identify another historical row.
        matches.append(existing_program)
    if len(matches) > 1:
        raise HTTPException(
            status_code=409,
            detail="Several historical programs use this name. Select the existing program from the catalog.",
        )
    if matches:
        return matches[0]
    stored_name = normalized_name.upper()
    program = Program(name=stored_name, canonical_key=program_key(stored_name))
    db.add(program)
    try:
        # Activity collection observes the whole session. Flush the full unit
        # of work so pending scholars are not audited again on the next flush.
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This program was added by another request. Select it from the catalog and save again.",
        ) from None
    return program


def apply_payload(db: Session, scholar: Scholar, payload: ScholarCreate | ScholarUpdate) -> None:
    existing_participations = {item.id: item for item in scholar.participations}
    existing_requirements = {item.id: item for item in scholar.requirements}
    participation_ids = [item.id for item in payload.participations if item.id is not None]
    requirement_ids = [item.id for item in payload.requirements if item.id is not None]
    if len(participation_ids) != len(set(participation_ids)) or len(requirement_ids) != len(
        set(requirement_ids)
    ):
        raise HTTPException(
            status_code=422, detail="A grant or requirement ID appears more than once."
        )
    if (
        not set(participation_ids) <= existing_participations.keys()
        or not set(requirement_ids) <= existing_requirements.keys()
    ):
        raise HTTPException(
            status_code=409,
            detail="A grant or requirement does not belong to this scholar. Reload before saving.",
        )
    previous_tenure = scholar.tenure
    new_scholar = scholar.created_at is None
    for field, value in payload.model_dump(
        exclude={"participations", "requirements", "education", "restore_education_program_ids"}
    ).items():
        if (
            field
            in {
                "tenure_years",
                "tenure_note",
                "personnel_type",
                "profile_remarks",
                "department",
                "has_hard_copy",
                "has_soft_copy",
            }
            and field not in payload.model_fields_set
        ):
            continue
        if field in {"name", "previous_degree", "rank", "tenure", "tenure_note", "profile_remarks"}:
            value = edited_text(value, getattr(scholar, field), new=new_scholar)
        setattr(scholar, field, value)
    scholar.profile_remarks = previous_affiliation_note(
        scholar.department, scholar.profile_remarks, uppercase_new=True
    )
    scholar.department = affiliation(scholar.department)
    scholar.personnel_type = personnel_type(scholar.department)
    if (
        "tenure_years" not in payload.model_fields_set
        and "tenure" in payload.model_fields_set
        and (
            new_scholar
            or (payload.tenure or "").strip().casefold()
            != (previous_tenure or "").strip().casefold()
        )
    ):
        scholar.tenure_years = tenure_in_years(payload.tenure)
        if "tenure_note" not in payload.model_fields_set:
            scholar.tenure_note = (
                uppercase_text(payload.tenure) if scholar.tenure_years is None else None
            )
    restore_ids = set(payload.restore_education_program_ids)
    suppressed = {item.program_id: item for item in scholar.education_suppressions}
    if not restore_ids <= suppressed.keys():
        raise HTTPException(
            status_code=409, detail="Reload the scholar before restoring education."
        )
    for program_id in restore_ids:
        scholar.education_suppressions.remove(suppressed[program_id])
        add_activity(
            db, "FSDP Education", "Restored automatic education", subject_scholar_id=scholar.id
        )
    if payload.education is not None:
        existing = {item.id: item for item in scholar.education}
        identifiers = [item.id for item in payload.education if item.id is not None]
        if len(identifiers) != len(set(identifiers)) or not set(identifiers) <= existing.keys():
            raise HTTPException(
                status_code=409,
                detail="An education entry does not belong to this scholar or appears more than once.",
            )
        for item in list(scholar.education):
            if item.id not in identifiers:
                if item.source_program_id is not None and item.source_program_id not in suppressed:
                    scholar.education_suppressions.append(
                        EducationSuppression(program_id=item.source_program_id)
                    )
                    suppressed[item.source_program_id] = scholar.education_suppressions[-1]
                    add_activity(
                        db,
                        "FSDP Education",
                        "Removed automatic education",
                        subject_scholar_id=scholar.id,
                    )
                scholar.education.remove(item)
        for item in payload.education:
            entry = existing[item.id] if item.id is not None else ScholarEducation()
            if "graduation_year" in item.model_fields_set:
                year = item.graduation_year
                # Full form submissions resend inferred blanks. A change in
                # the normalized value records intent; resending an unchanged
                # blank permits later evidence, and never clears manual intent.
                if (year or "").strip() != (entry.graduation_year or "").strip():
                    entry.graduation_year_manual = True
            for field, value in item.model_dump(
                exclude={"id"}, exclude_unset=item.id is not None
            ).items():
                if field in {"level", "degree", "institution", "graduation_year"}:
                    value = edited_text(value, getattr(entry, field), new=item.id is None)
                setattr(entry, field, value)
            if item.id is None:
                scholar.education.append(entry)
    elif payload.previous_degree and not scholar.education:
        scholar.education.append(
            ScholarEducation(
                level=education_level(payload.previous_degree).upper(),
                degree=payload.previous_degree.upper(),
                institution="",
            )
        )
    for item in list(scholar.participations):
        if item.id not in participation_ids:
            scholar.participations.remove(item)
    for item in list(scholar.requirements):
        if item.id not in requirement_ids:
            scholar.requirements.remove(item)
    for item in payload.participations:
        participation = (
            existing_participations[item.id] if item.id is not None else FsdpParticipation()
        )
        participation.program = resolve_program(
            db,
            item.program_name,
            item.source_program_id,
            participation.program if item.id is not None else None,
        )
        for field, value in item.model_dump(
            exclude={"id", "program_name", "source_program_id"}
        ).items():
            if (
                field
                in {
                    "start_date",
                    "end_date",
                    "contract_completed_on",
                    "allowed_duration_years",
                    "completion_due_on",
                    "payback_payment_status",
                    "graduation_date",
                    "case_status",
                    "program_category",
                    "application_key",
                }
                and field not in item.model_fields_set
                and item.id is not None
            ):
                continue
            if field in {"delivering_hei", "grant_other", "extension", "remarks"}:
                value = edited_text(value, getattr(participation, field), new=item.id is None)
            setattr(participation, field, value)
        if item.id is None:
            scholar.participations.append(participation)
    for item in payload.requirements:
        requirement = (
            existing_requirements[item.id] if item.id is not None else ScholarRequirement()
        )
        if item.is_complete and not requirement.is_complete:
            requirement.completed_at = datetime.now()
        elif not item.is_complete:
            requirement.completed_at = None
        requirement.requirement_name = edited_text(
            item.requirement_name, requirement.requirement_name, new=item.id is None
        )
        requirement.due_date = item.due_date
        requirement.is_complete = item.is_complete
        requirement.remarks = edited_text(
            item.remarks or None, requirement.remarks, new=item.id is None
        )
        if item.id is None:
            scholar.requirements.append(requirement)
    scholar.missing_requirements = payload.missing_requirements


@router.post("/programs/{program_id}/duplicate", response_model=ProgramRead, status_code=201)
def duplicate_program(
    program_id: int, db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> Program:
    original = db.get(Program, program_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    sequence = 1
    while True:
        name = f"{original.name} (COPY{f' {sequence}' if sequence > 1 else ''})".upper()
        if not matching_programs(db, name):
            break
        sequence += 1
    copy = Program(
        name=name,
        canonical_key=program_key(name),
        delivering_hei=uppercase_text(original.delivering_hei),
        description=uppercase_text(original.description),
    )
    db.add(copy)
    commit_record(db)
    db.refresh(copy)
    return copy


@router.post(
    "/{scholar_id}/grants/{grant_id}/duplicate", response_model=ScholarRead, status_code=201
)
def duplicate_grant(
    scholar_id: int,
    grant_id: int,
    if_match: int | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
) -> ScholarRead:
    scholar = db.scalar(select(Scholar).where(Scholar.id == scholar_id).options(*options()))
    if scholar is None:
        raise HTTPException(status_code=404, detail="Scholar not found.")
    original = next((item for item in scholar.participations if item.id == grant_id), None)
    if original is None:
        raise HTTPException(status_code=404, detail="Grant does not belong to this scholar.")
    advance_revision(db, Scholar, scholar_id, if_match)
    reset_fields = {
        "id",
        "scholar_id",
        "start_date",
        "end_date",
        "contract_completed_on",
        "completion_due_on",
        "payback_payment_status",
        "graduation_date",
        "extension",
        "status",
        "case_status",
    }
    if original.allowed_duration_years is not None or original.completion_due_on is not None:
        # Annual grants share one program application and its recorded deadline.
        # Keep historical copy behavior for old dates without new completion rules.
        reset_fields.difference_update({"start_date", "completion_due_on"})
    copy = FsdpParticipation(
        **{
            column.key: getattr(original, column.key)
            for column in FsdpParticipation.__table__.columns
            if column.key not in reset_fields
        }
    )
    copy.status = "On Going"
    copy.case_status = "Open"
    scholar.participations.append(copy)
    commit_record(db)
    db.refresh(scholar)
    return read_scholar(scholar)


@router.get("/programs", response_model=list[ProgramRead])
def list_programs(db: Session = Depends(get_db)) -> list[Program]:
    return list(db.scalars(select(Program).order_by(Program.name)).all())


@router.post("/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(
    payload: ProgramCreate, db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> Program:
    if matching_programs(db, payload.name):
        raise HTTPException(status_code=409, detail="A program with this name already exists.")
    values = {field: uppercase_text(value) for field, value in payload.model_dump().items()}
    program = Program(**values, canonical_key=program_key(values["name"]))
    db.add(program)
    commit_record(db)
    db.refresh(program)
    return program


@router.put("/programs/{program_id}", response_model=ProgramRead)
def update_program(
    program_id: int,
    payload: ProgramUpdate,
    if_match: int | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
) -> Program:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    matches = [item for item in matching_programs(db, payload.name) if item.id != program_id]
    unchanged_identity = program_key(payload.name) == program_key(program.name)
    if matches and not unchanged_identity:
        raise HTTPException(status_code=409, detail="A program with this name already exists.")
    advance_revision(db, Program, program_id, if_match)
    db.execute(
        update(Scholar)
        .where(
            Scholar.id.in_(
                select(FsdpParticipation.scholar_id).where(
                    FsdpParticipation.program_id == program_id
                )
            )
        )
        .values(revision=Scholar.revision + 1)
        .execution_options(synchronize_session=False)
    )
    for field, value in payload.model_dump().items():
        if field == "name" and matches and unchanged_identity:
            continue
        value = edited_text(value, getattr(program, field))
        setattr(program, field, value)
    stored_key = program_key(program.name)
    # Typed uppercase aliases can match a distinct historical identity. Only
    # actual canonical collisions lose their key; never merge or rekey those
    # distinct rows while saving an unchanged historical program.
    program.canonical_key = (
        None if any(program_key(item.name) == stored_key for item in matches) else stored_key
    )
    commit_record(db)
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(
    program_id: int, db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> Response:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    if db.scalar(
        select(func.count())
        .select_from(FsdpParticipation)
        .where(FsdpParticipation.program_id == program_id)
    ) or db.scalar(
        select(ScholarEducation.id).where(ScholarEducation.source_program_id == program_id).limit(1)
    ):
        raise HTTPException(
            status_code=409, detail="A program with participation history cannot be deleted."
        )
    db.delete(program)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[ScholarRead])
def list_scholars(
    search: str = Query(default=""),
    status_filter: str = Query(default="", alias="status"),
    db: Session = Depends(get_db),
) -> list[ScholarRead]:
    statement = scholar_statement(search, status_filter)
    return [
        read_scholar(scholar)
        for scholar in db.scalars(statement.order_by(func.name_sort_key(Scholar.name), Scholar.id))
        .unique()
        .all()
    ]


@router.get("/page")
def paged_scholars(
    search: str = Query(default=""),
    status_filter: str = Query(default="", alias="status"),
    missing: str = Query(default="", pattern="^(|personnel_type|starting_year|contract_date)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=10, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = scholar_statement(search, status_filter, missing)
    count_statement = statement.with_only_columns(Scholar.id).order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(count_statement)) or 0
    records = (
        db.scalars(
            statement.order_by(func.name_sort_key(Scholar.name), Scholar.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return {
        "items": [read_scholar(scholar) for scholar in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary", response_model=FsdpSummary)
def summary(db: Session = Depends(get_db)) -> FsdpSummary:
    def count(status_value: str) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(Scholar)
                .where(current_status_expression() == status_value)
            )
            or 0
        )

    return FsdpSummary(
        total=db.scalar(select(func.count()).select_from(Scholar)) or 0,
        ongoing=count("On Going"),
        graduated=count("Completed"),
        completed=count("Completed"),
        incomplete=count("Incomplete"),
        payback=count("Payback"),
        withdrawn=count("Withdrawn"),
        did_not_avail=count("Did Not Avail"),
        missing_requirements=db.scalar(
            select(func.count())
            .select_from(Scholar)
            .where(
                or_(
                    Scholar.missing_requirements.is_(True),
                    Scholar.requirements.any(ScholarRequirement.is_complete.is_(False)),
                )
            )
        )
        or 0,
    )


@router.get("/analytics")
def analytics(
    department: str = Query(default=""),
    start_academic_year: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    department_label = affiliation_expression(Scholar.department)
    year_label = func.nullif(func.trim(FsdpParticipation.start_academic_year), "")
    scope = select(Scholar.id)
    if department:
        scope = scope.where(department_label == affiliation(department))
    if start_academic_year:
        scope = scope.where(Scholar.participations.any(year_label == start_academic_year))
    scholar_ids = scope.subquery()
    selected_ids = select(scholar_ids.c.id)
    grant_scope = [FsdpParticipation.scholar_id.in_(selected_ids)]
    if start_academic_year:
        grant_scope.append(year_label == start_academic_year)

    def grant_rows(column, fallback):
        label = func.coalesce(func.nullif(func.trim(column), ""), fallback)
        return [
            {"label": name, "count": count}
            for name, count in db.execute(
                select(label, func.count()).where(*grant_scope).group_by(label).order_by(label)
            )
        ]

    ongoing = (
        db.scalar(
            select(func.count(func.distinct(FsdpParticipation.scholar_id))).where(
                *grant_scope,
                FsdpParticipation.scholar_id.in_(
                    select(Scholar.id).where(current_status_expression() == "On Going")
                ),
            )
        )
        or 0
    )
    follow_up = (
        db.scalar(
            select(func.count())
            .select_from(Scholar)
            .where(
                Scholar.id.in_(selected_ids),
                or_(
                    Scholar.missing_requirements.is_(True),
                    Scholar.requirements.any(ScholarRequirement.is_complete.is_(False)),
                ),
            )
        )
        or 0
    )
    department_group = func.coalesce(department_label, "Unassigned")
    recent = db.scalars(
        select(Scholar)
        .where(Scholar.id.in_(selected_ids))
        .options(*options())
        .order_by(Scholar.created_at.desc(), Scholar.id.desc())
        .limit(10)
    ).all()
    return {
        "payback_summary": payback_data(db, department, start_academic_year, include_items=False)[
            "scholar_counts"
        ],
        "registration_series": registration_series(db, selected_ids),
        "recent_scholars": [read_scholar(item).model_dump(mode="json") for item in recent],
        "scholars": db.scalar(select(func.count()).select_from(scholar_ids)) or 0,
        "grants": db.scalar(select(func.count()).select_from(FsdpParticipation).where(*grant_scope))
        or 0,
        "ongoing_scholars": ongoing,
        "requirements_follow_up": follow_up,
        "statuses": [
            {"label": label, "count": count}
            for label, count in db.execute(
                select(func.coalesce(current_status_expression(), "No grants"), func.count())
                .where(Scholar.id.in_(selected_ids))
                .group_by(current_status_expression())
                .order_by(current_status_expression())
            )
        ],
        "grant_types": grant_rows(FsdpParticipation.grant_type, "Not recorded"),
        "departments": [
            {"label": name, "count": count}
            for name, count in db.execute(
                select(department_group, func.count())
                .where(Scholar.id.in_(selected_ids))
                .group_by(department_group)
                .order_by(department_group)
            )
        ],
        "options": {
            "departments": [
                value
                for value in db.scalars(
                    select(department_label).distinct().order_by(department_label)
                )
                if value
            ],
            "start_academic_years": [
                value
                for value in db.scalars(select(year_label).distinct().order_by(year_label.desc()))
                if value
            ],
        },
    }


@router.get("/payback")
def payback_follow_up(
    department: str = "",
    start_academic_year: str = "",
    attention: str = "",
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    data = payback_data(db, department, start_academic_year)
    rows = [item for item in data["items"] if matches_attention(item["attention"], attention)]
    data.update(total=len(rows), items=rows)
    if page is not None:
        data.update(
            total=len(rows),
            page=page,
            page_size=page_size,
            items=rows[(page - 1) * page_size : page * page_size],
        )
    return data


@router.get("/payback.csv")
def export_payback(
    department: str = "",
    start_academic_year: str = "",
    attention: str = "",
    db: Session = Depends(get_db),
) -> Response:
    data = payback_data(db, department, start_academic_year)
    selected = [item for item in data["items"] if matches_attention(item["attention"], attention)]
    grants = {
        grant.id: grant
        for grant in db.scalars(
            select(FsdpParticipation).where(
                FsdpParticipation.id.in_([item["participation_id"] for item in selected])
            )
        )
    }
    selected.sort(
        key=lambda item: (
            item["scholar_name"].casefold(),
            item["scholar_id"],
            grant_order(
                grants.get(item["participation_id"])
                or SimpleNamespace(
                    start_academic_year=item["academic_year"],
                    start_term=None,
                    id=item["participation_id"],
                )
            ),
        )
    )
    output = StringIO(newline="")
    writer = SafeCsvWriter(output)
    writer.writerow(["Cathedra contract and payback follow-up", "As of", data["as_of"]])
    writer.writerow(
        [
            "Scholar",
            "Scholar ID",
            "Department",
            "Program",
            "Grant ID",
            "Academic year",
            "Recorded status",
            "Contract completed",
            "Grace ends",
            "Follow-up",
            "Program Start Date",
            "Allowed Duration (years)",
            "Allowed Completion Deadline",
            "Effective Completion Deadline",
            "Payback Payment Status",
        ]
    )
    previous_scholar_id = None
    for item in selected:
        profile = [item[key] for key in ("scholar_name", "scholar_id", "department")]
        writer.writerow(
            (profile if item["scholar_id"] != previous_scholar_id else [None] * len(profile))
            + [
                item[key]
                for key in (
                    "program_name",
                    "participation_id",
                    "academic_year",
                    "recorded_status",
                    "contract_completed_on",
                    "grace_ends_on",
                    "attention",
                    "start_date",
                    "allowed_duration_years",
                    "completion_due_on",
                    "completion_deadline_on",
                    "payback_payment_status",
                )
            ]
        )
        previous_scholar_id = item["scholar_id"]
    return csv_response(output, "cathedra-payback-follow-up.csv")


@router.get("/report")
def fsdp_report(
    department: str = Query(default=""),
    rank: str = Query(default=""),
    status_filter: str = Query(default="", alias="status"),
    grant_type: str = Query(default=""),
    delivering_hei: str = Query(default=""),
    missing_requirements: bool = Query(default=False),
    start_academic_year: str = Query(default=""),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    action_page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return fsdp_report_data(
        db,
        page=page,
        page_size=page_size,
        action_page=action_page,
        department=department,
        rank=rank,
        status_filter=status_filter,
        grant_type=grant_type,
        delivering_hei=delivering_hei,
        missing_requirements=missing_requirements,
        start_academic_year=start_academic_year,
    )


@router.get("/report-options")
def report_options(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    def values(column):
        label = func.nullif(func.trim(column), "")
        return [value for value in db.scalars(select(label).distinct().order_by(label)) if value]

    hei = func.nullif(FsdpParticipation.delivering_hei, "")
    heis = db.scalars(
        select(hei)
        .select_from(FsdpParticipation)
        .join(Program, FsdpParticipation.program_id == Program.id)
        .distinct()
        .order_by(hei)
    )
    return {
        "departments": list(
            db.scalars(
                select(affiliation_expression(Scholar.department))
                .distinct()
                .order_by(affiliation_expression(Scholar.department))
            )
        ),
        "ranks": values(Scholar.rank),
        "delivering_heis": [value.strip() for value in heis if value and value.strip()],
        "statuses": sorted({outcome(value) for value in values(FsdpParticipation.status)}),
        "grant_types": values(FsdpParticipation.grant_type),
    }


@router.get("/report.csv")
def export_fsdp_report(
    department: str = Query(default=""),
    rank: str = Query(default=""),
    status_filter: str = Query(default="", alias="status"),
    grant_type: str = Query(default=""),
    delivering_hei: str = Query(default=""),
    missing_requirements: bool = Query(default=False),
    start_academic_year: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    report = fsdp_report_data(
        db,
        department=department,
        rank=rank,
        status_filter=status_filter,
        grant_type=grant_type,
        delivering_hei=delivering_hei,
        missing_requirements=missing_requirements,
        start_academic_year=start_academic_year,
    )
    output = StringIO(newline="")
    writer = SafeCsvWriter(output)
    writer.writerow(["Cathedra FSDP Report"])
    writer.writerow(
        ["Scholars", report["total"], "Missing requirements", report["missing_requirements"]]
    )
    writer.writerow([])
    writer.writerow(
        [
            "Department",
            "Scholars",
            "On-going",
            "Completed",
            "Payback",
            "Withdrawn",
            "Did Not Avail",
            "Transferred",
            "Payback pending contract",
            "Requirements follow-up (scholars)",
            "Incomplete",
        ]
    )
    for item in report["department_totals"]:
        writer.writerow(
            [
                item["department"],
                item["scholars"],
                item["ongoing"],
                item["graduated"],
                item["payback"],
                item["withdrawn"],
                item["did_not_avail"],
                item["transferred"],
                item["payback_pending_contract"],
                item["requirements_follow_up"],
                item["incomplete"],
            ]
        )
    writer.writerow([])
    writer.writerow(["Needs action", "Scholar", "Department", "Detail", "Follow-up"])
    for item in report["action_items"]:
        writer.writerow(
            [
                item["kind"],
                item["scholar_name"],
                item["department"] or "",
                item["detail"],
                item["attention"],
            ]
        )
    writer.writerow([])
    writer.writerow(
        [
            "Name",
            "Rank / position",
            "Department",
            "Age",
            "Tenure (years)",
            "Education background",
            "Current scholar status",
            "Profile Remarks",
            "Program applied",
            "Delivering HEI",
            "Type of grant",
            "Start Term",
            "Start Academic Year",
            "End Term",
            "End Academic Year",
            "Contract Completion Date",
            "Extension",
            "Remarks",
            "Recorded grant status",
            "Graduation Date",
            "Case Status",
            "Program Start Date",
            "Allowed Duration (years)",
            "Allowed Completion Deadline",
            "Effective Completion Deadline",
            "Payback Payment Status",
        ]
    )
    for scholar in report["items"]:
        profile = [
            scholar.name,
            scholar.rank,
            scholar.department,
            scholar.age,
            scholar.tenure_years,
            " · ".join(item.degree for item in scholar.education),
            scholar.current_status,
            scholar.profile_remarks,
        ]
        for index, participation in enumerate(
            sorted(scholar.participations, key=grant_order) or [None]
        ):
            writer.writerow(
                (profile if index == 0 else [None] * len(profile))
                + [
                    participation.name if participation else "",
                    participation.delivering_hei or "" if participation else "",
                    (
                        participation.grant_other
                        if participation.grant_type == "Others"
                        else participation.grant_type
                    )
                    or ""
                    if participation
                    else "",
                    participation.start_term if participation else None,
                    participation.start_academic_year if participation else None,
                    participation.end_term if participation else None,
                    participation.end_academic_year if participation else None,
                    participation.contract_completed_on if participation else None,
                    participation.extension or "" if participation else "",
                    participation.remarks or "" if participation else "",
                    participation.status if participation else "",
                    participation.graduation_date or "" if participation else "",
                    participation.case_status if participation else "",
                    participation.start_date if participation else None,
                    participation.allowed_duration_years if participation else None,
                    participation.completion_due_on if participation else None,
                    participation.completion_deadline_on if participation else None,
                    participation.payback_payment_status if participation else None,
                ]
            )
    return csv_response(output, "cathedra-fsdp-report.csv")


@router.get("/{scholar_id}", response_model=ScholarRead)
def get_scholar(scholar_id: int, db: Session = Depends(get_db)) -> ScholarRead:
    scholar = db.scalar(select(Scholar).options(*options()).where(Scholar.id == scholar_id))
    if scholar is None:
        raise HTTPException(status_code=404, detail="Scholar not found")
    return read_scholar(scholar)


@router.post("", response_model=ScholarRead, status_code=status.HTTP_201_CREATED)
def create_scholar(
    payload: ScholarCreate,
    db: Session = Depends(get_db),
    user: LocalUser = Depends(require_signed_in),
    request_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=64)] = None,
) -> ScholarRead:
    digest = hashlib.sha256(
        json.dumps(
            payload.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    if request_key is not None:
        try:
            request_key = str(UUID(request_key))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="The save request identifier is invalid."
            ) from None
        db.rollback()
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        prior = db.get(CreationRequest, (user.id, request_key))
        if prior:
            if prior.payload_digest != digest:
                raise HTTPException(
                    status_code=409,
                    detail="This save request has different details. Retry the original draft.",
                )
            if db.get(Scholar, prior.scholar_id) is None:
                raise HTTPException(
                    status_code=409,
                    detail="This save completed earlier, but its scholar has since been deleted. Review the directory.",
                )
            return get_scholar(prior.scholar_id, db)
    scholar = Scholar(id=next_scholar_id(db))
    db.add(scholar)
    apply_payload(db, scholar, payload)
    db.flush()
    sync_graduated_education(scholar, uppercase_new=True)
    if request_key is not None:
        db.add(
            CreationRequest(
                user_id=user.id,
                request_key=request_key,
                payload_digest=digest,
                scholar_id=scholar.id,
            )
        )
    commit_record(db)
    return get_scholar(scholar.id, db)


@router.put("/{scholar_id}", response_model=ScholarRead)
def update_scholar(
    scholar_id: int,
    payload: ScholarUpdate,
    db: Session = Depends(get_db),
    if_match: int | None = Header(default=None, alias="If-Match"),
) -> ScholarRead:
    scholar = db.scalar(select(Scholar).options(*options()).where(Scholar.id == scholar_id))
    if scholar is None:
        raise HTTPException(status_code=404, detail="Scholar not found")
    advance_revision(db, Scholar, scholar_id, if_match)
    apply_payload(db, scholar, payload)
    db.flush()
    sync_graduated_education(scholar, uppercase_new=True)
    commit_record(db)
    return get_scholar(scholar_id, db)


@router.delete("/{scholar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scholar(
    scholar_id: int,
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
    if_match: int | None = Header(default=None, alias="If-Match"),
) -> Response:
    # Reserve the writer before the snapshot so no concurrent edit can land
    # between the recovery copy and deletion. No rows have changed yet.
    db.rollback()
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    scholar = db.get(Scholar, scholar_id)
    if scholar is None:
        raise HTTPException(status_code=404, detail="Scholar not found")
    if if_match is None:
        raise HTTPException(status_code=428, detail="Reload this record before saving changes.")
    if scholar.revision != if_match:
        raise HTTPException(
            status_code=409,
            detail="This record changed in another window. Review the latest version before saving.",
        )
    try:
        snapshot_before_delete(db)
    except Exception as caught:
        from app.diagnostics import log_private_exception

        reference = log_private_exception(caught)
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=f"A recovery copy could not be created. Nothing was deleted. Reference: {reference}",
        ) from None
    advance_revision(db, Scholar, scholar_id, if_match)
    db.delete(scholar)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
