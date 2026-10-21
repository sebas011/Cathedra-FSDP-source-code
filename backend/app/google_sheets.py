"""Manual, one-way Google report delivery. No scholar data is stored in this module."""

import base64
import ctypes
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.client import HTTPException as HTTPProtocolError
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.diagnostics import log_private_exception

REPORT_TAB = "CATHEDRA REPORT"
SCOPE = "https://www.googleapis.com/auth/spreadsheets"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets/"
MAX_REQUEST_BYTES = 8 * 1024 * 1024


class SheetsError(Exception):
    """A safe, actionable message that may be returned to the local user."""


def spreadsheet_id(value: str) -> str:
    value = value.strip()
    if value.startswith("https://"):
        parsed = urllib.parse.urlsplit(value)
        if parsed.netloc != "docs.google.com":
            raise SheetsError("Use a Google Sheets address from docs.google.com.")
        match = re.fullmatch(r"/spreadsheets/d/([A-Za-z0-9_-]+)(?:/.*)?", parsed.path)
        value = match[1] if match else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", value):
        raise SheetsError("Enter the reporting spreadsheet's Google Sheets address or ID.")
    return value


def desktop_client(configuration: dict) -> dict:
    installed = configuration.get("installed") if isinstance(configuration, dict) else None
    if not isinstance(installed, dict):
        raise SheetsError("Choose the JSON credentials for a Google Desktop app OAuth client.")
    client_id = installed.get("client_id", "")
    client_secret = installed.get("client_secret", "")
    redirect_uris = installed.get("redirect_uris", [])
    if (
        not isinstance(client_id, str)
        or not re.fullmatch(r"[A-Za-z0-9._-]+\.apps\.googleusercontent\.com", client_id)
        or not isinstance(client_secret, str)
        or not 1 <= len(client_secret) <= 1000
        or not isinstance(redirect_uris, list)
        or not any(
            isinstance(uri, str) and uri in {"http://localhost", "http://127.0.0.1"}
            for uri in redirect_uris
        )
    ):
        raise SheetsError("Choose the JSON credentials for a Google Desktop app OAuth client.")
    # Never follow endpoint URLs supplied in an uploaded configuration.
    return {"client_id": client_id, "client_secret": client_secret}


def _protect(value: bytes, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise SheetsError("Google connection storage requires the Windows desktop app.")
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    destination = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        function = crypt.CryptUnprotectData
        function.argtypes = [
            ctypes.POINTER(Blob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(Blob),
        ]
    else:
        function = crypt.CryptProtectData
        function.argtypes = [
            ctypes.POINTER(Blob),
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(Blob),
        ]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(destination)):
        raise SheetsError("Windows could not unlock the Google connection. Reconnect this account.")
    try:
        return ctypes.string_at(destination.data, destination.size)
    finally:
        kernel.LocalFree(ctypes.cast(destination.data, ctypes.c_void_p))


class WindowsVault:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        if self.path.is_symlink():
            raise SheetsError("The Google connection file must be a regular local file.")
        if not self.path.exists():
            return {}
        try:
            saved = json.loads(_protect(self.path.read_bytes(), decrypt=True))
            if not isinstance(saved, dict):
                raise ValueError("Unexpected connection structure")
            if "client" in saved:
                client = saved["client"]
                if not isinstance(client, dict):
                    raise ValueError("Unexpected client structure")
                desktop_client({"installed": {**client, "redirect_uris": ["http://localhost"]}})
            if "spreadsheet_id" in saved:
                if not isinstance(saved["spreadsheet_id"], str):
                    raise ValueError("Unexpected spreadsheet structure")
                saved["spreadsheet_id"] = spreadsheet_id(saved["spreadsheet_id"])
            if "refresh_token" in saved:
                _required_token(saved, "refresh_token")
                if not saved.get("client") or not saved.get("spreadsheet_id"):
                    raise ValueError("Incomplete connection structure")
            return saved
        except (ValueError, OSError) as caught:
            raise SheetsError(
                "The saved Google connection could not be read. Reconfigure it."
            ) from caught

    def save(self, value: dict) -> None:
        encrypted = _protect(json.dumps(value).encode("utf-8"))
        temporary = self.path.with_name(self.path.name + "." + secrets.token_hex(8) + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.is_symlink():
                raise SheetsError("The Google connection file must be a regular local file.")
            with temporary.open("xb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError as caught:
            raise SheetsError(
                "The Google connection could not be saved locally. Check storage access."
            ) from caught
        finally:
            temporary.unlink(missing_ok=True)


def _required_token(response: dict, key: str) -> str:
    value = response.get(key)
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 8192
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise SheetsError("Google did not provide continuing access. Reconnect the account.")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def google_request(
    url: str,
    *,
    body: dict | None = None,
    token: str | None = None,
    form: dict | None = None,
    method: str | None = None,
) -> dict:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in {"oauth2.googleapis.com", "sheets.googleapis.com"}
        or parsed.username
        or parsed.password
    ):
        raise SheetsError("The Google request address is not supported.")
    headers = {"Accept": "application/json"}
    payload = None
    if form is not None:
        payload = urllib.parse.urlencode(form).encode("ascii")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if payload and len(payload) > MAX_REQUEST_BYTES:
        raise SheetsError("This report is too large for one update. Use the CSV export instead.")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=25) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise SheetsError("Google returned an unexpectedly large response. Try again.")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise SheetsError(
                "Google returned an unexpected response. Check the reporting sheet before retrying."
            )
        return result
    except urllib.error.HTTPError as caught:
        if caught.code in {400, 401}:
            message = (
                "Google rejected the connection or request. Check setup and reconnect if needed."
            )
        elif caught.code in {403, 404}:
            message = "Google could not open the reporting sheet. Check its address, sharing and Sheets API access."
        elif caught.code == 429:
            message = "Google is limiting requests. Wait a minute before updating the sheet again."
        else:
            message = (
                "Google did not confirm the update. Check the reporting sheet before retrying."
            )
        raise SheetsError(message) from None
    except (OSError, ValueError, HTTPProtocolError) as caught:
        raise SheetsError(
            "Google could not be reached. Check internet access and try again."
        ) from caught


def replacement_request(sheet: dict, rows: list[list[object]]) -> dict:
    """One atomic batch clears stale cells and writes literal values in the dedicated tab."""
    sheet_id = sheet["sheetId"]
    width = max((len(row) for row in rows), default=1)
    height = max(len(rows), 1)
    grid = sheet.get("gridProperties", {})
    row_count = max(height, grid.get("rowCount", 1))
    column_count = max(width, grid.get("columnCount", 1))
    requests = []
    if row_count != grid.get("rowCount") or column_count != grid.get("columnCount"):
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {
                            "rowCount": row_count,
                            "columnCount": column_count,
                        },
                    },
                    "fields": "gridProperties.rowCount,gridProperties.columnCount",
                }
            }
        )
    requests.append(
        {
            "updateCells": {
                "range": {"sheetId": sheet_id},
                "rows": [
                    {
                        "values": [
                            {}
                            if value is None
                            else {"userEnteredValue": {"stringValue": str(value)}}
                            for value in row
                        ]
                    }
                    for row in rows
                ],
                "fields": "userEnteredValue",
            }
        }
    )
    return {"requests": requests, "includeSpreadsheetInResponse": False}


class GoogleSheetsConnection:
    def __init__(self, vault, *, authorization_timeout: float = 180, callback_timeout: float = 2):
        self.vault = vault
        self.lock = threading.Lock()
        self.state = "idle"
        self.message: str | None = None
        self.authorization_timeout = authorization_timeout
        self.callback_timeout = callback_timeout

    def status(self) -> dict:
        saved = self.vault.load()
        return {
            "configured": bool(saved.get("client") and saved.get("spreadsheet_id")),
            "connected": bool(saved.get("refresh_token")),
            "spreadsheet_id": saved.get("spreadsheet_id"),
            "worksheet": REPORT_TAB,
            "last_sync_at": saved.get("last_sync_at"),
            "connection_state": self.state,
            "message": self.message,
        }

    def configure(self, spreadsheet: str, client_configuration: dict | None) -> dict:
        if not self.lock.acquire(blocking=False):
            raise SheetsError("A Google operation is still running. Wait for it to finish.")
        try:
            target = spreadsheet_id(spreadsheet)
            uploaded_client = (
                desktop_client(client_configuration) if client_configuration is not None else None
            )
            try:
                saved = self.vault.load()
            except SheetsError:
                if uploaded_client is None:
                    raise
                # Valid explicit reconfiguration can recover an unreadable DPAPI file.
                saved = {}
            client = uploaded_client or saved.get("client")
            if not client:
                raise SheetsError("Choose your Google Desktop app credentials JSON first.")
            if saved.get("client") != client:
                saved = {}
            if saved.get("spreadsheet_id") != target:
                saved.pop("last_sync_at", None)
            saved.update(client=client, spreadsheet_id=target)
            self.vault.save(saved)
            self.message = None
            self.state = "connected" if saved.get("refresh_token") else "idle"
            return self.status()
        finally:
            self.lock.release()

    def disconnect(self) -> dict:
        if not self.lock.acquire(blocking=False):
            raise SheetsError(
                "Finish Google sign-in or wait for the current update before disconnecting."
            )
        try:
            try:
                saved = self.vault.load()
            except SheetsError:
                # Forgetting is a local operation, even when old credentials cannot unlock.
                saved = {}
            saved.pop("refresh_token", None)
            saved.pop("last_sync_at", None)
            self.vault.save(saved)
            self.state, self.message = "idle", None
            return self.status()
        finally:
            self.lock.release()

    def connect(self) -> dict:
        if not self.lock.acquire(blocking=False):
            raise SheetsError("Google sign-in or an update is already running.")
        try:
            saved = self.vault.load()
            if not saved.get("client") or not saved.get("spreadsheet_id"):
                raise SheetsError("Save the Google client and reporting sheet before connecting.")
            self.state, self.message = "waiting", None
            worker = threading.Thread(target=self._authorize, args=(saved,), daemon=True)
            worker.start()
        except Exception:
            self.lock.release()
            raise
        return self.status()

    def _authorize(self, saved: dict) -> None:
        server = None
        try:
            state = secrets.token_urlsafe(32)
            verifier = secrets.token_urlsafe(64)
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
                .rstrip(b"=")
                .decode("ascii")
            )
            result: dict = {}

            class Callback(BaseHTTPRequestHandler):
                def setup(self):
                    # An incomplete local request must not keep the sign-in lock forever.
                    self.request.settimeout(connection.callback_timeout)
                    super().setup()

                def log_message(self, *_):
                    pass  # The callback URL contains a private authorization code.

                def do_GET(self):
                    parsed = urllib.parse.urlsplit(self.path)
                    query = urllib.parse.parse_qs(parsed.query)
                    valid = (
                        parsed.path == "/oauth2/callback"
                        and len(query.get("state", [])) == 1
                        and secrets.compare_digest(
                            query.get("state", [""])[0].encode("utf-8"), state.encode("ascii")
                        )
                    )
                    if not valid:
                        self.send_response(400)
                        self.end_headers()
                        return
                    result.update(
                        code=query.get("code", [None])[0], error=query.get("error", [None])[0]
                    )
                    body = (
                        b"Google sign-in received. You can close this tab and return to Cathedra."
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except OSError:
                        pass  # A closed browser tab does not invalidate the received code.

            connection = self

            class CallbackServer(HTTPServer):
                def handle_error(self, request, client_address):
                    # HTTPServer's default traceback can expose callback details.
                    caught = sys.exception()
                    if isinstance(caught, Exception):
                        log_private_exception(caught)

            server = CallbackServer(("127.0.0.1", 0), Callback)
            server.timeout = 1
            redirect = f"http://127.0.0.1:{server.server_port}/oauth2/callback"
            query = urllib.parse.urlencode(
                {
                    "client_id": saved["client"]["client_id"],
                    "redirect_uri": redirect,
                    "response_type": "code",
                    "scope": SCOPE,
                    "state": state,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "access_type": "offline",
                    "prompt": "consent",
                }
            )
            if not webbrowser.open(AUTH_URL + "?" + query):
                raise SheetsError(
                    "The Google sign-in browser could not open. Check your default browser."
                )
            expires = time.monotonic() + self.authorization_timeout
            while not result and time.monotonic() < expires:
                server.handle_request()
            if result.get("error") or not result.get("code"):
                raise SheetsError(
                    "Google sign-in was cancelled or timed out. Choose Connect to try again."
                )
            response = google_request(
                TOKEN_URL,
                form={
                    **saved["client"],
                    "code": result["code"],
                    "code_verifier": verifier,
                    "redirect_uri": redirect,
                    "grant_type": "authorization_code",
                },
            )
            saved["refresh_token"] = _required_token(response, "refresh_token")
            self.vault.save(saved)
            self.state, self.message = "connected", None
        except SheetsError as caught:
            self.state, self.message = "error", str(caught)
        except Exception as caught:
            log_private_exception(caught)
            self.state, self.message = (
                "error",
                "Google sign-in could not finish. Check setup and try again.",
            )
        finally:
            if server:
                server.server_close()
            self.lock.release()

    def sync(self, rows: list[list[object]]) -> dict:
        if not self.lock.acquire(blocking=False):
            raise SheetsError("A Google operation is still running. Wait before updating again.")
        try:
            saved = self.vault.load()
            if not saved.get("refresh_token") or not saved.get("spreadsheet_id"):
                raise SheetsError("Connect your Google account before updating the report.")
            response = google_request(
                TOKEN_URL,
                form={
                    **saved["client"],
                    "refresh_token": saved["refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
            access_token = _required_token(response, "access_token")
            if response.get("refresh_token"):
                saved["refresh_token"] = _required_token(response, "refresh_token")
                # Rotation can invalidate the old token before report delivery finishes.
                # Preserve new access while last_sync_at still means a confirmed write.
                self.vault.save(saved)
            target = saved["spreadsheet_id"]
            url = SHEETS_URL + target
            metadata = google_request(url + "?fields=sheets.properties", token=access_token)
            sheets = metadata.get("sheets")
            if not isinstance(sheets, list) or any(
                not isinstance(item, dict) or not isinstance(item.get("properties"), dict)
                for item in sheets
            ):
                raise SheetsError("Google returned unexpected reporting sheet details. Try again.")
            sheet = next(
                (
                    item["properties"]
                    for item in sheets
                    if item["properties"].get("title") == REPORT_TAB
                ),
                None,
            )
            if sheet is None:
                created = google_request(
                    url + ":batchUpdate",
                    token=access_token,
                    body={
                        "requests": [{"addSheet": {"properties": {"title": REPORT_TAB}}}],
                    },
                )
                try:
                    sheet = created["replies"][0]["addSheet"]["properties"]
                except (KeyError, IndexError, TypeError) as caught:
                    raise SheetsError(
                        "Google did not confirm the new reporting tab. Check the spreadsheet before retrying."
                    ) from caught
            if (
                not isinstance(sheet, dict)
                or type(sheet.get("sheetId")) is not int
                or sheet["sheetId"] < 0
                or sheet.get("sheetType", "GRID") != "GRID"
            ):
                raise SheetsError(
                    "The Cathedra reporting tab must be a regular Google Sheets grid."
                )
            google_request(
                url + ":batchUpdate", token=access_token, body=replacement_request(sheet, rows)
            )
            synced_at = datetime.now(timezone.utc).isoformat()
            saved["last_sync_at"] = synced_at
            self.vault.save(saved)
            self.message = None
            self.state = "connected"
            return {
                "rows": max(0, len(rows) - 1),
                "synced_at": synced_at,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{target}/edit",
            }
        except SheetsError as caught:
            self.message = str(caught)
            raise
        finally:
            self.lock.release()
