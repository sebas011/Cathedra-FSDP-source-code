"""The compact scholar/grant projection sent only to Google Sheets."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.college_classification import affiliation
from app.current_grant import grant_order
from app.fsdp_values import effective_hei
from app.models import FsdpParticipation, Scholar
from app.profile_values import tenure_in_years
from app.record_text import outcome

GOOGLE_REPORT_HEADERS = [
    "No.",
    "Name",
    "Age",
    "Tenure",
    "Department",
    "Rank/position",
    "Previous degree",
    "Program",
    "Delivering HEI",
    "Grant type",
    "Date started",
    "Date ended",
    "Extension",
    "Status",
    "Remarks",
]


def _education(scholar: Scholar) -> str | None:
    if not scholar.education:
        return scholar.previous_degree
    entries = []
    for item in scholar.education:
        degree = ": ".join(value for value in (item.level, item.degree) if value)
        entries.append(
            " · ".join(value for value in (degree, item.institution, item.graduation_year) if value)
        )
    return "\n".join(value for value in entries if value) or None


def _period(recorded: date | None, term: str | None, year: str | None) -> str | None:
    if recorded is not None:
        return recorded.isoformat()
    return " ".join(value.strip() for value in (term, year) if value and value.strip()) or None


def _grant_type(grant: FsdpParticipation) -> str | None:
    kind = grant.grant_type
    if kind and kind.strip().casefold() == "other" and grant.grant_other:
        return f"{kind}: {grant.grant_other}"
    return kind


def _remarks(profile: str | None, grant: str | None) -> str | None:
    if profile and grant:
        return f"Profile: {profile}\nGrant: {grant}"
    return profile or grant


def google_report_table(db: Session) -> tuple[list[str], list[list[object | None]]]:
    """Keep every grant row, with profile information once per numbered scholar."""
    scholars = (
        db.scalars(
            select(Scholar)
            .options(
                selectinload(Scholar.participations).selectinload(FsdpParticipation.program),
                selectinload(Scholar.education),
            )
            .order_by(func.name_sort_key(Scholar.name), Scholar.id)
        )
        .unique()
        .all()
    )
    rows: list[list[object | None]] = []
    for number, scholar in enumerate(scholars, start=1):
        profile = [
            number,
            scholar.name,
            scholar.age,
            scholar.tenure_years
            if scholar.tenure_years is not None
            else tenure_in_years(scholar.tenure),
            affiliation(scholar.department),
            scholar.rank,
            _education(scholar),
        ]
        grants = sorted(scholar.participations, key=grant_order)
        if not grants:
            rows.append(profile + [None] * 7 + [scholar.profile_remarks])
            continue
        for index, grant in enumerate(grants):
            rows.append(
                (profile if index == 0 else [None] * len(profile))
                + [
                    grant.program.name,
                    effective_hei(grant),
                    _grant_type(grant),
                    _period(grant.start_date, grant.start_term, grant.start_academic_year),
                    _period(grant.end_date, grant.end_term, grant.end_academic_year),
                    grant.extension,
                    outcome(grant.status),
                    _remarks(scholar.profile_remarks if index == 0 else None, grant.remarks),
                ]
            )
    return GOOGLE_REPORT_HEADERS.copy(), rows
