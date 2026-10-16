# FSDP validation — 3 October 2026

## Interface redesign — 0.5.0

The current design specification is UI_UX_REDESIGN_0.5.0.md. Release-specific test and installation evidence is in VALIDATION_0.5.0.md; older entries below remain historical evidence, not assertions about the current release.

## Release safeguards — 0.3.9

- The pre-flight blocker was a Windows ACL: ordinary local users could modify the data and runtime. The installed FSDP tree is now restricted to its operating Windows account, SYSTEM and administrators, with original-permission recovery receipt retained. An independent unprivileged local account is denied reads of the database, executable and bundled VERSION. Owner write and inherited new-file permissions pass synthetic checks; a locked data directory refuses permission replacement.
- Complete release inventory covers executable, root identity, all bundled runtime/assets and the three portable verification/permission/smoke scripts. Modification, deletion and unexpected-file regression tests pass. Installer verifies the complete inventory before and after replacement; previous runtime archive also retains its manifest.
- Windows executable metadata and frontend package identity use Cathedra FSDP 0.3.9. There is no new database migration or scholar/grant business-rule change.
- npm reports no advisories for the lockfile. OSV initially flagged development-only pytest 8.4.2; its fixed 9.0.3 is pinned in a separate build environment. Rechecking all 36 Python constraints reports no advisories. Existing application/build environments remain unchanged.
- Five release-tool tests added to the existing suite. Final backend/frontend, static/type/build, packaged and built-in PowerShell acceptance results are recorded in RELEASE_VALIDATION_0.3.9.json after execution, not inferred from configuration.
- An isolated office-data migration rehearsal preserves every record (126 scholars, 126 grants, 92 programs), passes database integrity/foreign-key checks and changes no source database values. Live installation preserves the database hash.
- Subsequent external-drive check: user-created E:\Cathedra-Backups.hc mounted as V: is verified as VeraCryptVolumeV. A fresh encrypted external backup and isolated home-PC restore/migration rehearsal preserve every record and pass integrity/foreign-key checks. The user confirmed successful password-remount and backup-folder access. Only the mounted container is encrypted; home-device encryption remains unverified. No spare-PC test or trusted publisher signing is claimed. See RELEASE_READINESS_0.3.9.md for the plan, backup location and transfer checklist.

## Current audit remediation — 0.3.8

- See `AUDIT_REMEDIATION_0.3.8.md` for the phase plan and `AUDIT_REMEDIATION_RESULTS_0.3.8.md` for implemented repairs and verification boundaries.
- 96 backend and 85 frontend tests pass; Ruff, both TypeScript checks, production build and the strengthened packaged workflow checks pass.
- A current-office-data rehearsal retains every record, passes database integrity/links, and preserves all six summary/report/monitoring/review/verification/export outputs. It advances migration metadata only for this database.
- Before installation, keep a protected verified database snapshot and the previous runtime. First launch applies migration 2. A rollback to 0.3.7 needs its matching pre-upgrade database; do not downgrade over new office edits.
- Installed 0.3.8 with a protected verified snapshot and source/runtime rollback archives. Live database hash before/after is identical. The installed executable passes independent disposable workflow, data-directory identity, database-integrity and shutdown-lock checks. See `INSTALLATION_MANIFEST_0.3.8.json`.
- Older validation entries below describe their own releases, not additional assertions in today's automated checks. CI now includes packaging, but this task does not claim a GitHub run.

## Focused entry navigation — 0.3.7

- FSDP workspace tabs are hidden on add/edit scholar pages only; directory, profile, monitoring and legacy review retain them. Editor Back/sidebar/section controls, save behavior and unsaved-work guards are unchanged.
- Ten new route-level regression cases pass, including trailing-slash and query-string entry routes and preservation of Settings/Reports behavior. Frontend: 75 tests pass; backend: 83 tests pass. Ruff, both TypeScript checks and production build pass.
- No data, schema, dependency or business-rule changes. See `ENTRY_NAVIGATION_0.3.7.md` for scope. Staged and installed desktop package verification both pass.
- Installed 0.3.7 after the user confirmed FSDP closed. A protected pre-update backup and previous-runtime archive were retained; the installation manifest confirms unchanged office database hash and table counts. See `INSTALLATION_MANIFEST_0.3.7.json`.

## Installed redesign — 0.3.6

- Complete interface contract, original UX critique, page-by-page hierarchy and state annotations: `UX_UI_REDESIGN_0.3.6.md`.
- Backend: 83 tests pass; frontend: 65 tests pass. Ruff, application/test TypeScript and production asset build pass. The frontend remains route-split; main JavaScript is approximately 344 kB before gzip (110 kB gzip).
- Browser review uses eight synthetic scholars in an isolated database. Daily and administrative destinations, including accounts, open with task-specific titles. Directory search/actions, profile information, grant/requirement display, new/edit entry and the complete grant editor remain available.
- At 375px and 900px, all primary navigation destinations stay within the document width. Profile and open grant editor also reflow at 600px; dashboard and full entry check at 1440px pass. Wide tables scroll internally rather than forcing the whole document wider.
- Mobile menu opens with background inertness and closes with Escape and focus returned to its opener. The print action now has a visible icon and an accessible name at mobile widths.
- Palette contrast pairs exceed 4.5:1 for normal text; control boundary is 3.05:1. Structural accessibility tests pass. This is not a complete WCAG certification or a substitute for physical print and actual browser-zoom acceptance.
- Browser end-to-end review found the pre-existing `/fsdp/report-options` SQLAlchemy ambiguous-join error. Two regression tests reproduce it before the fix and pass after adding an explicit participation query origin. HEI filter loading and scoped report results subsequently pass in the browser without warning/error logs. The packaged check now requires filter options to load too.
- No migration, dependency additions, pay/calculation changes, Faculty changes or live-office record mutations. Protected backups were verified before stopping the stale FSDP process and before installation.
- Final 0.3.6 package build and the independent packaged-check entry point both pass, including the new report-options regression and backup/restore/exit workflows. Existing framework deprecation and optional-driver packaging warnings remain non-failing.
- Installed 0.3.6 in `Project/Cathedra-FSDP` after resolving the old background instance's data-folder lock. The first file replacement encountered a transient executable handle; rollback restored the old runtime, exclusive file checks confirmed the handles released, and the retry succeeded. The installation manifest verifies office database hashes and every table count unchanged. See `INSTALLATION_MANIFEST_0.3.6.json`.
- Browser preview tabs were closed, viewport overrides reset and the disposable preview service stopped. Screenshots in the parent audit workspace use synthetic data only.
- The installed 0.3.6 executable passes disposable startup/authentication/CRUD/report-filter/backup/restore/exit verification. After those checks, the office database still matches the pre-install hash and counts, and its data-folder lock can be acquired and released normally.

## Previous validation history

Release 0.3.4: see UI_ANALYTICS_0.3.4.md for the earlier profile/dashboard design and count contract. Its release gates covered 76 backend tests and 37 frontend tests, static/type checks, production build and packaged backup/restore/exit verification. Browser checks used synthetic records, not live office mutations.

For the preceding security/integrity repairs see AUDIT_REPAIR_RESULTS.md (0.3.3). The live database is preserved during installation, with a verified pre-update backup retained.

The 0.3.2 and earlier cleanup evidence below remains historical.
See FSDP_NAVIGATION_2026-10-01.md for calendar removal, sidebar changes and new checks.

- 45 backend tests passed, including FSDP CRUD, grants, accounts, migration/startup recovery, restore gating, schema conversion, other-domain route exclusion and backup/export checks.
- 28 frontend tests passed for 0.3.2; test TypeScript and release TypeScript/build passed.
- Ruff selected error/undefined-name checks passed. Runtime pip dependency consistency passed.
- Fresh packaged startup/setup, matching version/product/directory identity and frontend serving passed.
- Packaged workflow checks passed: setup/login, reusable programs across scholars, scholar edit/delete, requirement removal, stale-save rejection, report CSV, rejection of old mixed-schema backups, verified backup/restore with a safety backup, session revocation, SPA route serving and absent Faculty APIs.
- On isolated copies of actual office data, six endpoint outputs reconciled with 0.3.0: summary, report, monitoring, legacy grant review, report CSV and the FSDP part of verification. No office mutations were made during this check.
- Converted data preserves 126 scholars, 126 grant participations, 92 reusable programs, the account and one original archival FSDP row. 470 obsolete field values are preserved in fsdp_legacy_fields.
- Database integrity and foreign keys passed. Active database tables contain no Faculty Profile, teaching workload, salary or projection tables.
- Frontend import-closure scan found no unreferenced active source files. Package analysis contains no Faculty application modules.
- Installed in Project/Cathedra-FSDP; the previous app and verified source snapshot are retained in Project/Archives/Cathedra-FSDP-before-cleanup-20261001-221524. All 426 Faculty source/package hashes are unchanged. A protected clean-schema baseline backup is included in the FSDP data folder.

Existing framework test-client deprecation warnings and PyInstaller optional-database-driver warnings are not regressions. The app remains a SQLite local product; PostgreSQL is not claimed.

This is automated functional/source validation, not a fresh physical-printing, full visual, independent security, or clean-PC certification. Existing manual office acceptance still applies.
# Latest validation — 0.3.5

- Backend: 81 tests passed; Ruff passed. The two account-race regression tests fail against original behavior and pass after the fix.
- Frontend: 45 tests passed; application and test TypeScript checks passed; production assets built successfully.
- Packaged verification checks startup, first setup, authentication, scholar/grant/requirement persistence, stale edits, exports, backup/restore, session revocation, routes, product identity and exit using disposable data.
- The installed 0.3.5 package passed the same disposable-data verification. Office database hashes and table counts are unchanged; protected pre-service-stop and pre-update backups plus the previous runtime ZIP were retained. See `INSTALLATION_MANIFEST_0.3.5.json`.
- Browser checks: synthetic scholar creation, grant validation, hidden saved-grant editor, requirement persistence, section navigation, profile reopening, keyboard/mouse follow-up control and edit-save return. No office data is used.
- Responsive check at 600px caught and fixed a grid minimum-width overflow; document width is now 585px in a 600px viewport, with only the grants table scrolling internally.
- Final section-navigation browser recheck has no warning/error logs; scrolling does not change the URL and the unsaved-work confirmation still opens when leaving.
- Frontend source import closure has no unreferenced active files; installed Python dependencies pass consistency checks (not an advisory vulnerability scan).
- Repeat audit and revision matrix: `AUDIT_AND_ENTRY_FORM_0.3.5.md`. No new dependencies or migrations.
- Framework deprecation and PyInstaller optional-driver warnings remain; they are not newly broken tests. This is not full dependency-security, physical-printing or independent penetration-test certification.
