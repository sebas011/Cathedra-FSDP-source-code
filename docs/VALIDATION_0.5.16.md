# Validation: 0.5.16

Completed 11 October 2026, Asia/Manila. Release: **0.5.16**, schema: **12**.

The approved [remediation plan](plans/2026-10-10-review-remediation.md) is implemented. All fifteen confirmed findings in the comprehensive review (local historical evidence; excluded from this source snapshot) have code or tooling fixes with regression coverage. The development runtime and the application-only Office update package are verified. Actual Office-device acceptance remains separate.

## Findings delivered

| Finding | Result |
|---|---|
| F01: tenure parsing availability | Bounded deterministic parsing replaces the backtracking path; long/unconvertible source text remains retained. Numeric/null precedence and valid year/month formats remain supported. |
| F02: cleared education year restored | Persistent manual-edit intent preserves deliberate corrections and clears. An unchanged blank resubmission still permits new graduation evidence to populate the year. |
| F03: Unicode program save failure | Program lookup uses one Unicode NFKC/casefold/whitespace identity rule. Existing program selection uses its recorded ID. |
| F04: concurrent program identity split | A database unique canonical key and transaction conflict handling prevent new equivalent identities. Historical collisions remain separate and visibly flagged; no records are silently merged. |
| F05: stale asynchronous print scope | An isolated, complete print snapshot is cancelled on scope/view/order/revision/navigation changes, without overwriting the normal page state. |
| F06: false empty filtered pages | Effective scope changes reset report/action/contract pages; pagination is clamped to valid results. |
| F07: incomplete action total | Needs action uses the complete action total, independently of the visible page length. |
| F08: incomplete general printing | Dashboard app print controls prepare the overview, selected report view and selected contract category. Directory app printing fetches all matching pages and rejects inconsistent results. The Guide explains native Ctrl+P limits. |
| F09: missing program catalog workflow | Administrators can add, edit, copy and delete programs through Settings; grant entry can select an existing program. |
| F10: navigation during program copying | Pending copy operations guard navigation and stale/unmounted responses. |
| F11: missed undated graduation evidence | Conservative parsing recognizes valid date suffixes and direct undated current-degree claims; qualification names containing “in” remain intact. |
| F12: runtime prerequisites | Packaging verifies Windows x64, 64-bit Python 3.14.7 and Node 26.8.1 before dependency preparation, then checks pinned build inputs. |
| F13: obsolete migration helper | The obsolete helper fails early with the supported procedure and does not touch a database. Historical installation scripts identify their old release scope. |
| F14: unclear shell prerequisite | Build/verification scripts declare PowerShell 7. Office upgrade/smoke workflows remain compatible with Windows PowerShell 5.1. |
| F15: overstated endpoint checks | The import-safe, copy-only checker verifies actual endpoint identities, totals, report/payback contents and CSV headers/counts. Malformed successful responses fail validation. |

## Executed checks

| Check | Actual result |
|---|---|
| Final complete backend suite | **335 passed**, 139.45 seconds; two dependency deprecation warnings |
| Complete frontend suite | **153 passed** in 29 files |
| Static/type/build checks | Ruff passed; application and test TypeScript checks passed; production frontend build passed |
| Focused regressions | 24 tenure cases, 28 program identity/education-intent cases and 28 tooling cases are included in the backend total; frontend print/catalog regressions are included in the frontend total |
| Build inputs | Pinned dependency verification passed; 36 Python build packages checked |
| Final Windows package | Clean frozen backend repack, executable version 0.5.16 and **142 runtime file** manifest verified |
| Packaged behavior | Core records, authentication, revision conflicts, name search, program/grant copying, education, tenure, Summer, reports, payback, backup/restore, session revocation, persistence and normal shutdown passed |
| Documentation | Version identities, migration ceiling, internal links and export headers verified |
| Synthetic Office upgrade | Supported 0.5.15 → 0.5.16 update passed; protected snapshot, migration rehearsal, integrity/FK checks, existing login and normal shutdown passed |
| Development installation | Main runtime 0.5.16 and retained 0.5.15 runtime manifests verified; fresh-data packaged smoke passed; read-only permission audit found no violations in 9,840 files |

The normal build pipeline passed with 332 backend tests and the complete 153-test frontend suite. Three additional blank-year resubmission regressions were then added, reproduced and fixed. The complete final backend suite passed all 335 tests; the final backend was repackaged and its packaged workflows/manifest rechecked using the unchanged, already validated frontend assets. The final total is **488 automated tests**, without counting repeated runs or overlapping focused suites twice.

The first integration run exposed duplicate Created Scholar audit events when the new program resolver flushed only its pending program. The resolver now flushes the pending record set together, preserving the existing exactly-once history assertions. Neither this assertion nor the education regression assertions were weakened; no failing check was skipped.

## Browser verification

The final packaged application ran against a disposable fixture with 65 synthetic scholars, 51 requirement-follow-up profiles, 65 annual Summer grants and a Unicode program name. Verified sign-in, the dashboard counts and most-recent list, a 116-action total spanning pages, page 2 → CCS filter → page 1 with five matching actions, and the 65-scholar directory. A single scholar can contribute more than one action, so the action total differs from the scholar count.

The program catalog displayed the existing Unicode program, created a separate copy and exposed both recorded IDs in the grant picker. Profile remarks, Bachelor education, 5.5-year tenure and the three-year grace assessment displayed correctly. Cancelling the grant editor presented the discard confirmation and allowed navigation afterward. The Guide explained complete app printing and native Ctrl+P. No browser console errors were captured. The owned test server exited through its normal authenticated exit control.

See the catalog screenshot (local historical evidence; excluded from this source snapshot) and browser evidence (local historical evidence; excluded from this source snapshot). A requested narrow viewport did not take effect in the browser provider, so this run does not claim mobile breakpoint acceptance. Native printer preview/output was not available.

## Database and update preservation

The development installation replaced only the executable, `_internal`, runtime manifest and generated frontend assets. It preserved all 388 first-party source files at the installation boundary and did not replace or migrate the working database. Documentation finalization after installation is separate from that boundary check.

The before/after database SHA-256 was identical: `0edc991d898212ea21dd0345ba4dd2295a0b4d0479cad55d2e9df6af57a28586`. The protected snapshot, retained runtime and verified receipt are recorded in INSTALLATION_MANIFEST_0.5.16.json (local historical evidence; excluded from this source snapshot). Protected migration 12 runs on the next normal launch; installation did not infer that the live database was already schema 12.

The separate synthetic Office update preserved two scholars, three annual grants, two accounts, two education entries and both Summer records, including existing IDs, fields, program references, roles and authentication. The database hash was unchanged during runtime replacement; migration subsequently advanced the copied database from schema 11 to 12. See UPGRADE_VALIDATION_0.5.16.json (local historical evidence; excluded from this source snapshot).

Published folder: `<developer-home>\Desktop\Project\Releases\Cathedra-FSDP-0.5.16-Update`. Its 142 runtime files match the tested manifest. It includes update instructions and an empty installation seed, with no working data folder or accounts. Use the included updater against the existing closed Office installation; do not copy development data or the empty seed over Office records. The previous release was retained during delivery validation. The later owner-requested cleanup removed the obsolete 0.5.15 update payload; protected database backups and runtime rollback archives remain. E: and the actual Office PC were not changed.

Summer remains distinct from 1st/2nd/3rd. Optional dates and fields, the eight-college/Staff rules, profile and annual-grant remarks, historical IDs/history and program-specific graduation/payback precedence are preserved. Only Name and Program Applied remain essential business fields. Migration 12 adds program identity and education edit intent; it does not merge or rename historical programs.

## Evidence and remaining acceptance

General run details and log hashes are recorded in REGRESSION_VALIDATION_0.5.16.json (local historical evidence; excluded from this source snapshot). Security-specific tenure test evidence and the fix report were retained through the security artifact service, separately from the sealed original scan.

The subsequent cleanup receipt (local historical evidence; excluded from this source snapshot) records removal of test/lint/Python caches, an empty generated build folder, six inactive launcher temporary profiles and the obsolete update package. Before/after hashes confirmed 387 existing source/documentation files and 2,164 protected data/recovery files unchanged at the cleanup boundary. Both 142-file runtime manifests passed afterward. This cleanup annotation and receipt were then added separately; no application code was changed.

Actual Office-PC cold startup and update acceptance, native printing, clean-PC execution, signing, device encryption, remote CI and assistive-technology checks remain open in [Office acceptance](current/OFFICE_ACCEPTANCE.md). The delivery checks above did not measure coverage or refresh dependency advisories; follow-up coverage is recorded below. The two backend warnings concern dependency API deprecations and did not fail the suite. The application is locally tested and packaged; those external checks remain the practical deployment limits.

## Follow-up verification — 11 October 2026

The follow-up source review checked every confirmed finding, **F01–F15**, against its current implementation and regression tests. No surviving instance of a reported defect was found. All 388 source files captured before testing still matched the selected checkout before the documentation update. This follow-up changed only the review status and this validation record; no application source or regression tests needed further changes.

Checks ran in a disposable source copy with temporary test data:

| Check | Follow-up result |
|---|---|
| Complete backend suite with branch coverage | `python -B -m coverage run --branch --source=app -m pytest tests -q`: **335 passed**, 161.20 seconds; two dependency deprecation warnings |
| Backend coverage threshold | `python -B -m coverage report --fail-under=87`: **passed**, **91%** total coverage and **98%** for `profile_values.py` |
| Focused tenure and profile regressions | **35 passed**, including oversized legacy saves, preserved notes, numeric/null precedence and normal migration behavior |
| Python static checks | Ruff passed for application, tests and the launcher/update/maintenance Python modules |
| Complete frontend suite | `npm test`: **153 passed in 29 files**, 97.03 seconds |
| Frontend test type check | `npm run test:typecheck`: **passed** |
| Frontend application type check and production build | `npm run build`: **passed** |

The combined backend and frontend result is **488 passing tests**. Source inspection independently confirmed the bounded tenure boundary, manual education-year intent, Unicode program identity and race handling, print scope/page/total fixes, catalog and copy-navigation workflows, conservative graduation parsing, runtime/shell prerequisites, retired migration helper and meaningful endpoint checks.

The original comprehensive review now links to this completed remediation record at its start, while retaining its historical 0.5.15 findings. The Codex Security workbench's earlier generation attempt remains `failed` because the security fix was already present and no additional patch was generated; that workflow status does not indicate a remaining tenure vulnerability. No new workbench Apply, Verify or closure action was performed.

Actual Office-device checks, native print output and the separate improvement suggestions remain outside this source/test verification. No package was rebuilt or installed on the Office PC during this follow-up, and no live database was modified.
