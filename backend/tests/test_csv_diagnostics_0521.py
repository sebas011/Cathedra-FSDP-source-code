"""Excel downloads and private failure references use synthetic records only."""

import asyncio
import csv
import json
import logging
import socket
import sqlite3
import threading
import time
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
import uvicorn
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, StatementError

import app.main as main
from app.api.fsdp import commit_record
from app.db import engine
from app.diagnostics import PrivateErrorMiddleware
from app.request_gate import RestoreGateMiddleware
from app.security_headers import SECURITY_HEADERS


@pytest.fixture
def private_logs(caplog):
    logger = logging.getLogger("cathedra.errors")
    logger.addHandler(caplog.handler)
    with caplog.at_level(logging.ERROR, logger=logger.name):
        yield caplog
    logger.removeHandler(caplog.handler)


@pytest.mark.parametrize("export", ["directory", "education", "report", "payback", "office_logs"])
def test_excel_utf8_bom_preserves_accents_and_formula_guards(client, export):
    saved = client.post(
        "/api/v1/fsdp",
        json={
            "name": '=José Peña, "École"',
            "department": "CAS",
            "education": [{"degree": '=Éducation, "Étude"', "institution": "+École"}],
            "participations": [
                {
                    "program_name": '-Étude, "Thèse"',
                    "contract_completed_on": "2000-01-01",
                    "remarks": '=Évaluation\n"Peña"',
                }
            ],
        },
    )
    assert saved.status_code == 201, saved.text
    note = client.post(
        "/api/v1/office-logs",
        json={
            "scholar_id": saved.json()["id"],
            "note": '=Évaluation\n"Peña"',
        },
    )
    assert note.status_code == 201, note.text
    contract = json.loads(
        (Path(__file__).resolve().parents[2] / "docs/current/EXPORT_CONTRACTS.json").read_text(
            "utf-8"
        )
    )[export]
    response = client.get(contract["path"])
    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.content.count(b"\xef\xbb\xbf") == 1
    assert response.headers["content-type"].startswith("text/csv; charset=utf-8")
    assert "attachment; filename=" in response.headers["content-disposition"]
    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
    for header in contract["sections"].values():
        assert rows.count(header) == 1
    headings = contract["sections"]["records"]
    row = rows[rows.index(headings) + 1]
    assert len(row) == len(headings)
    name_column = "Name" if "Name" in headings else "Scholar"
    assert row[headings.index(name_column)] == "'" + saved.json()["name"]
    if export == "education":
        assert row[headings.index("Degree")] == "'=" + 'ÉDUCATION, "ÉTUDE"'
        assert row[headings.index("Institution")] == "'+ÉCOLE"
    elif export == "office_logs":
        assert row[headings.index("Note")] == "'=" + 'ÉVALUATION\n"PEÑA"'
    else:
        column = "Program applied" if export == "report" else "Program"
        assert row[headings.index(column)] == "'-" + 'ÉTUDE, "THÈSE"'


@pytest.mark.parametrize("error_type", [RuntimeError, StatementError])
def test_unexpected_500_logs_only_private_code_metadata(client, private_logs, error_type):
    sentinel = "SENSITIVE-0521-name-password-token-query-body-sql"

    def failing_route(record_id: str, request: Request):
        assert request.headers["X-Private-Header"] == sentinel
        if error_type is StatementError:
            raise StatementError(
                sentinel, f"SELECT '{sentinel}'", {"password": sentinel}, ValueError(sentinel)
            )
        raise RuntimeError(sentinel)

    route = APIRoute("/api/v1/synthetic-diagnostics/{record_id}", failing_route, methods=["POST"])
    main.app.router.routes.insert(0, route)
    try:
        # The client fixture supplies only an in-memory database and bypasses initialization.
        with TestClient(main.app, raise_server_exceptions=False) as errors_client:
            response = errors_client.post(
                f"/api/v1/synthetic-diagnostics/{sentinel}",
                params={"secret": sentinel},
                json={"record": sentinel},
                headers={"Authorization": f"Bearer {sentinel}", "X-Private-Header": sentinel},
            )
        assert response.status_code == 500
        result = response.json()
        assert set(result) == {"detail", "reference"}
        assert len(result["reference"]) == 32
        assert response.headers["cache-control"] == "no-store"
        for key, value in SECURITY_HEADERS.items():
            assert response.headers[key] == value
        assert sentinel not in response.text
        messages = [
            record.getMessage()
            for record in private_logs.records
            if record.name == "cathedra.errors"
        ]
        assert messages and all(sentinel not in message for message in messages)
        event = json.loads(
            next(
                message.removeprefix("private_error ")
                for message in messages
                if result["reference"] in message
            )
        )
        assert event["exception_class"] == error_type.__name__
        assert event["method"] == "POST"
        assert event["route_template"] == "/api/v1/synthetic-diagnostics/{record_id}"
        assert event["frames"][-1]["function"] == "failing_route"
        assert all(set(frame) == {"filename", "function", "line"} for frame in event["frames"])
        assert all(
            record.exc_info is None
            for record in private_logs.records
            if record.name == "cathedra.errors"
        )
    finally:
        main.app.router.routes.remove(route)


@pytest.mark.parametrize(
    "code,message,expected",
    [
        (
            sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY,
            "FOREIGN KEY constraint failed",
            "A linked record changed",
        ),
        (
            sqlite3.SQLITE_CONSTRAINT_NOTNULL,
            "NOT NULL constraint failed: scholars.name",
            "some details conflict with stored data",
        ),
        (
            sqlite3.SQLITE_CONSTRAINT_CHECK,
            "CHECK constraint failed: private_name",
            "some details conflict with stored data",
        ),
        (
            sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            "UNIQUE constraint failed: programs.name",
            "A program with this name already exists",
        ),
        (
            sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            "UNIQUE constraint failed: programs.canonical_key",
            "A program with this name already exists",
        ),
        (None, "UNIQUE constraint failed: programs.name", "some details conflict with stored data"),
    ],
)
def test_commit_integrity_failures_explain_constraint_without_record_data(
    private_logs, code, message, expected
):
    sentinel = "SENSITIVE-0521-SQL-parameter"
    original = sqlite3.IntegrityError(message)
    if code is not None:
        original.sqlite_errorcode = code
    error = IntegrityError(f"INSERT '{sentinel}'", {"name": sentinel}, original)
    session = SimpleNamespace(commit=Mock(side_effect=error), rollback=Mock())
    with pytest.raises(HTTPException) as caught:
        commit_record(session)
    session.rollback.assert_called_once()
    assert caught.value.status_code == 409
    assert expected in caught.value.detail
    assert "Reference: " in caught.value.detail
    assert sentinel not in caught.value.detail
    messages = [
        record.getMessage() for record in private_logs.records if record.name == "cathedra.errors"
    ]
    assert messages and all(
        sentinel not in message and message != str(error) for message in messages
    )
    assert all(
        record.exc_info is None
        for record in private_logs.records
        if record.name == "cathedra.errors"
    )


def test_database_engine_hides_bound_parameters():
    assert engine.hide_parameters is True


@pytest.mark.parametrize("failure_phase", ["before_headers", "sending_headers", "after_headers"])
def test_failed_error_delivery_does_not_propagate_private_transport_exceptions(
    private_logs, failure_phase
):
    sentinel = "SENSITIVE-0521-transport-error"
    messages = []

    async def application(scope, receive, send):
        if failure_phase == "before_headers":
            raise RuntimeError(sentinel)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"public", "more_body": True})
        raise RuntimeError(sentinel)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)
        if failure_phase == "sending_headers" and message["type"] == "http.response.start":
            raise OSError(sentinel)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            raise OSError(sentinel)

    asyncio.run(
        PrivateErrorMiddleware(application)(
            {
                "type": "http",
                "method": "GET",
                "path": f"/api/v1/synthetic/{sentinel}",
                "route": SimpleNamespace(path="/api/v1/synthetic/{record_id}"),
            },
            receive,
            send,
        )
    )
    assert sum(message["type"] == "http.response.start" for message in messages) == 1
    assert all(sentinel not in record.getMessage() for record in private_logs.records)
    assert all(
        record.exc_info is None
        for record in private_logs.records
        if record.name == "cathedra.errors"
    )


def test_uvicorn_does_not_log_sync_middleware_or_streaming_exception_data(
    client, private_logs, monkeypatch
):
    sentinel = "SENSITIVE-0521-live-server-exception"

    def synchronous_failure():
        raise RuntimeError(sentinel)

    async def streaming_failure():
        async def chunks():
            yield b"Public partial result"
            raise RuntimeError(sentinel)

        return StreamingResponse(chunks(), media_type="text/plain")

    original_gate = RestoreGateMiddleware.__call__

    async def middleware_failure(self, scope, receive, send):
        if scope.get("path") == "/api/v1/synthetic-live/middleware":
            raise RuntimeError(sentinel)
        await original_gate(self, scope, receive, send)

    monkeypatch.setattr(RestoreGateMiddleware, "__call__", middleware_failure)
    routes = [
        APIRoute("/api/v1/synthetic-live/synchronous", synchronous_failure),
        APIRoute("/api/v1/synthetic-live/streaming", streaming_failure),
    ]
    main.app.router.routes[0:0] = routes
    server_logger = logging.getLogger("uvicorn.error")
    server_logger.addHandler(private_logs.handler)
    server = None
    server_thread = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            address = listener.getsockname()
            # The existing fixture supplies an in-memory DB and initialized app state.
            server = uvicorn.Server(
                uvicorn.Config(
                    main.app,
                    host=address[0],
                    port=address[1],
                    lifespan="off",
                    log_config=None,
                    access_log=False,
                )
            )
            server_thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            server_thread.start()
            deadline = time.monotonic() + 5
            while not server.started and server_thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with httpx.Client(
                base_url=f"http://{address[0]}:{address[1]}", timeout=5
            ) as network_client:
                for kind in ("synchronous", "middleware"):
                    response = network_client.get(f"/api/v1/synthetic-live/{kind}")
                    assert response.status_code == 500
                    assert response.json()["reference"]
                    assert response.headers["cache-control"] == "no-store"
                    assert sentinel not in response.text
                response = network_client.get("/api/v1/synthetic-live/streaming")
                assert response.status_code == 200
                assert response.text == "Public partial result"
                assert response.headers["cache-control"] == "no-store"
            messages = [record.getMessage() for record in private_logs.records]
            assert all(sentinel not in message for message in messages)
            errors = [record for record in private_logs.records if record.name == "cathedra.errors"]
            assert len(errors) >= 3
            assert all(record.exc_info is None for record in errors)
            assert not [
                record
                for record in private_logs.records
                if record.name == "uvicorn.error" and record.exc_info
            ]
    finally:
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=5)
            assert not server_thread.is_alive()
        server_logger.removeHandler(private_logs.handler)
        for route in routes:
            main.app.router.routes.remove(route)


def test_read_scholar_classifies_each_grant_once(client, monkeypatch):
    import app.contract_rules as contract_rules
    import app.fsdp_reporting as reporting

    saved = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Synthetic classification count",
            "participations": [
                {"program_name": "Synthetic first", "contract_completed_on": "2000-01-01"},
                {"program_name": "Synthetic second"},
            ],
        },
    )
    assert saved.status_code == 201, saved.text
    classify = Mock(wraps=contract_rules.assess_contract)
    monkeypatch.setattr(reporting, "assess_contract", classify)
    response = client.get(f"/api/v1/fsdp/{saved.json()['id']}")
    assert response.status_code == 200
    assert classify.call_count == 2
    assert response.json()["participations"] == saved.json()["participations"]
