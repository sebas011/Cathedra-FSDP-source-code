"""Retired historical comparison helper; current updater owns migration rehearsal."""

import argparse
from pathlib import Path

RETIRED_MESSAGE = (
    "This historical migration comparison helper is retired. It does not understand "
    "current schema additions and must not be used as an Office acceptance gate. "
    "Use the verified package's tools/update-office.ps1 for installation; it rehearses "
    "the current transactional upgrade on a private copy. See docs/DEVELOPER_GUIDE.md "
    "and the current backend upgrade tests for migration verification. No files were changed."
)


def verify_migration(source: Path, destination: Path) -> dict:
    raise RuntimeError(RETIRED_MESSAGE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=RETIRED_MESSAGE)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.parse_args()
    raise SystemExit(RETIRED_MESSAGE)
