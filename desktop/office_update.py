"""Closed-app runtime replacement. The selected installation owns its data."""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT_FILES = {"Cathedra FSDP.exe", "VERSION", "APP_PRODUCT"}
TOOL_FILES = {
    "verify-package.ps1",
    "office-smoke.ps1",
    "protect-local-installation.ps1",
    "update-office.ps1",
}
RUNTIME_NAMES = (
    "Cathedra FSDP.exe",
    "VERSION",
    "APP_PRODUCT",
    "_internal",
    "tools",
    "release-manifest.json",
)


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def safe_directory(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    for item in (absolute, *absolute.parents):
        if item.is_symlink() or item.is_junction():
            raise ValueError("Linked installation paths are not supported.")
    if absolute == Path(absolute.anchor) or not absolute.is_dir():
        raise ValueError("Select an existing Cathedra installation folder.")
    return absolute


def version(value: str) -> tuple[int, ...]:
    parts = value.strip().split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("Unsupported release version.")
    return tuple(map(int, parts))


class PackageVerificationError(ValueError):
    def __init__(self, detail: str, root: Path, phase: str):
        super().__init__(f"{phase}: {detail}")
        self.package_root = str(root)
        self.phase = phase


def runtime_paths(root: Path) -> dict[str, Path]:
    """Enumerate runtime trees completely; access errors and links fail closed."""
    result = {name.casefold(): root / name for name in ROOT_FILES if (root / name).is_file()}

    def scan_error(error: OSError) -> None:
        raise error

    for folder in ("_internal", "tools"):
        base = root / folder
        if base.is_symlink() or base.is_junction():
            raise ValueError(f"Linked runtime files are not supported: {base}")
        for directory, children, files in os.walk(base, onerror=scan_error, followlinks=False):
            directory = Path(directory)
            for name in (*children, *files):
                path = directory / name
                if path.is_symlink() or path.is_junction():
                    raise ValueError(f"Linked runtime files are not supported: {path}")
            for name in files:
                path = directory / name
                key = path.relative_to(root).as_posix().casefold()
                if key in result:
                    raise ValueError(f"Unsafe or duplicate runtime path: {path}")
                result[key] = path
    return result


def inspect_package(
    root: Path, *, allow_installed_residue: bool = False
) -> tuple[dict, list[Path]]:
    root = safe_directory(root)
    manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8-sig"))
    if manifest["product"] != "fsdp" or (root / "APP_PRODUCT").read_text().strip() != "fsdp":
        raise ValueError("Select a Cathedra FSDP package.")
    if manifest["version"] != (root / "VERSION").read_text().strip():
        raise ValueError("Package version identity differs.")
    required = {name.casefold() for name in ROOT_FILES} | {f"tools/{name}" for name in TOOL_FILES}
    seen = set()
    missing_files = set()
    for entry in manifest["runtime_files"]:
        relative = Path(entry["path"])
        path = root / relative
        if (
            relative.is_absolute()
            or relative.drive
            or not relative.parts
            or any(":" in part for part in relative.parts)
            or ".." in relative.parts
            or relative.as_posix().casefold() in seen
        ):
            raise ValueError("Unsafe or duplicate release path.")
        seen.add(relative.as_posix().casefold())
        key = relative.as_posix().casefold()
        allowed = key in required or (
            len(relative.parts) > 1 and relative.parts[0].casefold() == "_internal"
        )
        if not allowed:
            raise ValueError(f"Unexpected or missing runtime file in {root}: {relative.as_posix()}")
        if not path.is_file():
            missing_files.add(key)
            continue
        for ancestor in (path, *path.parents):
            if ancestor == root:
                break
            if ancestor.is_symlink() or ancestor.is_junction():
                raise ValueError("Linked runtime files are not supported.")
        if path.stat().st_size != entry["size"] or file_sha256(path) != entry["sha256"].lower():
            raise ValueError(
                f"Package integrity verification failed in {root}: {relative.as_posix()}"
            )
    paths = runtime_paths(root)
    actual = {key for key in paths if key in required or key.startswith("_internal/")}
    missing = missing_files | (seen - actual) | (required - seen)
    unexpected = actual - seen - required
    if (
        missing
        or (unexpected and not allow_installed_residue)
        or not any(name.startswith("_internal/") for name in seen)
    ):
        raise ValueError(
            f"Package runtime inventory differs in {root}. "
            f"Manifest: {len(seen)}; runtime: {len(actual)}. "
            f"Missing required entries: {', '.join(sorted(missing)) or 'none'}. "
            f"Unexpected entries: {', '.join(sorted(unexpected)) or 'none'}."
        )
    return manifest, [paths[key] for key in sorted(paths.keys() - seen)]


def verify_package(root: Path) -> dict:
    manifest, _ = inspect_package(root)
    return manifest


def checked_package(
    root: Path, phase: str, *, allow_installed_residue: bool = False
) -> tuple[dict, list[Path]]:
    try:
        return inspect_package(root, allow_installed_residue=allow_installed_residue)
    except (ValueError, OSError, KeyError, TypeError) as caught:
        raise PackageVerificationError(str(caught), root, phase) from caught


def write_journal(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(state, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def copy_runtime(source: Path, destination: Path, manifest: dict | None = None) -> None:
    destination.mkdir()
    if manifest is not None:
        for entry in manifest["runtime_files"]:
            relative = Path(entry["path"])
            copied = destination / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, copied)
        shutil.copy2(source / "release-manifest.json", destination / "release-manifest.json")
        return
    for name in RUNTIME_NAMES:
        original = source / name
        if original.is_dir():
            shutil.copytree(original, destination / name)
        else:
            shutil.copy2(original, destination / name)


def restore_runtime(target: Path, old: Path) -> None:
    for name in RUNTIME_NAMES:
        original = old / name
        if not original.exists():
            raise RuntimeError("The runtime recovery archive is incomplete.")
        current = target / name
        if current.is_dir():
            shutil.rmtree(current)
        elif current.exists():
            current.unlink()
        if original.is_dir():
            shutil.copytree(original, current)
        else:
            shutil.copy2(original, current)


def check_installed_workflow(target: Path) -> None:
    shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    environment = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    if os.name == "nt":
        environment["PSModulePath"] = str(shell.parent / "Modules")
    frozen_windows = os.name == "nt" and getattr(sys, "frozen", False)
    if frozen_windows:
        import ctypes

        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        result = subprocess.run(
            [
                str(shell),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(target / "tools/office-smoke.ps1"),
                "-Package",
                str(target),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    finally:
        if frozen_windows:
            ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
    (target / "data" / "workflow-verification.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    if result.returncode:
        raise RuntimeError(
            "Installed isolated workflow verification failed; the preceding runtime will be restored."
        )


def update_office(
    package: Path,
    target: Path,
    lock_directory,
    *,
    rollback: bool = False,
    workflow_check=check_installed_workflow,
) -> dict:
    from sqlalchemy import create_engine

    from app.product import verify_product
    from app.upgrade import snapshot_database, upgrade_database

    package, target = safe_directory(package), safe_directory(target)
    if package == target or package in target.parents or target in package.parents:
        raise ValueError("The update package must be separate from the installation.")
    incoming, _ = checked_package(package, "Incoming package")
    data = safe_directory(target / "data")
    database_path = data / "cathedra.db"
    if not database_path.is_file() or database_path.is_symlink():
        raise ValueError("The Office database is missing. Restore it before updating.")
    journal = data / "update-state.json"
    lock = lock_directory(data)
    try:
        with closing(sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)) as database:
            verify_product(database)
        if journal.exists():
            prior = json.loads(journal.read_text())
            if prior["status"] not in {"verified", "rolled-back"} or (
                rollback and prior["status"] == "verified"
            ):
                if not rollback:
                    raise RuntimeError(
                        "An interrupted update needs runtime rollback first. Use -Rollback."
                    )
                old = safe_directory(Path(prior["old_runtime"]))
                if old.parent != data / "updates":
                    raise RuntimeError("Invalid runtime recovery location.")
                if file_sha256(database_path) != prior["database_sha256"]:
                    raise RuntimeError(
                        "Office data changed after the update. Use forward repair; do not restore an old runtime automatically."
                    )
                checked_package(old, "Recovery archive")
                restore_runtime(target, old)
                prior["status"] = "rolled-back"
                write_journal(journal, prior)
                return prior
        if rollback:
            raise ValueError("There is no interrupted runtime replacement to roll back.")
        old_version = (target / "VERSION").read_text().strip()
        minimum = incoming.get("update", {}).get("minimum_version", "0.5.4")
        if version(old_version) < version(minimum) or version(old_version) >= version(
            incoming["version"]
        ):
            raise ValueError(
                "This installation version is unsupported or already current. Downgrades are refused."
            )
        installed, residue = checked_package(
            target, "Existing installation", allow_installed_residue=True
        )
        total_bytes = sum(entry["size"] for entry in incoming["runtime_files"])
        installed_bytes = sum(entry["size"] for entry in installed["runtime_files"])
        residue_bytes = sum(path.stat().st_size for path in residue)
        if (
            shutil.disk_usage(data).free
            < total_bytes * 2
            + installed_bytes
            + residue_bytes
            + database_path.stat().st_size * 4
            + 10_485_760
        ):
            raise RuntimeError("Free disk space is insufficient for staging and recovery.")
        token = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex
        work = data / "updates"
        work.mkdir(exist_ok=True)
        safe_directory(work)
        if (data / "backups").exists():
            safe_directory(data / "backups")
        snapshot = data / "backups" / ("cathedra-protected-before-update-" + token + ".db")
        snapshot_database(database_path, snapshot)
        rehearsal = work / ("rehearsal-" + token)
        rehearsal.mkdir()
        shutil.copy2(snapshot, rehearsal / "cathedra.db")
        engine = create_engine(f"sqlite:///{(rehearsal / 'cathedra.db').as_posix()}")
        try:
            upgrade_database(engine, rehearsal / "cathedra.db")
        finally:
            engine.dispose()
        old = work / ("runtime-before-" + token)
        copy_runtime(target, old, installed)
        checked_package(old, "Verified preceding runtime archive")
        residue_archive = None
        if residue:
            residue_archive = work / ("runtime-residue-" + token)
            residue_archive.mkdir()
            for original in residue:
                copied = residue_archive / original.relative_to(target)
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, copied)
                if file_sha256(copied) != file_sha256(original):
                    raise RuntimeError("Runtime residue recovery copy differs; update stopped.")
        staged = work / ("staged-" + token)
        copy_runtime(package, staged, incoming)
        checked_package(staged, "Staged incoming runtime")
        state = {
            "status": "staged",
            "source_version": old_version,
            "version": incoming["version"],
            "snapshot": str(snapshot),
            "old_runtime": str(old),
            "database_sha256": file_sha256(database_path),
            "database_replaced": False,
            "runtime_residue_archive": str(residue_archive) if residue_archive else None,
            "runtime_residue_files": len(residue),
            "existing_runtime_residue_repaired": bool(residue),
        }
        write_journal(journal, state)
        try:
            state["status"] = "replacing"
            write_journal(journal, state)
            restore_runtime(target, staged)
            checked_package(target, "Installed replacement runtime")
            workflow_check(target)
            if file_sha256(database_path) != state["database_sha256"]:
                raise RuntimeError("Office database changed during file replacement.")
            state["status"] = "verified"
            write_journal(journal, state)
            return state
        except Exception:
            restore_runtime(target, old)
            state["status"] = "rolled-back"
            write_journal(journal, state)
            raise
    finally:
        lock.close()
