# Cathedra FSDP 0.5.5 — feature isolation validation

## Scope and results

All FSDP workflows and shared login, accounts, reporting, backup/restore, activity, guide, verification and readiness functions remain. Faculty Workload and Expenses Projection pages, endpoints, models, state and exclusive assets/dependencies were already absent. The remaining other-product guide copy and obsolete audit-field branches were removed. No whole source files required deletion.

FSDP backups use an explicit allowed-table inventory rather than deprecated product-specific prefixes. Startup refuses unmarked nonempty databases while allowing migration/counter metadata in clean seeds. Faculty/Staff scholar classification, historical FSDP archives and conversion tools remain because they support FSDP and data preservation. No schema migration or live database pruning is introduced.

## Record-entry behavior

Only nonblank Name and Program Applied (for each entered grant) are required business fields. Optional ages, text lengths, custom terms/types/statuses, partial academic periods, date order, Other Grant descriptions, requirement names and grant-review notes no longer block saving. Duplicate-name lookup is optional for long names. Custom recorded grant types/statuses remain visible when editing. Filters/searches accept the same long text values as saved records.

Storage-compatible number/date/boolean formats, account security, positive record identifiers, ownership, revision/concurrency and explicit collection replacement contracts remain. These protect writes and restore operations; they do not enforce optional FSDP business rules.

## Verification

- 139 backend regression tests passed; two pre-existing dependency deprecation warnings.
- Nine additional targeted backend checks passed against the final query changes.
- 117 frontend tests passed across 20 files, including permissive terms, optional requirements/age, long-name saves and custom grant/status editing.
- Backend static analysis, test and production TypeScript checks, pinned dependency verification and Vite production build passed.
- Desktop executable build, clean-seed/startup/nested-route/persistence/product checks passed. Packaged version is 0.5.5; all 141 runtime files verify.
- Removed-feature negative endpoint tests remain to prevent reintroduction. Existing record ownership, rollback, revision, restore recovery and security coverage remain.
- Read-only live database inspection identified only FSDP/shared tables. Its bytes match the pre-refactor SHA-256.

Evidence: evidence-0.5.5/build.log, query-regression.log, database-check.json and sanitation-scan.json. The audited inventory is docs/plans/2026-10-05-fsdp-feature-isolation.md. Original changed files are saved outside the project in fsdp-isolation-before-20261005.zip; installer backup/archive locations will be recorded in INSTALLATION_MANIFEST_0.5.5.json.

## Installation

Installed version 0.5.5 in the main project. Runtime inventory and source hashes verify; the installed desktop smoke check passed startup, backup/restore and shutdown with Python and Node unavailable on PATH. The live database hash remains unchanged. A verified protected database backup and source/runtime rollback archives were retained. Permission verification passed for the user, SYSTEM and administrators. Installed evidence is in evidence-0.5.5/installation.log and installed-smoke.json; backup locations are recorded in INSTALLATION_MANIFEST_0.5.5.json. The existing Office distribution is outside this source-refactoring request and remains unchanged.
