"""Private per-installation credentials and bounded owner-bridge transport."""

import hashlib
import json
import re
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException as HTTPProtocolError
from uuid import UUID, uuid4

from app.google_sheets import WindowsVault

PROTOCOL = "cathedra-shared-v1"
MAX_BYTES = 8 * 1024 * 1024


class SharedError(Exception):
    def __init__(self, message: str, code: str = "unavailable", *, uncertain: bool = False):
        super().__init__(message)
        self.code = code
        self.uncertain = uncertain


def endpoint_url(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,250}/exec", value.strip()
    ):
        raise SharedError("Enter the deployed Google Apps Script /exec address.", "invalid")
    return value.strip()


def encode(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def fingerprint(value) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bridge_request(endpoint: str, body: bytes) -> dict:
    """Only the initial Google endpoint receives credentials; redirects are GET-only."""
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        endpoint_url(endpoint),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        try:
            response = opener.open(request, timeout=90)
        except urllib.error.HTTPError as caught:
            if caught.code not in (302, 303):
                raise
            location = caught.headers.get("Location", "")
            caught.close()
            target = urllib.parse.urlsplit(location)
            if (
                target.scheme != "https"
                or target.netloc != "script.googleusercontent.com"
                or not target.path.startswith("/macros/")
                or target.fragment
            ):
                raise SharedError(
                    "The bridge redirected outside its Google response service. Check its deployment.",
                    uncertain=True,
                ) from None
            # A fresh request deliberately contains no POST body, device key or auth header.
            response = opener.open(
                urllib.request.Request(location, headers={"Accept": "application/json"}), timeout=90
            )
        with response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise SharedError(
                    "The shared workspace exceeds the supported response size.", uncertain=True
                )
            result = json.loads(raw)
        if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
            raise ValueError
        return result
    except SharedError:
        raise
    except OSError, ValueError, urllib.error.URLError, HTTPProtocolError:
        # Google/network errors can occur after a committed write. Do not guess.
        raise SharedError(
            "The shared result could not be confirmed. Retry the saved operation when connected.",
            uncertain=True,
        ) from None


class WorkspaceConnection:
    def __init__(self, vault: WindowsVault, transport=bridge_request):
        self.vault = vault
        self.transport = transport
        self.lock = threading.RLock()

    def saved(self) -> dict:
        with self.lock:
            saved = self.vault.load()
            if not saved:
                return {}
            if (
                saved.get("protocol") != PROTOCOL
                or not isinstance(saved.get("device_key"), str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{40,100}", saved["device_key"])
            ):
                raise SharedError("The private shared connection needs to be configured again.")
            endpoint_url(saved.get("endpoint", ""))
            return saved

    def configure(self, endpoint: str) -> dict:
        with self.lock:
            current = self.saved()
            if current and current["endpoint"] != endpoint_url(endpoint):
                raise SharedError(
                    "Disconnect this workspace before changing its bridge address.", "conflict"
                )
            if not current:
                current = {
                    "protocol": PROTOCOL,
                    "endpoint": endpoint_url(endpoint),
                    "device_id": str(uuid4()),
                    "device_key": secrets.token_urlsafe(32),
                    "binding_id": str(uuid4()),
                }
                self.vault.save(current)
            return self.public(current)

    def public(self, saved: dict | None = None) -> dict:
        value = self.saved() if saved is None else saved
        metadata = value.get("metadata", {})
        return {
            "configured": bool(value),
            "endpoint": value.get("endpoint"),
            "device_id": value.get("device_id"),
            "device_key_hash": hashlib.sha256(value["device_key"].encode()).hexdigest()
            if value
            else None,
            "device_label": metadata.get("device_label"),
            "workspace_id": metadata.get("workspace_id"),
            "storage_url": metadata.get("storage_url"),
            "report_url": metadata.get("report_url"),
            "can_initialize": metadata.get("can_initialize", False),
            "initialized": metadata.get("initialized", False),
        }

    def call(self, command: str, args: dict | None = None) -> dict:
        with self.lock:
            saved = self.saved()
            if not saved:
                raise SharedError("Configure the shared workspace first.", "invalid")
            body = encode(
                {
                    "protocol": PROTOCOL,
                    "device_id": saved["device_id"],
                    "device_key": saved["device_key"],
                    "command": command,
                    "args": args or {},
                }
            )
            if len(body) > MAX_BYTES:
                raise SharedError(
                    "The shared request exceeds 8 MiB. No request was sent.", "invalid"
                )
            envelope = self.transport(saved["endpoint"], body)
            if envelope.get("ok") is not True:
                error = envelope.get("error", {})
                code = error.get("code", "unavailable")
                messages = {
                    "unauthorized": "This device is not approved for the shared workspace. Check its registration or revocation.",
                    "conflict": "Shared records changed. Refresh the preview and review again.",
                    "invalid": "The shared request could not be accepted. Check the setup and recorded data.",
                    "busy": "Another computer is synchronizing. Try again shortly.",
                    "unavailable": "The shared service could not finish. Check its setup and capacity.",
                }
                raise SharedError(
                    messages.get(code, messages["unavailable"]),
                    code,
                    uncertain=error.get("outcome") != "not_committed",
                )
            result = envelope.get("result")
            if not isinstance(result, dict):
                raise SharedError("The shared result could not be verified.", uncertain=True)
            return result

    def remember_metadata(self, metadata: dict) -> None:
        with self.lock:
            try:
                UUID(metadata["workspace_id"])
                if metadata.get("protocol") != PROTOCOL or not isinstance(
                    metadata.get("initialized"), bool
                ):
                    raise ValueError
                for key in ("storage_url", "report_url"):
                    if not re.fullmatch(
                        r"https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{10,200}/edit",
                        metadata[key],
                    ):
                        raise ValueError
                if metadata["storage_url"] == metadata["report_url"]:
                    raise ValueError
                if (
                    not isinstance(metadata.get("device_label"), str)
                    or len(metadata["device_label"]) > 200
                ):
                    raise ValueError
            except ValueError, TypeError, KeyError, AttributeError:
                raise SharedError("The shared workspace metadata could not be verified.") from None
            saved = self.saved()
            previous = saved.get("metadata", {}).get("workspace_id")
            if previous and previous != metadata.get("workspace_id"):
                raise SharedError(
                    "The bridge now points to a different workspace. Disconnect and review the new connection.",
                    "conflict",
                )
            saved["metadata"] = {
                key: metadata.get(key)
                for key in (
                    "workspace_id",
                    "device_label",
                    "storage_url",
                    "report_url",
                    "can_initialize",
                    "initialized",
                )
            }
            self.vault.save(saved)

    def checkpoint(self, workspace_id: str, cache_id: str, baseline: dict) -> None:
        with self.lock:
            saved = self.saved()
            saved["checkpoint"] = {
                "workspace_id": workspace_id,
                "cache_id": cache_id,
                "baseline_digest": fingerprint(baseline),
            }
            self.vault.save(saved)

    def matches_checkpoint(self, state) -> bool:
        saved = self.saved()
        expected = saved.get("checkpoint")
        return bool(
            expected
            and state
            and state.baseline_json
            and expected
            == {
                "workspace_id": state.workspace_id,
                "cache_id": state.cache_id,
                "baseline_digest": fingerprint(json.loads(state.baseline_json)),
            }
        )

    def disconnect(self) -> None:
        with self.lock:
            # The existing atomic vault writer is retained; an empty vault has no active endpoint.
            self.vault.save({})
