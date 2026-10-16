"""The office's eight colleges and a single Staff affiliation."""

from sqlalchemy import case, func

COLLEGES = ("CIT", "CAS", "COED", "COE", "CCJ", "COF", "CBMA", "CCS")


def affiliation(value: str | None) -> str:
    label = (value or "").strip().upper()
    if not label or label in {"UNKNOWN", "NOT RECORDED"}:
        return "Unknown"
    return label if label in COLLEGES else "Staff"


def personnel_type(value: str | None) -> str:
    department = affiliation(value)
    return "Faculty" if department in COLLEGES else department


def affiliation_expression(column):
    label = func.upper(func.trim(func.coalesce(column, "")))
    return case(
        (label.in_(COLLEGES), label),
        (label.in_(("", "UNKNOWN", "NOT RECORDED")), "Unknown"),
        else_="Staff",
    )


def previous_affiliation_note(
    value: str | None, remarks: str | None, *, uppercase_new: bool = False
) -> str | None:
    raw = (value or "").strip()
    if raw and affiliation(raw) == "Staff" and raw.casefold() != "staff":
        note = f"Previous affiliation: {raw}"
        if uppercase_new:
            note = note.upper()
        if note.casefold() not in {line.casefold() for line in (remarks or "").splitlines()}:
            return "\n".join(part for part in (remarks, note) if part)
    return remarks
