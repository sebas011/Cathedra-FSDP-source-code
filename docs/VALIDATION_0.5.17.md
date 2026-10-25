# Validation: 0.5.17

Implementation, local verification and Office update publication completed **13 October 2026, Asia/Manila**. Release: **0.5.17**; database schema: **13**.

All twelve suggestions in the [approved user-findings plan](plans/2026-10-12-user-findings.md) are implemented. The owner confirmed that Open/Closed is a separate per-grant case status, and business record text is uppercase while account credentials retain their original case. Development installation is verified; actual Office-PC acceptance is separate.

## Delivered findings

| Finding | Implemented behavior |
|---|---|
| Uppercase entries | New and edited scholar, program, education, remarks and Office Log text is uppercased. Unchanged historical text and credential case are preserved. |
| Education evidence | Completed outcomes, including migrated Graduated records, provide program-specific education evidence without requiring a keyword in remarks. Manual education years and suppression choices remain authoritative. |
| Grant field order | Outcome and case controls follow grant remarks. |
| Academic year | Compact consecutive years receive a dash; a four-digit year can expand to its following year. Partial and custom entries remain editable. |
| Graduation date | Each annual grant supports an optional graduation date, separate from optional contract completion. A supplied graduation date can provide the education year. |
| Profile actions | Profile, education and grant actions use labelled icons with keyboard focus and 44-pixel targets. Save and Cancel remain explicit. |
| Payback outcome | Payback is selectable and remains independent of the automatic contract assessment and case status. |
| Numeric entry | A focused age/tenure field ignores mouse-wheel value changes while retaining keyboard entry. |
| Annual copy | Copying retains useful record text and advances the year while clearing dates and extensions; the new draft starts On Going/Open. The source grant is unchanged. |
| Grant history | The whole history can collapse and expands for printing, with its previous disclosure state restored. |
| Completed and case state | Completed replaces the current Graduated label, with legacy input compatibility. Open/Closed is independently stored on each grant; closing a case does not clear payback follow-up. |
| Office Log | A general and scholar-linked register records notes, document receipts and transfers, server-recorded author, search/filtering and complete filtered CSV. Entries are append-only; a correction is another entry. |

The approved terms remain **1st, 2nd, 3rd and Summer**. The eight-college classification, Staff/Unknown rules, latest-grant overall status, optional contract completion and three-calendar-year grace rule remain intact. Only Name and Program Applied remain essential business fields; an Office Log note is required to avoid creating an empty entry. The legacy workload, projection, verification and standalone reports modules are not reintroduced.

## Executed verification

| Check | Observed result |
|---|---|
| Backend regression | **369 tests passed**, 104.65 seconds; two dependency deprecation warnings. |
| Frontend regression | **185 tests passed** across 32 files, 56.74 seconds. |
| Static checks | Ruff, application TypeScript and test TypeScript passed. |
| Production frontend | Vite production build passed. |
| Build inputs | Pinned dependencies, Windows x64 Python 3.14.7 and Node 26.8.1 verified. |
| Frozen package | Clean schema-13 seed and **147 runtime files** verified against the release manifest. Packaged workflow, persistence, authentication, Office Log, backup/restore and normal shutdown checks passed. |
| Documentation | Current version, schema ceiling, document links and export-header contracts passed. |
| Synthetic upgrade | Supported Windows PowerShell 5.1 updater passed from 0.5.16/schema 12 to 0.5.17/schema 13, with protected snapshot, rehearsal, record retention and integrity checks. |
| Development installation | Installed runtime 0.5.17 verified; both the new manifest and retained 0.5.16 runtime archive verified. Fresh-data smoke/restore/shutdown passed. Final permissions audit inspected 5,854 items with no policy violations. |
| Office delivery | Published and verified as `Cathedra-FSDP-0.5.17-Update`, with 147 runtime files and a separate hashed documentation inventory. No working database or mutable data folder is included. |

There are **554 unique automated tests** in the final complete run. Earlier focused runs are not added to that count. The final build log is `cathedra-build-0517-20261013-frozen.log`; its hash, observed counts and gate results are retained in regression evidence (local historical evidence; excluded from this source snapshot). Tests used disposable data, not the working or Office database. No new coverage measurement, dependency-advisory refresh or remote CI run is claimed.

Review also corrected and covered annual-copy extension leakage, uppercase fallback for newly entered unparsed tenure text, stale education suppression when moving from editing to a new scholar, and Unicode program aliases under uppercase entry. The failing cases were reproduced before the corrections; no test was skipped to obtain the final result.

## Browser acceptance

The final frozen application was checked using five synthetic scholars and five Summer grants. Sign-in, dashboard, profile remarks and 5.5-year tenure displayed correctly. Grant history started collapsed and expanded correctly; accessible action icons and outcome controls appeared in the intended positions. Edited remarks became uppercase and compact `20262027` became `2026-2027`.

Payback with a Closed case persisted without clearing the outcome. An annual copy retained remarks, advanced its year and showed empty dates with On Going/Open; discarding it required confirmation. A Completed master's grant with no graduation wording in remarks added the education entry. Graduation date `2025-06-14` persisted and supplied education year 2025, while the existing bachelor's year 2015 remained.

Both a scholar-linked document transfer and a general note saved with uppercase text and the server-recorded author. Accented lowercase search and a document-transfer filter returned the intended record; its downloaded CSV contained one row and eleven columns, including the correct note and author. The Guide explains the new workflows. No captured browser console errors occurred.

The browser automation provider initially changed the native date field's DOM value without committing the React change event. Real keyboard input committed the date; saving/reopening and serialization review confirmed persistence. This was not an application serialization defect. Normal shutdown through the authenticated desktop-exit endpoint succeeded, and the owned test service was absent afterward. Browser Exit-button acceptance, mobile breakpoints, physical printing and assistive technology were not verified in this run.

See browser evidence (local historical evidence; excluded from this source snapshot), profile screenshot (local historical evidence; excluded from this source snapshot) and Office Log screenshot (local historical evidence; excluded from this source snapshot). Screenshots contain only synthetic records.

## Database and installation preservation

The development installation replaced only the executable, bundled runtime, runtime manifest and frontend build. The isolated final build matched 224 code/configuration files before installation. All **415 source and documentation files** present at the installation boundary were preserved; later report finalization is an intentional documentation-only change.

The working database SHA-256 before and after runtime replacement was identical:

`c8dcd258fd24b602153b0ea2d9e31ca7c1f10d08bd490015bea6ec5a509b4c29`

The database was not replaced or migrated by development installation. Protected migration 13 runs at the next normal application launch. The verified installation receipt (local historical evidence; excluded from this source snapshot) records the protected snapshot and retained runtime archive; it does not claim that the live working database has already reached schema 13.

The first installation attempt correctly rolled back after its permissions audit rejected inactive browser/cache access entries. The working database remained unchanged. The previously approved owner/SYSTEM/administrator policy was reapplied using the existing protection tool, with the original permission receipt retained privately outside the installation. The successful retry passed the final audit. No application code or permission-audit rule was weakened for this retry.

The synthetic Office upgrade separately preserved two scholars, three annual grants, two accounts, two education entries and two Summer grants. IDs, program references, password hashes/logins, historical text, manual year 2019 and education intent survived exact comparisons. Intended changes were limited to Graduated-to-Completed normalization, Open/null-date defaults, affected revision increments, schema ledger/new empty Office Log storage and normal session metadata. Snapshot, migration rehearsal, integrity, foreign keys and normal shutdown passed. A child-process-only adjustment selected native Windows PowerShell 5.1 modules for the updater rehearsal; user configuration and the release were unchanged. See upgrade evidence (local historical evidence; excluded from this source snapshot).

## Office delivery and remaining acceptance

Delivery target: `<developer-home>\Desktop\Project\Releases\Cathedra-FSDP-0.5.17-Update`.

Publication passed on 13 October at 07:12 Asia/Manila. The copied 147-file runtime and separate documentation inventory verified, and the runtime manifest matches the final tested build. See publication evidence (local historical evidence; excluded from this source snapshot); final report refresh uses a separate documentation-only inventory and leaves runtime bytes unchanged. The prior 0.5.16 package remains intact.

The package contains the intentional empty installation seed, but no working development or Office database. Transfer the complete update folder and use its included updater with Cathedra closed, pointing to the existing Office installation. Keep the Office database authoritative. The updater preserves it during runtime replacement, rehearses the protected migration and retains a recoverable prior runtime. Older release and recovery evidence remains intact.

The actual Office PC and E: were not changed by this implementation. Actual installed-version acceptance, first opening on that device, recent Office additions, physical printing, clean-PC execution, signing, device encryption and assistive-technology checks remain subject to [Office acceptance](current/OFFICE_ACCEPTANCE.md). Local smoke tests do not certify those external conditions.
