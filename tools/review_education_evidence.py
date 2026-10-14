"""Review a closed disposable FSDP snapshot without writing to it."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.education_review import review_education


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Closed disposable copy, not the working database")
    parser.add_argument("--output", type=Path, help="New private JSON report (IDs/reasons only)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.snapshot.resolve() == (root / "data/cathedra.db").resolve():
        parser.error("Make a disposable snapshot; do not inspect the working installation here.")
    try:
        result = review_education(args.snapshot)
        if args.output:
            with args.output.open("x", encoding="utf-8") as report:
                json.dump(result, report, indent=2)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.error(str(error))
    print(json.dumps({key: value for key, value in result.items() if key != "candidates"}))


if __name__ == "__main__":
    main()
