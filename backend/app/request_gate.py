import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth import require_admin, require_signed_in
from app.db import get_db

MAX_BODY_BYTES = 1024 * 1024
BODY_TIMEOUT_SECONDS = 10


async def finish_before_release(awaitable):
    operation = asyncio.create_task(awaitable)
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(operation)
            break
        except asyncio.CancelledError:
            if operation.done():
                raise
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    return result


def authorize_restore(scope: Scope) -> None:
    application = scope["app"]
    provider = application.dependency_overrides.get(get_db, get_db)
    session_provider = provider()
    try:
        database = next(session_provider)
        request = Request(scope)
        require_admin(require_signed_in(request, request.headers.get("authorization"), database))
    finally:
        session_provider.close()


class RestoreRequestGate:
    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._active_requests = 0
        self._restore_active = False
        self._restores_waiting = 0
        self.recovery_required = False

    @asynccontextmanager
    async def shared(self) -> AsyncIterator[None]:
        async with self._condition:
            await self._condition.wait_for(
                lambda: not self._restore_active and self._restores_waiting == 0
            )
            self._active_requests += 1
        try:
            yield
        finally:
            async with self._condition:
                self._active_requests -= 1
                if self._active_requests == 0:
                    self._condition.notify_all()

    @asynccontextmanager
    async def exclusive(self) -> AsyncIterator[None]:
        async with self._condition:
            self._restores_waiting += 1
            try:
                await self._condition.wait_for(
                    lambda: not self._restore_active and self._active_requests == 0
                )
                self._restore_active = True
            finally:
                self._restores_waiting -= 1
                self._condition.notify_all()
        try:
            yield
        finally:
            async with self._condition:
                self._restore_active = False
                self._condition.notify_all()


class RestoreGateMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        gate: RestoreRequestGate = scope["app"].state.restore_request_gate
        is_restore = scope["method"] == "POST" and scope["path"] == "/api/v1/maintenance/restore"
        body = bytearray()
        try:
            async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > MAX_BODY_BYTES:
                        await JSONResponse({"detail": "Request is too large."}, status_code=413)(
                            scope, receive, send
                        )
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse(
                {"detail": "Request body timed out. Retry the operation."}, status_code=408
            )(scope, receive, send)
            return

        delivered = False

        async def replay_body():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        if is_restore:
            try:
                async with gate.shared():
                    if gate.recovery_required:
                        raise HTTPException(
                            status_code=503,
                            detail="Restore recovery is required. Exit Cathedra and restart it before working with records.",
                        )
                    await finish_before_release(asyncio.to_thread(authorize_restore, scope))
            except HTTPException as caught:
                await JSONResponse({"detail": caught.detail}, status_code=caught.status_code)(
                    scope, replay_body, send
                )
                return
        async with gate.exclusive() if is_restore else gate.shared():
            if (
                gate.recovery_required
                and scope["path"].startswith("/api/")
                and scope["path"] not in {"/api/v1/health", "/api/v1/desktop/exit"}
            ):
                await JSONResponse(
                    {
                        "detail": "Restore recovery is required. Exit Cathedra and restart it before working with records."
                    },
                    status_code=503,
                )(scope, replay_body, send)
                return
            await finish_before_release(self.app(scope, replay_body, send))
