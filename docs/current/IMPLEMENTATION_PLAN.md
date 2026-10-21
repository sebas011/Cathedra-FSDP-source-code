# Implementation and release plan

**Product:** Cathedra FSDP  
**Documented:** 22 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.23; database schema 16<br>
**Status:** implementation-derived documentation; see [baseline and evidence](README.md).

## Purpose and boundary

Maintain and deliver the existing FSDP application without replacing its architecture or overwriting Office records. This is a plan derived from current implementation and known gaps. The approved 0.5.17 findings implementation is described below; final regression, packaging and installation are recorded independently, and external Office acceptance remains open. Stages have prerequisites and exit criteria; no schedule or completed external acceptance is invented.

The 16 October 0.5.21 source implements the [audit remediation plan](../plans/2026-10-16-audit-remediation.md): verified recovery before deletion, bounded daily snapshots, strict restore selection, private error references, UTF-8 CSV signatures, frozen historical migrations, scoped UI recovery and inactivity locking. Schema 15 adds nullable session activity time. Prior optional document facts, application grouping, certification/enhancement categories, Summer and lightweight validation remain. Runtime installation and package acceptance are recorded independently in [validation](../VALIDATION_0.5.21.md).

## Delivered baseline

| Area | Implemented result | Evidence / source |
|---|---|---|
| Feature isolation | Active FSDP-only routes, product identity and schema allowlist; obsolete workload/projection and legacy/verification modules removed | Routes, product guard, migration 6 |
| Profiles | Multiple education entries, years-based tenure, profile remarks, individual grant remarks, eight colleges plus Staff | Models/API, migrations 6/8/10 |
| Annual records | Multiple grants, administrator program/grant duplication and separate outcomes | FSDP API and editor |
| Reporting | Dashboard analytics/recent ten, embedded scoped reports, complete CSV and printing | Dashboard/report components and API |
| Payback review | Optional contract completion, calendar-year grace and application-scoped completion clearing | Contract rules/payback service |
| Integrity/access | Revisions, account-scoped create retries, durable education suppression, account/session controls | Migration 9, concurrency/auth services |
| Recovery/updates | Protected snapshots, compatible restore gating, runtime-only updater and rollback safeguards | Upgrade, maintenance and desktop updater |
| Chart correction | College bars, status doughnut, grant-type pie | Included in 0.5.14 |
| 12 October entry changes | Uppercase edited record text, Completed outcome, per-grant Open/Closed case and optional graduation date; compact protected entry controls | Approved findings, schema 13 and current form/profile |
| Office Log | Append-only notes/document receipt/transfer register with optional scholar snapshot, author-scoped retry safety and filtered CSV | Office Log model/API and register |

## Baseline implementation sequence — already delivered

Use this dependency sequence when rebuilding the existing product in an isolated environment or extending a related area. It records how the modules fit together; it is not a claim that these modules still need to be built.

| Order | Work package and dependency | Deliverable | Acceptance reference |
|---|---|---|---|
| B1 | Establish FSDP product/configuration, schema and migration runner | SQLite models, product guard, ID counter, disposable seed and protected schema upgrade | TR-01/02/07/10; schema dictionary |
| B2 | Add authentication before exposing protected data | First-admin setup, hashed passwords, sessions, role/temporary-password checks, revocation and protected shell | PRD-01/18; API access inventory |
| B3 | Build scholar/program services on B1/B2 | Owned nested CRUD, program resolution, revisions, account-scoped create retries and audit events | PRD-02/03/15; TR-03/04/05 |
| B4 | Build editor/profile on B3 | Education, years-based tenure, separate remarks, requirements, annual grants, duplication and unsaved-draft controls | PRD-04 through PRD-09/14 |
| B5 | Add derived status and contract rules on saved grant history | Latest grant ordering, optional completion/grace calculations and application-scoped completion handling | PRD-10/11; contract boundary tests |
| B6 | Add overview/reporting on B3/B5 | Scoped counts, mixed charts, recent ten, paginated results and complete filtered print/CSV | PRD-12/13/17; report reconciliation |
| B7 | Add operating/release recovery on B1/B2 | Backup/protection/restore, readiness, packaged launch and data-preserving updater | PRD-16; TR-11/12 |
| B8 | Verify the integrated workflow across B1–B7 | Regression evidence, responsive/keyboard review, manifest and intended-device acceptance | Release verification matrix below |

## Stage 1 — Validate and deliver the current findings release

**Owner:** project maintainer; Office administrator for destination acceptance.

1. Confirm the intended installation and that Cathedra is closed. Identify its own `data` directory; the Office database is authoritative.
2. Complete the 0.5.17 regression/migration/package gates and verify its complete manifest. Exclude any local `data` created by opening a package on the development PC.
3. Use the packaged updater against the existing Office installation. Retain its recovery snapshot, runtime archive and update receipt. Do not copy the development database over it.
4. On the development installation, account for new documentation/uncommitted work before any source synchronization. Do not assume the original clean fast-forward helper remains applicable.
5. Open the original installation path. Confirm version, scholar totals, recent Office additions, profile/grant notes, accounts and the appropriate mixed charts.
6. Confirm any required schema migration has a protected pre-migration snapshot and passes relationship/integrity checks.

**Exit criteria:** correct installation reports 0.5.17; destination records are preserved; schema/history valid; the Office user confirms essential workflows. A package transfer alone does not satisfy installation completion.

## Stage 2 — Audit corrections delivered in 0.5.15

Summer is retained, alongside 1st/2nd/3rd. The older three-term removal stage is superseded; see [decisions](DECISIONS.md).

[Audit corrections plan](../plans/2026-10-09-audit-corrections.md) covers program-specific graduation claims, full-date checks, dotted abbreviations, payback filtering before pagination, private read-only education review and documentation/export reconciliation. Existing achievements, manual corrections, recorded outcomes and schema 11 are preserved. See [validation](../VALIDATION_0.5.15.md) for actual completion evidence.

The [0.5.16 review remediation plan](../plans/2026-10-10-review-remediation.md) addresses F01–F15: bounded tenure inference, durable education-year changes, Unicode program identity and concurrent writes, catalog workflows, printing/pagination/counts, and release/support tooling. Schema 12 preserves historical equivalent-name programs without merging. See [0.5.16 validation](../VALIDATION_0.5.16.md) for actual completion evidence before transfer.

The [approved 12 October findings plan](../plans/2026-10-12-user-findings.md) is implemented in 0.5.17/schema 13. It covers uppercase record entry, status-driven education, final-position grant controls, academic-year formatting, optional graduation dates, icon actions, explicit payback selection, numeric wheel protection, date-free copying, full-history collapse, Completed plus independent case state and Office Log. Final local regression, packaging, synthetic upgrade, browser acceptance and development installation passed on 13 October. See [0.5.17 validation](../VALIDATION_0.5.17.md) for observed results and the separate Office delivery/device-acceptance boundary.

## Stage 3 — Complete intended Office-PC acceptance

The [13 October CSV plan](../plans/2026-10-13-csv-readability.md) implements readable grouped export rows in 0.5.18 without a migration. Directory/report/payback groups keep profile fields on each scholar's first row and all subsequent grant details below it. Export provenance columns are removed. [0.5.18 validation](../VALIDATION_0.5.18.md) records actual gates separately from the delivered 0.5.17 baseline.

**Owner:** Office administrator/tester, supported by maintainer.

Run the self-contained executable on the intended Office machine and a clean Windows environment with no developer runtimes on PATH. Verify first opening and normal exit, sign-in/password change, directory search, multiple education entries, years-based tenure, profile versus grant remarks, annual grant copy, Completed/case separation, optional graduation facts, Office Log receipt/transfer entry, report print/CSV, contract grace boundaries, backup creation and isolated restore.

Test an update from the Office's actual installed version using a disposable copy before updating authoritative records. Confirm behavior on the intended monitor, keyboard-only navigation, 200% zoom and representative assistive technology. Record who checked each workflow, date, installed version, result and any unresolved failure.

**Exit criteria:** a completed Office acceptance record, reliable first launch/exit and successful isolated recovery. Development-PC smoke tests alone do not close this stage.

## Stage 4 — Stabilize operating evidence

**Owner:** release maintainer and device administrator.

Establish a verified off-device recovery routine using existing snapshots/review controls. Confirm live-device encryption separately from encrypted removable backups. If the organization supplies a signing certificate, use the existing optional signing path and verify the signature. Record remote CI execution if a private remote is configured; the presence of a workflow file does not prove a run.

**Exit criteria:** usable restore evidence, documented device protection and explicit status of signing/CI. No credential, live database or personnel export is committed or published as evidence.

## Stage 5 — Improve report scale when needed

**Owner:** backend maintainer. **Status:** optional scale work, not a current correctness failure.

The existing 0.5.11 packaged service benchmark shows slower full report computations at 10,000 synthetic scholars. First define the actual Office data scale and a representative end-to-end budget. Profile scoped totals and reporting joins; optimize measured bottlenecks while preserving distinct scholar counts and application-scoped completion joins. Recheck query count, report totals, complete CSV/print and memory using disposable datasets.

**Exit criteria:** measured improvement on representative data without an invented p95 claim or incomplete exports. Do not add an unrequested caching/server architecture solely to satisfy synthetic scale.

## Stage 6 — Maintain documentation and release discipline

Keep this set, Office Guide, export schemas, source version, frontend version, bundled version and release manifest consistent. Place new evidence next to its release. Keep a clean application-only transfer package and recoverable older runtime archives. Never treat a package-local empty seed as the Office database.

## Verification matrix for any functional release

| Gate | Required evidence |
|---|---|
| Behavior/data | Targeted tests for changed rules; no changes to unrelated profiles, grants, education, requirements or accounts in a copy-based rehearsal |
| Backend | Existing regression suite and static checks |
| Frontend | Test/source TypeScript checks, regression tests and production build |
| Interface | Changed-page desktop/mobile review; relevant keyboard/printing checks |
| Migration | Protected snapshot, ordered history, integrity and foreign-key verification |
| Package | Clean seed, manifest/version reconciliation, packaged startup and persistence |
| Update | Destination database preservation, rehearsal result and usable rollback/safety archive |
| Office | Intended-device acceptance and verified newer records |

Rollback uses the supplied runtime updater's safeguards. If records change after an update, do not overwrite them with an earlier snapshot to force a rollback; review the fingerprint/journal and preserve newer data. An older runtime must not be pointed at a newer unsupported schema without a verified compatibility procedure.

Sources: [release history](../RELEASE_HISTORY.md), [baseline verification summary](README.md), performance evidence (local historical evidence; excluded from this source snapshot), [build pipeline](../../desktop/build-split-release.ps1), [migration rules](../../backend/app/migrations.py), [updater](../../desktop/office_update.py).

## User findings implemented in 0.5.14

See [the approved findings implementation plan](../plans/2026-10-09-findings-profile-grants-design.md). It covers automatic graduation education, Faculty/Staff/Unknown, form layout, explicit pending repayment contracts and Transferred, annual drafts and collapsible program history.

## 0.5.22 completion and reporting changes

The [implementation plan](../plans/2026-10-17-completion-and-cloud-reporting.md) covers literal calendar years, selection-preserving record editing, Incomplete grants, optional allowed completion rules, independent repayment progress and manual Google reporting. Schema 16 is additive. Source verification, development installation and actual Office-PC acceptance remain distinct; consult [0.5.22 validation](../VALIDATION_0.5.22.md) for observed results.

## Completion and reporting update (0.5.22)

Calendar years stay literal: 2021 remains 2021; 2021-2022 remains an explicit academic-year range. Uppercase record controls preserve cursor/selection and multiline composition. Incomplete is an additional known grant outcome. The optional program start date and whole allowed duration produce a completion deadline; an explicit optional deadline takes priority, including for shorter programs. Previous completion dates remain a fallback. Grace runs three calendar years from the effective deadline, including its final day. Repayment progress (Not recorded, Unpaid, Partially paid, Fully paid) is separate from outcome and case status.

The administrator can configure and connect Google reporting from Backup & Export, then explicitly confirm a one-way replacement of the CATHEDRA REPORT tab. Other tabs are preserved. Connection credentials are Windows-user encrypted outside SQLite. Internet and OAuth setup are needed for cloud delivery; offline records work independently. See [setup](../GOOGLE_SHEETS_SETUP.md) and [validation](../VALIDATION_0.5.22.md).

## Google report update (0.5.23)

Google reporting uses a dedicated [fifteen-column contract](GOOGLE_REPORT_CONTRACT.json) rather than the full CSV table. Each scholar is numbered once and their grants remain on consecutive rows. The report retains recorded education, tenure in years, exact dates or recorded academic periods, each grant's outcome and clearly labeled profile/grant remarks. Existing CSV exports and schema16 are unchanged. Setup, approved test accounts, spreadsheet editing access and per-PC sign-in are described in the [detailed guide](../GOOGLE_SHEETS_SETUP.md). See [0.5.23 validation](../VALIDATION_0.5.23.md) for observed delivery status.
