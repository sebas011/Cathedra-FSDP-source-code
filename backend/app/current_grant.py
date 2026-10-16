import re

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import aliased

from app.models import FsdpParticipation, Scholar
from app.record_text import outcome

TERM_POSITION = {"1st": 0, "2nd": 1, "3rd": 2, "Summer": 3}


def grant_order(grant):
    match = re.match(r"\s*(\d{4})", grant.start_academic_year or "")
    return (int(match[1]) if match else 0, TERM_POSITION.get(grant.start_term, -1), grant.id or 0)


def current_grant(scholar):
    return max(scholar.participations, key=grant_order, default=None)


def current_status(scholar):
    grant = current_grant(scholar)
    return outcome(grant.status) if grant else None


def current_status_expression():
    grant = aliased(FsdpParticipation)
    status = case(
        (func.lower(func.trim(grant.status)).in_(["graduated", "completed"]), "Completed"),
        else_=func.trim(grant.status),
    )
    return (
        select(status)
        .where(grant.scholar_id == Scholar.id)
        .order_by(
            case(
                (
                    func.substr(func.trim(grant.start_academic_year), 1, 4).op("GLOB")(
                        "[0-9][0-9][0-9][0-9]"
                    ),
                    cast(func.substr(func.trim(grant.start_academic_year), 1, 4), Integer),
                ),
                else_=0,
            ).desc(),
            case(TERM_POSITION, value=grant.start_term, else_=-1).desc(),
            grant.id.desc(),
        )
        .limit(1)
        .correlate(Scholar)
        .scalar_subquery()
    )


def name_prefix_matches(name, search):
    words = re.findall(r"[^\W_]+", (name or "").casefold())
    terms = re.findall(r"[^\W_]+", (search or "").casefold())
    return int(bool(terms) and all(any(word.startswith(term) for word in words) for term in terms))
