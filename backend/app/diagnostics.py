"""Bounded diagnostics and a private maintenance journal outside restored data."""

import json
import logging
import os
import threading
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_journal_lock = threading.Lock()


def configure_diagnostics(data: Path) -> None:
    directory = data / "diagnostics"
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("cathedra")
    path = directory / "operations.log"
    if any(
        isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == path
        for handler in logger.handlers
    ):
        return
    handler = RotatingFileHandler(path, maxBytes=1_048_576, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def record_maintenance(data: Path, action: str, username: str, backup: str) -> None:
    # This restricted local journal survives restoring an older database.
    event = {
        "at": datetime.now(UTC).isoformat(),
        "action": action,
        "username": username,
        "backup": backup,
    }
    data.mkdir(parents=True, exist_ok=True)
    with _journal_lock:
        with (data / "maintenance-history.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")
            output.flush()
            os.fsync(output.fileno())


def maintenance_history(data: Path, page: int, page_size: int) -> dict:
    path = data / "maintenance-history.jsonl"
    events = []
    if path.exists():
        with path.open(encoding="utf-8") as source:
            for line in source:
                try:
                    event = json.loads(line)
                    if set(event) == {"at", "action", "username", "backup"} and all(
                        isinstance(value, str) for value in event.values()
                    ):
                        events.append(event)
                except ValueError:
                    continue
    events.reverse()
    return {
        "items": events[(page - 1) * page_size : page * page_size],
        "total": len(events),
        "page": page,
        "page_size": page_size,
        "historical_gaps": True,
    }
