"""Google delivery is tested offline; no real account, sheet or credentials are used."""

import base64
import copy
import hashlib
import io
import json
import os
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

import app.api.google_sheets as api
import app.google_sheets as sheets

CLIENT = {
    "installed": {
        "client_id": "synthetic-client.apps.googleusercontent.com",
        "client_secret": "synthetic-client-secret",
        "redirect_uris": ["http://localhost"],
        "token_uri": "https://untrusted.invalid/token",
    }
}
TARGET = "synthetic-spreadsheet-123"


class MemoryVault:
    def __init__(self, value=None):
        self.value = copy.deepcopy(value or {})

    def load(self):
        return copy.deepcopy(self.value)

    def save(self, value):
        self.value = copy.deepcopy(value)


def configured(*, connected=True):
    value = {
        "client": sheets.desktop_client(CLIENT),
        "spreadsheet_id": TARGET,
        "last_sync_at": "2026-01-01T00:00:00+00:00",
    }
    if connected:
        value["refresh_token"] = "synthetic-refresh-token"
    return sheets.GoogleSheetsConnection(MemoryVault(value))


@pytest.mark.parametrize(
    "configuration",
    [
        None,
        [],
        {},
        {"installed": []},
        {"installed": {"client_id": "bad", "client_secret": "secret"}},
        {"installed": {**CLIENT["installed"], "redirect_uris": None}},
        {"installed": {**CLIENT["installed"], "redirect_uris": [{}]}},
    ],
)
def test_malformed_desktop_credentials_have_safe_validation(configuration):
    with pytest.raises(sheets.SheetsError, match="Desktop app"):
        sheets.desktop_client(configuration)


def test_desktop_credentials_ignore_uploaded_endpoint_urls():
    assert sheets.desktop_client(CLIENT) == {
        "client_id": CLIENT["installed"]["client_id"],
        "client_secret": CLIENT["installed"]["client_secret"],
    }


@pytest.mark.parametrize(
    "value",
    [
        "https://docs.google.com.evil.invalid/spreadsheets/d/1234567890",
        "https://docs.google.com:443/spreadsheets/d/1234567890",
        "short",
        "../1234567890",
    ],
)
def test_reporting_target_rejects_untrusted_or_invalid_addresses(value):
    with pytest.raises(sheets.SheetsError):
        sheets.spreadsheet_id(value)


def test_target_address_and_configuration_changes_preserve_only_appropriate_state():
    connection = configured()
    result = connection.configure(
        f"https://docs.google.com/spreadsheets/d/{TARGET}/edit#gid=0", None
    )
    assert result["connected"] and result["last_sync_at"]
    connection.configure("other-synthetic-sheet", None)
    assert "last_sync_at" not in connection.vault.value
    assert connection.status()["connected"]
    connection.configure(TARGET, {"installed": {**CLIENT["installed"], "client_secret": "changed"}})
    assert not connection.status()["connected"]
    with pytest.raises(sheets.SheetsError):
        connection.configure(TARGET, {})


@pytest.mark.skipif(os.name != "nt", reason="Actual Windows DPAPI storage")
def test_windows_vault_encrypts_and_roundtrips_secrets(tmp_path):
    path = tmp_path / "private" / "google-connection.bin"
    vault = sheets.WindowsVault(path)
    expected = configured().vault.value
    vault.save(expected)
    assert vault.load() == expected
    assert b"synthetic-refresh-token" not in path.read_bytes()
    assert b"synthetic-client-secret" not in path.read_bytes()
    assert list(path.parent.glob("*.tmp")) == []
    vault.save({})
    assert vault.load() == {}


def test_windows_vault_rejects_corrupt_structure_and_saves_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(sheets, "_protect", lambda value, decrypt=False: value)
    path = tmp_path / "connection.bin"
    vault = sheets.WindowsVault(path)
    assert vault.load() == {}
    for value in [b"[]", b"{", b'{"client": []}', b'{"spreadsheet_id": []}']:
        path.write_bytes(value)
        with pytest.raises(sheets.SheetsError):
            vault.load()
    vault.save(configured().vault.value)
    original = path.read_bytes()
    monkeypatch.setattr(
        sheets.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("secret path"))
    )
    with pytest.raises(sheets.SheetsError, match="saved locally"):
        vault.save({})
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def test_google_requests_are_bounded_literal_and_never_redirect(monkeypatch):
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return Response(b'{"ok": true}')

    def build(handler):
        assert isinstance(handler, sheets._NoRedirect)
        assert handler.redirect_request(None, None, 302, "", {}, "https://evil.invalid") is None
        return Opener()

    monkeypatch.setattr(sheets.urllib.request, "build_opener", build)
    assert sheets.google_request(sheets.TOKEN_URL, form={"code": "a+b"}) == {"ok": True}
    assert calls[0][0].data == b"code=a%2Bb"
    assert calls[0][1] == 25
    sheets.google_request(
        sheets.SHEETS_URL + TARGET, body={"cell": "=1+1"}, token="synthetic-access"
    )
    assert calls[1][0].get_header("Authorization") == "Bearer synthetic-access"
    with pytest.raises(sheets.SheetsError, match="address"):
        sheets.google_request("https://evil.invalid", token="synthetic-access")
    assert len(calls) == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 500, 302])
def test_google_http_failures_never_expose_remote_error_bodies(monkeypatch, code):
    class Opener:
        def open(self, *_args, **_kwargs):
            raise urllib.error.HTTPError(
                sheets.TOKEN_URL,
                code,
                "private error",
                {},
                io.BytesIO(b"private Google account data"),
            )

    monkeypatch.setattr(sheets.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(sheets.SheetsError) as caught:
        sheets.google_request(sheets.TOKEN_URL)
    assert "private" not in str(caught.value)


@pytest.mark.parametrize(
    "raw",
    [b"[]", b"invalid", b"x" * (2 * 1024 * 1024 + 1)],
    ids=["non-object", "invalid-json", "oversized-response"],
)
def test_unexpected_google_response_has_safe_error(monkeypatch, raw):
    class Opener:
        def open(self, *_args, **_kwargs):
            return Response(raw)

    monkeypatch.setattr(sheets.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(sheets.SheetsError):
        sheets.google_request(sheets.TOKEN_URL)


def test_replacement_clears_stale_cells_in_only_dedicated_tab_without_formulas():
    body = sheets.replacement_request(
        {"sheetId": 7, "gridProperties": {"rowCount": 100, "columnCount": 30}},
        [["NAME", "STATUS"], ['=IMPORTXML("private")', None]],
    )
    assert len(body["requests"]) == 1
    update = body["requests"][0]["updateCells"]
    assert update["range"] == {"sheetId": 7}
    assert update["fields"] == "userEnteredValue"
    assert update["rows"][1]["values"] == [
        {"userEnteredValue": {"stringValue": '=IMPORTXML("private")'}},
        {},
    ]
    expanded = sheets.replacement_request(
        {"sheetId": 7, "gridProperties": {"rowCount": 1, "columnCount": 1}},
        [["a", "b"], ["c", "d"]],
    )
    properties = expanded["requests"][0]["updateSheetProperties"]["properties"]
    assert properties == {"sheetId": 7, "gridProperties": {"rowCount": 2, "columnCount": 2}}


def test_sync_refreshes_then_updates_dedicated_existing_tab_and_records_success(monkeypatch):
    connection = configured()
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        if url == sheets.TOKEN_URL:
            return {"access_token": "synthetic-access", "refresh_token": "rotated-refresh"}
        if "?fields=" in url:
            return {
                "sheets": [
                    {"properties": {"sheetId": 10, "title": "UNRELATED"}},
                    {
                        "properties": {
                            "sheetId": 11,
                            "title": sheets.REPORT_TAB,
                            "gridProperties": {"rowCount": 20, "columnCount": 30},
                        }
                    },
                ]
            }
        return {}

    monkeypatch.setattr(sheets, "google_request", request)
    result = connection.sync([["NAME"], ["SYNTHETIC SCHOLAR"]])
    assert result["rows"] == 1
    assert result["synced_at"] == connection.status()["last_sync_at"]
    assert calls[-1][1]["body"]["requests"][0]["updateCells"]["range"] == {"sheetId": 11}
    assert connection.vault.value["refresh_token"] == "rotated-refresh"
    assert "synthetic-access" not in json.dumps(connection.status())
    assert "rotated-refresh" not in json.dumps(connection.status())


def test_new_tab_is_created_before_report_replacement_and_failure_preserves_last_success(
    monkeypatch,
):
    connection = configured()
    calls = []

    def request(url, **kwargs):
        calls.append(kwargs)
        if url == sheets.TOKEN_URL:
            return {"access_token": "synthetic-access"}
        if "?fields=" in url:
            return {"sheets": []}
        if "addSheet" in kwargs["body"]["requests"][0]:
            return {"replies": [{"addSheet": {"properties": {"sheetId": 17}}}]}
        raise sheets.SheetsError("Google did not confirm the update.")

    monkeypatch.setattr(sheets, "google_request", request)
    with pytest.raises(sheets.SheetsError, match="did not confirm"):
        connection.sync([["NAME"]])
    assert calls[-1]["body"]["requests"][-1]["updateCells"]["range"] == {"sheetId": 17}
    assert connection.status()["last_sync_at"] == "2026-01-01T00:00:00+00:00"
    assert not connection.lock.locked()


def test_rotated_refresh_token_survives_later_delivery_failure_without_recording_success(
    monkeypatch,
):
    connection = configured()
    prior_sync = connection.status()["last_sync_at"]

    def request(url, **kwargs):
        if url == sheets.TOKEN_URL:
            return {"access_token": "synthetic-access", "refresh_token": "rotated-after-refresh"}
        assert connection.vault.value["refresh_token"] == "rotated-after-refresh"
        raise sheets.SheetsError("Google could not open the reporting sheet.")

    monkeypatch.setattr(sheets, "google_request", request)
    with pytest.raises(sheets.SheetsError, match="could not open"):
        connection.sync([["NAME"], ["SYNTHETIC SCHOLAR"]])
    assert connection.vault.value["refresh_token"] == "rotated-after-refresh"
    assert connection.status()["last_sync_at"] == prior_sync
    assert not connection.lock.locked()


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"sheets": None},
        {"sheets": [None]},
        {"sheets": [{"properties": {"title": sheets.REPORT_TAB, "sheetId": "oops"}}]},
        {
            "sheets": [
                {"properties": {"title": sheets.REPORT_TAB, "sheetId": 1, "sheetType": "OBJECT"}}
            ]
        },
    ],
)
def test_sync_rejects_unexpected_sheet_details_without_writing(monkeypatch, metadata):
    connection = configured()
    calls = []

    def request(url, **kwargs):
        calls.append(url)
        return {"access_token": "synthetic-access"} if url == sheets.TOKEN_URL else metadata

    monkeypatch.setattr(sheets, "google_request", request)
    with pytest.raises(sheets.SheetsError):
        connection.sync([["NAME"]])
    assert len(calls) == 2


def test_mutating_operations_are_serialized_and_disconnect_only_forgets_local_token():
    connection = configured()
    connection.lock.acquire()
    try:
        for operation, args in [
            (connection.configure, (TARGET, None)),
            (connection.connect, ()),
            (connection.disconnect, ()),
            (connection.sync, ([["NAME"]],)),
        ]:
            with pytest.raises(sheets.SheetsError):
                operation(*args)
    finally:
        connection.lock.release()
    result = connection.disconnect()
    assert result["configured"] and not result["connected"]
    assert result["last_sync_at"] is None
    assert connection.vault.value["spreadsheet_id"] == TARGET


def test_explicit_reconfiguration_and_forget_recover_an_unreadable_local_vault():
    class UnreadableVault(MemoryVault):
        def load(self):
            if not self.value:
                raise sheets.SheetsError("The old Windows account cannot unlock this file.")
            return super().load()

    vault = UnreadableVault()
    connection = sheets.GoogleSheetsConnection(vault)
    with pytest.raises(sheets.SheetsError, match="cannot unlock"):
        connection.configure(TARGET, None)
    assert not connection.lock.locked()
    status = connection.configure(TARGET, CLIENT)
    assert status["configured"] and not status["connected"]

    class ResettableVault(MemoryVault):
        def __init__(self):
            super().__init__()
            self.unreadable = True

        def load(self):
            if self.unreadable:
                raise sheets.SheetsError("This file is corrupt.")
            return super().load()

        def save(self, value):
            super().save(value)
            self.unreadable = False

    reset = sheets.GoogleSheetsConnection(ResettableVault())
    assert not reset.disconnect()["configured"]


def test_oversized_report_stops_before_any_network_request(monkeypatch):
    monkeypatch.setattr(sheets, "MAX_REQUEST_BYTES", 20)
    monkeypatch.setattr(sheets.urllib.request, "build_opener", lambda *_: pytest.fail("No network"))
    with pytest.raises(sheets.SheetsError, match="too large"):
        sheets.google_request(sheets.SHEETS_URL + TARGET, body={"data": "x" * 100})


def test_missing_configuration_and_access_are_actionable_without_holding_lock():
    connection = sheets.GoogleSheetsConnection(MemoryVault())
    for operation, arguments in [(connection.connect, ()), (connection.sync, ([["NAME"]],))]:
        with pytest.raises(sheets.SheetsError):
            operation(*arguments)
        assert not connection.lock.locked()


@pytest.mark.parametrize("reply", [{}, {"replies": []}, {"replies": [None]}])
def test_malformed_new_tab_confirmation_never_writes_report(monkeypatch, reply):
    connection = configured()
    calls = []

    def request(url, **kwargs):
        calls.append(url)
        if url == sheets.TOKEN_URL:
            return {"access_token": "synthetic-access"}
        if "?fields=" in url:
            return {"sheets": []}
        return reply

    monkeypatch.setattr(sheets, "google_request", request)
    with pytest.raises(sheets.SheetsError, match="new reporting tab"):
        connection.sync([["NAME"]])
    assert len(calls) == 3


def test_oauth_callback_checks_state_pkce_and_exact_redirect_then_saves_token(monkeypatch):
    connection = configured(connected=False)
    browser_opened = threading.Event()
    authorization = {}
    token_calls = []

    def browser(url):
        authorization.update(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query))
        browser_opened.set()
        return True

    def request(url, **kwargs):
        token_calls.append((url, kwargs))
        return {"refresh_token": "new-synthetic-refresh"}

    monkeypatch.setattr(sheets.webbrowser, "open", browser)
    monkeypatch.setattr(sheets, "google_request", request)
    connection.connect()
    assert browser_opened.wait(3)
    assert connection.status()["connection_state"] == "waiting"
    redirect = authorization["redirect_uri"][0]
    assert urllib.parse.urlsplit(redirect).hostname == "127.0.0.1"
    for state in ["wrong-state", "é", authorization["state"][0] + "&state=duplicate"]:
        callback = (
            redirect + "?" + urllib.parse.urlencode({"state": state, "code": "untrusted-code"})
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(callback, timeout=3)
        assert caught.value.code == 400
    assert not token_calls
    callback = (
        redirect
        + "?"
        + urllib.parse.urlencode({"state": authorization["state"][0], "code": "synthetic-code"})
    )
    with urllib.request.urlopen(callback, timeout=3) as response:
        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-store"
    assert connection.lock.acquire(timeout=3)
    connection.lock.release()
    assert connection.status()["connected"]
    token_url, token_args = token_calls[0]
    assert token_url == sheets.TOKEN_URL
    form = token_args["form"]
    assert form["redirect_uri"] == redirect
    assert form["code"] == "synthetic-code"
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"].encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == authorization["code_challenge"][0]
    assert authorization["code_challenge_method"] == ["S256"]
    assert authorization["scope"] == [sheets.SCOPE]
    assert connection.vault.value["refresh_token"] == "new-synthetic-refresh"


def test_oauth_incomplete_socket_cannot_hold_connection_lock_forever(monkeypatch):
    connection = sheets.GoogleSheetsConnection(
        configured(connected=False).vault, authorization_timeout=0.15, callback_timeout=0.1
    )
    browser_opened = threading.Event()
    address = []

    def browser(url):
        redirect = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["redirect_uri"][0]
        parsed = urllib.parse.urlsplit(redirect)
        address.extend((parsed.hostname, parsed.port))
        browser_opened.set()
        return True

    monkeypatch.setattr(sheets.webbrowser, "open", browser)
    connection.connect()
    assert browser_opened.wait(3)
    with socket.create_connection(tuple(address), timeout=3) as incomplete:
        incomplete.sendall(b"GET /oauth2/callback")
        assert connection.lock.acquire(timeout=3)
        connection.lock.release()
    assert connection.status()["connection_state"] == "error"
    assert not connection.status()["connected"]


def test_oauth_browser_failure_and_unexpected_error_are_safe(monkeypatch):
    for failure in [False, RuntimeError("private credentials")]:
        connection = configured(connected=False)

        def browser(_url, failure=failure):
            if isinstance(failure, Exception):
                raise failure
            return failure

        monkeypatch.setattr(sheets.webbrowser, "open", browser)
        connection.connect()
        assert connection.lock.acquire(timeout=3)
        connection.lock.release()
        status = connection.status()
        assert status["connection_state"] == "error"
        assert "private" not in status["message"]


def test_google_routes_require_admin_and_confirmed_replacement(client, monkeypatch):
    connection = configured()
    monkeypatch.setattr(api, "connection", connection)
    assert client.get("/api/v1/google-sheets").json()["connected"]
    assert (
        client.post("/api/v1/google-sheets/sync", json={"replace_report": False}).status_code == 422
    )
    assert client.post("/api/v1/google-sheets/sync", json={}).status_code == 422
    malformed = client.post(
        "/api/v1/google-sheets/configure",
        json={"spreadsheet": TARGET, "client_configuration": {"installed": []}},
    )
    assert malformed.status_code == 422
    assert "Desktop app" in malformed.json()["detail"]
    created = client.post(
        "/api/v1/auth/users",
        json={"username": "sheet-reader", "password": "synthetic-password-123", "role": "staff"},
    )
    assert created.status_code == 201
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"username": "sheet-reader", "password": "synthetic-password-123"},
    ).json()
    staff_headers = {"Authorization": f"Bearer {signed_in['token']}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=staff_headers,
        json={
            "current_password": "synthetic-password-123",
            "new_password": "new-synthetic-password-123",
        },
    )
    assert changed.status_code == 204
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"username": "sheet-reader", "password": "new-synthetic-password-123"},
    ).json()
    staff_headers = {"Authorization": f"Bearer {signed_in['token']}"}
    operations = [
        ("get", "", None),
        ("post", "/configure", {"spreadsheet": TARGET}),
        ("post", "/connect", None),
        ("delete", "/connection", None),
        ("post", "/sync", {"replace_report": True}),
    ]
    for method, path, payload in operations:
        response = client.request(
            method, "/api/v1/google-sheets" + path, headers=staff_headers, json=payload
        )
        assert response.status_code == 403
    client.headers.clear()
    assert client.get("/api/v1/google-sheets").status_code == 401


def test_admin_sync_uses_current_export_and_does_not_expose_credentials(client, monkeypatch):
    connection = configured()
    monkeypatch.setattr(api, "connection", connection)
    monkeypatch.setattr(api, "google_report_table", lambda _db: (["NAME"], [["SYNTHETIC SCHOLAR"]]))
    received = []
    monkeypatch.setattr(connection, "sync", lambda rows: received.append(rows) or {"rows": 1})
    response = client.post("/api/v1/google-sheets/sync", json={"replace_report": True})
    assert response.status_code == 200
    assert received == [[["NAME"], ["SYNTHETIC SCHOLAR"]]]
    assert "synthetic-refresh" not in response.text
