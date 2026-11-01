import io
import json
from urllib.error import HTTPError

import pytest

from app.shared_connection import SharedError, bridge_request, endpoint_url

ENDPOINT = "https://script.google.com/macros/s/" + "a" * 30 + "/exec"


@pytest.mark.parametrize(
    "target",
    [
        "http://script.google.com/macros/s/abc/exec",
        "https://example.test/exec",
        ENDPOINT + "?key=private",
        ENDPOINT + "#fragment",
        ENDPOINT.replace("/exec", "/dev"),
    ],
)
def test_endpoint_rejects_unapproved_destinations(target):
    with pytest.raises(SharedError):
        endpoint_url(target)


def test_google_redirect_uses_fresh_get_without_credentials(monkeypatch):
    requests = []
    body = b'{"device_key":"PRIVATE TEST VALUE"}'

    def open_request(request, **kwargs):
        requests.append(request)
        if len(requests) == 1:
            raise HTTPError(
                ENDPOINT,
                302,
                "redirect",
                {"Location": "https://script.googleusercontent.com/macros/echo?response=one"},
                io.BytesIO(),
            )
        return io.BytesIO(json.dumps({"ok": True, "result": {}}).encode())

    monkeypatch.setattr(
        "urllib.request.build_opener",
        lambda *_: type("Opener", (), {"open": staticmethod(open_request)})(),
    )
    assert bridge_request(ENDPOINT, body)["ok"]
    assert requests[0].data == body and requests[0].get_method() == "POST"
    assert requests[1].data is None and requests[1].get_method() == "GET"
    assert "PRIVATE" not in requests[1].full_url
    assert not requests[1].has_header("Authorization")


@pytest.mark.parametrize(
    "target",
    [
        "https://example.test/macros/echo",
        "http://script.googleusercontent.com/macros/echo",
        "https://script.googleusercontent.com.evil.test/macros/echo",
    ],
)
def test_redirect_never_forwards_to_other_hosts(monkeypatch, target):
    calls = []

    def open_request(request, **kwargs):
        calls.append(request)
        raise HTTPError(ENDPOINT, 302, "redirect", {"Location": target}, io.BytesIO())

    monkeypatch.setattr(
        "urllib.request.build_opener",
        lambda *_: type("Opener", (), {"open": staticmethod(open_request)})(),
    )
    with pytest.raises(SharedError) as caught:
        bridge_request(ENDPOINT, b"PRIVATE")
    assert caught.value.uncertain
    assert len(calls) == 1
