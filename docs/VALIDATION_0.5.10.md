# Cathedra FSDP 0.5.10 validation

Date: 2026-10-07 (Asia/Manila)

Implementation follows all 15 items in Findings-for-FSDP.md. See plans/2026-10-07-user-findings.md for the audit, affected files, and implementation decisions.

## Delivered behavior

- Removed the standalone monitoring page, its navigation, API handler, service types, exclusive styling, and shell/profile context breadcrumbs. Core scholar requirement records remain available in profiles and dashboard reporting. Contract/payback assessment is available on the Dashboard and in individual profiles.
- Personnel type is explicitly Faculty, Staff, or Not recorded; a missing rank never implies Staff. Existing records remain Not recorded until an administrator selects the correct type. Rank is labeled Rank / position.
- Education uses an Add/Edit/Save/Cancel editor. Save Scholar stores the complete record. Graduated programs populate education, without duplicating annual grants or matching existing manual degree/institution entries. Graduation years are never inferred from contract dates or academic periods.
- Summer is a distinct term, Thesis Aid is a grant type, and Did Not Avail is a distinct outcome excluded from overdue payback assessment. Old terms previously saved as 3rd are not guessed back into Summer.
- Contract end period is labeled separately from graduation. The optional actual contract completion date starts the three-year grace period. Graduation in the same program clears assessment for all annual records. The existing three-year boundary and leap-year handling remain covered.
- The scholar's latest grant determines overall status in the directory, summary, dashboard, reports, and exports; profiles preserve every individual grant outcome. Ordering uses starting academic year, then term (1st, 2nd, 3rd, Summer), then record ID. Historical report scope does not replace overall status with an older outcome.
- Name search matches the start of each name word: dag matches Dagunan and excludes Cadagat. Other directory fields retain their existing search behavior.
- Removed the requested grant footer and tenure notes from the interface. Existing stored tenure notes remain preserved for compatibility.

## Verification

- 170 backend tests and 111 frontend tests passed (281 total).
- Lint, frontend test type checks, production type checks, and production build passed.
- Packaged executable verification passed, including saved records, migration, authentication, exports, education, current status, Summer, and contract/payback assessment.
- Release manifest verified 137 runtime files for 0.5.10.
- A private rehearsal on a copy of the office database preserved existing rows and values across 12 tables. Migration added 95 graduated-program education entries, inferred zero graduation years, and added zero duplicates when repeated. Database integrity and foreign-key checks passed.
- Browser verification used synthetic records only. Name search returned Dagunan and excluded Cadagat. A Faculty record with no rank stayed Faculty. Manual Bachelor education and automatically generated Master education persisted after reopening; the latter had no invented graduation year. Summer, Thesis Aid, and Graduated displayed correctly. No browser console errors were recorded.
- Screenshots: FINDINGS_SEARCH_0.5.10.png and FINDINGS_PROFILE_0.5.10.png (synthetic records).

## Installation and preservation

The guarded installer verifies the tested executable and source files, archives the previous source/runtime, creates a verified protected database backup, and confirms the office database hash remains unchanged during replacement. Migration 8 runs at the next application startup. Credentials and existing scholar/grant values are preserved. The separate Office distribution is outside this update's scope.
