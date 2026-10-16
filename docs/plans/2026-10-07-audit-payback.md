# Full audit and implementation plan — 2026-10-07

Scope: current 0.5.8 source (119 source/test files inventoried); API/authentication, record revision/ownership, migrations, backup/restore, CSV, reporting, frontend routing/forms/session behavior, desktop lifecycle and dependency/build configuration. Main source matches the tested staging copy. Live database opened read-only: integrity ok, 126 scholars, 126 grants, zero scholars currently recorded Payback. No full-scan assertion can guarantee the absence of all defects.

Findings and plan:
1. High: no contract-completion field or three-year payback identification. Add nullable contract_completed_on to grants with migration7; do not infer it from hidden end dates or academic terms. Preserve omitted dates in older client payloads. Add shared pure calculation with calendar-year/leap-date boundaries and same-program graduation exclusion. Show Recorded Payback, Payback review, In grace period, Contract not completed, Completion date missing and Graduated groups. Computed candidates never rewrite recorded outcomes or assert a monetary debt.
2. Medium: annual copies retain Graduated/Payback status. Clear new contract-completion date and reset copied grant outcome to On Going in both frontend and API; source remains unchanged. Program catalog copies remain separate programs.
3. Medium: recorded custom grant types/statuses are accepted and charted but absent from report filters. Return recorded values with report options and merge with standard choices, including any active selection. Preserve lightweight scholar validation.
4. Medium: dashboard normalizes historical department/year labels while reporting compares raw strings. Normalize comparisons consistently without changing saved records. Test scopes and CSV together.
5. Low: frontend canonical term helper omits numeric aliases accepted by backend. Align aliases and test existing legacy inputs.

User decisions: optional explicit contract completion date; Graduated clears computed follow-up for all annual grants referencing the same program. Three calendar years, inclusive through the grace-end date; payback review begins the next day. Feb29 anniversary clips to Feb28. Multiple distinct programs remain independent; explicit Payback records remain visible even if another record has Graduated.

Implementation surfaces: backend models/schemas/migrations, reporting and payback service/API/CSV; frontend grant form/copy/profile, dashboard widget and monitoring payback list/export. Main records and credentials are not changed by a scan. Add date only when the office supplies it.

Verification: targeted business/API/UI tests (leap dates, anniversary boundary, program graduation, independent programs, missing/future dates, deduplicated scholar counts, date persistence/copy reset, authorization, CSV safety, dynamic report filters, normalized scope); full existing backend/frontend and build checks; migration rehearsal compares every existing table/row, package inventory and desktop smoke; guarded install with protected original database snapshot and rollback archives. Office distribution unchanged.

6. High, build dependency: npm audit reported GHSA-68fv-2mgg-jv7q in source-map-js 1.2.1. Updated locked dependency to 1.2.2 within its supported range; no direct application dependency changed. OSV checked all36 pinned Python/build packages and returned no matching advisories. Recheck npm after the update.
