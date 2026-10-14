"""Normalization for newly entered business text; historical values stay intact."""

import re


def uppercase_text(value: str | None) -> str | None:
    return value.upper() if value is not None else None


def edited_text(value: str | None, previous: str | None, *, new: bool = False) -> str | None:
    # Old full forms resend values. Do not rewrite preserved historical notes or
    # program identities merely because an unrelated field was saved.
    unchanged = value == previous or (isinstance(value, str) and isinstance(previous, str) and value.strip() == previous.strip())
    return previous if not new and unchanged else uppercase_text(value)


def academic_year(value: str | None) -> str | None:
    """Format recognizable eight-digit year ranges without rejecting custom text."""
    if value is None:
        return None
    match = re.fullmatch(r"(\d{4})(\d{4})", value.strip())
    if match and 1900 <= int(match[1]) <= 2199 and int(match[2]) == int(match[1]) + 1:
        return f"{match[1]}-{match[2]}"
    return value


def outcome(value: str) -> str:
    return "Completed" if value.strip().casefold() in {"graduated", "completed"} else value.strip()


def is_completed(value: str) -> bool:
    return value.strip().casefold() in {"graduated", "completed"}


def unicode_contains(value: str | None, search: str | None) -> int:
    """Literal substring matching for new uppercase and historical Unicode text."""
    return int((search or "").casefold() in (value or "").casefold())
