# Audit corrections implementation plan — 0.5.15

Baseline: 0.5.14 / schema 11. Input: current and future issues review (local historical evidence; excluded from this source snapshot). User authorizes planning and immediate implementation, explicitly retaining Summer.

## Constraints and decisions

- Keep 1st, 2nd, 3rd and Summer, existing green, FSDP scope, account roles and annual-grant identity.
- Name and Program Applied remain the essential business fields. Evidence inference is conservative; uncertain remarks remain saveable without automatic education.
- Preserve grants, recorded outcomes, optional dates, manual education, suppression and database identity. No schema change or destructive correction migration is required.
- Existing linked achievements lack sufficient provenance for safe bulk deletion. Provide a read-only snapshot review tool; staff make individual corrections through existing education controls.
- Reuse the isolated source for changes/builds; use synthetic/disposable data for checks. Install a verified runtime without replacing the development or Office database.

## Execution sequence

1. **Graduation evidence (F1–F3).** Match only an affirmative scholar/current-program claim. Reject historical/third-party/different-degree or uncertain claims. Preserve Ph.D./Ed.D. abbreviations while splitting sentences. Parse explicit full dates as actual calendar dates, rejecting invalid/future and ambiguous numeric dates; preserve year-only evidence without invented days. Inject today's date for deterministic tests. Pass program identity into inference during saves and existing migration 11 execution. Preserve corrections and suppressions.
2. **Payback filter parity (F4).** Apply attention before pagination and share the predicate with CSV. Frontend passes filters independently of pagination. Summary counts continue to describe the department/year scope, and filtered totals describe the selected results. Test paged/unpaged/CSV identities and same-program pending/graduated precedence.
3. **Review existing education safely.** Add a read-only command for a closed disposable database copy. Default output gives counts; an optional private report lists only IDs/reasons for linked entries lacking current accepted evidence. Never change records or infer manual entries are wrong.
4. **Documentation (D1–D6).** Retain Summer with an explicit decision record; align seven current documents to 0.5.15/schema 11; correct pending-contract precedence, staff catalog creation exception, education limits, migration/test evidence and export headers. Mark the older analysis historical, preserving its content. Add actual-device acceptance and release documentation checklists without inventing Office/CI/signing results.
5. **Verification and delivery.** Targeted adversarial parser/save tests; filter/export parity; read-only review safety; Summer/history preservation; full existing backend/frontend/type/static/build gates; fresh schema and documentation contracts; packaged startup/persistence/recovery; updater rehearsal on a disposable installation. Verify runtime manifest and unchanged destination database hash before installing. Archive the prior release recoverably and keep one current app-only update.

## Completion criteria

The reproduced wrong-degree, future-date, abbreviation and filter failures are covered by passing regressions. Historical/manual education and recorded payback remain unchanged. No current roadmap proposes removing Summer. Documentation links and current export headers match actual output. Packaged version and source agree; installation preserves data. Record actual check counts in validation after checks pass.

## Conditional follow-up, not speculative implementation

Office-PC/clean-PC, screen-reader, signing/device encryption and remote CI acceptance require their actual environments. Record open acceptance items. New enrolment modeling, broad report optimization, automatic retention and persistent sensitive draft storage require a demonstrated need/design and are not part of this bounded correction release.
