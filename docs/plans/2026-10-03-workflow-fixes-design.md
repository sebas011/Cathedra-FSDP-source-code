# Scholar and grant workflow fixes — 0.5.2

Use the requested brainstorming, senior-architect and senior-backend skills. User authorization covers planning and implementation; no additional readiness confirmation is needed. No project-local Git repository exists, so isolate the work in the staging checkout and preserve source/runtime/database rollback artifacts at installation.

## Decisions and alternatives

1. Allow namesakes with advisory matching and ID-based identity (chosen). Keeping the restriction and changing the UI would prevent legitimate separate people. Adding a new personnel identifier is a larger feature and unnecessary for these repairs. Remove only uq_scholars_name in migration 5; keep the ordinary searchable name index. Existing IDs and relationships remain unchanged.
2. Allow complete child-list replacement under the mandatory current scholar revision (chosen). Two successive saves leave an unnecessary empty register. Adding explicit deletion intent is a larger API contract change. Retain child ownership, duplicate-ID validation, and atomic revision/transaction checks.
3. Count department follow-up once per scholar using the same predicate as report and analytics totals. Requirement rows still produce individual actions. Add one separate manual action when the scholar flag is set, even if requirement rows also exist. A manual flag explicitly represents additional follow-up, so it must remain independently visible.

## Implementation and validation

Update model/API/migration/report builder and label the department count as scholars in the UI and CSV. Update the tests enforcing the previous name restriction and add behavioral tests for complete replacement, stale writes, foreign child IDs, namesakes and separate histories, manual-only/register-only/combined reporting, filtered counts and CSV reconciliation. Verify migration 5 against a copy of the office database and compare all rows. Run backend/frontend tests, static checks and package builds; test the staged and installed executable using temporary synthetic data. Save protected rollback archives and database snapshot; install only while the app is stopped. Reapply installation access restrictions and verify package hashes and unchanged office database.
