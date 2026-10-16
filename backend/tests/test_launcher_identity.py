import hashlib
import importlib.util
import json
import os
import threading
from pathlib import Path

import pytest


def launcher_module():
    path = Path(__file__).resolve().parents[2] / "desktop" / "run_cathedra.py"
    spec = importlib.util.spec_from_file_location("cathedra_launcher_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_reuses_only_matching_version_and_data_folder(monkeypatch, tmp_path: Path) -> None:
    launcher = launcher_module()
    office_directory = tmp_path / "office"
    office_directory.mkdir()
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    identity = hashlib.sha256(
        str(office_directory.resolve()).casefold().encode("utf-8")
    ).hexdigest()[:16]

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size=-1):
            return json.dumps(
                {
                    "status": "ok",
                    "product": "fsdp",
                    "release_version": "test",
                    "data_directory_identity": identity,
                }
            ).encode("utf-8")

    monkeypatch.setattr(launcher.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert launcher.service_is_ready(8100, "test", office_directory)
    assert not launcher.service_is_ready(8100, "other", office_directory)
    assert not launcher.service_is_ready(8100, "test", other_directory)


def test_launcher_rejects_second_process_on_same_data_folder(tmp_path: Path) -> None:
    launcher = launcher_module()
    data_directory = tmp_path / "office"
    first_lock = launcher.lock_data_directory(data_directory)
    try:
        with pytest.raises(RuntimeError, match="already open"):
            launcher.lock_data_directory(data_directory)
    finally:
        first_lock.close()
    second_lock = launcher.lock_data_directory(data_directory)
    second_lock.close()


def test_exit_requires_packaged_shutdown_signal(client) -> None:
    from app.main import app

    assert client.post("/api/v1/desktop/exit").status_code == 409
    shutdown_signal = threading.Event()
    app.state.shutdown_signal = shutdown_signal
    try:
        assert client.post("/api/v1/desktop/exit").json() == {"status": "closing"}
        assert shutdown_signal.is_set()
    finally:
        del app.state.shutdown_signal


class BrowserSignal:
    def __init__(self):
        self.closed = False

    def is_set(self):
        return self.closed

    def set(self):
        self.closed = True

    def wait(self, _):
        return self.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows Edge window ownership")
def test_edge_relaunch_keeps_service_until_actual_window_closes(monkeypatch):
    from types import SimpleNamespace

    launcher = launcher_module()
    signal = BrowserSignal()
    observations = iter(
        (
            (set([10, 11]), False),
            (set([10, 11]), True),
            (set([10, 11]), True),
            (set([10, 11]), False),
            (set([10, 11]), False),
        )
    )
    times = iter((0, 0.5, 1, 3, 4, 6))
    monkeypatch.setattr(launcher.time, "monotonic", lambda: next(times))

    def state(known):
        assert 10 in known
        assert not signal.closed
        return next(observations)

    monkeypatch.setattr(launcher, "windows_browser_state", state)
    launcher.watch_app_window(SimpleNamespace(pid=10), signal)
    assert signal.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows Edge window ownership")
def test_transient_window_relaunch_does_not_stop_service(monkeypatch):
    from types import SimpleNamespace

    launcher = launcher_module()
    signal = BrowserSignal()
    observations = iter((True, False, True, False, False))
    times = iter((0, 1, 2, 3, 4, 6))
    monkeypatch.setattr(launcher.time, "monotonic", lambda: next(times))

    def state(known):
        assert not signal.closed
        return known, next(observations)

    monkeypatch.setattr(launcher, "windows_browser_state", state)
    launcher.watch_app_window(SimpleNamespace(pid=10), signal)
    assert signal.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows Edge window ownership")
def test_failed_window_inspection_keeps_service_alive(monkeypatch):
    from types import SimpleNamespace

    launcher = launcher_module()
    signal = BrowserSignal()
    calls = []

    def state(known):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("inspection unavailable")
        signal.set()  # explicit application exit remains authoritative
        return known, True

    monkeypatch.setattr(launcher, "windows_browser_state", state)
    launcher.watch_app_window(SimpleNamespace(pid=10), signal)
    assert len(calls) == 2


def test_shutdown_holds_resources_until_backend_has_stopped() -> None:
    from types import SimpleNamespace

    launcher = launcher_module()
    calls = []
    server = SimpleNamespace(should_exit=False)
    thread = SimpleNamespace(join=lambda: calls.append("stopped"))
    listener = SimpleNamespace(close=lambda: calls.append("listener"))
    lock = SimpleNamespace(close=lambda: calls.append("lock"))
    launcher.stop_service(server, thread, listener, lock)
    assert server.should_exit
    assert calls == ["stopped", "listener", "lock"]
