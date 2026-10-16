# Validation: 0.5.21

Completed local implementation, packaged verification and development installation on **16 October 2026, Asia/Manila**. Source/runtime **0.5.21**, supported schema **15**. The working database was preserved byte-for-byte during runtime installation. Its additive migration runs on the next normal launch; the actual Office-PC installation remains separate.

The [audit verification/report](analysis/AUDIT_REMEDIATION_0.5.21.md) and [implementation plan](plans/2026-10-16-audit-remediation.md) distinguish confirmed defects, counterevidence, completed fixes, accepted policy and future work across all 22 supplied findings.

## Observed checks

| Gate | Result |
| --- | --- |
| Backend regression | **494 unique cases passed across runs**: 492 cases in the final complete suite (491 passed plus one isolated temporary-parent setup retry), then two new clock-retention cases in the final 42-case safety regression. Overlapping reruns are not added. |
| Frontend regression | **220 passed** in 35 files. Full coverage and an independent thread-worker run both passed. |
| Frontend coverage | Statements80.81%, branches73.07%, functions75.44%, lines84.11%. Configured floors80/70/70/80 passed. |
| Backend coverage | Earlier full branch-coverage run89%, above87% gate. This measurement preceded the final token/retention review deltas; those final deltas passed42 focused tests. No new complete post-delta coverage percentage is claimed. |
| Static/types/build | Ruff checks and formatting, Prettier checks, source/test TypeScript and production Vite build passed. |
| Source fidelity | **232** application/test/build source files match the isolated packaged inputs. |
| Package | Clean schema15 seed, persisted record workflow, auth/backup/restore/shutdown and manifest passed. Actual bundled executable verified **148 runtime files**, with database_accessed:false. |
| Native Office-style update | Windows PowerShell5.1 updated a disposable20 installation to21 without changing database bytes during replacement. Private rehearsal and normal startup migrated14 to15 while retaining old rows, IDs, credentials, application facts and Summer. Fixture had4 scholars,7 grants and2 accounts. |
| Frozen safeguards | Verified daily backup, pre-delete recovery containing the removed synthetic scholar, input activity endpoint and CSV BOM. |
| Development installation | New21 and retained20 manifests, smoke/restore/shutdown passed. **471** first-party source/document files and actual working DB bytes were preserved through replacement. Private schema13-to15 rehearsal preserved every original column value and migration-history row. |
| Independent security review | Stale heartbeat/session-id reuse and clock-rollback pruning were found, corrected, covered by focused regressions and separately rechecked. No new actionable issue in those reviewed deltas. |

There are **714 unique automated cases** across the final backend and frontend sets. The custom build harness initially omitted the temporary directory parent for one fixture; creating that parent made the isolated case pass. A focused idle test also assumed its synthetic disk-usage path existed; its fixture now explicitly supplies its own private path. Neither failure required changing Office data. Final formatting checks were completed after the isolated remaining test-file formatting correction. Two existing backend test-client dependency deprecations remain.

See [regression evidence](analysis/REGRESSION_VALIDATION_0.5.21.json) and [frozen upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.21.json). Private development installation recovery receipts stay outside the portable delivery.

## Preserved rules and limits

Transferred and Withdrawn remain eligible for calculated payback review. Application-specific completion clearing, recorded Payback, Summer, optional dates, grouped CSV rows, uppercase record text and essential Name/Program Applied validation remain.

Only automatic unpinned copies are pruned; a just-verified copy is retained independently of the system clock. Manual and pinned copies remain. Failed pre-delete copying prevents deletion. Startup copy failure logs a private reference and does not prevent opening the app.

No GitHub21 publication, remote green CI run, actual Office-PC/E-drive update, publisher signature, backup encryption or whole-interface assistive-technology certification is claimed. Organizational signing, passphrase backup design, remote CI evidence and the other future items are listed in the audit report.

## Local Office delivery

Published and verified `Releases/Cathedra-FSDP-0.5.21-Update`:148 runtime files and23 delivery documents, with a verified empty schema15 seed. No working database, account credentials, mutable data directory or backups are included. The prior0.5.20 package is preserved. Publication evidence (local historical evidence; excluded from this source snapshot) records local delivery separately from actual Office-PC acceptance and GitHub publication.
