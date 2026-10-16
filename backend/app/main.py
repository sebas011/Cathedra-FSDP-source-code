import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from starlette.middleware.trustedhost import TrustedHostMiddleware

import app.activity_audit
from app.api.activity import router as activity_router
from app.api.auth import router as auth_router
from app.api.fsdp import router as fsdp_router
from app.api.maintenance import router as maintenance_router
from app.api.office_logs import router as office_logs_router
from app.auth import require_signed_in
from app.backups import daily_backup
from app.db import DB_PATH, engine
from app.db import SessionLocal as SessionLocal
from app.diagnostics import PrivateErrorMiddleware, configure_diagnostics, unexpected_error_response
from app.login_limits import LoginLimiter
from app.models import LocalUser
from app.product import PRODUCT, PRODUCT_NAME
from app.request_gate import RestoreGateMiddleware, RestoreRequestGate
from app.request_timing import SlowRequestMiddleware
from app.restore_recovery import recover_interrupted_restore
from app.security_headers import SecurityHeadersMiddleware
from app.upgrade import upgrade_database
from app.version import release_version


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    configure_diagnostics(DB_PATH.parent)
    recover_interrupted_restore(DB_PATH, DB_PATH.parent / "backups")
    upgrade_database(engine, DB_PATH)
    try:
        daily_backup(DB_PATH)
    except Exception as caught:
        from app.diagnostics import log_private_exception

        log_private_exception(caught)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.restore_request_gate = RestoreRequestGate()
    application.state.login_limiter = LoginLimiter()
    if not getattr(application.state, "bootstrap_token", None):
        application.state.bootstrap_token = os.environ.get(
            "CATHEDRA_SETUP_TOKEN"
        ) or secrets.token_urlsafe(32)
    try:
        initialize_database()
        with SessionLocal() as database:
            application.state.setup_required = not database.scalar(
                select(func.count()).select_from(LocalUser)
            )
            if application.state.setup_required:
                print(
                    f"Cathedra first-time setup code: {application.state.bootstrap_token}",
                    flush=True,
                )
        yield
    finally:
        engine.dispose()


app = FastAPI(title=f"{PRODUCT_NAME} API", version=release_version(), lifespan=lifespan)
app.add_exception_handler(Exception, unexpected_error_response)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (5174,)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RestoreGateMiddleware)
app.add_middleware(SlowRequestMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
app.add_middleware(PrivateErrorMiddleware)


@app.get("/api/v1/health")
def health(request: Request) -> dict[str, str | bool]:
    directory_identity = hashlib.sha256(
        str(DB_PATH.parent.resolve()).casefold().encode("utf-8")
    ).hexdigest()[:16]
    return {
        "status": "ok",
        "product": PRODUCT,
        "release_version": release_version(),
        "data_directory_identity": directory_identity,
        "desktop_mode": getattr(request.app.state, "shutdown_signal", None) is not None,
        "recovery_required": request.app.state.restore_request_gate.recovery_required,
    }


@app.post("/api/v1/desktop/exit", dependencies=[Depends(require_signed_in)])
def exit_desktop(request: Request) -> dict[str, str]:
    shutdown_signal = getattr(request.app.state, "shutdown_signal", None)
    if shutdown_signal is None:
        raise HTTPException(
            status_code=409, detail="Exit Cathedra is available only in the desktop app."
        )
    shutdown_signal.set()
    return {"status": "closing"}


app.include_router(auth_router, prefix="/api/v1")
for router in (
    fsdp_router,
    maintenance_router,
    activity_router,
    office_logs_router,
):
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_signed_in)])

_default_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_DIST = Path(os.environ.get("CATHEDRA_FRONTEND_DIST", _default_frontend_dist)).resolve()
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str) -> FileResponse:
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found.")
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend assets have not been built.")
    requested_file = (FRONTEND_DIST / path).resolve()
    if FRONTEND_DIST in requested_file.parents and requested_file.is_file():
        return FileResponse(requested_file)
    return FileResponse(FRONTEND_INDEX)
