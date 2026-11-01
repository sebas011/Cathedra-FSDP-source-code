"""Review a reporting snapshot and apply explicitly matched changes atomically."""

import copy
import hashlib
import json
import math
import re
import threading
import unicodedata
from datetime import date, timedelta
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.college_classification import affiliation
from app.concurrency import advance_revision
from app.fsdp_reporting import options
from app.google_report import GOOGLE_REPORT_HEADERS, _period
from app.google_sheets import SheetsError
from app.models import Scholar, SheetImportReceipt
from app.profile_values import tenure_in_years
from app.program_identity import program_key
from app.record_text import outcome
from app.schemas import ParticipationInput, RequirementInput, ScholarCreate, ScholarUpdate

MAX_ROWS = 2000
MAX_PROFILES = 5000
MAX_GRANTS = 20000
MAX_CELL = 20000
TTL = timedelta(minutes=20)
LEGACY_HEADERS = [name for name in GOOGLE_REPORT_HEADERS if name != "Profile remarks"]
PROFILE_FIELDS = ("name", "age", "tenure_years", "department", "rank", "profile_remarks")


def name_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def problem(message: str, code: int = 422):
    raise HTTPException(status_code=code, detail=message)


def cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise SheetsError("The report contains an unsupported cell value.")
    if isinstance(value, float) and not math.isfinite(value):
        raise SheetsError("The report contains an invalid number.")
    text = str(value).strip()
    if len(text) > MAX_CELL:
        raise SheetsError("A report cell exceeds the 20,000-character preview limit.")
    return text


def text(value) -> str | None:
    return cell(value).upper() or None


def number(value, row: int, label: str, *, integer: bool = False):
    value = cell(value)
    if not value:
        return None
    try:
        parsed = float(value)
        if not math.isfinite(parsed) or (integer and not parsed.is_integer()):
            raise ValueError
        if integer and not -(2**63) <= parsed < 2**63:
            raise ValueError
        if label == "Tenure" and parsed < 0:
            raise ValueError
        return int(parsed) if integer else parsed
    except ValueError, OverflowError:
        raise SheetsError(f"Row {row}: enter a number or leave {label} blank.") from None


def period(value, row: int) -> dict:
    rendered = cell(value)
    if not rendered:
        return {"date": None, "term": None, "academic_year": None}
    # Google dates can be returned as spreadsheet serial numbers. Strings emitted
    # by Cathedra remain literal ISO dates or recorded academic periods.
    if isinstance(value, int | float) and not isinstance(value, bool):
        if 1000 <= value <= 9999 and float(value).is_integer():
            rendered = str(int(value))
        else:
            try:
                recorded = date(1899, 12, 30) + timedelta(days=float(value))
                return {"date": recorded.isoformat(), "term": None, "academic_year": None}
            except ValueError, OverflowError:
                raise SheetsError(
                    f"Row {row}: the recorded date is outside its supported range."
                ) from None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", rendered):
        try:
            recorded = date.fromisoformat(rendered)
        except ValueError:
            raise SheetsError(
                f"Row {row}: use a valid YYYY-MM-DD date, or leave it blank."
            ) from None
        return {"date": recorded.isoformat(), "term": None, "academic_year": None}
    match = re.fullmatch(r"(1st|2nd|3rd|Summer)(?:\s+(.+))?", rendered, re.I)
    term = (
        {"1st": "1st", "2nd": "2nd", "3rd": "3rd", "summer": "Summer"}.get(match[1].lower())
        if match
        else None
    )
    return {"date": None, "term": term, "academic_year": match[2] if match else rendered}


def grant_fields(values: dict, row: int, *, legacy: bool) -> dict | None:
    program = text(values.get("Program"))
    detail_names = (
        "Delivering HEI",
        "Grant type",
        "Date started",
        "Date ended",
        "Extension",
        "Status",
    )
    if not program:
        if any(cell(values.get(name)) for name in detail_names) or (
            not legacy and cell(values.get("Remarks"))
        ):
            raise SheetsError(f"Row {row}: Program is required for a grant row.")
        return None
    kind = cell(values.get("Grant type"))
    other = None
    if kind.lower().startswith("other:"):
        kind, other = "Other", kind.split(":", 1)[1].strip().upper() or None
    result = {
        "program_name": program,
        "delivering_hei": text(values.get("Delivering HEI")),
        "grant_type": kind or None,
        "grant_other": other,
        "extension": text(values.get("Extension")),
    }
    if cell(values.get("Status")):
        result["status"] = outcome(cell(values.get("Status")))
    for source, prefix in (("Date started", "start"), ("Date ended", "end")):
        if not cell(values.get(source)):
            continue
        recorded = period(values.get(source), row)
        # A report cell may show only a term, only a year, or an exact date.
        # Updating it must not clear the other facts hidden by that presentation.
        represented = {key: value for key, value in recorded.items() if value is not None}
        result.update({f"{prefix}_{key}": value for key, value in represented.items()})
    if not legacy:
        result["remarks"] = text(values.get("Remarks"))
    return result


def parse_report(values: list[list]) -> tuple[list[dict], list[str]]:
    rows = list(values)
    while rows and not any(cell(value) for value in rows[-1]):
        rows.pop()
    if not rows:
        raise SheetsError("The reporting tab is empty. Add the report headings before pulling.")
    if len(rows) > MAX_ROWS + 1:
        raise SheetsError("Pull at most 2,000 report rows at a time.")
    headings = [cell(value) for value in rows[0]]
    while headings and not headings[-1]:
        headings.pop()
    legacy = headings == LEGACY_HEADERS
    if headings != GOOGLE_REPORT_HEADERS and not legacy:
        raise SheetsError(
            "Use the Cathedra report headings, including Name and Program. Column order must match the exported report."
        )
    warnings = [
        "Choose existing profiles and annual grants carefully. Report numbers are not record IDs.",
        "Existing education, requirements, document availability and unreported grant details are retained.",
        "An explicitly new grant creates an independent application.",
    ]
    if legacy:
        warnings.append(
            "This older report combines remarks. Separate profile and grant remarks will stay unchanged; the other reported fields can be imported."
        )
    profiles = []
    current = None
    for row_number, raw in enumerate(rows[1:], start=2):
        if len(raw) > len(headings) and any(cell(value) for value in raw[len(headings) :]):
            raise SheetsError(
                f"Row {row_number}: unexpected values appear after the report columns."
            )
        if not any(cell(value) for value in raw):
            current = None
            continue
        incoming = dict(zip(headings, [*raw, *([None] * (len(headings) - len(raw)))], strict=False))
        name = text(incoming.get("Name"))
        if name:
            profile_values = {
                "name": name,
                "age": number(incoming.get("Age"), row_number, "Age", integer=True),
                "tenure_years": number(incoming.get("Tenure"), row_number, "Tenure"),
                "department": affiliation(cell(incoming.get("Department"))),
                "rank": text(incoming.get("Rank/position")),
            }
            if not legacy:
                profile_values["profile_remarks"] = text(incoming.get("Profile remarks"))
            current = {
                "key": f"profile-{row_number}",
                "row": row_number,
                "fields": profile_values,
                "education_text": text(incoming.get("Previous degree")),
                "suggested_scholar_id": None,
                "grants": [],
            }
            profiles.append(current)
        elif current is None:
            raise SheetsError(
                f"Row {row_number}: Name is required before any continuation grant rows."
            )
        elif any(
            cell(incoming.get(name))
            for name in (
                "No.",
                "Age",
                "Tenure",
                "Department",
                "Rank/position",
                "Previous degree",
                "Profile remarks",
            )
        ):
            raise SheetsError(
                f"Row {row_number}: a profile row needs its Name; continuation rows contain grant details only."
            )
        grant = grant_fields(incoming, row_number, legacy=legacy)
        if grant is not None:
            current["grants"].append(
                {
                    "key": f"grant-{row_number}",
                    "row": row_number,
                    "fields": grant,
                    "suggested_participation_id": None,
                }
            )
    return profiles, warnings


def current_grant_fields(grant) -> dict:
    result = {
        key: getattr(grant, key)
        for key in ParticipationInput.model_fields
        if key not in {"id", "source_program_id", "program_name"}
    }
    result["program_name"] = grant.program.name
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in result.items()
    }


def signature(fields: dict) -> tuple:
    # Compare exactly what the report can identify; repeated applications with
    # the same visible facts deliberately remain ambiguous.
    periods = []
    for prefix in ("start", "end"):
        recorded = fields.get(f"{prefix}_date")
        if isinstance(recorded, str) and recorded:
            recorded = date.fromisoformat(recorded)
        periods.append(
            _period(recorded, fields.get(f"{prefix}_term"), fields.get(f"{prefix}_academic_year"))
        )
    return program_key(fields["program_name"]), *periods


class PreviewStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.items: dict[str, dict] = {}

    def clear(self):
        with self.lock:
            self.items.clear()

    def create(self, user_id: int, report: dict, db: Session) -> dict:
        profiles, warnings = parse_report(report["values"])
        scholars = list(
            db.scalars(
                select(Scholar).options(*options()).order_by(Scholar.id).limit(MAX_PROFILES + 1)
            ).unique()
        )
        if (
            len(scholars) > MAX_PROFILES
            or sum(len(item.participations) for item in scholars) > MAX_GRANTS
        ):
            raise SheetsError(
                "This directory is too large for one pull preview. Use a smaller reviewed import."
            )
        matches = [
            {
                "id": scholar.id,
                "name": scholar.name,
                "revision": scholar.revision,
                "fields": {
                    **{key: getattr(scholar, key) for key in PROFILE_FIELDS},
                    "tenure_years": scholar.tenure_years
                    if scholar.tenure_years is not None
                    else tenure_in_years(scholar.tenure),
                },
                "grants": [
                    {"id": grant.id, "fields": current_grant_fields(grant)}
                    for grant in scholar.participations
                ],
            }
            for scholar in scholars
        ]
        by_name: dict[str, list] = {}
        for match in matches:
            by_name.setdefault(name_key(match["name"]), []).append(match)
        for profile in profiles:
            candidates = by_name.get(name_key(profile["fields"]["name"]), [])
            if len(candidates) != 1:
                continue
            match = candidates[0]
            profile["suggested_scholar_id"] = match["id"]
            for grant in profile["grants"]:
                candidates = [
                    item
                    for item in match["grants"]
                    if signature(item["fields"]) == signature(grant["fields"])
                ]
                if len(candidates) == 1:
                    grant["suggested_participation_id"] = candidates[0]["id"]
        now = clock.utc_now()
        identity = str(uuid4())
        result = {
            "preview_id": identity,
            "fetched_at": now.isoformat(),
            "expires_at": (now + TTL).isoformat(),
            "worksheet": report["worksheet"],
            "warnings": warnings,
            "profiles": profiles,
            "matches": matches,
        }
        with self.lock:
            self.items = {
                key: value
                for key, value in self.items.items()
                if value["expires"] > now and value["user_id"] != user_id
            }
            if len(self.items) >= 10:
                raise SheetsError(
                    "Other pull previews are still open. Wait before creating another."
                )
            self.items[identity] = {
                "user_id": user_id,
                "expires": now + TTL,
                "result": copy.deepcopy(result),
                "baselines": {scholar.id: record_digest(scholar) for scholar in scholars},
            }
        return result

    def get(self, identity: str, user_id: int) -> dict:
        with self.lock:
            entry = self.items.get(identity)
            if entry is None or entry["user_id"] != user_id or entry["expires"] <= clock.utc_now():
                problem(
                    "This pull preview expired or is no longer available. Pull the sheet again.",
                    409,
                )
            return {**copy.deepcopy(entry["result"]), "_baselines": entry["baselines"].copy()}


class GrantChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=64)
    participation_id: int | None = Field(default=None, ge=1)


class ProfileChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=64)
    scholar_id: int | None = Field(default=None, ge=1)
    expected_revision: int | None = Field(default=None, ge=0)
    grants: list[GrantChoice] = Field(default_factory=list, max_length=MAX_ROWS)


class ApplyPull(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=36, max_length=36, pattern=r"^[0-9a-f-]{36}$")
    profiles: list[ProfileChoice] = Field(min_length=1, max_length=100)


def original_payload(scholar: Scholar) -> dict:
    values = {
        key: getattr(scholar, key)
        for key in ScholarCreate.model_fields
        if key
        not in {"education", "restore_education_program_ids", "participations", "requirements"}
    }
    values["participations"] = [
        {**current_grant_fields(grant), "id": grant.id, "source_program_id": grant.program_id}
        for grant in scholar.participations
    ]
    values["requirements"] = [
        {key: getattr(item, key) for key in RequirementInput.model_fields}
        for item in scholar.requirements
    ]
    return values


def record_digest(scholar: Scholar) -> str:
    values = {
        "payload": original_payload(scholar),
        "education": [
            {
                "id": item.id,
                "level": item.level,
                "degree": item.degree,
                "institution": item.institution,
                "graduation_year": item.graduation_year,
            }
            for item in scholar.education
        ],
        "suppressions": sorted(item.program_id for item in scholar.education_suppressions),
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def apply_pull(payload: ApplyPull, db: Session, user_id: int, store: PreviewStore) -> dict:
    from app.api.fsdp import apply_payload, assessment_day, commit_record
    from app.graduated_education import sync_graduated_education
    from app.scholar_identity import next_scholar_id

    canonical = payload.model_dump(mode="json")
    canonical["profiles"].sort(key=lambda item: item["key"])
    for item in canonical["profiles"]:
        item["grants"].sort(key=lambda grant: grant["key"])
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    # Reserve a writer before checking revisions/receipts. All aggregate writes,
    # audit events and the durable replay result commit together.
    db.rollback()
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    receipt = db.get(SheetImportReceipt, (user_id, payload.preview_id))
    if receipt is not None:
        if receipt.payload_digest != digest:
            problem(
                "This pull already saved a different selection. Pull again to review new changes.",
                409,
            )
        result = json.loads(receipt.result_json)
        result["replayed"] = True
        db.rollback()
        return result
    preview = store.get(payload.preview_id, user_id)
    sources = {item["key"]: item for item in preview["profiles"]}
    matches = {item["id"]: item for item in preview["matches"]}
    existing_names: dict[str, set] = {}
    for identity, name in db.execute(select(Scholar.id, Scholar.name)):
        existing_names.setdefault(name_key(name), set()).add(identity)
    prior_names: dict[str, set] = {}
    for match in matches.values():
        prior_names.setdefault(name_key(match["name"]), set()).add(match["id"])
    seen_profiles, seen_targets, seen_grants, seen_existing_grants = set(), set(), set(), set()
    prepared = []
    for choice in payload.profiles:
        if choice.key in seen_profiles or choice.key not in sources:
            problem("A selected profile appears twice or is not part of this preview.")
        seen_profiles.add(choice.key)
        source = sources[choice.key]
        scholar = None
        if choice.scholar_id is not None:
            if choice.scholar_id in seen_targets or choice.scholar_id not in matches:
                problem("Choose each existing scholar only once, from this preview.")
            seen_targets.add(choice.scholar_id)
            captured = matches[choice.scholar_id]
            if choice.expected_revision != captured["revision"]:
                problem("The selected scholar revision differs from the preview. Pull again.", 409)
            scholar = db.scalar(
                select(Scholar).where(Scholar.id == choice.scholar_id).options(*options())
            )
            if (
                scholar is None
                or scholar.revision != captured["revision"]
                or record_digest(scholar) != preview["_baselines"][scholar.id]
            ):
                problem(
                    "A selected scholar changed after the preview. Pull again before saving.", 409
                )
            values = original_payload(scholar)
        else:
            if choice.expected_revision is not None:
                problem("A new scholar cannot use an existing record revision.")
            key = name_key(source["fields"]["name"])
            if existing_names.get(key, set()) - prior_names.get(key, set()):
                problem(
                    "A scholar with this name was added after the preview. Pull again to avoid a duplicate.",
                    409,
                )
            values = {
                "participations": [],
                "requirements": [],
                "education": [
                    {"level": "", "degree": line.strip(), "institution": ""}
                    for line in (source["education_text"] or "").splitlines()
                    if line.strip()
                ],
            }
        values.update(source["fields"])
        if (
            scholar is not None
            and source["fields"].get("tenure_years") is None
            and tenure_in_years(scholar.tenure) is not None
        ):
            # Clearing the reported number must not redisplay a numeric legacy
            # fallback; non-numeric employment notes remain untouched.
            values["tenure"] = None
        grants = {item["key"]: item for item in source["grants"]}
        new_grants = updated_grants = 0
        for selected in choice.grants:
            if selected.key in seen_grants or selected.key not in grants:
                problem("A selected grant appears twice or is not part of its source profile.")
            seen_grants.add(selected.key)
            incoming = grants[selected.key]["fields"]
            if selected.participation_id is not None:
                target = next(
                    (
                        item
                        for item in values["participations"]
                        if item.get("id") == selected.participation_id
                    ),
                    None,
                )
                if scholar is None or target is None:
                    problem("The selected grant does not belong to the chosen scholar.")
                if selected.participation_id in seen_existing_grants:
                    problem("Choose each existing annual grant only once.")
                seen_existing_grants.add(selected.participation_id)
                target.update(incoming)
                original = next(
                    item for item in scholar.participations if item.id == selected.participation_id
                )
                if program_key(incoming["program_name"]) != program_key(original.program.name):
                    target["source_program_id"] = None
                updated_grants += 1
            else:
                values["participations"].append({**incoming, "application_key": str(uuid4())})
                new_grants += 1
        try:
            validated = (ScholarUpdate if scholar is not None else ScholarCreate).model_validate(
                values
            )
        except ValidationError as caught:
            label = source["row"]
            problem(
                f"Row {label}: some reported values cannot be represented. Review the preview and source cells. {caught.errors()[0]['msg']}"
            )
        prepared.append((choice, scholar, validated, new_grants, updated_grants))
    result = {
        "scholars_created": 0,
        "scholars_updated": 0,
        "grants_created": 0,
        "grants_updated": 0,
        "scholar_ids": [],
        "replayed": False,
    }
    for choice, scholar, values, new_grants, updated_grants in prepared:
        if scholar is None:
            scholar = Scholar(id=next_scholar_id(db))
            db.add(scholar)
            result["scholars_created"] += 1
        else:
            advance_revision(db, Scholar, scholar.id, choice.expected_revision)
            result["scholars_updated"] += 1
        apply_payload(db, scholar, values)
        db.flush()
        sync_graduated_education(scholar, uppercase_new=True, today=assessment_day(db))
        result["scholar_ids"].append(scholar.id)
        result["grants_created"] += new_grants
        result["grants_updated"] += updated_grants
    db.add(
        SheetImportReceipt(
            user_id=user_id,
            request_key=payload.preview_id,
            payload_digest=digest,
            result_json=json.dumps(result),
        )
    )
    commit_record(db)
    return result
