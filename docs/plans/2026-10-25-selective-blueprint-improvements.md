# Selective blueprint improvements — 0.5.26

## Selected changes

1. Extend administrator change history with bounded, allowlisted before/after business values. Keep existing field-name history and historical events readable. Store new details atomically with the change and never copy credentials or tokens into history.
2. Add a shared pure contract assessment that returns the existing result plus a stable internal rule and a factual explanation. Show optional assessment details in grant profiles and dashboard follow-up without adding general explanatory blocks or changing export columns.
3. Centralize the Philippine business date and capture one date per report/request. Keep authentication expiry on UTC instants and preserve existing backup/recovery timestamp handling. Preserve the existing three-calendar-year grace boundary and all deadline precedence rules.

## Preserved behaviour

Keep Name and Program Applied as essential fields, optional dates, literal calendar years, Summer, Faculty/Staff/Unknown, certification/enhancement programs, independent applications and annual grants, profile/document facts, case status, repayment progress, the latest-grant directory outcome, and existing CSV/Google contracts. Existing atomic saves, revisions, idempotency, access controls and recovery remain in place. No approval workflow, mandatory appointment history, semester ledger, payment-disbursement system or degree-only restrictions are introduced.

## Data compatibility

Schema 17 adds only nullable activity_events.change_details. Existing audit events have no invented before/after values. Preserve all existing business rows, IDs, migration history and the local Google connection. New history is append-only through existing application routes; direct database tamper protection is not claimed.

## Verification and delivery

Test transaction rollback, delete-orphan history, unloaded old values, absent/cleared data, credential redaction, legacy history, administrator access, Manila midnight boundaries and consistent profile/report/payback explanations. Run backend/frontend regression and static checks, inspect the running production interface with fictional records, build the Windows application and rehearse a schema-16 upgrade before guarded local installation. Keep the published 0.5.25 release immutable. Remote publication is a separate action.
