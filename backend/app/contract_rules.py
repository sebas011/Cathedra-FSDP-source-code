"""Pure contract grace-period and outcome rules shared by reports."""

from dataclasses import dataclass
from datetime import date

GROUPS = (
    "Recorded Payback",
    "Payback pending contract",
    "Payback review",
    "In grace period",
    "Completion date missing",
    "Contract not completed",
    "Completed",
    "Did Not Avail",
)


def completion_deadline(
    start_date: date | None = None,
    allowed_duration_years: int | None = None,
    completion_due_on: date | None = None,
    contract_completed_on: date | None = None,
) -> tuple[date | None, str | None]:
    """Choose recorded facts, preserving old contract dates as a fallback."""
    if completion_due_on is not None:
        return completion_due_on, "Explicit deadline"
    if start_date is not None and allowed_duration_years is not None:
        target_year = start_date.year + allowed_duration_years
        if 1 <= target_year <= 9999:
            try:
                deadline = start_date.replace(year=target_year)
            except ValueError:
                # 29 February has a 28 February anniversary in a non-leap year.
                deadline = start_date.replace(year=target_year, day=28)
            return deadline, "Program start and allowed duration"
        return None, None
    if contract_completed_on is not None:
        return contract_completed_on, "Previously recorded completion date"
    return None, None


def matches_attention(attention: str, selected: str) -> bool:
    selected = selected.strip()
    if selected.casefold() == "graduated":
        selected = "Completed"
    if selected == "Payback action":
        return attention in {"Recorded Payback", "Payback review", "Payback pending contract"}
    return not selected or attention == selected


def grace_end(completed: date) -> date:
    # A leap-day anniversary falls on the last February day three years later.
    return completed.replace(
        year=completed.year + 3,
        day=28 if completed.month == 2 and completed.day == 29 else completed.day,
    )


@dataclass(frozen=True, slots=True)
class ContractAssessment:
    attention: str
    grace_ends_on: date | None
    rule_code: str
    reason: str
    as_of: date


def assess_contract(
    status: str, completed: date | None, graduated: bool, today: date
) -> ContractAssessment:
    """Explain the existing rules without replacing recorded office outcomes."""
    deadline = grace_end(completed) if completed and completed.year <= 9996 else None
    recorded = status.strip().casefold()

    def result(attention: str, code: str, reason: str, grace: date | None = deadline):
        return ContractAssessment(attention, grace, code, reason, today)

    if recorded == "payback":
        return result(
            "Recorded Payback",
            "CONTRACT_RECORDED_PAYBACK",
            "Payback was recorded by the office. Calculated dates, case status and payment "
            "progress do not replace that recorded outcome.",
        )
    if recorded == "payback pending contract":
        return result(
            "Payback pending contract",
            "CONTRACT_RECORDED_PENDING",
            "The office recorded a pending repayment contract. Calculated dates, case status "
            "and payment progress do not replace that recorded outcome.",
        )
    if recorded == "did not avail":
        return result(
            "Did Not Avail",
            "CONTRACT_NOT_AVAILED",
            "This grant is recorded as Did Not Avail, so calculated payback review does not apply.",
            None,
        )
    if recorded in {"graduated", "completed"}:
        return result(
            "Completed",
            "CONTRACT_COMPLETED_RECORDED",
            "This grant has a recorded Completed outcome, so calculated payback review is cleared.",
        )
    if graduated:
        return result(
            "Completed",
            "CONTRACT_COMPLETED_APPLICATION",
            "Another grant in the same recorded application group has a Completed outcome, so "
            "calculated payback review is cleared for this group.",
        )
    if completed is None:
        return result(
            "Completion date missing",
            "CONTRACT_DEADLINE_MISSING",
            "No usable completion deadline is recorded. An exact deadline, or a program start "
            "date and allowed duration, is needed to calculate the grace period.",
        )
    if deadline is None:
        return result(
            "Contract not completed",
            "CONTRACT_DEADLINE_UNUSABLE",
            "The recorded completion reference is outside the supported three-year grace "
            "calculation range. No payback review date has been inferred.",
        )
    if completed > today:
        return result(
            "Contract not completed",
            "CONTRACT_BEFORE_DEADLINE",
            f"The completion reference date is {completed.isoformat()}, which has not arrived. "
            f"The three-year grace period ends {deadline.isoformat()}.",
        )
    if today > deadline:
        return result(
            "Payback review",
            "CONTRACT_REVIEW_DUE",
            f"The completion reference date was {completed.isoformat()} and the three-year "
            f"grace period ended {deadline.isoformat()}. This application group has no recorded "
            "Completed outcome and needs office review.",
        )
    return result(
        "In grace period",
        "CONTRACT_IN_GRACE",
        f"The completion reference date was {completed.isoformat()}. The three-year grace "
        f"period includes {deadline.isoformat()}; calculated payback review begins after that day.",
    )


def classify_contract(
    status: str, completed: date | None, graduated: bool, today: date
) -> tuple[str, date | None]:
    """Compatibility interface for existing reports, callers and integrations."""
    assessment = assess_contract(status, completed, graduated, today)
    return assessment.attention, assessment.grace_ends_on
