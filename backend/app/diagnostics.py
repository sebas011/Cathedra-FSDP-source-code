"""Bounded diagnostics and a private maintenance journal outside restored data."""

import json
import logging
import os
import threading
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.security_headers import SECURITY_HEADERS

_journal_lock = threading.Lock()


def log_private_exception(
    exception: Exception, *, method: str = "", route_template: str = "<internal>"
) -> str:
    """Log code locations only; exception text and request data can contain records."""
    reference = uuid4().hex
    frames = []
    traceback = exception.__traceback__
    while traceback is not None:
        code = traceback.tb_frame.f_code
        frames.append(
            {
                "filename": Path(code.co_filename).name,
                "function": code.co_name,
                "line": traceback.tb_lineno,
            }
        )
        traceback = traceback.tb_next
    logging.getLogger("cathedra.errors").error(
        "private_error %s",
        json.dumps(
            {
                "reference": reference,
                "exception_class": type(exception).__name__,
                "method": method,
                "route_template": route_template,
                "frames": frames,
            }
        ),
    )
    return reference


async def unexpected_error_response(request: Request, exception: Exception) -> JSONResponse:
    route = request.scope.get("route")
    reference = log_private_exception(
        exception,
        method=request.method,
        route_template=getattr(route, "path", "<unmatched>"),
    )
    # Starlette's server-error handler runs outside user middleware.
    return JSONResponse(
        {
            "detail": f"An unexpected error occurred. Retry the operation. If it continues, contact support. Reference: {reference}",
            "reference": reference,
        },
        status_code=500,
        headers={
            **SECURITY_HEADERS,
            "Cache-Control": "no-store",
        },
    )


class PrivateErrorMiddleware:
    """Finish failed HTTP requests without propagating private tracebacks to the server."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False
        response_complete = False

        async def track_response(message):
            nonlocal response_started, response_complete
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_complete = True

        try:
            await self.app(scope, receive, track_response)
        except Exception as caught:
            if not response_started:
                response = await unexpected_error_response(Request(scope), caught)
                try:
                    await response(scope, receive, send)
                except Exception as transport_error:
                    log_private_exception(
                        transport_error,
                        method=scope["method"],
                        route_template=getattr(scope.get("route"), "path", "<unmatched>"),
                    )
                return
            log_private_exception(
                caught,
                method=scope["method"],
                route_template=getattr(scope.get("route"), "path", "<unmatched>"),
            )
            if not response_complete:
                # Already-sent status and chunks cannot be replaced. End the partial
                # response; a disconnected or length-limited transport can also fail.
                try:
                    await send({"type": "http.response.body", "body": b"", "more_body": False})
                except Exception as transport_error:
                    log_private_exception(
                        transport_error,
                        method=scope["method"],
                        route_template=getattr(scope.get("route"), "path", "<unmatched>"),
                    )


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
