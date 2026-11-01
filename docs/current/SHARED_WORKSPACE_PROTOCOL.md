# Shared workspace protocol v1 (implementation contract)

Endpoint: HTTPS `https://script.google.com/macros/s/<deployment>/exec`, POST JSON only. Requests carry `protocol: "cathedra-shared-v1"`, `device_id` UUID, `device_key` random URL-safe credential, `command`, and `args`. Never put credentials in URLs or logs. Redirect handling must not retransmit POST credentials/body to a redirect destination; only fetch the known Google ContentService response URL.

Success: `{ok:true,result:{...}}`. Failure: `{ok:false,error:{code,message,outcome}}`, where outcome is `not_committed` or `unknown`. Codes: unauthorized, invalid, conflict, busy, unavailable. A write failure establishes `not_committed` only after a healthy, locked receipt lookup confirms no prior commit for that device/request. Authentication, protection and sharing failures on a retry cannot establish the earlier outcome. Generic exceptions and any unverified successful response remain unknown; retain the exact pending request.

Snapshot:

```json
{"protocol":"cathedra-shared-v1","workspace_id":"UUID","revision":0,"initialized":false,"records":[]}
```

Record:

```json
{"key":"UUID","kind":"program|scholar|office_log","revision":1,"value":{},"origin":{"device_label":"OFFICE PC","actor":"ADMIN"},"changed_at":"ISO UTC"}
```

`value:null` is a retained tombstone. `key` and all nested child `cloud_key` values are permanent UUIDs. Snapshot records are sorted by key for deterministic serialization. Local IDs/revisions and calculated fields never appear in record values. Kind and key are immutable. Revisions increase on a committed changed record. A batch uses one next global revision; empty commits keep the revision unchanged but record the operation receipt.

Program values contain name, canonical_key (nullable for recorded ambiguity), delivering_hei and description. Scholar values contain stored profile facts and created_at/updated_at, plus ordered participations/education/requirements arrays and `suppressed_program_keys`. Internal local data_source is excluded and retained locally. Grants replace program_id with `program_key`; education replaces source_program_id with `source_program_key`. Each child has `cloud_key`, no local id/scholar_id. Preserve every grant fact, application_key, education graduation_year_manual and requirement completed_at. Grant-array order preserves period/tie ordering; application assigns a local shared_order cache, never a shared integer identity. Office Log values omit local user_id/request_key/payload_digest and contain scholar_key (nullable), scholar_name, username, occurred_on, created_at, entry_type, note, document_name, from_department and to_department.

Commands:

- `status`: no args. Returns workspace_id, revision, initialized, device_label, can_initialize, storage_url, report_url, protocol.
- `read`: no args. Returns the same metadata plus snapshot.
- `initialize`: args request_id UUID, actor, expected_revision=0, records: array of `{key,kind,value}`. Requires initializer permission, empty uninitialized workspace, and no tombstones.
- `commit`: args request_id UUID, actor, expected_revision, changes: array of `{key,kind,expected_revision,value}`. New keys require expected_revision=0; existing keys must match their captured revision. Validate the resulting graph before writing. Office logs are append-only. Returns snapshot, committed_revision and replayed. Exact request replay is device-scoped and durable; changed content under the same request_id is rejected. Check a prior receipt before current revision checks.
- `report`: args expected_revision, table (the exact sixteen-column report). Requires initialized workspace and captured revision still current. Writes only CATHEDRA REPORT in the separately configured report file, preserving other tabs. Returns rows, synced_at, spreadsheet_url, revision. Report replacement is independently retryable; storage and report are not one cross-file transaction.

Storage layout: CAT_META, CAT_RECORDS, CAT_RECEIPTS. Entire scholar JSON may span several ordered chunks; a chunk is at most 12,000 Unicode code points (below Sheets cell limits even for astral characters). Hash and chunk count validate reassembly. Store literal strings, never formulas. Use one Sheets batchUpdate to replace changed canonical storage and update metadata/append receipt atomically. Keep all tombstones/receipts, stop with a capacity error before exceeding bounded storage. Default limits: 8 MiB UTF-8 command/snapshot; 20,000 records; 100,000 chunk/receipt rows. Records require only essential business identifiers plus representable structural types and valid UUID/reference relationships; do not invent strict degree/date/age completeness rules.

Local service contract (Python): `capture(db)` returns `{key:{kind,value}}`; `validate_snapshot(snapshot)` checks the wire; `merge(base,local,remote,choices={})` returns `changes`, `merged`, `items`, `conflicts`. `apply_snapshot(db,snapshot)` maps UUIDs to retained local IDs, restores shared business facts only, advances local revisions for changes, and marks `db.info['shared_import']=True` while applying. It never commits or performs network access. Snapshot transactions/state/checkpoint are owned by the API service.

Local state row fields: id=1, workspace_id, cache_id, baseline_json, pending_json, last_completed_id, last_result_json, dirty (default false), last_synced_at. No credential material. `pending_json` contains immutable request, actor/user context, preflight local fingerprint and apply context; it survives process restart. Main state access always goes through the shared service, with a private encrypted per-PC checkpoint outside SQLite.

Local API under `/api/v1/shared-workspace`:

- GET status (signed-in users): configured, connected, initialized, joined, state (disconnected/ready/dirty/pending/rejoin_required), device_id, device_label, device_key_hash, endpoint, workspace_id, revision, last_synced_at, storage_url, report_url, can_initialize, message. Secret never returned; non-admin responses omit registration hash, endpoint and spreadsheet URLs.
- POST configure (admin): endpoint. Generates private device credential if absent; returns status and registration hash only. This saves configuration locally, no records uploaded.
- POST check (admin): authenticate status, bind expected workspace only after reviewed join/initialization.
- DELETE connection (admin): refuses unresolved pending operation; disconnects local device only, does not delete cloud data.
- POST preview (admin): mode join/initialize/sync. Returns preview_id, mode, expires_at, items `{key,kind,label,direction,conflict,local_summary,shared_summary}`, conflicts keys, counts `{local,shared,upload,download,conflicts}`, warnings. Initializing and joining require confirmation in apply; initialization remains owner-device gated.
- POST apply (admin): preview_id, choices map UUID to local/shared, confirm true. Returns state, revision, uploaded, downloaded, conflicts=0, replayed, message. Reject stale local snapshot before any outbound write.
- POST retry (admin): no supplied source; retries the exact persisted pending request and returns apply result.
- POST report (admin): canonical shared report; same visible result fields as existing reporting plus revision.

Frontend: shared panel is shown above legacy Google panel. While configured, hide legacy reporting controls and use shared report action. Preview shows conflicts and direction summaries; no raw JSON in office UI. Header status displays pending/last shared state. All pending actions block navigation/duplicate submissions and expose exact retry on uncertain result.
