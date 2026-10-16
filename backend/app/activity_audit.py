"""Write record activity in the same transaction as the record change."""

import json

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import (
    ActivityEvent,
    FsdpParticipation,
    LocalUser,
    Program,
    Scholar,
    ScholarEducation,
    ScholarRequirement,
)

AREAS = {
    Scholar: "FSDP",
    ScholarRequirement: "FSDP Requirements",
    ScholarEducation: "FSDP Education",
    FsdpParticipation: "FSDP Grants",
    Program: "FSDP Programs",
    LocalUser: "Local Accounts",
}


def add_activity(
    db: Session,
    area: str,
    action: str,
    record_type: str | None = None,
    record_id: int | None = None,
    operation: str | None = None,
    changed_fields: list[str] | None = None,
    subject_scholar_id: int | None = None,
) -> None:
    actor = db.info.get("audit_actor")
    if actor is None:
        return
    user_id, username = actor
    db.add(
        ActivityEvent(
            user_id=user_id,
            username=username,
            area=area,
            action=action,
            record_type=record_type,
            record_id=record_id,
            operation=operation,
            changed_fields=json.dumps(changed_fields or []),
            subject_scholar_id=subject_scholar_id,
        )
    )


def _changed_fields(record: object, operation: str) -> list[str]:
    mapper = inspect(record).mapper
    if operation == "Updated":
        names = [
            attribute.key
            for attribute in mapper.column_attrs
            if inspect(record).attrs[attribute.key].history.has_changes()
        ]
    else:
        names = [attribute.key for attribute in mapper.column_attrs]
    return sorted(
        "credentials" if name == "password_hash" else name
        for name in names
        if name
        not in {
            "id",
            "created_at",
            "updated_at",
            "token_hash",
        }
    )


@event.listens_for(Session, "before_flush")
def collect_activity(db: Session, _, __) -> None:
    if "audit_actor" not in db.info:
        return
    pending = []
    removed = set()
    for parent in db.dirty:
        if isinstance(parent, Scholar):
            for relationship in ("participations", "requirements", "education"):
                for child in inspect(parent).attrs[relationship].history.deleted:
                    if child.id is not None and child not in db.deleted:
                        pending.append((child, "Deleted", _changed_fields(child, "Deleted")))
                        removed.add(child)
    for operation, records in (("Created", db.new), ("Updated", db.dirty), ("Deleted", db.deleted)):
        for record in records:
            if record in removed:
                continue
            if type(record) not in AREAS:
                continue
            if operation == "Updated" and not db.is_modified(record, include_collections=False):
                continue
            fields = _changed_fields(record, operation)
            label = operation
            pending.append((record, label, fields))
    if pending:
        db.info.setdefault("audit_pending", []).extend(pending)


@event.listens_for(Session, "after_flush_postexec")
def write_activity(db: Session, _) -> None:
    pending = db.info.pop("audit_pending", [])
    for record, operation, fields in pending:
        area = AREAS[type(record)]
        record_id = record.id
        add_activity(
            db,
            area,
            f"{operation} {area} #{record_id}",
            record_type=record.__tablename__,
            record_id=record_id,
            operation=operation,
            changed_fields=fields,
            subject_scholar_id=(
                record_id
                if isinstance(record, Scholar)
                else record.scholar_id
                if isinstance(record, (FsdpParticipation, ScholarRequirement, ScholarEducation))
                else None
            ),
        )


@event.listens_for(Session, "after_rollback")
def discard_pending_activity(db: Session) -> None:
    db.info.pop("audit_pending", None)
