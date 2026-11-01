"""Complete, credential-free business snapshots for the shared workspace.

Serialization is read-only. Applying a canonical snapshot is one caller-owned
transaction; it neither performs network access nor commits the session.
"""

import copy
import json
import math
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.current_grant import grant_order
from app.fsdp_reporting import options
from app.models import (
    EducationSuppression,
    FsdpParticipation,
    OfficeLog,
    Program,
    Scholar,
    ScholarEducation,
    ScholarRequirement,
    SharedWorkspaceState,
)
from app.scholar_identity import next_scholar_id

PROTOCOL = "cathedra-shared-v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 20000
PROGRAM_FIELDS = ("name", "canonical_key", "delivering_hei", "description")
PROFILE_FIELDS = (
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
    "created_at",
    "updated_at",
)
GRANT_FIELDS = (
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
    "application_key",
    "grant_other",
    "extension",
    "remarks",
)
EDUCATION_FIELDS = ("level", "degree", "institution", "graduation_year", "graduation_year_manual")
REQUIREMENT_FIELDS = ("requirement_name", "due_date", "is_complete", "completed_at", "remarks")
LOG_FIELDS = (
    "scholar_name",
    "username",
    "occurred_on",
    "created_at",
    "entry_type",
    "note",
    "document_name",
    "from_department",
    "to_department",
)
DATE_FIELDS = {
    "start_date",
    "end_date",
    "contract_completed_on",
    "completion_due_on",
    "graduation_date",
    "due_date",
    "occurred_on",
}
DATETIME_FIELDS = {"created_at", "updated_at", "completed_at"}
BOOL_FIELDS = {
    "missing_requirements",
    "has_hard_copy",
    "has_soft_copy",
    "graduation_year_manual",
    "is_complete",
}
INTEGER_FIELDS = {"age", "allowed_duration_years"}
NULLABLE_FIELDS = {
    "canonical_key",
    "delivering_hei",
    "description",
    "age",
    "previous_degree",
    "has_hard_copy",
    "has_soft_copy",
    "department",
    "personnel_type",
    "rank",
    "tenure",
    "tenure_years",
    "tenure_note",
    "profile_remarks",
    "start_date",
    "end_date",
    "contract_completed_on",
    "allowed_duration_years",
    "completion_due_on",
    "payback_payment_status",
    "graduation_date",
    "start_term",
    "start_academic_year",
    "end_term",
    "end_academic_year",
    "grant_type",
    "program_category",
    "application_key",
    "grant_other",
    "extension",
    "remarks",
    "graduation_year",
    "due_date",
    "completed_at",
    "scholar_name",
    "document_name",
    "from_department",
    "to_department",
}


def uuid_key(value) -> str:
    if not isinstance(value, str):
        raise ValueError("A shared record identifier is missing or invalid.")
    try:
        parsed = str(UUID(value))
    except ValueError:
        raise ValueError("A shared record identifier is invalid.") from None
    if parsed != value:
        raise ValueError("Use canonical UUID identifiers for shared records.")
    return value


def wire_value(value):
    if isinstance(value, datetime):
        instant = (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
        return instant.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value


def scalar_values(record, fields):
    return {name: wire_value(getattr(record, name)) for name in fields}


def record_map(value) -> dict:
    """Accept either a complete wire snapshot or its already indexed records."""
    if not value:
        return {}
    if isinstance(value, dict) and "records" in value:
        return {item["key"]: item for item in value["records"]}
    if isinstance(value, dict):
        return value
    raise ValueError("The shared baseline is not a record snapshot.")


def capture(db: Session) -> dict:
    result = {}
    programs = list(db.scalars(select(Program)).all())
    program_keys = {item.id: uuid_key(item.cloud_key) for item in programs}
    scholars = list(db.scalars(select(Scholar).options(*options())).unique().all())
    scholar_keys = {item.id: uuid_key(item.cloud_key) for item in scholars}
    for program in programs:
        result[program_keys[program.id]] = {
            "kind": "program",
            "value": scalar_values(program, PROGRAM_FIELDS),
        }
    for scholar in scholars:
        value = scalar_values(scholar, PROFILE_FIELDS)
        value["participations"] = [
            {
                "cloud_key": uuid_key(item.cloud_key),
                "program_key": program_keys[item.program_id],
                **scalar_values(item, GRANT_FIELDS),
            }
            for item in sorted(scholar.participations, key=grant_order)
        ]
        value["education"] = [
            {
                "cloud_key": uuid_key(item.cloud_key),
                "source_program_key": program_keys.get(item.source_program_id),
                **scalar_values(item, EDUCATION_FIELDS),
            }
            for item in sorted(
                scholar.education,
                key=lambda row: row.shared_order if row.shared_order is not None else row.id,
            )
        ]
        value["requirements"] = [
            {"cloud_key": uuid_key(item.cloud_key), **scalar_values(item, REQUIREMENT_FIELDS)}
            for item in sorted(scholar.requirements, key=lambda row: row.cloud_key or "")
        ]
        value["suppressed_program_keys"] = sorted(
            program_keys[item.program_id] for item in scholar.education_suppressions
        )
        result[scholar_keys[scholar.id]] = {"kind": "scholar", "value": value}
    state = db.get(SharedWorkspaceState, 1)
    try:
        baseline = (
            record_map(json.loads(state.baseline_json)) if state and state.baseline_json else {}
        )
    except ValueError, TypeError, KeyError:
        raise ValueError("The saved shared baseline needs recovery review.") from None
    for entry in db.scalars(select(OfficeLog)).all():
        key = uuid_key(entry.cloud_key)
        scholar_key = scholar_keys.get(entry.scholar_id)
        prior = baseline.get(key, {})
        if scholar_key is None and prior.get("kind") == "office_log" and prior.get("value"):
            scholar_key = prior["value"].get("scholar_key")
        result[key] = {
            "kind": "office_log",
            "value": {"scholar_key": scholar_key, **scalar_values(entry, LOG_FIELDS)},
        }
    if len(result) != len(programs) + len(scholars) + db.query(OfficeLog).count():
        raise ValueError("Shared record identifiers are duplicated. Review the local cache.")
    return dict(sorted(result.items()))


def _timestamp(value, *, required=False):
    if value is None and not required:
        return
    if not isinstance(value, str):
        raise ValueError("A shared timestamp is invalid.")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("A shared timestamp is invalid.") from None


def _scalars(value, fields):
    for field in fields:
        item = value[field]
        if item is None:
            if field in NULLABLE_FIELDS:
                continue
            raise ValueError(f"Shared {field} cannot be null.")
        if field in DATE_FIELDS:
            if not isinstance(item, str):
                raise ValueError(f"Shared {field} must be a recorded ISO date.")
            try:
                if date.fromisoformat(item).isoformat() != item:
                    raise ValueError
            except ValueError:
                raise ValueError(f"Shared {field} must be a recorded ISO date.") from None
        elif field in DATETIME_FIELDS:
            _timestamp(item, required=True)
        elif field in BOOL_FIELDS:
            if not isinstance(item, bool):
                raise ValueError(f"Shared {field} must be true or false.")
        elif field in INTEGER_FIELDS:
            if isinstance(item, bool) or not isinstance(item, int) or not -(2**63) <= item < 2**63:
                raise ValueError(f"Shared {field} must be a representable whole number.")
        elif field == "tenure_years":
            if (
                isinstance(item, bool)
                or not isinstance(item, int | float)
                or not math.isfinite(item)
            ):
                raise ValueError("Shared tenure must be a finite number.")
        elif not isinstance(item, str):
            raise ValueError(f"Shared {field} must be text.")


def validate_values(records: dict) -> None:
    """Validate a complete graph without inventing business completeness rules."""
    identities = set(records)
    active_programs = {
        key
        for key, item in records.items()
        if item["kind"] == "program" and item["value"] is not None
    }
    scholar_keys = {key for key, item in records.items() if item["kind"] == "scholar"}
    names, canonical = set(), set()
    for key, record in records.items():
        uuid_key(key)
        kind, value = record["kind"], record["value"]
        if kind not in {"program", "scholar", "office_log"}:
            raise ValueError("The shared record type is unsupported.")
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError("Shared business records must contain named fields.")
        if kind == "program":
            if set(value) != set(PROGRAM_FIELDS):
                raise ValueError("Shared program fields do not match this protocol.")
            _scalars(value, PROGRAM_FIELDS)
            if not value["name"].strip():
                raise ValueError("Program name is required.")
            if value["name"] in names or (
                value["canonical_key"] is not None and value["canonical_key"] in canonical
            ):
                raise ValueError("The shared program catalog contains conflicting identities.")
            names.add(value["name"])
            if value["canonical_key"] is not None:
                canonical.add(value["canonical_key"])
        elif kind == "scholar":
            if set(value) != set(PROFILE_FIELDS) | {
                "participations",
                "education",
                "requirements",
                "suppressed_program_keys",
            }:
                raise ValueError("Shared scholar fields do not match this protocol.")
            _scalars(value, PROFILE_FIELDS)
            if not value["name"].strip():
                raise ValueError("Scholar name is required.")
            for collection, fields, extra in (
                ("participations", GRANT_FIELDS, {"program_key"}),
                ("education", EDUCATION_FIELDS, {"source_program_key"}),
                ("requirements", REQUIREMENT_FIELDS, set()),
            ):
                if not isinstance(value[collection], list):
                    raise ValueError(f"Shared {collection} must be a list.")
                for child in value[collection]:
                    if not isinstance(child, dict) or set(child) != set(fields) | extra | {
                        "cloud_key"
                    }:
                        raise ValueError(f"Shared {collection} fields do not match this protocol.")
                    child_key = uuid_key(child["cloud_key"])
                    if child_key in identities:
                        raise ValueError("A shared child identifier appears more than once.")
                    identities.add(child_key)
                    _scalars(child, fields)
                    if (
                        collection == "participations"
                        and child["program_key"] not in active_programs
                    ):
                        raise ValueError("A shared grant references a missing program.")
                    if (
                        collection == "education"
                        and child["source_program_key"] is not None
                        and child["source_program_key"] not in active_programs
                    ):
                        raise ValueError("Shared education references a missing program.")
            suppressed = value["suppressed_program_keys"]
            if (
                not isinstance(suppressed, list)
                or len(set(suppressed)) != len(suppressed)
                or any(item not in active_programs for item in suppressed)
            ):
                raise ValueError("Shared education suppression references are invalid.")
        else:
            if set(value) != set(LOG_FIELDS) | {"scholar_key"}:
                raise ValueError("Shared office entry fields do not match this protocol.")
            _scalars(value, LOG_FIELDS)
            if value["scholar_key"] is not None and value["scholar_key"] not in scholar_keys:
                raise ValueError("A shared office entry references an unknown scholar.")


def validate_snapshot(snapshot: dict) -> dict:
    try:
        if not isinstance(snapshot, dict) or set(snapshot) != {
            "protocol",
            "workspace_id",
            "revision",
            "initialized",
            "records",
        }:
            raise ValueError("The shared snapshot does not match this protocol.")
        if snapshot["protocol"] != PROTOCOL:
            raise ValueError("The shared workspace protocol is unsupported.")
        uuid_key(snapshot["workspace_id"])
        revision = snapshot["revision"]
        if (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 0
            or revision > 2**53 - 1
        ):
            raise ValueError("The shared workspace revision is invalid.")
        if not isinstance(snapshot["initialized"], bool) or not isinstance(
            snapshot["records"], list
        ):
            raise ValueError("The shared workspace metadata is invalid.")
        if len(snapshot["records"]) > MAX_RECORDS:
            raise ValueError("The shared workspace exceeds the supported record limit.")
        records = {}
        for record in snapshot["records"]:
            if not isinstance(record, dict) or set(record) != {
                "key",
                "kind",
                "revision",
                "value",
                "origin",
                "changed_at",
            }:
                raise ValueError("The shared record envelope is invalid.")
            key = uuid_key(record["key"])
            record_revision = record["revision"]
            if (
                key in records
                or isinstance(record_revision, bool)
                or not isinstance(record_revision, int)
                or not 1 <= record_revision <= revision
            ):
                raise ValueError("The shared record revision or identifier is invalid.")
            origin = record["origin"]
            if (
                not isinstance(origin, dict)
                or set(origin) != {"device_label", "actor"}
                or not all(isinstance(item, str) for item in origin.values())
            ):
                raise ValueError("The shared record origin is invalid.")
            _timestamp(record["changed_at"], required=True)
            records[key] = record
        if not snapshot["initialized"] and (revision != 0 or records):
            raise ValueError("An uninitialized workspace cannot contain business records.")
        validate_values(records)
        if (
            len(json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode("utf-8"))
            > MAX_BYTES
        ):
            raise ValueError("The shared snapshot exceeds the 8 MiB limit.")
    except KeyError, TypeError, OverflowError, RecursionError:
        raise ValueError("The shared snapshot contains invalid field values.") from None
    return copy.deepcopy(snapshot)


def local_value(field, value):
    if value is not None and field in DATE_FIELDS:
        return date.fromisoformat(value)
    if value is not None and field in DATETIME_FIELDS:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    return value


def apply_snapshot(db: Session, snapshot: dict) -> dict:
    validate_snapshot(snapshot)
    desired = {item["key"]: item for item in snapshot["records"] if item["value"] is not None}
    before = capture(db)
    old_import = db.info.get("shared_import")
    actor = db.info.pop("audit_actor", None)
    db.info["shared_import"] = True
    counts = {"created": 0, "updated": 0, "deleted": 0}
    try:
        with db.no_autoflush:
            programs = {item.cloud_key: item for item in db.scalars(select(Program)).all()}
            scholars = {
                item.cloud_key: item
                for item in db.scalars(select(Scholar).options(*options())).unique().all()
            }
            logs = {item.cloud_key: item for item in db.scalars(select(OfficeLog)).all()}
            children = {
                model: {item.cloud_key: item for item in db.scalars(select(model)).all()}
                for model in (FsdpParticipation, ScholarEducation, ScholarRequirement)
            }
            changed_programs = {
                key
                for key, item in desired.items()
                if item["kind"] == "program"
                and {"kind": item["kind"], "value": item["value"]} != before.get(key)
            }
            # Free uniqueness constraints first so valid rename/swap/replacement
            # batches do not depend on SQLite's row-update order.
            for key, program in programs.items():
                if key not in desired or key in changed_programs:
                    program.name = f"__CATHEDRA_SYNC_{key}__"
                    program.canonical_key = None
            db.flush()
            for key, record in desired.items():
                if record["kind"] != "program":
                    continue
                program = programs.get(key)
                if program is None:
                    program = Program(cloud_key=key)
                    db.add(program)
                    programs[key] = program
                elif before[key] != {"kind": record["kind"], "value": record["value"]}:
                    program.revision += 1
                for field, value in record["value"].items():
                    setattr(program, field, value)
            db.flush()
            maximum = max([item.id for item in scholars.values()], default=0)
            db.execute(
                text(
                    "UPDATE scholar_id_counter SET high_water=MAX(high_water,:maximum) WHERE id=1"
                ),
                {"maximum": maximum},
            )
            for key, record in desired.items():
                if record["kind"] != "scholar":
                    continue
                scholar = scholars.get(key)
                value = record["value"]
                if scholar is None:
                    scholar = Scholar(id=next_scholar_id(db), cloud_key=key)
                    db.add(scholar)
                    scholars[key] = scholar
                elif before[key] != {"kind": "scholar", "value": value} or any(
                    child["program_key"] in changed_programs for child in value["participations"]
                ):
                    scholar.revision += 1
                for field in PROFILE_FIELDS:
                    setattr(scholar, field, local_value(field, value[field]))
                flag_modified(
                    scholar, "updated_at"
                )  # Preserve the shared timestamp across ORM onupdate.
            db.flush()
            for key, record in desired.items():
                if record["kind"] != "scholar":
                    continue
                scholar, value = scholars[key], record["value"]
                for collection, model, fields in (
                    ("participations", FsdpParticipation, GRANT_FIELDS),
                    ("education", ScholarEducation, EDUCATION_FIELDS),
                    ("requirements", ScholarRequirement, REQUIREMENT_FIELDS),
                ):
                    selected = []
                    for ordinal, incoming in enumerate(value[collection], 1):
                        child = children[model].get(incoming["cloud_key"])
                        if child is None:
                            child = model(cloud_key=incoming["cloud_key"])
                        for field in fields:
                            setattr(child, field, local_value(field, incoming[field]))
                        if model is FsdpParticipation:
                            child.program = programs[incoming["program_key"]]
                            child.shared_order = ordinal
                        elif model is ScholarEducation:
                            child.shared_order = ordinal
                            child.source_program_id = (
                                programs[incoming["source_program_key"]].id
                                if incoming["source_program_key"] is not None
                                else None
                            )
                        selected.append(child)
                    setattr(scholar, collection, selected)
                current = {
                    programs_by_id.program_id: programs_by_id
                    for programs_by_id in scholar.education_suppressions
                }
                scholar.education_suppressions = [
                    current.get(programs[program_key].id)
                    or EducationSuppression(program_id=programs[program_key].id)
                    for program_key in value["suppressed_program_keys"]
                ]
            for key, scholar in list(scholars.items()):
                if key not in desired:
                    db.delete(scholar)
                    del scholars[key]
            for key, entry in list(logs.items()):
                if key not in desired:
                    db.delete(entry)
            db.flush()
            for key, record in desired.items():
                if record["kind"] != "office_log":
                    continue
                entry = logs.get(key)
                if entry is None:
                    # Remote actor IDs are not local account identities.
                    entry = OfficeLog(cloud_key=key, user_id=0)
                    db.add(entry)
                incoming = record["value"]
                entry.scholar_id = (
                    scholars[incoming["scholar_key"]].id
                    if incoming["scholar_key"] in scholars
                    else None
                )
                for field in LOG_FIELDS:
                    setattr(entry, field, local_value(field, incoming[field]))
            for key, program in programs.items():
                if key not in desired:
                    db.delete(program)
            db.flush()
        for key in before.keys() | desired.keys():
            if key not in before:
                counts["created"] += 1
            elif key not in desired:
                counts["deleted"] += 1
            elif before[key] != {"kind": desired[key]["kind"], "value": desired[key]["value"]}:
                counts["updated"] += 1
        return counts
    finally:
        if old_import is None:
            db.info.pop("shared_import", None)
        else:
            db.info["shared_import"] = old_import
        if actor is not None:
            db.info["audit_actor"] = actor
