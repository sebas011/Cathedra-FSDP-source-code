import re
from decimal import Decimal, InvalidOperation

# Optional legacy text remains stored intact; only inference has a small parsing budget.
TENURE_PARSE_LIMIT = 128
_YEAR_UNITS = {"year", "years", "yr", "yrs"}
_MONTH_UNITS = {"month", "months", "mo", "mos"}


def _tenure_token(text: str, position: int) -> tuple[str, str, int] | None:
    start = position
    while position < len(text) and text[position].isdecimal():
        position += 1
    if position == start:
        return None
    if position < len(text) and text[position] == ".":
        position += 1
        fraction = position
        while position < len(text) and text[position].isdecimal():
            position += 1
        if position == fraction:
            return None
    number = text[start:position]
    while position < len(text) and text[position].isspace():
        position += 1
    unit_start = position
    while position < len(text) and text[position].isalpha():
        position += 1
    unit = text[unit_start:position]
    while position < len(text) and text[position].isspace():
        position += 1
    return number, unit, position


def tenure_in_years(value: str | None) -> float | None:
    if value is None or len(value) > TENURE_PARSE_LIMIT:
        return None
    text = (value or "").strip().lower()
    if not text:
        return None
    first = _tenure_token(text, 0)
    if first is None:
        return None
    number, unit, position = first
    years, months = "0", "0"
    if unit in _MONTH_UNITS:
        if position != len(text):
            return None
        months = number
    elif not unit or unit in _YEAR_UNITS:
        years = number
        if position != len(text):
            second = _tenure_token(text, position)
            if second is None or second[1] not in _MONTH_UNITS or second[2] != len(text):
                return None
            months = second[0]
    else:
        return None
    try:
        total = Decimal(years) + Decimal(months) / Decimal(12)
        return float(total.quantize(Decimal("0.000001")))
    except InvalidOperation:
        return None


def education_level(degree: str) -> str:
    text = degree.lower()
    if "bachelor" in text or re.match(r"^(?:bs|ba|bsc|b\.s\.|b\.a\.)(?:\s|$)", text.strip()):
        return "Bachelor’s"
    if "master" in text or re.match(r"^(?:ma|ms|mba|med|meng|msc)\b", text):
        return "Master’s"
    if "doctor" in text or "ph.d" in text or "phd" in text or "ph d" in text:
        return "Ph.D."
    return "Other"
