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
