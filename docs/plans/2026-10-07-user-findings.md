# User findings implementation plan — 0.5.10

Input: Findings-for-FSDP.md, 15 requested changes. Read-only inspection completed before edits. User confirmed word-prefix name search and the most recent grant as overall scholar status.

1. Delete the standalone monitoring page, its API/service/types/tests and navigation. Retain existing scholar requirements as record data. Keep the previously requested payback business rule in dashboard reports and profiles; move the detailed contract/payback list to the dashboard.
2–3. Remove shell context breadcrumbs and the profile's Scholars/name breadcrumb.
4. Add nullable explicit Faculty/Staff selection. Unspecified means Not recorded; stop inferring type from a rank or absence of rank. Existing records are not guessed or silently reclassified.
5. Replace inline education inputs with a saved-entry table and Add/Edit editor using the grant form's styling, draft/save/cancel behavior and discard protection.
6. Add one education entry per graduated program, including delivering institution and inferred degree level. Deduplicate against existing degree/institution entries and preserve manual data. Do not invent graduation years from grant end periods or contract dates. Apply to existing graduated records through a versioned migration and to later saves. Track generated entries by source program so repeated saves remain idempotent.
7. Support Summer as a separate selectable term in frontend/backend; leave previously normalized 3rd terms unchanged because their original meaning cannot be recovered.
8. Remove the specified grant editor footer copy.
9. Label end term/year as contract end period, explicitly not a graduation date. Only recorded Graduated status creates education entries. Contract completion date starts the separate inclusive three-calendar-year grace period; no expiry-based graduation.
10. Share the current-status rule across API, directory, summary, dashboard and reports. Order grants by starting academic year, starting term (1st, 2nd, 3rd, Summer), then ID as deterministic tie-breaker. Grant history keeps every recorded outcome. The overall status uses the newest grant, including when reporting filters select historical records.
11–12. Rename visible rank labels to Rank / position; remove tenure-note editing/display while preserving historical database notes for compatibility.
13. Name search requires every search word to match the start of a name word; punctuation separates words. Other directory fields retain their existing search behavior. Paginated and unpaginated endpoints must match.
14–15. Add Thesis Aid and Did Not Avail throughout selectors, dashboard/report counts and exports. Did Not Avail is distinct from Withdrawn and is not classified as an overdue funded contract.

Validation: targeted API/UI tests for explicit/unknown personnel, word-prefix search, latest status/filter/count agreement, Summer, new categories, graduated education deduplication and absence of inferred dates, education draft/discard behavior, removed routes/breadcrumbs; full regression/lint/type/build/package checks; private migration rehearsal comparing existing rows and reporting deliberate added education rows; synthetic browser checks; guarded installation with backup and rollback archives. Preserve user database and credentials. Office release remains outside this request.

Education editor design: reuse entry-section, entry-grid, grant-entry, action-group and TableRegion tokens/components; saved rows show degree/level, institution/year, Edit/Remove. Add education opens a draft. Save education applies the draft to the scholar form; Save Scholar persists the complete record. Cancel confirms discarding a draft. Buttons have explicit types and labels; table headers have scopes; no new palette.
