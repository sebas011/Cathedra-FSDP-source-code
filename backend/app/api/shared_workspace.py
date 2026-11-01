"""Admin-reviewed shared synchronization; local accounts never leave this PC."""

from types import SimpleNamespace
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import shared_workspace as workspace
from app.auth import require_admin, require_signed_in
from app.db import get_db
from app.google_report import google_report_rows
from app.models import LocalUser
from app.shared_connection import SharedError
from app.shared_records import local_value

router = APIRouter(prefix="/shared-workspace", tags=["shared-workspace"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Configure(Payload):
    endpoint: str = Field(min_length=1, max_length=400)


class Preview(Payload):
    mode: Literal["join", "initialize", "sync"]


class Apply(Payload):
    preview_id: UUID
    choices: dict[UUID, Literal["local", "shared"]] = Field(default_factory=dict)
    confirm: Literal[True]


def safe(operation, *args):
    try:
        return operation(*args)
    except SharedError as caught:
        code = 503 if caught.uncertain else 409 if caught.code == "conflict" else 422
        raise HTTPException(status_code=code, detail=str(caught)) from None
    except ValueError as caught:
        raise HTTPException(status_code=422, detail=str(caught)) from None


def no_pending(db):
    state = workspace.state_row(db)
    if state and state.pending_json:
        workspace.failure("Retry the saved shared operation before changing its connection.")


@router.get("")
def status(db: Session = Depends(get_db), user: LocalUser = Depends(require_signed_in)):
    result = safe(workspace.local_status, db)
    if user.role != "admin":
        for key in ("device_key_hash", "endpoint", "storage_url", "report_url"):
            result[key] = None
    return result


@router.post("/configure")
def configure(
    payload: Configure, db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)
):
    no_pending(db)
    safe(workspace.connection.configure, payload.endpoint)
    workspace.previews.clear()
    return safe(workspace.local_status, db)


@router.post("/check")
def check(db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)):
    db.rollback()
    result = safe(workspace.connection.call, "status")
    safe(workspace.connection.remember_metadata, result)
    return safe(workspace.local_status, db)


@router.delete("/connection")
def disconnect(db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)):
    no_pending(db)
    safe(workspace.connection.disconnect)
    state = workspace.state_row(db)
    if state:
        state.workspace_id = state.baseline_json = state.last_completed_id = (
            state.last_result_json
        ) = None
        state.cache_id = str(uuid4())
        state.dirty = False
        state.last_synced_at = None
        db.commit()
    workspace.previews.clear()
    return safe(workspace.local_status, db)


@router.post("/preview")
def preview(
    payload: Preview, db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)
):
    return safe(workspace.previews.create, db, user, payload.mode)


@router.post("/apply")
def apply(payload: Apply, db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)):
    return safe(
        workspace.apply_preview,
        db,
        user,
        str(payload.preview_id),
        {str(key): value for key, value in payload.choices.items()},
    )


@router.post("/retry")
def retry(db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)):
    return safe(workspace.finish_pending, db, user)


def report_table(snapshot):
    programs = {
        record["key"]: SimpleNamespace(**record["value"])
        for record in snapshot["records"]
        if record["kind"] == "program" and record["value"] is not None
    }
    scholars = []
    for record in snapshot["records"]:
        if record["kind"] != "scholar" or record["value"] is None:
            continue
        value = record["value"]
        scholar = SimpleNamespace(**value)
        scholar.id = record["key"]
        scholar.education = [SimpleNamespace(**entry) for entry in value["education"]]
        scholar.participations = [
            SimpleNamespace(
                id=ordinal,
                program=programs[entry["program_key"]],
                **{key: local_value(key, val) for key, val in entry.items()},
            )
            for ordinal, entry in enumerate(value["participations"], 1)
        ]
        scholars.append(scholar)
    headings, rows = google_report_rows(
        sorted(scholars, key=lambda item: (item.name.casefold(), item.id))
    )
    return [headings, *rows]


@router.post("/report")
def report(db: Session = Depends(get_db), user: LocalUser = Depends(require_admin)):
    no_pending(db)
    db.rollback()
    snapshot = safe(workspace.verify_read, safe(workspace.connection.call, "read"))
    if not snapshot["initialized"]:
        workspace.failure("Initialize shared records from the Office PC first.")
    table = safe(report_table, snapshot)
    return safe(
        workspace.connection.call,
        "report",
        {"expected_revision": snapshot["revision"], "table": table},
    )
