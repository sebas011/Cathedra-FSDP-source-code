"""Bounded business-value history. Account and internal fields are never snapshots."""

import json
import math
from datetime import date, datetime

MAX_DETAIL_TEXT = 1000
MAX_DETAIL_JSON = 512_000
MAX_DETAIL_ROWS = 64

# Keep this explicit: adding a model field must not silently add it to history.
DETAIL_FIELDS = {
    "scholars": frozenset(
        {
            "name",
            "age",
            "previous_degree",
            "missing_requirements",
            "has_hard_copy",
            "has_soft_copy",
            "department",
            "personnel_type",
            "rank",
            "tenure",
            "tenure_years",
            "tenure_note",
            "profile_remarks",
        }
    ),
    "scholar_education": frozenset({"level", "degree", "institution", "graduation_year"}),
    "scholar_requirements": frozenset(
        {"requirement_name", "due_date", "is_complete", "completed_at", "remarks"}
    ),
    "fsdp_participations": frozenset(
        {
            "delivering_hei",
            "start_date",
            "end_date",
            "contract_completed_on",
            "allowed_duration_years",
            "completion_due_on",
            "payback_payment_status",
            "graduation_date",
            "case_status",
            "start_term",
            "start_academic_year",
            "end_term",
            "end_academic_year",
            "status",
            "grant_type",
            "program_category",
            "grant_other",
            "extension",
            "remarks",
        }
    ),
    "programs": frozenset({"name", "delivering_hei", "description"}),
}


def detail_value(value: object) -> tuple[object, bool]:
    """Convert only supported scalar values; never stringify an arbitrary object."""
    if isinstance(value, datetime | date):
        return value.isoformat(), False
    if value is None or isinstance(value, bool | int):
        return value, False
    if isinstance(value, float) and math.isfinite(value):
        return value, False
    if isinstance(value, str):
        return value[:MAX_DETAIL_TEXT], len(value) > MAX_DETAIL_TEXT
    raise ValueError("Unsupported history value")


def sanitize_change_details(record_type: str | None, payload: object) -> list[dict[str, object]]:
    """Treat old database payloads as untrusted; return safe rows or an empty list."""
    allowed = DETAIL_FIELDS.get(record_type or "", frozenset())
    if not allowed:
        return []
    if isinstance(payload, str):
        if len(payload) > MAX_DETAIL_JSON:
            return []
        try:
            payload = json.loads(payload)
        except ValueError, TypeError, RecursionError:
            return []
    if not isinstance(payload, list):
        return []
    result = []
    seen = set()
    for item in payload[:MAX_DETAIL_ROWS]:
        if not isinstance(item, dict):
            continue
        name = item.get("field")
        if not isinstance(name, str) or name not in allowed or name in seen:
            continue
        if "before" not in item or "after" not in item:
            continue
        try:
            before, before_truncated = detail_value(item["before"])
            after, after_truncated = detail_value(item["after"])
        except ValueError:
            continue
        row = {"field": name, "before": before, "after": after}
        if before_truncated or (item.get("before_truncated") is True and isinstance(before, str)):
            row["before_truncated"] = True
        if after_truncated or (item.get("after_truncated") is True and isinstance(after, str)):
            row["after_truncated"] = True
        result.append(row)
        seen.add(name)
    return result
