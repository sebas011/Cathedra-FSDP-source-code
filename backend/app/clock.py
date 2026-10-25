"""The office's business date is independent of the computer's timezone."""

from datetime import date, datetime, timedelta, timezone

MANILA_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Manila")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def business_today(now: datetime | None = None) -> date:
    """Resolve an instant to the Manila day; naive supplied instants mean UTC."""
    instant = now if now is not None else utc_now()
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(MANILA_TIMEZONE).date()
