"""Conservative, offline graduation evidence; never alters grant outcomes."""

import re
from datetime import date

from app import clock
from app.models import ScholarEducation
from app.profile_values import education_level

_MARKER = re.compile(r"\bgraduated\b|\bgraduation\s+(?:date|year)\s*[:=]", re.I)
_UNCERTAIN = re.compile(
    r"\b(?:not|never|no|hasn['’]?t|haven['’]?t|didn['’]?t|expected|expecting|"
    r"scheduled|planned|planning|target|tentative|pending|awaiting|will|would|"
    r"might|should|hopefully|if|previously|previous|prior|formerly|earlier)\b|\?",
    re.I,
)
_CLAIM = re.compile(
    r"^(?:(?:(?:the\s+)?scholar|he|she)\s+)?(?:has\s+)?(?:successfully\s+)?"
    r"(?P<marker>graduated\b|graduation\s+(?:date|year)\s*[:=])(?P<tail>.*)$",
    re.I,
)
_ABBREVIATION = re.compile(
    r"(?<!\w)(?:Ph\.D\.?|Ed\.D\.?|D\.B\.A\.?|M\.Ed\.?|M\.Sc\.?|B\.Sc\.?|"
    r"M\.A\.?|M\.S\.?|B\.A\.?|B\.S\.?)(?!\w)",
    re.I,
)
_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_MONTHS = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}
_DEGREES = (
    ("doctor of philosophy", "phd"),
    ("doctor of education", "edd"),
    ("doctor of business administration", "dba"),
    ("master of science", "ms"),
    ("master of arts", "ma"),
    ("master of education", "med"),
    ("master of business administration", "mba"),
    ("bachelor of science", "bs"),
    ("bachelor of arts", "ba"),
    ("msc", "ms"),
    ("bsc", "bs"),
)


def _abbreviations(text: str) -> str:
    text = _ABBREVIATION.sub(lambda match: match.group().replace(".", ""), text)
    return re.sub(rf"\b({_MONTH})\.(?=\s+\d)", r"\1", text, flags=re.I)


def _qualification(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", _abbreviations(text).casefold())
    text = " ".join(text.split())
    for phrase, replacement in _DEGREES:
        text = re.sub(rf"\b{phrase}\b", replacement, text)
    return " ".join(word for word in text.split() if word not in {"a", "the", "in", "of", "degree"})


def _same_program(qualification: str, program_name: str | None) -> bool:
    qualification = re.sub(r"^(?:with|from)\s+", "", qualification, flags=re.I)
    if qualification.casefold() in {
        "",
        "this program",
        "the program",
        "current program",
        "this degree",
    }:
        return True
    if program_name is None:
        # Without program context a named qualification cannot be safely attributed.
        return False
    claimed, program = _qualification(qualification), _qualification(program_name)
    if claimed == program:
        return True
    if claimed in {"phd", "edd", "dba", "ms", "ma", "med", "mba", "bs", "ba"}:
        return program.split()[:1] == [claimed]
    generic = {
        "bachelor": "Bachelor’s",
        "master": "Master’s",
        "doctorate": "Ph.D.",
        "doctoral": "Ph.D.",
    }
    return claimed in generic and education_level(program_name) == generic[claimed]


def _period(text: str, today: date) -> tuple[bool, str | None]:
    """Validate only explicitly asserted evidence, not optional profile fields."""
    text = re.sub(r"^(?:on|in|last)\s+", "", text.strip(), flags=re.I).strip(" :=,.-")
    if not text:
        return True, None
    if re.fullmatch(r"(?:19|20)\d{2}", text):
        return int(text) <= today.year, text
    iso = re.fullmatch(r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})", text)
    numeric = re.fullmatch(r"(?P<a>\d{1,2})[/\-](?P<b>\d{1,2})[/\-](?P<y>\d{4})", text)
    named = re.fullmatch(
        rf"(?P<m>{_MONTH})\.?\s+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(?P<y>\d{{4}})", text, re.I
    )
    day_first = re.fullmatch(
        rf"(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m>{_MONTH})\.?[,]?\s+(?P<y>\d{{4}})", text, re.I
    )
    month_only = re.fullmatch(rf"(?P<m>{_MONTH})\.?\s+(?P<y>\d{{4}})", text, re.I)
    try:
        if iso:
            completed = date(int(iso["y"]), int(iso["m"]), int(iso["d"]))
        elif numeric:
            first, second, year = int(numeric["a"]), int(numeric["b"]), int(numeric["y"])
            if first <= 12 and second <= 12 and first != second:
                return False, None
            month, day = (second, first) if first > 12 else (first, second)
            completed = date(year, month, day)
        elif match := named or day_first or month_only:
            completed = date(
                int(match["y"]),
                _MONTHS[match["m"][:3].casefold()],
                int(match["d"]) if match is not month_only else 1,
            )
        else:
            return False, None
    except ValueError:
        return False, None
    return completed <= today, str(completed.year)


def _tail_evidence(tail: str, program_name: str | None, today: date) -> tuple[bool, str | None]:
    tail = tail.strip().strip(" :=,.-")
    qualifier, period = tail, ""
    if re.match(rf"^(?:(?:on|in|last)\s+)?(?:\d|{_MONTH}\b)", tail, re.I):
        qualifier, period = "", tail
    else:
        separators = list(re.finditer(r"\b(?:on|in)\s+", tail, re.I))
        if separators:
            last = separators[-1]
            suffix = tail[last.start() :]
            # A qualification may itself contain "in" (Arts in Education).
            # Split only a recognized, completed date; invalid/future suffixes
            # still fail the complete-qualification comparison conservatively.
            if _period(suffix, today)[0]:
                qualifier, period = tail[: last.start()].strip(), suffix
    if not _same_program(qualifier, program_name):
        return False, None
    return _period(period, today)


def graduation_evidence(
    remarks: str | None, program_name: str | None = None, *, today: date | None = None
) -> tuple[bool, str | None]:
    """Accept direct current-program claims; uncertain text remains saveable."""
    today = today if today is not None else clock.business_today()
    clauses = re.split(r"[;\n]+|(?<=[.!?])\s+", _abbreviations(remarks or ""))
    if any(_MARKER.search(clause) and _UNCERTAIN.search(clause) for clause in clauses):
        return False, None
    confirmed, years = False, set()
    for clause in clauses:
        claim = _CLAIM.fullmatch(clause.strip())
        if not claim:
            continue
        valid, year = _tail_evidence(claim["tail"], program_name, today)
        if not valid:
            return False, None
        if claim["marker"].casefold().startswith("graduation") and not year:
            continue
        confirmed = True
        if year:
            years.add(year)
    return confirmed, next(iter(years)) if len(years) == 1 else None


def sync_graduated_education(
    scholar, *, uppercase_new: bool = False, today: date | None = None
) -> bool:
    """Return whether achievements changed; preserve corrections and removals."""
    today = today if today is not None else clock.business_today()
    graduated: dict[int, list] = {}
    for grant in scholar.participations:
        evidence, year = graduation_evidence(grant.remarks, grant.program.name, today=today)
        if grant.graduation_date is not None:
            year = str(grant.graduation_date.year)
        if grant.status.strip().casefold() in {"graduated", "completed"} or evidence:
            graduated.setdefault(grant.program_id, []).append((grant, year))
    changed = False
    suppressed = {item.program_id for item in scholar.education_suppressions}
    for program_id, achievements in graduated.items():
        if program_id in suppressed:
            continue
        grant = max((item[0] for item in achievements), key=lambda item: item.id or 0)
        years = {year for _, year in achievements if year}
        year = next(iter(years)) if len(years) == 1 else None
        linked = next(
            (entry for entry in scholar.education if entry.source_program_id == program_id), None
        )
        if linked:
            explicit_date = any(item[0].graduation_date is not None for item in achievements)
            if (
                not linked.graduation_year_manual
                and year
                and (not (linked.graduation_year or "").strip() or explicit_date)
                and linked.graduation_year != year
            ):
                linked.graduation_year = year
                changed = True
            continue
        degree = grant.program.name.strip()
        institution = (grant.delivering_hei or "").strip()
        if any(
            entry.degree.strip().casefold() == degree.casefold()
            and entry.institution.strip().casefold() == institution.casefold()
            for entry in scholar.education
        ):
            continue
        scholar.education.append(
            ScholarEducation(
                source_program_id=program_id,
                level=education_level(degree).upper() if uppercase_new else education_level(degree),
                degree=degree.upper() if uppercase_new else degree,
                institution=institution.upper() if uppercase_new else institution,
                graduation_year=year,
            )
        )
        changed = True
    return changed
