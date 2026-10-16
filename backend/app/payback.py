"""Read-only contract follow-up; recorded outcomes remain office decisions."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.college_classification import affiliation, affiliation_expression
from app.contract_rules import GROUPS, classify_contract
from app.contract_rules import grace_end as grace_end
from app.grant_applications import has_completed_application_expression
from app.models import FsdpParticipation, Program, Scholar
from app.record_text import outcome


def payback_data(
    db: Session,
    department: str = "",
    start_academic_year: str = "",
    *,
    today: date | None = None,
    include_items: bool = True,
) -> dict:
    today = today or date.today()
    has_graduated = has_completed_application_expression()
    statement = (
        select(
            Scholar.id,
            Scholar.name,
            affiliation_expression(Scholar.department),
            FsdpParticipation.id,
            FsdpParticipation.program_id,
            FsdpParticipation.application_key,
            Program.name,
            FsdpParticipation.start_academic_year,
            FsdpParticipation.status,
            FsdpParticipation.contract_completed_on,
            has_graduated,
        )
        .join(FsdpParticipation, FsdpParticipation.scholar_id == Scholar.id)
        .join(Program, Program.id == FsdpParticipation.program_id)
    )
    if department.strip():
        statement = statement.where(
            affiliation_expression(Scholar.department) == affiliation(department)
        )
    if start_academic_year.strip():
        statement = statement.where(
            func.trim(FsdpParticipation.start_academic_year) == start_academic_year.strip()
        )
    items = []
    scholar_sets = {group: set() for group in GROUPS}
    grant_counts = {group: 0 for group in GROUPS}
    for (
        scholar_id,
        name,
        department_name,
        grant_id,
        program_id,
        application_key,
        program_name,
        year,
        status,
        completed,
        graduated,
    ) in db.execute(statement):
        group, deadline = classify_contract(status, completed, graduated, today)
        scholar_sets[group].add(scholar_id)
        grant_counts[group] += 1
        if not include_items:
            continue
        items.append(
            {
                "scholar_id": scholar_id,
                "scholar_name": name,
                "department": department_name,
                "participation_id": grant_id,
                "program_id": program_id,
                "application_key": application_key,
                "program_name": program_name,
                "academic_year": year,
                "recorded_status": outcome(status),
                "contract_completed_on": completed,
                "grace_ends_on": deadline,
                "attention": group,
                "days_remaining": max(0, (deadline - today).days)
                if group == "In grace period" and deadline
                else None,
            }
        )
    items.sort(
        key=lambda item: (
            GROUPS.index(item["attention"]),
            item["scholar_name"].casefold(),
            item["participation_id"],
        )
    )
    return {
        "as_of": today.isoformat(),
        "items": items,
        "scholar_counts": {group: len(identities) for group, identities in scholar_sets.items()},
        "grant_counts": grant_counts,
    }
