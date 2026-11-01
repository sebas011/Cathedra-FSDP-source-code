"""Three-way reconciliation by stable business identity, never by display name."""

import copy

from app.shared_records import record_map, validate_values


def fact(record):
    return (
        None
        if not record or record.get("value") is None
        else {"kind": record["kind"], "value": record["value"]}
    )


def summary(record, catalog):
    if not record or record.get("value") is None:
        return ["Deleted or absent"]
    value = record["value"]
    if record["kind"] == "scholar":
        lines = [
            value["name"],
            "Department: " + (value.get("department") or "—"),
            "Profile remarks: " + (value.get("profile_remarks") or "—"),
        ]
        for field, label in (
            ("participations", "grants"),
            ("education", "education entries"),
            ("requirements", "requirements"),
        ):
            lines.append(f"{len(value[field])} {label}")
        # Show all stored facts in human-readable form so conflict choices are informed.
        for field, item in value.items():
            if field in {"name", "department", "profile_remarks", "suppressed_program_keys"}:
                continue
            if isinstance(item, list):
                for number, child in enumerate(item, 1):
                    program_key = child.get("program_key") or child.get("source_program_key")
                    program = catalog.get(program_key, {}).get("value") or {}
                    lines.append(
                        f"{field.title()} {number}: "
                        + ((program.get("name", "") + "; ") if program else "")
                        + "; ".join(
                            f"{key.replace('_', ' ')}: {val}"
                            for key, val in child.items()
                            if key
                            not in {
                                "cloud_key",
                                "program_key",
                                "source_program_key",
                                "application_key",
                                "graduation_year_manual",
                            }
                            and val is not None
                        )
                    )
            elif item is not None:
                lines.append(f"{field.replace('_', ' ').title()}: {item}")
        return lines
    return [
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in value.items()
        if key not in {"canonical_key", "scholar_key"} and value is not None
    ]


def merge(base, local, remote, choices=None):
    choices = choices or {}
    original, shared = record_map(base), record_map(remote)
    merged = copy.deepcopy(shared)
    changes, items, conflicts, selectable = [], [], [], set()
    for key in sorted(original.keys() | local.keys() | shared.keys()):
        prior, here, there = fact(original.get(key)), fact(local.get(key)), fact(shared.get(key))
        local_changed, remote_changed = here != prior, there != prior
        if not local_changed and not remote_changed:
            continue
        conflict = local_changed and remote_changed and here != there
        if conflict:
            selectable.add(key)
            if key not in choices:
                conflicts.append(key)
        chosen = here if local_changed and (not conflict or choices.get(key) == "local") else there
        record = here or there or fact(original.get(key))
        if record is None:
            continue
        direction = (
            "conflict"
            if conflict and key not in choices
            else "upload"
            if chosen != there
            else "download"
        )
        if here == there:
            direction = "unchanged"
        items.append(
            {
                "key": key,
                "kind": record["kind"],
                "label": record["value"].get("name")
                or record["value"].get("note", "Office log entry")[:100],
                "direction": direction,
                "conflict": conflict,
                "local_summary": summary(here, local),
                "shared_summary": summary(there, shared),
            }
        )
        if chosen != there:
            # Tombstones cannot be resurrected, nor immutable logs changed.
            existing = shared.get(key)
            if (existing and existing["value"] is None and chosen is not None) or (
                existing and existing["kind"] == "office_log"
            ):
                raise ValueError(
                    "A deleted identity or existing Office Log cannot be overwritten. Keep the shared version."
                )
            changes.append(
                {
                    "key": key,
                    "kind": record["kind"],
                    "expected_revision": existing["revision"] if existing else 0,
                    "value": chosen["value"] if chosen else None,
                }
            )
        merged[key] = {"kind": record["kind"], "value": chosen["value"] if chosen else None}
    if set(choices) - selectable or any(
        choice not in {"local", "shared"} for choice in choices.values()
    ):
        raise ValueError("Conflict choices must match this preview.")
    if not conflicts:
        validate_values(merged)
    return {"changes": changes, "merged": merged, "items": items, "conflicts": conflicts}
