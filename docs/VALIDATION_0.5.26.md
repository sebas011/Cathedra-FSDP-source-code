# Release 0.5.26 validation

Prepared on 25 October 2026, Asia/Manila. This release adopts selected blueprint improvements: bounded administrator before/after history, factual contract-assessment explanations and consistent Philippine business dates. Schema 17 adds nullable activity history details; existing events gain no invented values. Record requirements, application/annual-grant structure, payback rules, credentials and reporting columns remain unchanged.

## Verification gates

- Passed: focused history, rollback, credential exclusion, schema-16 upgrade/restore, assessment and Manila-midnight tests.
- Passed: all 628 backend tests, runtime/test static and formatting checks, and 92.35% combined statement/branch coverage against the 87% gate.
- Passed: all 270 frontend tests; coverage is 82.75% statements, 75.39% branches, 78.45% functions and 86.08% lines. Formatting, production/test types and production build pass. The affected ten interaction tests passed again after the table readability adjustment.
- Passed: production browser checks with twelve fictional profiles. A saved profile edit shows actual previous/new remarks, mobile comparisons stack vertically, and profile/dashboard assessments show their reason, deadline basis and observation date. The follow-up explanation column retains a readable 256-pixel minimum inside the horizontally scrollable table. Desktop and narrow-page scroll widths equal their client widths; no page-wide horizontal overflow was observed. Browser zoom produced a 416-pixel content width at the requested mobile override, so this is not a claim of a physical-device test.
- Passed: constrained Windows build, empty schema-17 seed, 151 verified runtime files, both package inventory verifiers and PowerShell 5.1/7 packaged backup/restore, session-revocation and shutdown checks. The bundled verifier opened no database.
- Passed: packaged 0.5.25/schema-16 to 0.5.26/schema-17 update using seven fictional scholars, ten grants and two accounts. All prior business rows, IDs, migration records and history values were retained, with NULL details on old events. New edits captured exact name, cleared-remark and true-to-false changes. Runtime replacement preserved database and encrypted dummy-Google bytes; protected rehearsal, startup, CSV, pre-delete recovery and normal shutdown passed.
- Passed: guarded development installation as 0.5.26, before/after access-policy audits and unchanged working-database/encrypted-Google-connection bytes during replacement. A protected copy of the existing database passed schema-17 migration, exact pre-existing-value/history comparison and repeated-upgrade checks before replacement. The retained working database receives its protected additive migration at its next normal startup.

All listed local gates passed. Earlier 0.5.25 results remain historical evidence. This does not certify a different Office PC or a remote publication.

See [regression evidence](analysis/REGRESSION_VALIDATION_0.5.26.json) for the measured totals and tested backend source hashes.

## Delivery and limits

The published [0.5.25 Office release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.25) remains immutable. This document does not claim 0.5.26 source publication, remote CI, GitHub delivery or Office-PC acceptance. Physical printing, complete screen-reader testing and live Google transmission require their own observed checks.

See the [selected blueprint plan](plans/2026-10-25-selective-blueprint-improvements.md), [current schema](current/BACKEND_SCHEMA.md) and [current app flow](current/APP_FLOW.md).

Fictional browser evidence: history comparison (local historical evidence; excluded from this source snapshot), mobile comparison (local historical evidence; excluded from this source snapshot), grant assessment (local historical evidence; excluded from this source snapshot), and dashboard follow-up (local historical evidence; excluded from this source snapshot).

See [packaged upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.26.json) and [local package/installation evidence](analysis/LOCAL_PACKAGE_VALIDATION_0.5.26.json). Private installation receipts, snapshots, record contents and connection files remain excluded from delivery.
