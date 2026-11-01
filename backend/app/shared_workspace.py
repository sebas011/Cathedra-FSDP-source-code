"""Explicit, revision-checked reconciliation of the local cache and shared facts."""

import copy
import json
import sqlite3
import threading
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app import clock
from app.activity_audit import add_activity
from app.db import DB_PATH
from app.google_sheets import WindowsVault
from app.models import SharedWorkspaceState
from app.shared_connection import SharedError, WorkspaceConnection, encode, fingerprint
from app.shared_merge import merge
from app.shared_records import apply_snapshot, capture, validate_snapshot
from app.upgrade import snapshot_database

connection = WorkspaceConnection(WindowsVault(DB_PATH.parent / "shared-workspace.bin"))


def failure(message: str, code: int = 409):
    raise HTTPException(status_code=code, detail=message)


def state_row(db, *, create=False):
    state = db.get(SharedWorkspaceState, 1)
    if state is None and create:
        state = SharedWorkspaceState(id=1, cache_id=str(uuid4()), dirty=False)
        db.add(state)
        db.flush()
    return state


def baseline(state) -> dict:
    return json.loads(state.baseline_json) if state and state.baseline_json else {}


def bound(state) -> bool:
    return bool(
        state
        and state.workspace_id
        and state.baseline_json
        and connection.matches_checkpoint(state)
    )


def local_status(db) -> dict:
    public = connection.public()
    state = state_row(db)
    saved = connection.saved()
    joined = bool(public["configured"] and bound(state))
    restored = bool(public["configured"] and saved.get("checkpoint") and not joined)
    phase = (
        "pending"
        if state and state.pending_json
        else "rejoin_required"
        if restored
        else "dirty"
        if joined and state.dirty
        else "ready"
        if public["configured"]
        else "disconnected"
    )
    return {
        **public,
        "connected": bool(saved.get("metadata")),
        "joined": joined,
        "state": phase,
        "revision": baseline(state).get("revision") if joined else None,
        "last_synced_at": state.last_synced_at.isoformat() + "Z"
        if state and state.last_synced_at
        else None,
        "message": (
            "Resolve the saved synchronization before editing records."
            if phase == "pending"
            else "This cache needs a reviewed join after a restore or interrupted checkpoint."
            if restored
            else None
        ),
    }


def assert_local_writes_allowed(db, path: str) -> None:
    state = state_row(db)
    if state and state.pending_json:
        failure(
            "A shared save is not confirmed. Use Sync workspace → Retry saved operation before changing records.",
            423,
        )
    if connection.public()["configured"]:
        if path == "/api/v1/maintenance/restore":
            failure(
                "Disconnect the shared workspace before restoring a local backup. Rejoin and review shared records afterward."
            )
        if path.startswith("/api/v1/google-sheets/"):
            failure(
                "Use the shared workspace controls while this PC is connected to shared storage."
            )


def verify_read(result: dict) -> dict:
    snapshot = result.get("snapshot")
    validate_snapshot(snapshot)
    if (
        result.get("workspace_id", snapshot["workspace_id"]) != snapshot["workspace_id"]
        or result.get("revision", snapshot["revision"]) != snapshot["revision"]
    ):
        raise SharedError(
            "The shared response metadata does not match its snapshot.", uncertain=True
        )
    metadata = {
        **connection.saved().get("metadata", {}),
        **result,
        **{key: snapshot[key] for key in ("protocol", "workspace_id", "revision", "initialized")},
    }
    connection.remember_metadata(metadata)
    return snapshot


def recovery_copy(db) -> Path:
    """Snapshot the actual supplied session's database, including isolated test databases."""
    db.rollback()
    destination = (
        DB_PATH.parent / "backups" / ("cathedra-protected-before-shared-" + uuid4().hex + ".db")
    )
    source = db.get_bind().url.database
    if source and source != ":memory:" and Path(source).is_file():
        snapshot_database(Path(source).resolve(), destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        raw = db.get_bind().raw_connection()
        try:
            with sqlite3.connect(destination) as backup:
                raw.driver_connection.backup(backup)
                if (
                    backup.execute("PRAGMA integrity_check").fetchone() != ("ok",)
                    or backup.execute("PRAGMA foreign_key_check").fetchone()
                ):
                    raise RuntimeError("Shared recovery copy failed verification.")
        finally:
            raw.close()
    return destination


class PreviewStore:
    def __init__(self):
        self.values = {}
        self.lock = threading.Lock()

    def clear(self):
        with self.lock:
            self.values.clear()

    def create(self, db, user, mode: str) -> dict:
        status = local_status(db)
        state = state_row(db)
        if state and state.pending_json:
            failure("Retry the saved operation first.")
        if mode == "sync" and not status["joined"]:
            failure("Join the shared workspace before synchronizing.")
        db.rollback()  # No database reservation is held while contacting Google.
        result = connection.call("read")
        remote = verify_read(result)
        local = capture(db)
        original = baseline(state)
        if mode == "initialize":
            if remote["initialized"] or remote["records"] or not result.get("can_initialize"):
                failure(
                    "Only an approved Office initializer can populate an empty shared workspace."
                )
            items = [
                {
                    "key": key,
                    "kind": value["kind"],
                    "label": label(value),
                    "direction": "upload",
                    "conflict": False,
                    "local_summary": ["Create from this Office PC"],
                    "shared_summary": [],
                }
                for key, value in local.items()
            ]
            planned = {"items": items, "conflicts": []}
        elif mode == "join":
            if not remote["initialized"]:
                failure("Initialize shared storage from the authoritative Office PC first.")
            planned = {
                "items": [
                    {
                        "key": record["key"],
                        "kind": record["kind"],
                        "label": label(record),
                        "direction": "download",
                        "conflict": False,
                        "local_summary": [],
                        "shared_summary": ["Use shared records on this PC"],
                    }
                    for record in remote["records"]
                    if record["value"] is not None
                ],
                "conflicts": [],
            }
        else:
            if remote["workspace_id"] != state.workspace_id:
                failure("This is a different workspace. Disconnect and review it first.")
            planned = merge(original, local, remote)
        now = clock.utc_now()
        preview_id = str(uuid4())
        saved = connection.saved()
        stored = {
            "user_id": user.id,
            "mode": mode,
            "remote": remote,
            "local": local,
            "local_digest": fingerprint(local),
            "base": original,
            "binding": fingerprint(
                {
                    key: saved.get(key)
                    for key in ("endpoint", "device_id", "binding_id", "checkpoint")
                }
            ),
            "expires": now + timedelta(minutes=20),
        }
        with self.lock:
            self.values = {
                key: value
                for key, value in self.values.items()
                if value["expires"] > now and value["user_id"] != user.id
            }
            if len(self.values) >= 5:
                self.values.pop(next(iter(self.values)))
            self.values[preview_id] = stored
        items = planned["items"]
        return {
            "preview_id": preview_id,
            "mode": mode,
            "expires_at": stored["expires"].isoformat(),
            "items": items,
            "conflicts": planned["conflicts"],
            "counts": {
                "local": len(local),
                "shared": sum(record["value"] is not None for record in remote["records"]),
                "upload": sum(item["direction"] == "upload" for item in items),
                "download": sum(item["direction"] == "download" for item in items),
                "conflicts": len(planned["conflicts"]),
            },
            "warnings": [
                "Review whole-scholar conflicts before applying changes.",
                "A protected local recovery copy is created before applying.",
                *(
                    [
                        "This replaces local business records with the shared workspace. Accounts stay local."
                    ]
                    if mode == "join"
                    else []
                ),
                *(
                    [
                        "Initialize only from the Office PC containing the authoritative scholar records."
                    ]
                    if mode == "initialize"
                    else []
                ),
            ],
        }

    def get(self, preview_id, user_id):
        with self.lock:
            item = self.values.get(preview_id)
            if not item or item["user_id"] != user_id or item["expires"] <= clock.utc_now():
                failure("The preview expired or belongs to another account. Read a new preview.")
            return copy.deepcopy(item)


def label(record):
    value = record.get("value") or {}
    return value.get("name") or value.get("note", "Office log entry")[:100]


previews = PreviewStore()


def apply_preview(db, user, preview_id: str, choices: dict) -> dict:
    state = state_row(db)
    selection_digest = fingerprint({"preview_id": preview_id, "choices": choices})
    if state and state.last_completed_id == preview_id and state.last_result_json:
        completed = json.loads(state.last_result_json)
        if completed["user_id"] != user.id or completed["selection_digest"] != selection_digest:
            failure("A completed preview cannot be retried with a different account or selection.")
        return {**completed["result"], "replayed": True}
    if state and state.pending_json:
        failure("Retry the exact saved operation before beginning another one.")
    item = previews.get(preview_id, user.id)
    saved = connection.saved()
    binding = fingerprint(
        {key: saved.get(key) for key in ("endpoint", "device_id", "binding_id", "checkpoint")}
    )
    local = capture(db)
    if binding != item["binding"] or fingerprint(local) != item["local_digest"]:
        failure("Local records or the shared connection changed. Refresh the preview.")
    remote = item["remote"]
    mode = item["mode"]
    if mode == "sync":
        if not bound(state) or baseline(state) != item["base"]:
            failure("The local shared baseline changed. Refresh the preview.")
        planned = merge(item["base"], local, remote, choices)
        if planned["conflicts"]:
            failure("Choose which version to keep for every conflict.", 422)
        changes = planned["changes"]
    elif mode == "initialize":
        if choices:
            failure("Initialization does not accept conflict choices.", 422)
        changes = [{"key": key, **value} for key, value in sorted(local.items())]
    else:
        if choices:
            failure("Joining does not accept conflict choices.", 422)
        changes = []
    args = {
        "request_id": preview_id,
        "actor": user.username,
        "expected_revision": remote["revision"],
    }
    args["records" if mode == "initialize" else "changes"] = changes
    pending = {
        "request_id": preview_id,
        "mode": mode,
        "command": "initialize" if mode == "initialize" else "commit",
        "args": args,
        "local_digest": item["local_digest"],
        "workspace_id": remote["workspace_id"],
        "user_id": user.id,
        "actor": user.username,
        "uploaded": len(changes),
        "selection_digest": selection_digest,
    }
    # Validate capacity before preserving a pending request and sending any data.
    if len(encode(pending)) > 7 * 1024 * 1024:
        failure("This shared change exceeds the supported synchronization size.", 422)
    recovery_copy(db)
    db.execute(text("BEGIN IMMEDIATE"))
    if fingerprint(capture(db)) != item["local_digest"]:
        db.rollback()
        failure("Local records changed before synchronization. Refresh the preview.")
    state = state_row(db, create=True)
    state.pending_json = encode(pending).decode()
    db.commit()
    return finish_pending(db, user)


def finish_pending(db, user) -> dict:
    state = state_row(db)
    if not state or not state.pending_json:
        if state and state.last_result_json:
            return {**json.loads(state.last_result_json)["result"], "replayed": True}
        failure("There is no saved shared operation to retry.")
    pending = json.loads(state.pending_json)
    if fingerprint(capture(db)) != pending["local_digest"]:
        failure(
            "Local records changed outside Cathedra during an unconfirmed save. Keep the recovery copy and review before retrying."
        )
    db.rollback()
    try:
        response = connection.call(pending["command"], pending["args"])
    except SharedError as caught:
        if not caught.uncertain:
            state = state_row(db)
            state.pending_json = None
            db.commit()
        raise
    except Exception:
        # A committed cloud result must remain recoverable even if validation fails.
        raise SharedError(
            "The shared response needs verification. The saved operation is retained for retry.",
            uncertain=True,
        ) from None
    try:
        snapshot = verify_read(response)
        if snapshot["workspace_id"] != pending["workspace_id"]:
            raise ValueError
    except Exception:
        raise SharedError(
            "The shared response needs verification. The saved operation is retained for retry.",
            uncertain=True,
        ) from None
    db.execute(text("BEGIN IMMEDIATE"))
    state = state_row(db)
    if fingerprint(capture(db)) != pending["local_digest"]:
        db.rollback()
        failure(
            "Local records changed outside Cathedra. The confirmed shared result is retained remotely; review the recovery copy."
        )
    before = capture(db)
    try:
        apply_snapshot(db, snapshot)
        state = state_row(db)
        state.workspace_id = snapshot["workspace_id"]
        state.baseline_json = encode(snapshot).decode()
        state.pending_json = None
        state.dirty = False
        state.last_synced_at = clock.utc_now().replace(tzinfo=None)
        state.last_completed_id = pending["request_id"]
        after = capture(db)
        downloaded = sum(before.get(key) != value for key, value in after.items()) + len(
            set(before) - set(after)
        )
        result = {
            "state": "ready",
            "revision": snapshot["revision"],
            "uploaded": pending["uploaded"],
            "downloaded": downloaded,
            "conflicts": 0,
            "replayed": response.get("replayed", False),
            "message": "Shared records synchronized. Local accounts and credentials were retained.",
        }
        state.last_result_json = encode(
            {
                "result": result,
                "user_id": pending["user_id"],
                "selection_digest": pending["selection_digest"],
            }
        ).decode()
        add_activity(
            db, "Shared workspace", "Shared records synchronized", operation="Synchronized"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise SharedError(
            "The shared save was confirmed, but the local copy needs its exact retry. The recovery copy and pending request are retained.",
            uncertain=True,
        ) from None
    try:
        connection.checkpoint(snapshot["workspace_id"], state.cache_id, snapshot)
    except Exception:
        # Database commit is complete. A missing checkpoint forces a reviewed rejoin.
        failure(
            "Shared records were saved, but the private checkpoint could not be completed. Rejoin the shared workspace before sending more changes.",
            503,
        )
    return result
