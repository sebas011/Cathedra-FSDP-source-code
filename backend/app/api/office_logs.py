"""Append-only operational notes and document movements, with server actors."""

import hashlib
import json
from datetime import date, datetime
from io import StringIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity_audit import add_activity
from app.auth import require_editor
from app.csv_export import SafeCsvWriter
from app.db import get_db
from app.models import LocalUser, OfficeLog, Scholar
from app.record_text import uppercase_text
from app.schemas import TextModel

EntryType = Literal["Note", "Document received", "Document transferred"]
router = APIRouter(prefix="/office-logs", tags=["Office Log"])
CSV_HEADERS = ["ID", "Occurred On", "Created At", "Entry Type", "Scholar ID", "Scholar", "Note", "Document", "From Department", "To Department", "Recorded By"]


class OfficeLogCreate(TextModel):
    scholar_id: int | None = Field(default=None, ge=1)
    occurred_on: date | None = None
    entry_type: EntryType = "Note"
    note: str = Field(min_length=1)
    document_name: str | None = None
    from_department: str | None = None
    to_department: str | None = None


class OfficeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scholar_id: int | None
    scholar_name: str | None
    user_id: int
    username: str
    occurred_on: date
    created_at: datetime
    entry_type: EntryType
    note: str
    document_name: str | None
    from_department: str | None
    to_department: str | None


def log_statement(scholar_id: int | None, search: str, entry_type: str):
    statement = select(OfficeLog)
    if scholar_id is not None:
        statement = statement.where(OfficeLog.scholar_id == scholar_id)
    if entry_type:
        statement = statement.where(OfficeLog.entry_type == entry_type)
    if search.strip():
        # SQLite LOWER/ILIKE handles ASCII only. Use the connection's literal
        # Unicode matcher for both historical and newly uppercase records.
        statement = statement.where(or_(*(func.unicode_contains(column, search.strip()) == 1 for column in (
            OfficeLog.note, OfficeLog.scholar_name, OfficeLog.document_name,
            OfficeLog.from_department, OfficeLog.to_department, OfficeLog.username,
        ))))
    return statement


@router.get("/export.csv")
def export_logs(
    scholar_id: int | None = Query(default=None, ge=1), search: str = "",
    entry_type: EntryType | None = None, db: Session = Depends(get_db),
) -> Response:
    output = StringIO(newline="")
    writer = SafeCsvWriter(output)
    writer.writerow(CSV_HEADERS)
    records = db.scalars(log_statement(scholar_id, search, entry_type or "")
                         .order_by(OfficeLog.occurred_on.desc(), OfficeLog.id.desc()))
    for item in records:
        writer.writerow([item.id, item.occurred_on, item.created_at, item.entry_type,
                         item.scholar_id, item.scholar_name, item.note, item.document_name,
                         item.from_department, item.to_department, item.username])
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="cathedra-office-log.csv"'})


@router.get("")
def list_logs(
    scholar_id: int | None = Query(default=None, ge=1), search: str = "",
    entry_type: EntryType | None = None, page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = log_statement(scholar_id, search, entry_type or "")
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    records = db.scalars(statement.order_by(OfficeLog.occurred_on.desc(), OfficeLog.id.desc())
                         .offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [OfficeLogRead.model_validate(item) for item in records],
            "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=OfficeLogRead, status_code=201)
def create_log(
    payload: OfficeLogCreate, db: Session = Depends(get_db),
    user: LocalUser = Depends(require_editor),
    request_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=64)] = None,
) -> OfficeLog:
    values = payload.model_dump()
    for field in ("note", "document_name", "from_department", "to_department"):
        values[field] = uppercase_text(values[field])
    digest = hashlib.sha256(json.dumps({**values, "occurred_on": payload.occurred_on.isoformat() if payload.occurred_on else None},
                                     sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if request_key is not None:
        try:
            request_key = str(UUID(request_key))
        except ValueError:
            raise HTTPException(status_code=422, detail="The save request identifier is invalid.") from None
        db.rollback()
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        existing = db.scalar(select(OfficeLog).where(OfficeLog.user_id == user.id, OfficeLog.request_key == request_key))
        if existing is not None:
            if existing.payload_digest != digest:
                raise HTTPException(status_code=409, detail="This save request has different details. Retry the original office entry.")
            return existing
    scholar = db.get(Scholar, payload.scholar_id) if payload.scholar_id is not None else None
    if payload.scholar_id is not None and scholar is None:
        raise HTTPException(status_code=404, detail="Scholar not found. Reload before adding the office entry.")
    values["occurred_on"] = payload.occurred_on or date.today()
    entry = OfficeLog(**values, scholar_name=scholar.name if scholar else None,
                      user_id=user.id, username=user.username, request_key=request_key,
                      payload_digest=digest if request_key else None)
    db.add(entry)
    try:
        db.flush()
        add_activity(db, "Office Log", "Added office entry", record_type="office_logs",
                     record_id=entry.id, operation="Created", subject_scholar_id=payload.scholar_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(OfficeLog).where(OfficeLog.user_id == user.id, OfficeLog.request_key == request_key)) if request_key else None
        if existing is not None and existing.payload_digest == digest:
            return existing
        raise HTTPException(status_code=409, detail="The office entry could not be saved. Reload and retry the original entry.") from None
    db.refresh(entry)
    return entry
