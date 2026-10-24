# Release 0.5.24 validation

Verified locally on 24 October 2026, Asia/Manila. Paper & Ink is integrated into the existing React/FastAPI application. Schema16, existing records and export/Google contracts remain unchanged.

## Regression and build checks

- All 588 backend cases passed. Branch-enabled backend coverage: 92.10%.
- All 261 frontend tests passed across 40 files. Coverage: 82.42% statements, 74.85% branches, 77.73% functions, 85.8% lines. Formatting, static checks and production/test type checks passed.
- Registration-history checks cover full selected scope, UTC/Manila boundaries, explicit offsets, prior-period baseline, zero months and unavailable/future timestamps.
- The four-step editor retains one owned aggregate, draft guards, revisions and idempotency. Browser testing identified and corrected Continue activating submission on entering Review; final Save Scholar is an explicit action. Search focus and education disclosure printing were also corrected. Existing business, session, print, annual-copy and reporting regression checks remain in the suite.
- Constrained Windows x64 packaging passed: clean schema 16 seed, 149 runtime hashes, packaged startup, persistence, backup/restore, revoked restored sessions and shutdown. The actual bundled inventory verifier confirmed no database access. Windows PowerShell 5.1 smoke checks passed with developer runtimes removed from PATH.

## Browser acceptance

The running production build was inspected using a disposable fictional database. Desktop and 390px dashboard/profile/editor views have no page-level horizontal overflow. The expanded registration table keeps overflow inside its labelled keyboard region. Word-prefix search, filter focus, multiline insertion at the first line, explicit name-only saving, separate applications and mobile menu focus/Escape were checked. See [UI evidence](analysis/UI_VALIDATION_0.5.24.json). This is not full WCAG, screen-reader, physical printing or intended Office-PC certification.

## Update and development installation

The supported native Windows PowerShell updater passed a synthetic 0.5.23 to 0.5.24 rehearsal. Six existing scholars, nine annual grants, two accounts, IDs, Summer and historical rows were retained; database bytes were unchanged during runtime replacement. The protected snapshot/private rehearsal and existing encrypted Google configuration bytes were verified. Configuration, encryption and forgetting were checked without contacting Google. See [upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.24.json).

The development runtime was installed as 0.5.24 after restoring the previously approved owner/SYSTEM/administrator rules and passing the protected snapshot and preservation rehearsal. Its working database bytes and encrypted Google connection were preserved. The private installation receipt remains excluded from publication.

## Dependencies and delivery

The complete npm audit reported zero advisories. The constrained Python scan initially identified a newly reported setuptools issue; the official 84.1.0 patch was installed before packaging and the scan then reported no findings across 36 packages. See [dependency evidence](analysis/DEPENDENCY_VALIDATION_0.5.24.json) and the [maintainer advisory](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w). These are point-in-time results.

Source publication, its exact-revision GitHub Actions result, and the fresh Office-release download are verified separately through the [source checks](https://github.com/sebas011/Cathedra-FSDP-source-code/actions) and [versioned release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.24). Local validation is not a claim that a remote workflow has already passed. Working records, accounts, snapshots, OAuth credentials and connection tokens are excluded from delivery. Actual Office-PC acceptance remains separate.

See [regression evidence](analysis/REGRESSION_VALIDATION_0.5.24.json), [implementation plan](plans/2026-10-24-paper-office.md), [current documentation](current/README.md) and [Google setup](GOOGLE_SHEETS_SETUP.md).
