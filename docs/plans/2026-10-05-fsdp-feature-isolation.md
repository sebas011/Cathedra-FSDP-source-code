# FSDP feature isolation — read-only audit and implementation plan

Scope: retain all FSDP workflows and common login, accounts, backups, reports, activity, verification and readiness functions. Remove Faculty Workload and Expenses Projection only.

Audit completed before source edits. No AGENTS.md files were found in the workspace ancestry or source inventory. Applied tech-debt and senior-backend skills.

## Candidate inventory

No exclusive deprecated pages, routes, hooks, API handlers, ORM models, assets or dependencies exist in this split codebase. No whole source files are scheduled for deletion. React/router and backend runtime libraries support FSDP. Inactive historical CSS has no Workload/Expenses references and is outside feature-specific deletion scope.

- frontend/src/pages/ProductGuidePage.tsx: remove other-product article copy; keep FSDP-only backup guidance.
- backend/app/activity_audit.py: remove obsolete rate-field translation and exclusions for fields absent from all FSDP models.
- backend/app/product.py: replace deprecated table-prefix list and named old-table startup branch with FSDP allowlist and generic nonempty-database protection.
- backend/app/schemas.py, backend/app/api/fsdp.py: remove age-range, text-length, term/year pairing, chronology and optional-detail business validation; retain nonblank Name/Program Applied and persistence-compatible data types.
- frontend/src/utils/grantValidation.ts, pages/FsdpFormPage.tsx, components/GrantEntry.tsx, types.ts: mirror relaxed validation; remove obsolete original-grant validation state and HTML optional-field limits.
- Affected backend/frontend tests: replace obsolete strict-input assertions with permissive round-trip/save coverage; retain concurrency, ownership, rollback and security coverage. Add backend/tests/test_feature_isolation.py for permissive round trips, required-field and FSDP-only backup/startup isolation checks.

Faculty/Staff classification is part of FSDP and remains. Historical FSDP field archives, migration/conversion utilities, negative endpoint tests and backup identity protections remain. They preserve FSDP data and block incompatible restores; they do not implement deprecated features. Live databases and existing Office release are outside source refactoring.

## Verification plan

Run backend regression/static checks, frontend regression/test type checks and production build using isolated test data. Verify permissive fields round-trip, essential names reject blanks, removed endpoints remain absent, foreign record IDs and stale revisions remain blocked, and live database bytes stay unchanged.

## Refinements from regression testing

Startup sanitation permits migration history/counter metadata in unmarked clean seeds. Restore-recovery fixtures now identify their FSDP database before adding a synthetic crash probe. Optional grant-review note lengths are relaxed in backend/app/grant_review_schemas.py and frontend/src/pages/GrantReviewPage.tsx. Existing optional-requirement/custom-term assertions are updated in test_audit_repairs.py and test_remediation_038.py; crash-recovery fixture setup is adjusted in test_restore_recovery.py. All are covered by the rollback archive.

Candidate follow-up: backend/app/api/verification.py and existing fsdp.py report/list/search Query text lengths must be relaxed to accept values that the form now permits. Pagination and positive record ID guards remain; optional name-match lookup stays bounded and is skipped for names beyond its lookup limit.
