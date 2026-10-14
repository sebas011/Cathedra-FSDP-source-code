"""A single Unicode policy for program identity, independent of display names."""

import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session


def program_key(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def default_program_key(context) -> str:
    return program_key(context.get_current_parameters()["name"])


def program_entry_keys(name: str) -> set[str]:
    # New business text is stored uppercase. Unicode upper() can change more
    # than casefold() (for example dotless i), so typed text must also resolve
    # its final stored spelling without changing historical canonical keys.
    return {program_key(name), program_key(name.upper())}


def matching_programs(db: Session, name: str) -> list:
    from app.models import Program

    keys = program_entry_keys(name)
    # Uppercase aliases must be compared in both directions: clients may send
    # an already-uppercase name for a historical mixed-case catalog entry.
    # Inspect catalog names in Python because SQLite upper()/lower() do not
    # implement this Unicode policy. Return every identity so callers reject
    # ambiguous aliases instead of silently merging distinct historical rows.
    return [item for item in db.scalars(select(Program)).all()
            if program_entry_keys(item.name) & keys]
