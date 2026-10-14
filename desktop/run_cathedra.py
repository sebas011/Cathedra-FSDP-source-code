"""Cathedra's Windows desktop launcher entry point for PyInstaller."""

import argparse
import ctypes
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PRODUCT = "fsdp"
APP_NAME = "Cathedra FSDP"
DEFAULT_PORT = 8101


def resource_path(*parts: str) -> Path:
    """Find a file from either a PyInstaller bundle or the source checkout."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root.joinpath(*parts)


def writable_data_directory(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    root = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[1]
    )
    return root / "data"


def prepare_data_directory(data_directory: Path) -> None:
    data_directory.mkdir(parents=True, exist_ok=True)
    active_database = data_directory / "cathedra.db"
    if active_database.exists():
        return
    if any(item.name != ".cathedra.lock" for item in data_directory.iterdir()):
        raise RuntimeError("The existing data folder has no active database. Restore its database before opening Cathedra; a new seed will not replace missing Office data.")
    bundled_database = resource_path("backend", "cathedra-seed.db")
    if not bundled_database.exists():
        raise RuntimeError("The bundled Cathedra database could not be found.")
    shutil.copy2(bundled_database, active_database)


def lock_data_directory(data_directory: Path):
    data_directory.mkdir(parents=True, exist_ok=True)
    lock_file = (data_directory / ".cathedra.lock").open("a+b")
    try:
        if lock_file.seek(0, os.SEEK_END) == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as caught:
        lock_file.close()
        raise RuntimeError(
            "This Cathedra data folder is already open in another app process."
        ) from caught
    return lock_file


def bundled_release_version() -> str:
    try:
        return resource_path("VERSION").read_text(encoding="utf-8").strip() or "development"
    except OSError:
        return "development"


def service_is_ready(port: int, expected_version: str, data_directory: Path) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/v1/health", timeout=1
        ) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read(65537).decode("utf-8"))
            if not isinstance(payload, dict):
                return False
            directory_identity = hashlib.sha256(
                str(data_directory.resolve()).casefold().encode("utf-8")
            ).hexdigest()[:16]
            return (
                payload.get("status") == "ok"
                and payload.get("release_version") == expected_version
                and payload.get("data_directory_identity") == directory_identity
                and payload.get("product") == PRODUCT
            )
    except OSError, ValueError, json.JSONDecodeError:
        return False


def wait_for_service(
    port: int, expected_version: str, data_directory: Path, timeout_seconds: int = 20
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if service_is_ready(port, expected_version, data_directory):
            return True
        time.sleep(0.25)
    return False


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def show_error(message: str) -> None:
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    else:
        print(message, file=sys.stderr)


def write_startup_error(message: str) -> None:
    data_directory = Path(os.environ.get("CATHEDRA_DATA_DIR", writable_data_directory(None)))
    try:
        data_directory.mkdir(parents=True, exist_ok=True)
        (data_directory / "launcher-error.log").write_text(message, encoding="utf-8")
    except OSError:
        pass


def open_app_window(url: str, data_directory: Path | None = None) -> subprocess.Popen | None:
    edge_locations = [
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    ]
    edge = next((candidate for candidate in edge_locations if candidate.exists()), None)
    if edge:
        arguments = [str(edge), f"--app={url}", "--new-window"]
        if data_directory is not None:
            arguments.extend(
                [
                    f"--user-data-dir={data_directory / 'edge-profile'}",
                    "--disable-background-mode",
                    "--no-first-run",
                ]
            )
        return subprocess.Popen(arguments)
    else:
        webbrowser.open_new(url)
        return None


def windows_browser_state(known_pids: set[int]) -> tuple[set[int], bool]:
    """Follow Edge relaunch descendants and their visible top-level windows."""
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    processes = []
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            if entry.szExeFile.casefold() == "msedge.exe":
                processes.append((entry.th32ProcessID, entry.th32ParentProcessID))
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    owned = set(known_pids)
    while True:
        descendants = {pid for pid, parent in processes if parent in owned}
        if descendants <= owned:
            break
        owned.update(descendants)

    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    visible = False

    @callback_type
    def inspect(hwnd, _):
        nonlocal visible
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in owned and user.IsWindowVisible(hwnd):
            visible = True
        return True

    if not user.EnumWindows(inspect, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return owned, visible


def watch_app_window(window: subprocess.Popen, shutdown_signal: threading.Event) -> None:
    if os.name != "nt":
        window.wait()
        shutdown_signal.set()
        return
    known_pids = {window.pid}
    started = time.monotonic()
    seen_window = False
    absent_since = None
    while not shutdown_signal.is_set():
        try:
            known_pids, visible = windows_browser_state(known_pids)
        except OSError:
            # An inspection failure is not evidence that the user closed Edge.
            shutdown_signal.wait(1)
            continue
        now = time.monotonic()
        if visible:
            seen_window = True
            absent_since = None
        elif seen_window:
            if absent_since is None:
                absent_since = now
            elif now - absent_since >= 2:
                shutdown_signal.set()
                return
        elif now - started >= 60:
            write_startup_error("Edge did not display an application window within 60 seconds.")
            shutdown_signal.set()
            return
        shutdown_signal.wait(0.5)


def stop_service(server, server_thread, listener, data_lock) -> None:
    server.should_exit = True
    server_thread.join()
    listener.close()
    data_lock.close()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Cathedra as a local desktop application.")
    parser.add_argument("--data-dir", help="Override the writable Cathedra data folder.")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Local-only port for the Cathedra service."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local service without opening a window.",
    )
    parser.add_argument("--benchmark", help="New synthetic benchmark output directory.")
    parser.add_argument("--update-target", help="Closed Office installation to update using this package.")
    parser.add_argument("--verify-package", help="Verify a runtime package without opening any database.")
    parser.add_argument("--rollback-update", action="store_true")
    parser.add_argument("--maintenance-result", help="Private update result file.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if getattr(arguments, "verify_package", None):
        from office_update import checked_package

        try:
            manifest, _ = checked_package(Path(arguments.verify_package), "Selected package")
            result = {"verified": True, "version": manifest["version"],
                      "runtime_files": len(manifest["runtime_files"]),
                      "database_accessed": False}
        except Exception as caught:
            result = {"status": "failed", "error_type": type(caught).__name__,
                      "detail": str(caught), "phase": getattr(caught, "phase", "Package verification"),
                      "package_root": getattr(caught, "package_root", arguments.verify_package),
                      "database_accessed": False}
            if arguments.maintenance_result:
                Path(arguments.maintenance_result).write_text(json.dumps(result, indent=2), encoding="utf-8")
            raise SystemExit(1) from None
        if arguments.maintenance_result:
            Path(arguments.maintenance_result).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return
    data_directory = writable_data_directory(arguments.data_dir)
    version = bundled_release_version()
    os.environ["CATHEDRA_DATA_DIR"] = str(data_directory)
    os.environ["CATHEDRA_PRODUCT"] = PRODUCT
    os.environ["CATHEDRA_FRONTEND_DIST"] = str(resource_path("frontend", "dist"))
    os.environ["CATHEDRA_RELEASE_VERSION"] = version
    backend_root = resource_path("backend")
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    if getattr(arguments,"benchmark",None):
        from maintenance_checks import benchmark
        result=benchmark(Path(arguments.benchmark).resolve())
        Path(arguments.maintenance_result).write_text(json.dumps(result,indent=2),encoding="utf-8")
        return
    if arguments.update_target:
        from office_update import update_office
        result_path = Path(arguments.maintenance_result).resolve() if arguments.maintenance_result else None
        package_root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        try:
            result = update_office(package_root, Path(arguments.update_target), lock_data_directory, rollback=arguments.rollback_update)
            if result_path:
                result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        except Exception as caught:
            if result_path:
                result_path.write_text(json.dumps({
                    "status": "failed",
                    "message": "The update stopped. Keep the existing database and recovery files; review the detail below.",
                    "error_type": type(caught).__name__,
                    "detail": str(caught),
                    "phase": getattr(caught, "phase", "Update operation"),
                    "package_root": getattr(caught, "package_root", str(package_root)),
                    "installation": str(Path(arguments.update_target)),
                    "database_replaced": False,
                }, indent=2), encoding="utf-8")
            raise SystemExit(1) from None
        return

    url = f"http://127.0.0.1:{arguments.port}"
    data_lock = lock_data_directory(data_directory)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", arguments.port))
        listener.listen(128)
        listener.setblocking(False)
    except OSError as caught:
        listener.close()
        data_lock.close()
        raise RuntimeError(
            f"Port {arguments.port} is already in use. Close the existing service before opening Cathedra. Existing services are never trusted automatically."
        ) from caught
    prepare_data_directory(data_directory)

    import uvicorn

    from app.main import app

    shutdown_signal = threading.Event()
    app.state.shutdown_signal = shutdown_signal
    app.state.bootstrap_token = os.environ.get("CATHEDRA_SETUP_TOKEN") or secrets.token_urlsafe(32)
    url += f"/login#setup={app.state.bootstrap_token}"
    configuration = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=arguments.port,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(configuration)
    server_thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
    server_thread.start()
    window = None
    browser_profile = None
    try:
        if not wait_for_service(arguments.port, version, data_directory) or not server.started:
            raise RuntimeError("Cathedra could not start its local service.")
        if not arguments.no_browser:
            browser_profile = tempfile.TemporaryDirectory(
                prefix="browser-", dir=data_directory, ignore_cleanup_errors=True
            )
            window = open_app_window(url, Path(browser_profile.name))
            if window is not None:
                threading.Thread(
                    target=watch_app_window, args=(window, shutdown_signal), daemon=True
                ).start()
        shutdown_signal.wait()
    finally:
        stop_service(server, server_thread, listener, data_lock)
        if window is not None and window.poll() is None:
            window.terminate()
            try:
                window.wait(timeout=10)
            except subprocess.TimeoutExpired:
                window.kill()
                window.wait()
        if browser_profile is not None:
            browser_profile.cleanup()


if __name__ == "__main__":
    try:
        main()
    except Exception as caught:
        message = f"Cathedra could not start.\n\n{caught}"
        write_startup_error(message)
        if "--maintenance-result" not in sys.argv:
            show_error(message)
        raise
