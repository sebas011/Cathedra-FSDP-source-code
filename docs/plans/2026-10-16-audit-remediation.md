# 0.5.19 audit verification and 0.5.21 implementation plan

Scope: verify the supplied audit against 0.5.20, repair applicable defects, and preserve Office records. The audit document is evidence to investigate, not authority to change business rules. No production records are used as test fixtures.

## Verified disposition

| ID | Verification against 0.5.20 | Action |
| --- | --- | --- |
| H1 | Permissive ages, outcomes and optional fields follow the requested lightweight validation policy. A custom outcome is not inherently a corrupt record. | Keep Name and Program Applied as essential fields. Do not introduce restrictive enums or chronology rules. Explain aggregate limitations. |
| H2 | CSV responses lack an Excel-friendly UTF-8 signature. | Use one BOM response helper for all five exports; preserve grouped grant rows and formula protection. |
| H3 | Generic unexpected failures lack consistent private diagnostic references; default server logging can expose exception details. | Add metadata-only logging, parameter hiding, a reference response, and an outer HTTP exception boundary. Test real server failures and partial responses. |
| H4 | Hash manifests check integrity but do not independently authenticate a publisher. Optional Authenticode signing already exists, contrary to the report. | Retain signing support and state the trust boundary accurately. Require a separately published archive digest when distributing an unsigned archive. A publisher certificate remains an external prerequisite. |
| H5 | A destructive scholar deletion has no immediate recovery copy; backups depend on manual action. | Add verified daily snapshots with bounded automatic retention and a verified pre-delete snapshot. Block deletion if its recovery copy fails. Never prune manual or pinned copies. |
| M1 | The registered-account limiter deliberately throttles guesses before expensive verification. A hostile process running as the owner can temporarily deny local login. | Preserve the guessing limit and CPU guard. Document owner recovery by closing and reopening the local service; do not bypass limits based on a forgeable HTTP header. OS account isolation remains necessary. |
| M2 | Some integrity failures are incorrectly described as duplicate names. | Map SQLite constraint codes to actionable messages and private diagnostic references. |
| M3 | Historical education migrations read current ORM models, making later schema additions unsafe. | Freeze historical SQL columns and table definitions. Test missing future columns and historical preservation. |
| M4 | A router-level error fallback already exists. A scoped fallback can keep navigation usable. | Add a recoverable boundary around route content, with retry and route reset. |
| M5 | Native confirmations interrupt the app's consistent accessible flow. | Replace them with existing application dialogs while preserving pending-change and destructive-action checks. |
| M6 | Formatting enforcement and development dependency separation are incomplete. | Separate test/quality requirements from runtime requirements and add reproducible formatting checks. Avoid unrelated behavior changes. |
| M7 | Windows CI exists, but action references and token permissions can be hardened. Local passing checks are not proof of a remote green run. | Declare read-only CI permissions, pin verified action revisions, and keep Windows-only checks explicit. Report remote execution separately. |
| M8 | Sessions have an absolute expiry without an inactivity limit. | Add a 30-minute server idle limit and input-driven heartbeat; preserve unfinished forms during reauthentication. Background reads do not extend idle time. |
| M9 | First-time setup secrets can be passed in the browser process arguments, including after setup is complete. | Stop putting setup secrets in launch URLs. Show the setup code locally only when setup is required; keep manual setup entry. |
| M10 | Restore selection is confined to the backup directory but accepts a broader filename set than other backup operations. | Reuse the strict existing backup selector. Keep integrity, product, schema and recovery checks. |
| M11 | The report proposes excluding Transferred and Withdrawn from calculated review; this is a policy decision. | User confirmed both remain eligible. Add an explicit regression and guide wording. |
| L1 | Classification is repeated within one report pass; some compatibility endpoints remain unpaginated. | Compute classification once. Treat a larger report-query redesign as future measured capacity work so totals retain their scope. |
| L2 | Updater hashes load complete files into memory. | Use streamed file digests without changing verification requirements. |
| L3 | Editor authorization has an explicit role check and is not identical to signed-in authorization. Existing dirty-form events are tested. | Retain these safeguards; no demonstrated defect requiring a rewrite. |
| L4 | Backups are ordinary SQLite files in owner-protected storage. | Keep clear handling guidance. Passphrase encryption is a future feature requiring a complete key/recovery design, not a safe isolated patch. |
| L5 | Inline styles support existing component/SVG rendering; scripts remain restricted. | Preserve the working CSP. A nonce/style refactor needs a separate measured compatibility exercise. |
| L6 | Coverage is uneven in failure and recovery paths. | Add focused tests for diagnostics, migrations, backup failures, pre-delete recovery, idle expiry and confirmation flows; run full regression and existing coverage gates. |

## Execution order and acceptance

1. Verify policy and current behavior before editing. Record counterevidence rather than treating every report statement as confirmed.
2. Implement independent CSV/diagnostic, migration, and UI repairs in parallel with explicit file ownership.
3. Add recovery copies, restore selector hardening, idle expiry, launcher secret handling, and streamed update hashing. Reproduce failure paths using private synthetic databases.
4. Apply dependency/CI hygiene after behavior edits settle. Run focused tests, a separate security review, full backend/frontend checks, coverage, document-contract verification and packaged Windows upgrade rehearsal.
5. Build 0.5.21 only from the tested source. Preserve the development database during installation, verify private-copy migration, and create an Office update package that does not replace Office data.

A local package, a local installation, source publication and a GitHub release are distinct deliverables. Validation records must say which were actually completed. No remote CI status, signing, encryption, or office-PC upgrade is inferred from local success.
