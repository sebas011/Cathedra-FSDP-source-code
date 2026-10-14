# Cathedra FSDP 0.5.1 — integrity remediation validation

Date: 3 October 2026 (Asia/Manila).

## Implemented fixes

1. New scholars receive IDs from a transactional, persistent counter seeded above live and historical scholar references. Committed deleted IDs are not reused by scholar creation. Explicit imports advance the counter, failed creations roll back their allocation, and restores retain the pre-restore ID floor.
2. Program edits atomically increment each affected scholar revision once in the same transaction as the program change. Concurrent saves cannot lose the increment. Failed commits roll back the revision change.
3. The database enforces unique usernames using SQLite lower(username). Account creation performs its final availability check and insert inside BEGIN IMMEDIATE and returns HTTP 409 for conflicts. Login uses matching normalization. Migration stops for offline administrator review if legacy usernames collide; accounts are never silently merged or renamed.

Schema migration 4 is additive. Existing scholar IDs, grants, requirements, accounts, passwords, sessions, and audit rows are preserved. Previously ambiguous history is not automatically reassigned. An old executable cannot open a database once migration 4 has been applied; a downgrade requires the preserved pre-upgrade database snapshot as well as the old runtime.

## Executed checks

| Check | Result |
| --- | --- |
| Pinned Python/backend/packaging inputs | Pass |
| Ruff, backend + tests + desktop launcher | Pass |
| Backend regressions | 121 passed; includes 16 new integrity cases; two existing dependency deprecation warnings |
| Frontend regressions | 94 passed in 17 files |
| Application and test TypeScript checks | Pass |
| Vite production build | Pass |
| Clean installation seed | Pass; no office/account/personnel records |
| Packaged release verification | Pass; persisted SQLite, authentication, authorization, records, exports, restore and shutdown |
| Runtime manifest | Pass; 141 files, version 0.5.1 |
| Three fixes exercised against compiled executable | Pass; synthetic data only |
| Windows PowerShell 5.1 office smoke without Python/Node on PATH | Pass |
| Migration rehearsal on protected office copy | Pass; all existing rows preserved, integrity/foreign-key checks pass, source database unchanged |

Evidence remains in the isolated build workspace: build-051.log, integrity-executable-051.log, office-smoke-051.log, and migration-051.log. The migration rehearsal is stored under update-archives/0.5.1 with restricted installation permissions.

## Installed result

Installed into C:\Users\rodia\Desktop\Project\Cathedra-FSDP. Independent installed-executable integrity checks and the Windows PowerShell 5.1 office smoke both pass on disposable synthetic data. Source hashes match the tested source. The office database SHA-256 remains identical to its pre-installation value.

Rollback archives are under update-archives/0.5.1. Verified pre-update database snapshot: data/backups/cathedra-protected-before-0.5.1-20261003-164437.db.

The final permission restoration checked 3,633 paths with zero violations, allowing only the owner, SYSTEM and Administrators. Copied runtime files initially carried additional access entries. The existing helper requested an unavailable security privilege, so it was corrected to update only the DACL through the Windows API, preserving ownership and audit metadata. Disposable fixtures pass under PowerShell 7 and Windows PowerShell 5.1. The installer now reapplies this restriction automatically and saves a permission receipt.

Installed evidence is under docs/evidence-0.5.1; installation metadata is INSTALLATION_MANIFEST_0.5.1.json. Runtime manifests were refreshed for the corrected permission helper; the tested executable and backend code did not change.

## Installation safeguards

The installer accepts only the authorized FSDP folder and the expected prior version 0.5.0. It requires the app to be closed, locks the data directory, verifies the staged release, creates source/runtime archives and a protected SQLite snapshot, and verifies the database SHA-256 is unchanged during replacement. The repaired source, frontend assets, executable, version metadata, and runtime manifest are installed together.

Installation execution and independent installed-package checks are recorded below after completion. The live office database acquires migration 4 on the next normal startup; rehearsals and smoke tests do not start the app against office data.

## Plan and review

Design and implementation plan: plans/2026-10-03-integrity-fixes-design.md.
Original review: CODE_REVIEW_2026-10-03.md.

