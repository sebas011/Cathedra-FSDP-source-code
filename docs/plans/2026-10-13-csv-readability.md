# CSV readability implementation plan — 13 October 2026

Target: Cathedra FSDP 0.5.18, database schema 13; no database migration. The requested layout starts each scholar with a named profile row and first grant, follows with one continuation row per remaining grant, then starts the next scholar. Existing stored history remains intact.

## Implementation

1. Remove Source, Legacy Start Date and Legacy End Date from the directory CSV, and Source Program ID from the education CSV. Keep stable IDs, optional business dates, recorded outcomes, case status, profile remarks and individual grant remarks.
2. Group directory records by scholar. Write the 13 profile fields on the first row only, with one grant's 14 fields per row; keep one profile row for a scholar without grants. Do not add blank separator rows or combine multiple grants into a cell.
3. Apply the same grouping to Dashboard report detail: eight profile fields followed by 13 grant fields. Keep terms, academic years and actual optional dates in separate columns. Preserve department totals, follow-up sections and complete filtered scope. Group contract follow-up grants by scholar and leave its first three fields blank on continuation rows; keep its ten headers unchanged.
4. Preserve Unicode, multiline remarks, spreadsheet formula protection, permissions and independent education/Office Log rows. Update the machine-readable export contracts, technical schema guide and searchable Office Guide to explain continuation rows and safe spreadsheet sorting.

## Verification

- Exercise several scholars, multiple annual grants and no-grant profiles. Check exact ordered headers, one grant per row, continuation blanks, next-scholar boundaries and no blank separator rows.
- Verify same-name scholars stay separate by ID, all selected records are exported beyond a displayed page, and unmatched grants do not enter scoped report/payback groups.
- Retain separate profile/grant remarks and each grant's dates, outcomes and case state. Check Unicode, embedded commas/newlines and formula protection, including continuation rows.
- Run relevant export tests, full regression checks, frontend type/build checks and the current documentation contract checker. Use synthetic data only.

## Delivery

Build and verify an application-only update. Install only while Cathedra is closed, with the existing protected update workflow; keep the working database and accounts. Publish the tested payload with the clearer Office update walkthrough. Verify the transfer-drive copy only when that drive is available. Intended Office-PC and printer checks remain separate.

## Execution evidence

Implementation, all 390 backend and 185 frontend tests, production packaging, frozen CSV acceptance, the schema-13 upgrade rehearsal and database-preserving development installation passed on 13 October. The [release validation](../VALIDATION_0.5.18.md) records the observed delivery status and links the retained regression, upgrade and installation receipts. Office-device acceptance and transfer to a disconnected E: drive remain separate.
