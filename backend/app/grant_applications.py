"""Completion is shared by annual grants in one scholar application only."""

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.models import FsdpParticipation
from app.record_text import is_completed


def application_group_key(grant) -> tuple[int | None, int, str | None]:
    """NULL keeps historical annual records together without guessing cycles."""
    return grant.scholar_id, grant.program_id, grant.application_key or None


def completed_application_keys(grants: Iterable) -> set[tuple[int | None, int, str | None]]:
    return {application_group_key(grant) for grant in grants if is_completed(grant.status)}


def has_completed_application_expression(grant=FsdpParticipation):
    """SQL equivalent of the Python key, including the legacy NULL group."""
    completed = aliased(FsdpParticipation)
    return (
        select(completed.id)
        .where(
            completed.scholar_id == grant.scholar_id,
            completed.program_id == grant.program_id,
            func.coalesce(completed.application_key, "")
            == func.coalesce(grant.application_key, ""),
            func.lower(func.trim(completed.status)).in_(["graduated", "completed"]),
        )
        .correlate(grant)
        .exists()
    )
