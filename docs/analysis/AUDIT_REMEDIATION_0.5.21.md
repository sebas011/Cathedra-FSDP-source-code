# Supplied 0.5.19 audit: verification and remediation

Reviewed against 0.5.20 and implemented in 0.5.21 on 16 October 2026, Asia/Manila. The [implementation plan](../plans/2026-10-16-audit-remediation.md) contains the individual disposition of all 22 supplied findings. This is a verification of that report and its affected paths, not a claim of exhaustive vulnerability discovery or independent Office-PC acceptance.

## Implemented changes

| Findings | Result |
| --- | --- |
| H2 | All five CSV exports deliver an Excel-friendly UTF-8 BOM. Scholar/grant row grouping and spreadsheet formula protection remain intact. |
| H3, M2 | Unexpected failures receive private references and metadata-only logs. The HTTP error boundary prevents raw server tracebacks, SQL parameters are hidden, and constraint messages distinguish linked-record conflicts from program uniqueness. The reference is visible in the ordinary UI error message. |
| H5 | Startup creates a verified daily snapshot. Retention keeps 14 unpinned daily copies and 30 unpinned pre-delete copies, excluding manual and pinned backups. Scholar deletion holds a SQLite writer reservation across verified recovery copy and deletion, rejects stale revisions before copying, and fails closed if copying fails. Pruning and protection mutations share a lock. |
| M3 | Historical education migrations use frozen SQL fields and table definitions. Tests cover future mapped columns, manual edits, suppressions, deduplication and old academic years. |
| M4, M5 | A scoped page boundary retains navigation and offers retry. Application confirmation dialogs replace native prompts while preserving pending-operation, draft and destructive-action guards. |
| M8 | Server-enforced 30-minute idle expiry is separate from the 12-hour absolute limit. Only input-driven activity renews valid sessions. An old heartbeat cannot refresh a replacement session with a reused numeric ID. Same-account recovery preserves unfinished forms. |
| M9, M10 | Setup codes no longer enter browser launch addresses and appear locally only during first setup. Restore uses the existing strict backup selector. Product, integrity, schema and recovery safeguards remain. |
| L1, L2, L6 | Contract classification runs once per grant; updater digests stream files. New tests cover private diagnostics, migration compatibility, snapshot failure, retention, idle expiry, token reuse and recovery dialogs. |
| M6, M7 | Runtime/development Python requirements are separated. Exact pinned Prettier, Ruff formatting checks, EditorConfig and frontend coverage gates are added. CI has read-only permissions, verified action revisions and explicit Windows-only test markers. |

## Policy decisions and counterevidence

- **H1:** Lightweight validation is an explicit product requirement. Name and Program Applied remain essential; optional/custom facts are not rejected merely for being unusual. Strict status enums, age rules and chronology constraints from the supplied snippets were not adopted.
- **M11:** The user explicitly retained Transferred and Withdrawn in calculated payback review. A regression checks both. Application-scoped completion clearing, recorded Payback visibility, calendar-year grace and Summer remain.
- **M4:** A router-level error fallback already existed; the new boundary adds scoped recovery.
- **H4:** Optional Authenticode support already existed. A manifest/checksum detects corruption but does not authenticate an unsigned publisher. The new download helper checks a separately obtained SHA-256 digest and explicitly reports `publisher_authenticated: false`.
- **L3:** Editor authorization already includes an explicit role check. Tested dirty-form events are retained; the reported duplication did not establish a defect.

## Remaining improvements and operational limits

| Item | Remaining work / reason |
| --- | --- |
| H4: publisher authentication | Supply an organizational code-signing certificate and verify its trust on the intended Office PC. The current build is unsigned. |
| M1: hostile same-owner process | Existing throttling and CPU limits are retained. A process running as the Windows owner can also read the database or stop the service; HTTP headers cannot isolate it. Keep approved filesystem permissions and separate OS accounts. Legitimate temporary throttling can clear by waiting or closing/reopening the service. |
| M6: expanded static analysis | Prettier, TypeScript and Ruff checks are enforced. A separate React-hooks ESLint adoption remains a maintenance improvement; this change does not claim it was installed. |
| M7: remote CI | The workflow is hardened and local gates are exercised. A green remote run requires publishing the reviewed source to the intended repository. It is not inferred from local success. |
| L1: larger-scale report queries | Compatibility collection/report queries still deserve measured pagination/query work for substantially larger datasets. Aggregate scope must be preserved during that redesign. |
| L4: passphrase backups | Raw SQLite backups contain private data and account hashes. A complete encryption/key/recovery design remains separate work; keep private off-device storage. |
| L5: inline-style policy | Existing inline-style compatibility remains for React/SVG rendering. Script restrictions remain active. Removing it requires a separate compatibility refactor. |
| Intended-device acceptance | Actual Office-PC update, keyboard/screen-reader acceptance, device encryption and off-device restore rehearsal require device-specific evidence. |

## Validation record

See [versioned validation](../VALIDATION_0.5.21.md) for the final observed test, coverage, package, migration and installation results. Focused reruns are not added to unique test totals. Separate security review found and rechecked both the stale-heartbeat token race and retention removing a newly verified copy after a clock rollback. The final retention explicitly preserves that copy, independent of timestamps, and two regressions cover future-dated older daily/pre-delete copies. Review used synthetic data and did not access Office records.
