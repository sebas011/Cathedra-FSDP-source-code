import hmac
import threading
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity_audit import add_activity
from app.auth import (
    PASSWORD_ITERATIONS,
    create_session,
    password_hash,
    require_admin,
    require_signed_in,
    token_digest,
    verify_password,
)
from app.db import get_db
from app.models import LocalSession, LocalUser

router = APIRouter(prefix="/auth", tags=["Local Accounts"])
setup_lock = threading.Lock()
dummy_password_hash = password_hash("Cathedra non-account verification")


class Credentials(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=80)]
    password: str = Field(min_length=10, max_length=200)


class UserCreate(Credentials):
    role: str = Field(pattern="^(admin|staff)$")


class LoginCredentials(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    password: str = Field(min_length=10, max_length=200)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=10, max_length=200)


def user_data(user: LocalUser) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "created_at": user.created_at,
    }


def session_data(db: Session, user: LocalUser) -> dict[str, object]:
    return {"token": create_session(db, user), "user": user_data(user)}


def begin_account_write(db: Session) -> None:
    db.rollback()
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")


@router.get("/status")
def account_status(db: Session = Depends(get_db)) -> dict[str, bool]:
    return {"setup_required": (db.scalar(select(func.count()).select_from(LocalUser)) or 0) == 0}


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup_first_admin(
    payload: Credentials,
    request: Request,
    db: Session = Depends(get_db),
    setup_token: str = Header(default="", alias="X-Cathedra-Setup"),
) -> dict[str, object]:
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        str(request.base_url).rstrip("/"),
    }:
        raise HTTPException(
            status_code=403, detail="Setup must be completed from this local Cathedra window."
        )
    if db.scalar(select(func.count()).select_from(LocalUser)):
        raise HTTPException(
            status_code=409, detail="An administrator account has already been set up."
        )
    db.rollback()
    expected = getattr(request.app.state, "bootstrap_token", "")
    if not expected or not hmac.compare_digest(setup_token, expected):
        raise HTTPException(
            status_code=403,
            detail="First setup requires the private setup code from this app's launch or development console.",
        )
    hashed_password = password_hash(payload.password)
    with setup_lock:
        try:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            if (db.scalar(select(func.count()).select_from(LocalUser)) or 0) != 0:
                raise HTTPException(
                    status_code=409, detail="An administrator account has already been set up."
                )
            user = LocalUser(username=payload.username, password_hash=hashed_password, role="admin")
            db.add(user)
            db.flush()
            token = create_session(db, user, commit=False)
            db.commit()
            request.app.state.bootstrap_token = ""
            return {"token": token, "user": user_data(user)}
        except Exception:
            db.rollback()
            raise


@router.post("/login")
def login(
    payload: LoginCredentials, request: Request, db: Session = Depends(get_db)
) -> dict[str, object]:
    limiter = request.app.state.login_limiter
    with limiter.verification():
        user = db.scalar(
            select(LocalUser).where(func.lower(LocalUser.username) == func.lower(payload.username))
        )
        reservation = limiter.check(
            payload.username,
            request.client.host if request.client else "local",
            registered=user is not None,
        )
        try:
            verified = verify_password(
                payload.password,
                user.password_hash if user and user.is_active else dummy_password_hash,
            )
            if user is None or not user.is_active or not verified:
                raise HTTPException(status_code=401, detail="Username or password is incorrect.")
            user_id, verified_hash = user.id, user.password_hash
            begin_account_write(db)
            user = db.get(LocalUser, user_id, populate_existing=True)
            if user is None or not user.is_active or user.password_hash != verified_hash:
                db.rollback()
                raise HTTPException(status_code=401, detail="Username or password is incorrect.")
            if int(verified_hash.split("$", 3)[1]) < PASSWORD_ITERATIONS:
                user.password_hash = password_hash(payload.password)
            result = session_data(db, user)
        except HTTPException:
            raise
        except Exception:
            limiter.release_attempt(reservation)
            raise
        limiter.release_attempt(reservation)
        return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_signed_in),
) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    db.query(LocalSession).filter(LocalSession.token_hash == token_digest(token)).delete()
    db.commit()


@router.get("/me")
def current_user(user: LocalUser = Depends(require_signed_in)) -> dict[str, object]:
    return user_data(user)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> list[dict[str, object]]:
    return [
        user_data(user) for user in db.scalars(select(LocalUser).order_by(LocalUser.username)).all()
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> dict[str, object]:
    username = payload.username.strip()
    hashed_password = password_hash(payload.password)
    begin_account_write(db)
    try:
        if db.scalar(
            select(LocalUser.id).where(func.lower(LocalUser.username) == func.lower(username))
        ):
            raise HTTPException(status_code=409, detail="That username is already in use.")
        user = LocalUser(
            username=username,
            password_hash=hashed_password,
            role=payload.role,
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_data(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is already in use.") from None
    except Exception:
        db.rollback()
        raise


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    user: LocalUser = Depends(require_signed_in),
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Your current password is incorrect."
        )
    user_id, verified_hash = user.id, user.password_hash
    new_hash = password_hash(payload.new_password)
    begin_account_write(db)
    user = db.get(LocalUser, user_id, populate_existing=True)
    if user is None or not user.is_active or user.password_hash != verified_hash:
        db.rollback()
        raise HTTPException(status_code=401, detail="Your account changed. Please sign in again.")
    user.password_hash = new_hash
    user.must_change_password = False
    db.query(LocalSession).filter(LocalSession.user_id == user.id).delete()
    db.commit()


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
) -> None:
    new_hash = password_hash(payload.new_password)
    begin_account_write(db)
    user = db.get(LocalUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Local account not found.")
    user.password_hash = new_hash
    user.must_change_password = True
    db.query(LocalSession).filter(LocalSession.user_id == user.id).delete()
    db.commit()


class AccountStatusUpdate(BaseModel):
    active: bool


@router.put("/users/{user_id}/status")
def set_account_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    _: LocalUser = Depends(require_admin),
) -> dict[str, object]:
    begin_account_write(db)
    user = db.get(LocalUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Local account not found.")
    if not payload.active and user.is_active and user.role == "admin":
        administrators = (
            db.scalar(
                select(func.count())
                .select_from(LocalUser)
                .where(LocalUser.role == "admin", LocalUser.is_active.is_(True))
            )
            or 0
        )
        if administrators <= 1:
            raise HTTPException(
                status_code=409, detail="The last active administrator cannot be disabled."
            )
    user.is_active = payload.active
    if not payload.active:
        db.query(LocalSession).filter(LocalSession.user_id == user_id).delete()
    db.commit()
    return user_data(user)


@router.post("/users/{user_id}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user_sessions(
    user_id: int, db: Session = Depends(get_db), _: LocalUser = Depends(require_admin)
) -> None:
    if db.get(LocalUser, user_id) is None:
        raise HTTPException(status_code=404, detail="Local account not found.")
    db.query(LocalSession).filter(LocalSession.user_id == user_id).delete()
    add_activity(
        db,
        "Local Accounts",
        f"Revoked Local Accounts sessions #{user_id}",
        record_type="local_users",
        record_id=user_id,
        operation="Revoked sessions",
    )
    db.commit()
