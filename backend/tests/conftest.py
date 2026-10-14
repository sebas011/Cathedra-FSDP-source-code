from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app.db import Base, get_db
from app.main import app
from app.migrations import run_migrations
from app.product import bind_empty_database


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON")
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        bind_empty_database(connection)
        run_migrations(connection)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    original_session_local = main.SessionLocal
    original_initialize_database = main.initialize_database
    main.SessionLocal = TestingSession
    main.initialize_database = lambda: None
    try:
        with TestClient(app) as test_client:
            setup = test_client.post(
                "/api/v1/auth/setup",
                json={"username": "test-admin", "password": "test-password-123"},
                headers={"X-Cathedra-Setup": app.state.bootstrap_token},
            )
            assert setup.status_code == 201
            test_client.headers.update({"Authorization": f"Bearer {setup.json()['token']}"})
            yield test_client
    finally:
        main.SessionLocal = original_session_local
        main.initialize_database = original_initialize_database
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
