# Cathedra FSDP 0.5.22 validation

Date: 17 October 2026, Asia/Manila. Supported schema: 16.

## Implementation

Literal calendar years are preserved; explicit academic ranges remain supported. Shared uppercase record controls preserve selection and composition, including earlier lines in remarks. Grants support Incomplete, optional program start/allowed years or an exact completion deadline, and separate repayment progress. Exact deadlines take priority; old completion dates remain a fallback. Three calendar years of grace include the final anniversary day; review starts the next day. Annual copies retain explicitly recorded program completion rules in the same application and reset outcome/payment facts; later applications clear the previous rules.

Google reporting uses an administrator-confirmed one-way replacement of CATHEDRA REPORT. Other tabs are preserved, literal values prevent formulas executing, stale values are cleared atomically and credentials are Windows-user encrypted outside SQLite. No hosting or new runtime dependency is required. See the [plan](plans/2026-10-17-completion-and-cloud-reporting.md) and [setup guide](GOOGLE_SHEETS_SETUP.md).

## Automated verification

- 567 unique backend cases verified: the complete run passed 566/566, followed by all 47 Google cases after the final refresh-token recovery fix (one new case). Backend branch-enabled coverage reported 92%, above its 87% gate.
- The complete frontend run passed 245/245 across 38 files with one threaded worker. Coverage: 81.55% statements, 73.6% branches, 76.8% functions and 85.05% lines; all configured gates passed.
- Ruff, Prettier, test/source TypeScript checks, production build, pinned build inputs and current documentation/export contracts passed.
- Migration13/14/15-to16 regressions preserve previous scholar, grant, program, account, session and Office Log values. Deadline precedence, leap anniversaries, grace boundaries, independent applications, Transferred/Withdrawn eligibility and payment history are covered.
- Google tests include real Windows DPAPI and real loopback callbacks with Google network responses mocked. Malformed credentials, state/PKCE, failures, concurrency, corrupt connection recovery and token rotation are covered.

See [regression evidence](analysis/REGRESSION_VALIDATION_0.5.22.json).

## Packaged Office verification

The isolated desktop build and its 149-file runtime inventory passed both PowerShell verification and the actual bundled Python verifier without database access. Packaged startup/persistence checks passed.

The supported PowerShell5.1 updater passed a synthetic 0.5.21/schema 15 to 0.5.22/schema 16 upgrade. Four synthetic scholars, seven grants, two accounts and Summer/history remained intact. Database bytes were unchanged during runtime replacement; a protected snapshot and private migration rehearsal passed. The frozen application verified literal 2021, Incomplete, exact deadline/grace and payment progress. Synthetic Google configuration was encrypted by the frozen runtime and locally forgotten without external Google requests. Daily/pre-delete recovery, CSV, activity and normal shutdown checks passed. See [upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.22.json).

## Development installation and delivery

The development installation is verified at 0.5.22. Its working database bytes were unchanged and 489 first-party source/documentation files were preserved during replacement. A protected snapshot and private schema 13 to 16 migration rehearsal preserved all preexisting values and history; the working database itself was not used as the upgrade target. Normal first launch performs any needed protected migration. Native smoke/restore/shutdown and a 7,502-entry permission audit passed. The private installation receipt remains excluded from delivery and source publication.

The local Office update uses the same verified 149-file runtime and intentionally empty schema16 seed. Application-only delivery excludes working databases, accounts, backups and Google connection credentials. Older verified packages are retained. No GitHub publication was performed for 0.5.22 in this work.

## Acceptance limits

The actual Office PC is separate and has not been tested. No real Google account has been authorized and no live spreadsheet has been modified. Google delivery requires the owner's Desktop OAuth credentials, consent and reporting spreadsheet setup. Report delivery is not a database backup. The working development and Office databases were not test fixtures.

The local Office update copy is verified at `Releases/Cathedra-FSDP-0.5.22-Update`, with 149 runtime files and no working records or Google credentials. See the local delivery receipt (local historical evidence; excluded from this source snapshot).
