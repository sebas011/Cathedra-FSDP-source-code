import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.api import auth as account_api
from app.auth import password_hash
from app.db import Base
from app.login_limits import LoginLimiter
from app.models import LocalSession, LocalUser


def test_rotation_rejects_login_verified_with_old_password(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'auth.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        user = LocalUser(
            username="race-user", password_hash=password_hash("old-password-123"), role="staff"
        )
        database.add(user)
        database.commit()
        user_id = user.id
    entered = threading.Event()
    release = threading.Event()
    original_verify = account_api.verify_password

    def paused_verify(password, stored):
        verified = original_verify(password, stored)
        entered.set()
        assert release.wait(10)
        return verified

    monkeypatch.setattr(account_api, "verify_password", paused_verify)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(login_limiter=LoginLimiter())),
        client=SimpleNamespace(host="local"),
    )

    def login():
        with Session(engine) as database:
            try:
                account_api.login(
                    account_api.LoginCredentials(username="race-user", password="old-password-123"),
                    request,
                    database,
                )
            except HTTPException as error:
                return error.status_code
            return 200

    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(login)
        assert entered.wait(10)
        try:
            with Session(engine) as database:
                user = database.get(LocalUser, user_id)
                user.password_hash = password_hash("new-password-123")
                database.execute(delete(LocalSession).where(LocalSession.user_id == user_id))
                database.commit()
        finally:
            release.set()
        assert pending.result(timeout=10) == 401
    with Session(engine) as database:
        assert database.scalar(select(func.count()).select_from(LocalSession)) == 0
    engine.dispose()


def test_concurrent_disables_leave_one_active_administrator(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'admins.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        database.add_all(
            [
                LocalUser(
                    username=f"admin-{index}",
                    password_hash="unused",
                    role="admin",
                    is_active=True,
                    must_change_password=False,
                )
                for index in range(2)
            ]
        )
        database.commit()
        user_ids = list(database.scalars(select(LocalUser.id)))
    barrier = threading.Barrier(2)

    def disable(user_id):
        with Session(engine) as database:
            actor = database.get(LocalUser, user_id)
            barrier.wait(timeout=10)
            try:
                account_api.set_account_status(
                    user_id, account_api.AccountStatusUpdate(active=False), database, actor
                )
            except HTTPException as error:
                return error.status_code
            return 200

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(disable, user_ids))
    assert sorted(results) == [200, 409]
    with Session(engine) as database:
        assert (
            database.scalar(
                select(func.count()).select_from(LocalUser).where(LocalUser.is_active.is_(True))
            )
            == 1
        )
    engine.dispose()
