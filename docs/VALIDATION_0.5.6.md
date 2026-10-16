# Cathedra FSDP 0.5.6 validation

Validated on 2026-10-05. Applied the local senior-architect and senior-backend skills; completed a read-only scope audit before refactoring.

## Delivered changes

- Multiple independent education entries, institution and graduation-year details, profile/editor sections and scholar activity history.
- Numeric tenure in years, including fractional years. Existing readable years/months converted; unclear original tenure retained as a note. No inferred hire dates.
- Administrator program catalog duplication and independent grant duplication. Grant copies may use distinct academic years; existing grant IDs and years remain unchanged. Program copies persist immediately as separate catalog entries; grant drafts persist with Save Scholar.
- Canonical 1st, 2nd and 3rd terms. Known historical aliases normalized; unclear terms preserved in remarks. Grant start/end dates remain optional compatibility fields and are removed from the editor. Missing grant dates do not create report action items; requirements retain their separate due dates.
- Legacy grant review and Needs Verification components, API routes, styles, obsolete converter and two old tables removed. Historic migration compatibility and protected rollback backups remain.
- Standalone Reports page/menu/routes removed; report views, CSV export and printing integrated into Dashboard. Analytics and reports share department/year scope. Latest ten scholars sorted by creation time, then ID descending; scoped consistently.

## Executed checks

- Backend static checks: passed.
- Backend regression: 142 passed. Coverage includes education ownership and replacements, tenure conversion, copies and stale revisions, administrator permissions, migration repeatability, canonical terms and recent-ten/report scope.
- Frontend test typecheck and regression: 113 passed in 21 files. New coverage includes multi-degree saving, fractional tenure, independent annual grants, program duplication and Dashboard reports/export scope.
- Production TypeScript and Vite build: passed.
- Desktop packaging and full isolated desktop smoke: passed, including the new features, authentication, backup/restore, session invalidation, history, graceful exit and database integrity.
- Release inventory: 137 runtime files verified for version 0.5.6.
- Browser walkthrough on synthetic records: profile education/tenure, latest ten Dashboard rows, embedded reports, canonical-term controls, and copied annual grant persistence confirmed. Preview stopped afterward.

## Current-database migration rehearsal

The source database remained untouched during rehearsal. Every retained table was compared row-by-row against expected migration changes; integrity and foreign-key checks passed. Preserved 126 scholars, 126 grants, 92 programs and one local account. Converted 120 prior degree strings into education entries. Retired fsdp_records (1 row) and fsdp_legacy_fields (470 rows) are preserved in the pre-update protected backup and excluded from the active schema, as requested. See MIGRATION_REHEARSAL_0.5.6.json and MIGRATION_HASHES_0.5.6.json for aggregate evidence.

## Installation

The guarded installer verifies the source and migrated database fingerprints, closes out concurrent access, archives prior source/runtime and creates a protected original database snapshot. It installs the verified migration copy with atomic replacement, removes only audited retired files, and restores the approved owner/SYSTEM/administrator permissions. Failure restores the original source/runtime/database. Installation and final installed checks are recorded in INSTALLATION_MANIFEST_0.5.6.json.

The separate Cathedra-FSDP-0.5.0-Office distribution is not changed by this request. Separate-PC acceptance is still an external deployment check.

!Synthetic profile with multiple education entries and distinct annual grants (local historical evidence; excluded from this source snapshot)

Final installed checks passed: installed desktop startup, persistence, backup/restore, session invalidation and graceful exit; actual office database migration 6 and retained counts verified. A final access audit confirms the approved restricted permissions. The original database backup remains in data/backups; source/runtime archives remain in Releases.
