"""Read-only candidate review; never treats absent current evidence as a deletion rule."""

import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path

from app.graduated_education import graduation_evidence


def review_education(snapshot: Path, *, today: date | None = None) -> dict:
    snapshot = snapshot.resolve(strict=True)
    with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("SELECT product FROM cathedra_product WHERE id=1").fetchone() != ("fsdp",):
            raise ValueError("Choose a compatible FSDP snapshot.")
        grants = defaultdict(list)
        for scholar, program, name, status, remarks in connection.execute(
            "SELECT f.scholar_id,f.program_id,p.name,f.status,f.remarks "
            "FROM fsdp_participations f JOIN programs p ON p.id=f.program_id"
        ):
            grants[scholar, program].append(
                status.strip().casefold() in {"graduated", "completed"}
                or graduation_evidence(remarks, name, today=today)[0]
            )
        candidates = []
        checked = 0
        for identity, scholar, program in connection.execute(
            "SELECT id,scholar_id,source_program_id FROM scholar_education "
            "WHERE source_program_id IS NOT NULL ORDER BY scholar_id,id"
        ):
            checked += 1
            if not any(grants[scholar, program]):
                candidates.append({
                    "education_id": identity, "scholar_id": scholar, "program_id": program,
                    "reason": "No current recorded graduation or accepted program-specific remark evidence",
                })
    return {"linked_entries_checked": checked, "review_candidates": len(candidates),
            "candidates": candidates,
            "notice": "Review only. Historical achievements and manual corrections may be valid. Nothing was changed."}
