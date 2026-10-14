from app.models import FsdpParticipation, Scholar


def effective_hei(participation: FsdpParticipation) -> str | None:
    return (participation.delivering_hei or "").strip() or None


def has_missing_requirements(scholar: Scholar) -> bool:
    return scholar.missing_requirements or any(
        not item.is_complete for item in scholar.requirements
    )
