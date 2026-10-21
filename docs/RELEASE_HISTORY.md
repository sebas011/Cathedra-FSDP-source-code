# Cathedra FSDP 0.5.23

Google Sheets has a dedicated fifteen-column report: No., Name, Age, Tenure, Department, Rank/position, Previous degree, Program, Delivering HEI, Grant type, Date started, Date ended, Extension, Status, Remarks. Grants remain grouped beneath each scholar. Saved dates take priority over recorded academic periods, education entries remain readable, and profile/grant remarks share one labeled cell. CSV exports and schema16 are unchanged. Adds a detailed Google setup/troubleshooting guide and fixes its in-app link. See [validation](VALIDATION_0.5.23.md), the [plan](plans/2026-10-21-google-reporting.md) and [Google setup](GOOGLE_SHEETS_SETUP.md).

# Cathedra FSDP 0.5.22

Calendar years stay literal and record text editing preserves the cursor. Grants add Incomplete, optional program completion deadlines/allowed years and separate payback payment progress. Annual copies retain recorded completion rules in the same application; later applications clear them. Schema16 adds three nullable facts without rewriting records. Administrators can manually replace a separate Google reporting tab after one-time Desktop OAuth setup; no hosting is needed. See [validation](VALIDATION_0.5.22.md), the [plan](plans/2026-10-17-completion-and-cloud-reporting.md) and [Google setup](GOOGLE_SHEETS_SETUP.md).

# Cathedra FSDP 0.5.21

Adds verified pre-delete recovery and bounded daily snapshots, private error references, server-enforced inactivity protection, UTF-8 CSV signatures and frozen historical migration helpers. Schema15 adds nullable session activity time. See [validation](VALIDATION_0.5.21.md).

# Cathedra FSDP 0.5.20

Office Log entries close after confirmed saving and stack in compact disclosures. Scholar profiles track hard-copy and soft-copy availability independently. Grants support separate repeat applications with annual entries and application-specific completion/payback, plus optional Degree, Certification and Enhancement categories. The directory sorts names consistently before pagination. Schema14 is additive; existing records remain authoritative. See [validation](VALIDATION_0.5.20.md) and [current documentation](current/README.md).

# Cathedra FSDP 0.5.19

Corrects the Windows Office updater's tool identity/counting and directory enumeration. A verified existing installation with unlisted runtime/tool leftovers receives a clean manifest-only preceding-runtime archive, while all leftovers are separately preserved under its private updates directory. Missing or altered declared files, linked paths, unreadable trees and unlisted incoming bundled files remain blocked. Working database replacement is prohibited. Failure receipts now identify the phase, selected root and affected paths; maintenance failures exit quietly. Production packaging requires database-free verification by the actual bundled updater. Schema 13 and CSV/business features remain unchanged. See [the repair plan](plans/2026-10-14-updater-inventory.md) and [validation](VALIDATION_0.5.19.md).

# Cathedra FSDP 0.5.18

Readable directory, Dashboard detail and payback CSV exports group annual grants under each scholar. The first row contains profile information and the first grant; continuation rows contain the remaining grant information. All matching grants retain their dates, outcome, case and remarks. Source/provenance columns are removed from directory/education exports. Full filtering, formula protection, Unicode and data-preserving Office updates remain. No database migration is added. See [the CSV plan](plans/2026-10-13-csv-readability.md) and [validation](VALIDATION_0.5.18.md).

# Cathedra FSDP 0.5.17

Implements the twelve approved 12 October findings: uppercase newly entered record text, education linked to Completed programs, grant status beside final remarks, academic-year formatting, optional graduation dates, icon actions, visible payback selection, numeric wheel protection, date-free annual grant copying, collapsible full grant history, separate Open/Closed case tracking and an append-only Office Log for document receipts/transfers. Migration 13 normalizes the former Graduated outcome to Completed and adds grant date/case tracking plus Office Log storage. Account credentials, historical program identities, education edit intent, recovery safeguards and Summer remain intact. See [the implementation plan](plans/2026-10-12-user-findings.md) and [validation](VALIDATION_0.5.17.md) for actual verification and delivery status.

# Cathedra FSDP 0.5.16

Addresses F01–F15 from the comprehensive review: bounded tenure inference, persistent education-year clears/corrections, Unicode-consistent program identity and concurrent catalog writes, complete scoped printing, accurate Dashboard pages/action totals, existing-program selection and administrator catalog management, pending-copy navigation protection, conservative undated degree claims, and build/support tooling checks. Migration 12 adds canonical program keys and year-edit intent without merging historical programs or changing their IDs. Summer remains supported. See [validation](VALIDATION_0.5.16.md) and [implementation plan](plans/2026-10-10-review-remediation.md).

# Cathedra FSDP 0.5.15

Corrects graduation evidence attribution, calendar-date checks and dotted degree abbreviations; applies payback attention consistently before pagination and in CSV; preserves Summer and schema 11. Existing achievements and manual corrections remain intact. Adds read-only private education review, current export contracts, reconciled product/technical rules and explicit Office acceptance evidence. See [validation](VALIDATION_0.5.15.md) and [plan](plans/2026-10-09-audit-corrections.md).

# Cathedra FSDP 0.5.14

Implements the ten profile/grant findings: conservative graduation remark education and years, automatic Faculty/Staff/Unknown, reorganized forms and profile remarks, compact program duplication, pending repayment contracts and Transferred, annual copying under one program and collapsible grant history. Migration 11 preserves source grants, education corrections and removals. See [validation](VALIDATION_0.5.14.md) and [implementation plan](plans/2026-10-09-findings-profile-grants-design.md).

# Cathedra FSDP 0.5.10

Implements the 15 user findings: explicit Faculty/Staff classification, draft-based education entry, automatic education records for graduated programs, latest-grant scholar status, Summer, Thesis Aid and Did Not Avail. Removes standalone monitoring and breadcrumbs. Name words use prefix search. Contract end periods are separate from graduation and the three-year grace period. See docs/VALIDATION_0.5.10.md and docs/plans/2026-10-07-user-findings.md.

# Cathedra FSDP 0.5.8

Fixes the first-launch local connection failure caused by Edge process relaunch. See docs/VALIDATION_0.5.8.md. No database migration.

# Release 0.5.7 — Dashboard charts and presentation

Reorganized Dashboard summary, department count charts, grant outcome donut with percentages, grant-type comparison, recent scholars and follow-up. Embedded reporting/export/print and shared filters remain. The institutional green is preserved. No database migration or data changes are required. See docs/VALIDATION_0.5.7.md.

# Release 0.5.6 — Scholar profiles and Dashboard reporting

Profiles support separate education entries and numeric tenure in years. Administrators can duplicate programs and grants, then set a distinct academic year for each grant. Terms are stored as 1st, 2nd or 3rd; grant dates are optional and removed from the editor. Reports, CSV exports and printing are integrated into the Dashboard, alongside the 10 latest scholars. The legacy grant review and Needs Verification modules are removed. Migration 6 preserves retained records and accounts, converts prior education and readable tenure, and keeps unclear historical values in notes. See docs/VALIDATION_0.5.6.md.

# Release 0.5.5 — FSDP feature isolation

FSDP-only guide and audit logic; explicit FSDP backup-table allowlist; record-entry business validation requires only Name and Program Applied. Optional fields remain editable without chronology, age-range or academic-period restrictions. Storage-compatible types, authentication, ownership, revision and restore safety checks remain.

# Cathedra FSDP 0.5.4

Reference-driven UI redesign: light administration workspace, original green, scholar identity and section navigation, consistent forms and tables, visible report filter chips, grouped requirement monitoring, account role/status presentation and an offline searchable guide. Core APIs, permissions, persistence and recovery safeguards are preserved. Calendar functionality is excluded.

# Cathedra FSDP 0.5.3

Open **Cathedra FSDP.exe** in this folder. Existing FSDP credentials remain valid; sign in again after the update.

Release 0.5.3 protects pending maintenance operations, prevents stale readiness results, separates operation errors from database health, and validates grant terms before leaving the editor. No new schema migration is required. See docs/VALIDATION_0.5.3.md.

Release 0.5.2 supports separate scholars with identical names, replaces entire grant and requirement registers in one save, and reconciles manual follow-up actions and scholar totals. Migration 5 removes only the name-only unique index. The earlier identity, revision, and account safeguards remain active. Release 0.5.1 fixed scholar identity reuse, concurrent program revision loss, and case-equivalent account creation. Its additive schema migration preserves existing records and history. If existing accounts differ only by letter case, startup stops for administrator review instead of merging or renaming them. See docs/plans/2026-10-03-integrity-fixes-design.md and docs/VALIDATION_0.5.1.md. For the workflow fixes, see docs/plans/2026-10-03-workflow-fixes-design.md and docs/VALIDATION_0.5.2.md.

Release 0.4.0 adds advisory similar-name checks before saving, administrator-only scholar change history, seven-day backup reminders and explicit recovery-review confirmations. No identities are merged automatically. See docs/QUALITY_IMPROVEMENT_PLAN_0.4.0.md for the implementation plan and docs/VALIDATION_0.4.0.md for release evidence and remaining external checks.

Release 0.5.0 consolidates the interface into one green design system, with responsive navigation, structured scholar entry, clearer profiles, accessible chart values and collapsible dashboard/report filters. All existing workflows and permissions remain. See docs/UI_UX_REDESIGN_0.5.0.md for tokens and page specifications, and docs/VALIDATION_0.5.0.md for executed checks.

Keep the executable, _internal, and data together. The office database is data/cathedra.db. Backups contain private personnel data: store them in a restricted location.

Release 0.3.9 introduced complete package verification, Windows product/version metadata and installation-permission safeguards, retained in 0.4.0. Keep VERSION, APP_PRODUCT, release-manifest.json and tools with the executable for office verification. Read docs/RELEASE_READINESS_0.3.9.md and docs/VALIDATION_0.4.0.md before transferring. An encrypted external backup and isolated restore rehearsal are verified; actual separate-PC acceptance remains open.

## Local development

Install Python dependencies in backend/.venv using backend/requirements.txt together with backend/constraints-win-py314.txt on the matching Windows/Python version. Install frontend dependencies with npm ci. No dependency on the Faculty source or original combined project is required.

Start the backend from backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8101
```

Start the frontend from frontend with npm run dev; open http://127.0.0.1:5174. Do not run the desktop app against the same database simultaneously. For disposable tests set CATHEDRA_DATA_DIR to a separate directory.

For a fresh development database, enter the private first-time setup code printed in the backend console. The desktop launcher supplies it automatically. Existing accounts do not need it. Do not share this code or expose the service beyond loopback.

Close an existing desktop or development service before opening the executable. The launcher refuses to reuse an occupied port. Sessions remain only in the current browser session; sign in again after closing the window.

Edge app windows shut down their own local service when closed. If Edge is unavailable and Cathedra opens in a normal browser, use Exit Cathedra before closing that tab; ordinary browser tabs do not provide a reliable window-lifetime signal.

Build with desktop/build-split-release.ps1 using a dedicated Windows/Python 3.14 environment. Use -InstallDependencies to install the constrained requirements first. Packaging checks every pinned Python dependency and installs frontend dependencies from the lockfile. It runs backend/frontend regressions, both TypeScript checks, clean-seed creation and packaged workflow checks. The package includes a release manifest. See docs/AUDIT_REMEDIATION_0.3.8.md for the current plan and acceptance criteria.

Session expiry keeps unsaved work in memory for same-account reauthentication; it does not save or resend it automatically. Refreshing or closing the window still discards an unsaved draft. Wait for submitted saves to finish before leaving. If restore recovery remains unresolved, record operations are blocked until a successful restart restores the protected safety copy.

See docs/FSDP_CLEANUP.md for boundaries, archives and old-backup conversion.


## 0.5.12

Adds whole-profile remarks and CSV support, eight college classifications plus Staff, a spacious Dashboard with vertical charts and guidance moved into the Office Guide, and refreshed scholar profiles. Migration 10 preserves original staff affiliations in profile remarks and existing grant notes.

## 0.5.13

Uses a mix of Dashboard charts: college comparisons as vertical bars, current scholar statuses as a doughnut, and grant types as a pie. Counts and percentages accompany the composition charts; guidance stays in the Office Guide. No database migration is added.
