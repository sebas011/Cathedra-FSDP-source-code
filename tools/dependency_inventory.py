"""Machine-readable pinned dependency and licence inventory; no private data."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path


def inventory(root: Path) -> dict:
    constraints = root / "backend/constraints-win-py314.txt"
    lockfile = root / "frontend/package-lock.json"
    python = []
    for line in constraints.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        metadata = importlib.metadata.metadata(name)
        python.append(
            {
                "name": name,
                "version": version,
                "licence": metadata.get("License-Expression")
                or metadata.get("License")
                or "Review package licence files",
            }
        )
    frontend = []
    for path, package in json.loads(lockfile.read_text())["packages"].items():
        if not path:
            continue
        metadata = root / "frontend" / path / "package.json"
        installed = json.loads(metadata.read_text()) if metadata.is_file() else {}
        frontend.append(
            {
                "name": path.split("node_modules/")[-1],
                "version": package["version"],
                "licence": installed.get("license")
                or package.get("license")
                or "Review package licence files",
                "integrity": package.get("integrity"),
            }
        )
    return {
        "format": "Cathedra dependency inventory 1",
        "formal_sbom_validated": False,
        "constraints_sha256": hashlib.sha256(constraints.read_bytes()).hexdigest(),
        "lockfile_sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest(),
        "python": python,
        "frontend": frontend,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(inventory(arguments.root), indent=2), encoding="utf-8")
