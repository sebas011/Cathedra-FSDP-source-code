# Review remediation implementation plan

Approved 10 October 2026, against the 0.5.15 review. Target release: 0.5.16.

## Requirements to preserve

Keep Name and Program Applied as essential business fields, optional dates, Summer as a distinct term, the eight-college classification, program-specific graduation and manual pending-contract precedence. Preserve all scholar/grant/program IDs, history and Office data. Use synthetic data for development and tests. Existing equivalent program names require explicit identity selection, not silent merging.

## Delivery groups

1. **Records and availability (F01–F04):** replace legacy tenure regex with bounded deterministic parsing; persist manual education-year corrections; add Unicode-consistent program identity enforced in SQLite and handle creation races; preserve historical collisions without merging.
2. **Reporting (F05–F08):** bind print snapshots to scope/navigation, keep normal paged state separate, reset/clamp pages on effective filters, show complete action totals and provide a consistent full-scope print workflow. Describe native printing limits in the Guide.
3. **Workflow (F09–F11):** add existing-program selection and admin catalog screens, guard navigation during program copying and parse qualification date suffixes conservatively.
4. **Build/support tooling (F12–F15):** enforce documented runtime/shell prerequisites, retire the obsolete migration helper or align it with current upgrade validation, accurately check endpoint response contents/counts and mark historical installation scripts.
5. **Delivery verification:** targeted regressions first, then backend/frontend suites, static/type checks, documentation/schema checks, packaged smoke and synthetic upgrade/restore checks. Record actual results in the release validation document. Real Office-device acceptance remains separate.

## Validation and rollout

Use an isolated source/build workspace with pinned dependencies. Never replace an Office database with a development seed. Record collision behavior, upgrade preservation and print filter consistency in tests. Publish an application-only package only after checks pass. Any development runtime installation must use the closed-app updater and retain the existing data folder.

The review is at COMPREHENSIVE_CODEBASE_REVIEW_2026-10-10.md (local historical evidence; excluded from this source snapshot). This plan is an implementation record; completion is established by the validation results, not the plan itself.

## Completion record

Completed 11 October 2026 as 0.5.16/schema12. F01–F15 are implemented, with 335 final backend and 153 frontend tests passing, static/type/build gates passing, final packaged workflows verified and a synthetic 0.5.15 upgrade preserving records/accounts/Summer terms. The development runtime installation preserved the working database and retained a recovery snapshot and old runtime. The application-only Office update package is published; E: and the Office PC are untouched.

See [VALIDATION_0.5.16.md](../VALIDATION_0.5.16.md) for exact checks, installation/upgrade receipts, browser evidence and remaining external acceptance tasks. No successful remote CI, real Office-PC acceptance, native printing or assistive-technology certification is claimed.
