# Validation: 0.5.18

Implementation, local verification, development installation and Office update publication completed **13 October 2026, Asia/Manila**. Release **0.5.18**, schema **13**; no new database migration. Actual Office-PC acceptance remains separate.

The [CSV readability plan](plans/2026-10-13-csv-readability.md) implements the owner's requested first-row profile and consecutive grant-only continuation rows. Directory, Dashboard detail and payback exports retain all matching annual grants, dates, recorded status, case and remarks. Source/provenance columns are removed from user directory/education exports, while database metadata remains intact. Education and Office Log retain their separate row meanings.

## Delivered CSV layout

| Export | Implemented layout |
|---|---|
| Scholar directory | 27 columns: 13 profile fields on the first row, followed by the first grant's 14 fields. Remaining grants have their own rows with empty profile cells. A scholar without grants retains one profile row. |
| Dashboard report detail | 21 columns: eight profile fields and 13 grant fields. Terms, academic years, contract completion and graduation date remain separate. Summary and follow-up sections retain their existing layout. |
| Payback follow-up | Ten existing columns, grouped by scholar. The first row contains scholar/name/department fields; continuation rows leave those three cells empty. Every matching annual grant remains visible. |
| Education | Seven columns, one achievement per row; Source Program ID is removed. Education values and manual years remain. |
| Office Log | Existing eleven-column, one-entry-per-row export is unchanged. |

Directory Source, Legacy Start Date and Legacy End Date columns are removed. Grant details are ordered by academic year, term and ID within each scholar. Equal names with distinct scholar IDs form separate named groups. Filtered report and payback exports include only matching grants and cover the complete result, beyond the visible page. Profile Remarks and grant Remarks remain separate. Unicode, commas, multiline text and spreadsheet formula protection are preserved. Blank profile cells inherit the preceding named scholar; blank grant cells mean no value was recorded. No blank separator rows are added. See [export schemas](EXPORT_SCHEMAS.md).

## Executed verification

| Check | Observed result |
|---|---|
| Backend regression | **390 tests passed**, 220.20 seconds; two existing dependency deprecation warnings. |
| Frontend regression | **185 tests passed** across 32 files, 114.54 seconds. |
| Static and production checks | Ruff, test/application TypeScript and Vite production build passed. |
| Build inputs | Pinned dependencies, Windows x64 Python 3.14.7 and Node 26.8.1 verified. |
| Frozen package | Clean schema-13 seed and **147 runtime files** verified. Persistence, authentication, Office Log, backup/restore and normal shutdown checks passed. |
| Export regression | Exact headers, first-row profiles, continuation rows, no-grant scholars, namesakes, filter scope, dates/status/cases, formula protection and multiline/Unicode remarks passed. A 53-scholar/55-grant fixture verifies complete results beyond pagination. The integrity-check tool validates scholar groups, including same-name/formula-like names, and rejects orphaned/split/moved grant rows. |
| Documentation | Current identities, schema ceiling, local links and machine-readable export-header contracts passed. |
| Synthetic upgrade and CSV acceptance | Supported Windows PowerShell 5.1 updater passed from 0.5.17/schema 13 to 0.5.18/schema 13. Grouped directory, Dashboard detail and payback downloads passed from the finished executable. |
| Development installation | Runtime 0.5.18 and retained 0.5.17 archive verified. Fresh-data smoke, restore and normal shutdown passed. Final permissions audit inspected 6,130 items with no violations. |
| Office delivery | Published and verified as `Cathedra-FSDP-0.5.18-Update`, with 147 runtime files and a separate hashed documentation inventory. No working database or mutable data folder is included. |

The complete run contains **575 unique automated tests**. Earlier focused runs are not added to this count. Twenty-one new export/tool regression cases are included in the full backend count. Regression evidence (local historical evidence; excluded from this source snapshot) records the actual results, final build-log hash and runtime-manifest hash. Tests used disposable data. No new coverage measurement, dependency-advisory refresh, remote CI run or whole-interface browser acceptance is claimed for this export-only change.

## Synthetic upgrade and packaged downloads

The disposable prior-version fixture contains three scholars, five annual grants, two accounts and three Summer grants. Two scholars have exactly the same displayed name and different IDs. The supported updater verified its protected snapshot, private schema-13 rehearsal, prior runtime archive and new 147-file manifest. Database bytes stayed unchanged during runtime replacement. After launching and signing in, schema, records, scholar/grant/program identities, password hashes/authentication, historical text, manual education year 2019 and Summer values were retained. Only normal session metadata was allowed to change.

Frozen directory/report/payback exports each retained all five grant rows, grouped with first-row profile values and blank continuation cells. Chronology, namesake boundaries, per-grant dates/statuses/cases/remarks, removed provenance columns, unchanged report totals/actions, education values and Office Log layout passed. Scholar JSON remained unchanged. Integrity, foreign keys and normal shutdown passed; the owned test service was absent afterward. A child-process-only module-path adjustment selected native Windows PowerShell 5.1 modules for the rehearsal, without altering user configuration or the release. See upgrade and CSV evidence (local historical evidence; excluded from this source snapshot).

## Working database and source preservation

Development installation replaced only the executable, bundled runtime, runtime manifest and frontend build. The isolated source matched **421 first-party source/document files** before packaging. All **422 first-party files** present at the installation boundary, including the new regression receipt, were preserved. Subsequent report finalization is an intentional documentation-only update.

The working database SHA-256 was identical before and after installation:

`209335cb803578581e7219e1f47c1daf9ea127be208f4c6a14e1c36256df63f0`

The working database was neither replaced nor migrated by development installation. Schema 13 remains the application ceiling; an older database receives its protected migration at normal startup when needed. The installation receipt (local historical evidence; excluded from this source snapshot) records the protected recovery snapshot and retained runtime archive. No live Office database was used for tests or opened during delivery.

## Office delivery and remaining acceptance

Delivery target: `<developer-home>\Desktop\Project\Releases\Cathedra-FSDP-0.5.18-Update`.

Publication passed on 13 October at 20:07 Asia/Manila. All 147 runtime files verified and the runtime manifest matches the final tested build. The prior 0.5.17 package remains intact. See publication evidence (local historical evidence; excluded from this source snapshot). The finalized reports are delivered through a separate documentation-only refresh and hashed inventory; runtime bytes remain unchanged.

The package contains only verified application files, documentation and the intentional empty installation seed. Keep the existing Office database authoritative. Transfer the complete update folder, follow its two-folder walkthrough with Cathedra closed, and reopen the original Office installation afterward. The update preserves the newest Office records and accounts through the supplied updater. See [Office Guide](OFFICE_GUIDE.md).

The actual Office PC was not changed. E: is disconnected and has not received 0.5.18. Actual Office-device first opening, newest records, physical printing, clean-PC execution and assistive-technology acceptance remain separate from local implementation. See [Office acceptance](current/OFFICE_ACCEPTANCE.md).
