from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.college_classification import affiliation, affiliation_expression, personnel_type
from app.contract_rules import completion_deadline
from app.current_grant import current_status, current_status_expression
from app.fsdp_values import effective_hei, has_missing_requirements
from app.grant_applications import application_group_key, completed_application_keys
from app.models import FsdpParticipation, Scholar, ScholarRequirement
from app.record_text import outcome
from app.schemas import EducationRead, ParticipationRead, RequirementRead, ScholarRead


def registration_series(db: Session, selected_ids, *, now: datetime | None = None) -> dict:
    """Monthly registration history from actual profile timestamps, never grant years.

    SQLite CURRENT_TIMESTAMP stores UTC without a timezone suffix. Explicit offsets
    are also understood by strftime; +8 hours maps both to the office's Manila day.
    Invalid and future timestamps remain in the scope total but outside the plot.
    """
    manila = timezone(timedelta(hours=8))
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    today = instant.astimezone(manila).date()
    end_month = today.year * 12 + today.month - 1
    months = [
        f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(end_month - 11, end_month + 1)
    ]
    month = func.strftime("%Y-%m", Scholar.created_at, "+8 hours")
    # A single aggregate query includes the entire selected history, not recent 10.
    groups = dict(
        db.execute(
            select(month, func.count())
            .where(
                Scholar.id.in_(selected_ids),
                func.julianday(Scholar.created_at) <= func.julianday(instant.isoformat()),
            )
            .group_by(month)
        ).all()
    )
    before = sum(count for key, count in groups.items() if key and key < months[0])
    cumulative = before
    rows = []
    for key in months:
        count = groups.get(key, 0)
        cumulative += count
        rows.append({"month": key, "count": count, "cumulative": cumulative})
    return {
        "timezone": "Asia/Manila",
        "starts_on": months[0] + "-01",
        "ends_on": today.isoformat(),
        "before_period": before,
        "rows": rows,
        "plotted": cumulative,
    }


def options():
    return [
        selectinload(Scholar.participations).selectinload(FsdpParticipation.program),
        selectinload(Scholar.requirements),
        selectinload(Scholar.education),
        selectinload(Scholar.education_suppressions),
    ]


def matching_participations(scholar: Scholar, filters: dict) -> list[FsdpParticipation]:
    return [
        item
        for item in scholar.participations
        if (
            not filters.get("status_filter")
            or current_status(scholar) == outcome(filters["status_filter"])
        )
        and (
            not filters.get("start_academic_year")
            or (item.start_academic_year or "").strip() == filters["start_academic_year"]
        )
        and (
            not filters.get("grant_type")
            or (item.grant_type or "").strip() == filters["grant_type"]
        )
        and (not filters.get("delivering_hei") or effective_hei(item) == filters["delivering_hei"])
    ]


def read_scholar(scholar: Scholar) -> ScholarRead:
    from app.contract_rules import classify_contract

    completed_applications = completed_application_keys(scholar.participations)
    today = date.today()
    return ScholarRead(
        id=scholar.id,
        revision=scholar.revision,
        name=scholar.name,
        age=scholar.age,
        previous_degree=scholar.previous_degree,
        missing_requirements=has_missing_requirements(scholar),
        manual_requirements_follow_up=scholar.missing_requirements,
        has_hard_copy=scholar.has_hard_copy,
        has_soft_copy=scholar.has_soft_copy,
        department=affiliation(scholar.department),
        rank=scholar.rank,
        personnel_type=personnel_type(scholar.department),
        current_status=current_status(scholar),
        tenure=scholar.tenure,
        tenure_years=scholar.tenure_years,
        tenure_note=scholar.tenure_note,
        profile_remarks=scholar.profile_remarks,
        education=[
            EducationRead(
                source_program_id=item.source_program_id,
                id=item.id,
                level=item.level,
                degree=item.degree,
                institution=item.institution,
                graduation_year=item.graduation_year,
            )
            for item in scholar.education
        ],
        suppressed_education_program_ids=[
            item.program_id for item in scholar.education_suppressions
        ],
        data_source=scholar.data_source,
        created_at=scholar.created_at,
        updated_at=scholar.updated_at,
        participations=[
            ParticipationRead(
                id=item.id,
                program_id=item.program_id,
                name=item.program.name,
                delivering_hei=effective_hei(item),
                description=item.program.description,
                start_date=item.start_date,
                end_date=item.end_date,
                contract_completed_on=item.contract_completed_on,
                allowed_duration_years=item.allowed_duration_years,
                completion_due_on=item.completion_due_on,
                completion_deadline_on=effective_deadline,
                completion_deadline_source=deadline_source,
                payback_payment_status=item.payback_payment_status,
                graduation_date=item.graduation_date,
                case_status=item.case_status,
                payback_attention=attention,
                grace_ends_on=deadline,
                start_term=item.start_term,
                start_academic_year=item.start_academic_year,
                end_term=item.end_term,
                end_academic_year=item.end_academic_year,
                grant_type=item.grant_type,
                program_category=item.program_category,
                application_key=item.application_key,
                grant_other=item.grant_other,
                status=outcome(item.status),
                extension=item.extension,
                remarks=item.remarks,
            )
            for item in scholar.participations
            for effective_deadline, deadline_source in [
                completion_deadline(
                    item.start_date,
                    item.allowed_duration_years,
                    item.completion_due_on,
                    item.contract_completed_on,
                )
            ]
            for attention, deadline in [
                classify_contract(
                    item.status,
                    effective_deadline,
                    application_group_key(item) in completed_applications,
                    today,
                )
            ]
        ],
        requirements=[
            RequirementRead(
                id=item.id,
                requirement_name=item.requirement_name,
                due_date=item.due_date,
                is_complete=item.is_complete,
                completed_at=item.completed_at,
                remarks=item.remarks,
            )
            for item in scholar.requirements
        ],
    )


def report_scholars(
    db: Session,
    department: str = "",
    rank: str = "",
    status_filter: str = "",
    grant_type: str = "",
    delivering_hei: str = "",
    missing_requirements: bool = False,
    start_academic_year: str = "",
    summary_only: bool = False,
) -> list[Scholar]:
    from sqlalchemy.orm import selectinload

    load_options = (
        [
            selectinload(Scholar.participations).selectinload(FsdpParticipation.program),
            selectinload(Scholar.requirements),
        ]
        if summary_only
        else options()
    )
    statement = select(Scholar).options(*load_options).distinct()
    if department.strip():
        statement = statement.where(
            affiliation_expression(Scholar.department) == affiliation(department)
        )
    if rank.strip():
        statement = statement.where(func.trim(Scholar.rank) == rank.strip())
    if missing_requirements:
        statement = statement.where(
            or_(
                Scholar.missing_requirements.is_(True),
                Scholar.requirements.any(ScholarRequirement.is_complete.is_(False)),
            )
        )
    if (
        status_filter.strip()
        or grant_type.strip()
        or delivering_hei.strip()
        or start_academic_year.strip()
    ):
        statement = statement.join(Scholar.participations).join(FsdpParticipation.program)
        if start_academic_year.strip():
            statement = statement.where(
                func.trim(FsdpParticipation.start_academic_year) == start_academic_year.strip()
            )
        if status_filter.strip():
            statement = statement.where(current_status_expression() == outcome(status_filter))
        if grant_type.strip():
            statement = statement.where(
                func.trim(FsdpParticipation.grant_type) == grant_type.strip()
            )
        if delivering_hei.strip():
            statement = statement.where(
                func.trim(FsdpParticipation.delivering_hei) == delivering_hei.strip()
            )
    return list(
        db.scalars(statement.order_by(func.name_sort_key(Scholar.name), Scholar.id)).unique().all()
    )


def fsdp_report_data(db: Session, **filters: object) -> dict[str, object]:
    page = filters.pop("page", None)
    page_size = int(filters.pop("page_size", 50))
    action_page = int(filters.pop("action_page", 1))
    filters = {
        key: value.strip() if isinstance(value, str) else value for key, value in filters.items()
    }
    scholars = report_scholars(db, summary_only=page is not None, **filters)
    visible_ids = (
        {item.id for item in scholars[(int(page) - 1) * page_size : int(page) * page_size]}
        if page is not None
        else {item.id for item in scholars}
    )
    if page is not None and visible_ids:
        db.scalars(select(Scholar).where(Scholar.id.in_(visible_ids)).options(*options())).all()
    report_items = []
    statuses = tuple(
        dict.fromkeys(
            [
                "On Going",
                "Completed",
                "Incomplete",
                "Payback",
                "Payback pending contract",
                "Transferred",
                "Withdrawn",
                "Did Not Avail",
                *[
                    outcome(value)
                    for value in db.scalars(select(FsdpParticipation.status).distinct())
                    if value.strip()
                ],
            ]
        )
    )
    grant_types = tuple(
        dict.fromkeys(
            [
                "Full Scholarship",
                "Partial Scholarship",
                "Dissertation Aid",
                "Thesis Aid",
                "Others",
                *[
                    value.strip()
                    for value in db.scalars(
                        select(FsdpParticipation.grant_type)
                        .where(FsdpParticipation.grant_type.is_not(None))
                        .distinct()
                    )
                    if value.strip()
                ],
            ]
        )
    )
    today = date.today()
    upcoming_date = today + timedelta(days=90)
    department_totals: dict[str, dict[str, int | str]] = {}
    action_items: list[dict[str, object]] = []
    for scholar in scholars:
        department = affiliation(scholar.department)
        subtotal = department_totals.setdefault(
            department,
            {
                "department": department,
                "scholars": 0,
                "ongoing": 0,
                "graduated": 0,
                "completed": 0,
                "incomplete": 0,
                "payback": 0,
                "withdrawn": 0,
                "did_not_avail": 0,
                "transferred": 0,
                "payback_pending_contract": 0,
                "requirements_follow_up": 0,
            },
        )
        subtotal["scholars"] = int(subtotal["scholars"]) + 1
        if has_missing_requirements(scholar):
            subtotal["requirements_follow_up"] = int(subtotal["requirements_follow_up"]) + 1
        if scholar.missing_requirements:
            action_items.append(
                {
                    "scholar_id": scholar.id,
                    "scholar_name": scholar.name,
                    "department": affiliation(scholar.department),
                    "kind": "Requirement follow-up",
                    "detail": "Additional requirement follow-up flagged in the scholar record",
                    "attention": "Manual follow-up",
                    "priority": 2,
                }
            )
        selected = matching_participations(scholar, filters)
        if scholar.id in visible_ids:
            rendered = read_scholar(scholar)
            selected_ids = {item.id for item in selected}
            rendered.participations = [
                item for item in rendered.participations if item.id in selected_ids
            ]
            report_items.append(rendered)
        from app.contract_rules import classify_contract

        completed_applications = completed_application_keys(scholar.participations)
        for participation in selected:
            attention, deadline = classify_contract(
                participation.status,
                completion_deadline(
                    participation.start_date,
                    participation.allowed_duration_years,
                    participation.completion_due_on,
                    participation.contract_completed_on,
                )[0],
                application_group_key(participation) in completed_applications,
                today,
            )
            if attention in {"Recorded Payback", "Payback review", "Payback pending contract"}:
                action_items.append(
                    {
                        "scholar_id": scholar.id,
                        "scholar_name": scholar.name,
                        "department": affiliation(scholar.department),
                        "kind": "Contract payback",
                        "detail": f"{participation.program.name}: "
                        + (
                            "Repayment contract pending"
                            if attention == "Payback pending contract"
                            else "Payback recorded by the office"
                            if attention == "Recorded Payback"
                            else f"grace period ended {deadline.isoformat()}"
                        )
                        + (
                            f" · Payment: {participation.payback_payment_status}"
                            if participation.payback_payment_status
                            else ""
                        ),
                        "attention": attention,
                        "priority": 0,
                    }
                )
        status_key = {
            "On Going": "ongoing",
            "Completed": "completed",
            "Incomplete": "incomplete",
            "Payback": "payback",
            "Withdrawn": "withdrawn",
            "Did Not Avail": "did_not_avail",
            "Transferred": "transferred",
            "Payback pending contract": "payback_pending_contract",
        }.get(current_status(scholar))
        if status_key:
            subtotal[status_key] = int(subtotal[status_key]) + 1
            if status_key == "completed":
                subtotal["graduated"] = int(subtotal["graduated"]) + 1
        for requirement in scholar.requirements:
            if requirement.is_complete:
                continue
            if requirement.due_date is None:
                attention, priority, detail = (
                    "Due date not set",
                    2,
                    f"{requirement.requirement_name}: no due date",
                )
            elif requirement.due_date < today:
                attention, priority, detail = (
                    "Overdue",
                    0,
                    f"{requirement.requirement_name}: due {requirement.due_date.isoformat()}",
                )
            elif requirement.due_date <= upcoming_date:
                attention, priority, detail = (
                    "Due within 90 days",
                    1,
                    f"{requirement.requirement_name}: due {requirement.due_date.isoformat()}",
                )
            else:
                continue
            action_items.append(
                {
                    "scholar_id": scholar.id,
                    "scholar_name": scholar.name,
                    "department": affiliation(scholar.department),
                    "kind": "Requirement",
                    "detail": detail,
                    "attention": attention,
                    "priority": priority,
                }
            )
    action_items.sort(key=lambda item: (int(item["priority"]), str(item["scholar_name"])))
    return {
        "items": report_items,
        "total": len(scholars),
        "missing_requirements": sum(has_missing_requirements(scholar) for scholar in scholars),
        "status_counts": {
            item: sum(
                any(
                    current_status(scholar) == item
                    for participation in matching_participations(scholar, filters)
                )
                for scholar in scholars
            )
            for item in statuses
        },
        "grant_type_counts": {
            item: sum(
                any(
                    (participation.grant_type or "").strip() == item
                    for participation in matching_participations(scholar, filters)
                )
                for scholar in scholars
            )
            for item in grant_types
        },
        "department_totals": list(department_totals.values()),
        "action_total": len(action_items),
        "action_items": action_items[(action_page - 1) * page_size : action_page * page_size]
        if page is not None
        else action_items,
        "page": page,
        "page_size": page_size,
    }
