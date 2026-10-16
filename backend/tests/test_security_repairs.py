import importlib.util
import socket
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.api.auth as accounts
import app.main as main
from app.db import Base, get_db
from app.models import LocalSession, LocalUser


@contextmanager
def empty_installation(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def database():
        with sessions() as session:
            yield session

    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[get_db] = database
    monkeypatch.setattr(main, "initialize_database", lambda: None)
    monkeypatch.setattr(main, "SessionLocal", sessions)
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            yield client, sessions
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)
        engine.dispose()


def credentials(name="owner"):
    return {"username": name, "password": "synthetic-password-123"}


def test_bootstrap_requires_private_capability(tmp_path, monkeypatch):
    with empty_installation(tmp_path, monkeypatch) as (client, sessions):
        assert client.post("/api/v1/auth/setup", json=credentials()).status_code == 403
        assert (
            client.post(
                "/api/v1/auth/setup", json=credentials(), headers={"X-Cathedra-Setup": "wrong"}
            ).status_code
            == 403
        )
        headers = {"X-Cathedra-Setup": main.app.state.bootstrap_token}
        assert (
            client.post(
                "/api/v1/auth/setup",
                json=credentials(),
                headers={**headers, "Origin": "https://attacker.example"},
            ).status_code
            == 403
        )
        assert (
            client.post("/api/v1/auth/setup", json=credentials(), headers=headers).status_code
            == 201
        )
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(LocalUser)) == 1


def test_concurrent_bootstrap_creates_one_admin_and_session(tmp_path, monkeypatch):
    with empty_installation(tmp_path, monkeypatch) as (client, sessions):
        headers = {"X-Cathedra-Setup": main.app.state.bootstrap_token}
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(
                workers.map(
                    lambda name: (
                        client.post(
                            "/api/v1/auth/setup", json=credentials(name), headers=headers
                        ).status_code
                    ),
                    ["owner-one", "owner-two"],
                )
            )
        assert sorted(results) == [201, 409]
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(LocalUser)) == 1
            assert session.scalar(select(func.count()).select_from(LocalSession)) == 1


def test_bootstrap_failure_rolls_back_and_can_retry(tmp_path, monkeypatch):
    with empty_installation(tmp_path, monkeypatch) as (client, sessions):
        headers = {"X-Cathedra-Setup": main.app.state.bootstrap_token}
        original = accounts.create_session

        def failed_session(*args, **kwargs):
            raise RuntimeError("synthetic session insertion failure")

        monkeypatch.setattr(accounts, "create_session", failed_session)
        assert (
            client.post("/api/v1/auth/setup", json=credentials(), headers=headers).status_code
            == 500
        )
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(LocalUser)) == 0
        monkeypatch.setattr(accounts, "create_session", original)
        assert (
            client.post("/api/v1/auth/setup", json=credentials(), headers=headers).status_code
            == 201
        )


def test_launcher_does_not_open_an_occupied_service(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "desktop" / "run_cathedra.py"
    spec = importlib.util.spec_from_file_location("launcher_security_test", path)
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    with socket.socket() as foreign:
        foreign.bind(("127.0.0.1", 0))
        foreign.listen()
        args = SimpleNamespace(
            data_dir=str(tmp_path),
            port=foreign.getsockname()[1],
            no_browser=False,
            update_target=None,
        )
        monkeypatch.setattr(launcher, "parse_arguments", lambda: args)
        monkeypatch.setattr(launcher, "service_is_ready", lambda *args: True)
        opened = []
        monkeypatch.setattr(launcher, "open_app_window", lambda *args: opened.append(args))
        import pytest

        with pytest.raises(RuntimeError, match="already in use"):
            launcher.main()
        assert opened == []


def test_legacy_short_username_can_still_sign_in(client):
    from app.auth import password_hash

    provider = main.app.dependency_overrides[get_db]()
    with next(provider) as database:
        database.add(
            LocalUser(
                username="ab", password_hash=password_hash("legacy-password-123"), role="admin"
            )
        )
        database.commit()
    provider.close()
    response = client.post(
        "/api/v1/auth/login", json={"username": " ab ", "password": "legacy-password-123"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "ab"
