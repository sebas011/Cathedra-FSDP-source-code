# Release 0.5.23 validation

Verified locally on 22 October 2026, Asia/Manila. Database schema remains 16; no new migration is added. CSV contracts remain unchanged.

## Source and regression checks

- 586 backend cases passed, including nineteen compact-report cases and the existing Google authorization, permission, literal-cell and replacement checks.
- Branch-enabled backend coverage is 92.10%; the new report projection has 100% coverage.
- All 245 frontend tests passed across 38 files. Coverage: 81.55% statements, 73.60% branches, 76.80% functions and 85.05% lines. Formatting and production/test type checks passed.
- The fifteen-column contract, grouped grant rows, all education entries, optional dates/periods, zero/missing tenure, remarks, Unicode ordering and bounded loading were checked with synthetic data.
- The Windows sandbox blocked asyncio's local socketpair before test execution. The identical backend suite passed outside that restriction; no application fix or weakened assertion was needed.

## Dependency checks before publication

The first source workflow correctly stopped at newly published dependency advisories. The final inputs pin Vite 7.3.7, Vitest and coverage-v8 4.1.12, and certifi 2026.10.19. These are compatible patch updates; application rules and database schema remain unchanged. The frontend checks were rerun with the patched tools: all 245 tests and coverage gates, formatting, type checks and production build passed. The locked npm audit reported zero advisories, and the OSV check reported zero findings across all 36 constrained Python packages on 22 October 2026. Advisory results describe that check time and are not a guarantee about future disclosures.

See the [dependency check evidence](analysis/DEPENDENCY_VALIDATION_0.5.23.json) and [dependency inventory](DEPENDENCY_INVENTORY.json). The maintained [Vite advisory](https://github.com/advisories/GHSA-rq7h-c2jc-7f22), [Vitest advisory](https://github.com/advisories/GHSA-xp26-3454-mjgp), and [certifi advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) identify the patched releases. The Office package serves compiled frontend files through Python; Vite and Vitest development servers are not distributed.

## Windows package and development installation

The production build passed clean schema16 seed verification, packaged startup/persistence, backup/restore/shutdown, PowerShell manifest verification, and the actual bundled database-free inventory verifier. The package contains 149 runtime files. The pinned Windows x64 Python/Node/build dependencies were checked.

The development runtime was installed as 0.5.23 after a protected database snapshot and private preservation/repeat-upgrade rehearsal. Its working database hash and existing encrypted Google connection were preserved. Application source was retained. Existing runtime recovery copies remain private. The supported Windows PowerShell 5.1 Office updater also passed a synthetic 0.5.22 to 0.5.23 rehearsal: five scholars, eight grants, two accounts, Summer history, private snapshots, schema16, database-byte preservation, Google DPAPI configuration and normal startup/shutdown were verified. See [upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.23.json).

## Publication and external acceptance

The source snapshot is prepared before its own GitHub publication completes. Current public delivery status is available on the [versioned Office release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.23), and the exact source revision's checks appear in [GitHub Actions](https://github.com/sebas011/Cathedra-FSDP-source-code/actions). Local tests do not certify the separate Office PC, organization signing, or an unrelated future workflow run.

The user confirmed a successful real Google report update before this layout change. The new projection was tested with synthetic records; private scholar rows, spreadsheet identifiers, account details, credentials and connection tokens are excluded from source and delivery artifacts. No live scholar export was used as a regression fixture.

See [regression evidence](analysis/REGRESSION_VALIDATION_0.5.23.json), the [implementation plan](plans/2026-10-21-google-reporting.md), [detailed Google setup](GOOGLE_SHEETS_SETUP.md) and [Google report contract](current/GOOGLE_REPORT_CONTRACT.json).
