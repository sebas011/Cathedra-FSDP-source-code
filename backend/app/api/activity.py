import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activity_details import sanitize_change_details
from app.auth import require_admin
from app.db import get_db
from app.models import ActivityEvent, LocalUser, Scholar

router = APIRouter(prefix="/activity", tags=["Activity History"])


def read_event(event: ActivityEvent, *, include_details: bool = False) -> dict[str, object]:
    try:
        fields = json.loads(event.changed_fields or "[]")
    except ValueError, TypeError:
        fields = []
    if not isinstance(fields, list):
        fields = []
    result = {
        "id": event.id,
        "username": event.username,
        "action": event.action,
        "area": event.area,
        "created_at": event.created_at,
        "record_type": event.record_type,
        "record_id": event.record_id,
        "operation": event.operation,
        "changed_fields": [field for field in fields if isinstance(field, str)],
    }
    if include_details:
        result["change_details"] = sanitize_change_details(event.record_type, event.change_details)
    return result


@router.get("/scholars/{scholar_id}")
def scholar_activity(
    scholar_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
) -> dict[str, object]:
    if db.get(Scholar, scholar_id) is None:
        raise HTTPException(status_code=404, detail="Scholar not found.")
    statement = select(ActivityEvent).where(ActivityEvent.subject_scholar_id == scholar_id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    events = db.scalars(
        statement.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [read_event(event, include_details=True) for event in events],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("")
def list_activity(
    db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> list[dict[str, object]]:
    events = db.scalars(
        select(ActivityEvent)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(200)
    ).all()
    return [read_event(event) for event in events]
