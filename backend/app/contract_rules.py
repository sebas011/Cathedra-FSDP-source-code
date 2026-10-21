"""Pure contract grace-period and outcome rules shared by reports."""

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


def classify_contract(
    status: str, completed: date | None, graduated: bool, today: date
) -> tuple[str, date | None]:
    deadline = grace_end(completed) if completed and completed.year <= 9996 else None
    if status.strip().casefold() == "payback":
        return "Recorded Payback", deadline
    if status.strip().casefold() == "payback pending contract":
        return "Payback pending contract", deadline
    if status.strip().casefold() == "did not avail":
        return "Did Not Avail", None
    if graduated or status.strip().casefold() in {"graduated", "completed"}:
        return "Completed", deadline
    if completed is None:
        return "Completion date missing", None
    if completed > today or deadline is None:
        return "Contract not completed", deadline
    return ("Payback review" if today > deadline else "In grace period"), deadline
