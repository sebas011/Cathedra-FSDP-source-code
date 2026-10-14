# Cathedra FSDP 0.5.7 — Dashboard presentation

Dashboard layout reorganized with the existing green palette and unchanged APIs and data schema.

- Shared department/year scope above four concise summary metrics.
- Department comparison uses a zero-baseline count axis and horizontal bars.
- Grant outcomes use a proportional SVG donut with counts and percentage legend.
- Grant types use a separate count chart. Full values are available to assistive technology.
- Latest ten scholars use a clear table with profile links, department and creation date.
- Follow-up shortcuts sit beside grant types; reporting, CSV export and print views remain embedded. Blank report filters start collapsed; active filters remain visible.
- Honest empty states; no fabricated trends or estimates; no additional dependencies.

Validation: 142 backend tests and 121 frontend tests passed, frontend test TypeScript and production build passed. Chart tests cover integer axis ranges, zero totals, sorting, and small/unknown outcome categories. Existing dashboard scope/export integration passed. Profile test corrected to use the Windows locale when asserting fractional tenure.

Browser preview used a separate synthetic database with varied departments, statuses and grant types. Desktop and narrow-screen screenshots retained below. Chart and table scrolling is contained within their regions. No production records were used in the preview.

Installation uses the tested desktop package, a protected database snapshot and source/runtime rollback archives. No database migration for this update; schema remains 6. Installation manifest records database hashes before and after. The Office distribution is unchanged.

!Dashboard sample (local historical evidence; excluded from this source snapshot)
!Narrow-screen sample (local historical evidence; excluded from this source snapshot)
