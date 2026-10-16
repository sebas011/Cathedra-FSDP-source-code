# Cathedra FSDP 0.5.9 — audit and validation

Reviewed 2026-10-07. The audit plan was recorded before changes in `plans/2026-10-07-audit-payback.md`. Scope covered authentication, request/restore handling, record ownership and concurrency, database migrations, backups, CSV exports, reporting, frontend routes/forms/session handling, desktop startup and build dependencies. 119 source/test files were inventoried before implementation. This combines focused manual inspection with regression and build checks; it is not a guarantee that all possible defects have been eliminated.

## Resolved findings

| Priority | Finding | Delivered change |
| --- | --- | --- |
| High | Contract completion and grace-period follow-up absent | Optional completion date; shared three-calendar-year calculation; dashboard totals, monitoring categories, profile details and scoped CSV |
| High | Build dependency source-map-js 1.2.1 advisory GHSA-68fv-2mgg-jv7q | Locked patched version 1.2.2; post-update npm audit reports zero advisories |
| Medium | Annual copies retained old outcomes | New copies begin On Going with no completion date; source grant unchanged |
| Medium | Custom recorded categories missing from report filters | Recorded values included in selectable filters and report totals |
| Medium | Historical whitespace produced inconsistent dashboard/report scopes | Matching and labels normalized without rewriting stored data |
| Low | Numeric legacy terms handled differently in frontend/backend | Frontend recognizes 1, 2 and 3 as 1st, 2nd and 3rd |

## Payback behavior

Enter the actual contract completion date through Edit profile → Edit grant → Contract completion date (optional) → Update Grant → Save Scholar. Unknown dates remain blank. Grace lasts through the third anniversary; review starts the following day. A February 29 anniversary clips to February 28. A Graduated record clears computed follow-up for all annual grants referencing the same program catalog entry, across years. Different programs remain independent. Explicit Recorded Payback remains visible. Calculations do not overwrite recorded statuses. Duplicating a program creates a separate catalog entry.

Dashboard → Review scholars opens the contract/payback section of Monitoring & follow-up. Recorded Payback and Payback review appear together by default. Missing completion dates have their own category. Department/year scope and selected category carry into CSV exports. Scholar counts are distinct within each category; the table lists individual grants.

## Results

- Backend: 162 tests passed, including migration replay, authentication/CSV safety, calendar boundaries, program graduation, date preservation and annual copies.
- Frontend: 125 tests passed across 22 files; TypeScript and production frontend build passed.
- Python lint, pinned build-input validation, packaged persisted-database checks and desktop release verification passed.
- Runtime package inventory: all 138 files verified, release 0.5.9.
- Npm: zero reported advisories after patch. OSV queried all 36 pinned Python/runtime/build packages; no matching advisories returned at scan time.
- Private database migration rehearsal compared original columns/rows in every existing table (12 tables). All existing rows preserved; integrity ok, no foreign-key violations, no inferred completion dates. See `MIGRATION_REHEARSAL_0.5.9.json`.
- Existing data: 126 scholars, 126 grants; 96 graduated scholars; 30 non-graduated scholars need completion dates; zero explicitly recorded Payback. No reliable overdue classification is possible for those 30 until dates are supplied.
- Isolated browser check: dashboard totals/list navigation, category selection, grant edit/save and profile calculation passed. A synthetic completion date 2025-06-30 produced grace end 2028-06-30 and In grace period; recorded On Going remained unchanged. No browser console errors observed. Browser automation's direct date fill required normal keyboard input to trigger React's date change; keyboard input persisted correctly. Screenshots contain synthetic records only.

Installation uses a protected database snapshot and source/runtime rollback archives. The installed database stays unchanged during file replacement; migration 7 adds the nullable column on the next app startup. The separate Office distribution is outside this installation scope.
