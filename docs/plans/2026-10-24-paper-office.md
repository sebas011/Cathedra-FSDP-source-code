# Paper & Ink production integration — 0.5.24

## Authorized result

Integrate the reviewed Scholar Office redesign into the existing React/FastAPI application, verify the real workflows, and publish the matching source and database-preserving Windows Office update to the existing GitHub repositories. This implements the design reference in `docs/redesign/2026-10-24`; the standalone preview remains a historical design artifact using fictional records.

## Implementation sequence

1. Replace the shared visual tokens and shell with ink navigation, paper surfaces, cobalt actions, local serif display headings, readable working text and consistent control boundaries. Preserve mobile keyboard behavior, role checks, health checks, print, account/security, sign out and desktop exit.
2. Reorganize the scholar directory and profile around identity, education, distinct program applications, annual grants, remarks and independent hard/soft-copy availability. Retain name-word prefix search, alphabetical order, filtering, pagination and full-scope export.
3. Present the existing aggregate editor in four steps: identity, education, programs/grants and final review. Keep nested drafts in one owner and commit only at the final save. Preserve record IDs, optimistic revisions, idempotent uncertain retries, unknown values, session recovery, unsaved prompts and caret/IME behavior.
4. Rebuild the dashboard with real metrics, an attention queue, affiliation columns, outcome composition and the ten newest scholars. Reporting remains inside the dashboard. Add an additive, tested historical-registration series rather than inventing a line from recent records. Clearly state its time interval and unit.
5. Apply the shared system to Office Log, program catalog, accounts, guide, backups/Google reporting, activity and readiness. Keep descriptions in the guide where they explain business rules. No working Google request is needed for regression testing.
6. Run source formatting/static/type checks, backend and frontend regression/coverage checks, and browser acceptance against synthetic records. Review the final production diff and correct findings. Build the Windows executable from constrained inputs; verify the clean schema16 seed, runtime inventory, startup, backup/restore, shutdown and a record-preserving upgrade rehearsal.
7. Prepare a reviewed source snapshot and app-only update package excluding local scholar records, accounts, backups, OAuth files and encrypted connection state. Preserve remote Git history and older releases. Verify the source workflow and freshly downloaded release assets before reporting publication complete.

## Domain and recovery invariants

- Name is the essential profile field; Program Applied is essential for each included grant. Other record fields remain optional.
- Terms remain 1st, 2nd, 3rd and Summer. Calendar years stay literal. Tenure supports partial years.
- Annual copies stay within the same application; a later independent application has its own completion/payback assessment. Completed, recorded Payback, calculated review, case Open/Closed and repayment progress retain their separate meanings.
- The eight colleges remain CIT, CAS, COED, COE, CCJ, COF, CBMA and CCS. Other known affiliations are Staff; missing affiliation remains Unknown.
- Profile and grant remarks remain separate. Availability is Available, Not available or Not recorded, independently for hard and soft copies.
- No database migration or business-record rewrite is needed for this visual release. Existing Office `data/cathedra.db` and Windows-user Google configuration must be preserved by the supported updater.
- The production app retains its current authenticated JSON API and local Windows architecture. The optional HTMX adapter described by the design kit is not introduced by this release.

## Completion evidence

Record measured checks and package/publication evidence in `docs/VALIDATION_0.5.24.md` and versioned analysis receipts. Local or CI tests do not certify the separate Office PC or constitute a live Google transmission test. A partial build or uploaded source alone does not complete this plan.
