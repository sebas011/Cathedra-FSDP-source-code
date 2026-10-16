# Validation of 0.5.11

This release implements the local improvement plan from the October 7 audit. The staged work is delivered as one tested update; separate proposed Release A/B/C numbers were not published.

## Implemented

All eleven concrete audit findings have corrections: both Windows shell versions, persistent removal/restoration of generated education, program revision checks, account-scoped retry-safe creation, password hash upgrades, required pre-migration snapshots, bounded dashboard/detail pages, complete exports, archived unused CSS, Bachelor abbreviations, and one weekly backup-due policy. Additional work includes private rotating diagnostics, maintenance history surviving restore, missing-data filters, protected updater/recovery, coverage gates, signing integration, current guides and dependency inventory.

Migration 9 adds program revisions, request receipts and education suppression records. It is additive. Pending startup migrations require a protected, verified snapshot. The updater preserves the selected installation's database and never substitutes project data.

## Evidence

- 187 backend regression tests passed. 117 frontend/component tests passed, including five expanded accessibility checks. Static checks, source/test type checks and production build passed.
- Measured backend statement/branch coverage was approximately 89%; a regression floor of 87% is configured. Subprocess launcher coverage is supplemented by packaged scenarios, not represented as full in-process coverage.
- Both Windows PowerShell 5.1 and PowerShell 7 completed packaged create, backup, restore, session invalidation and graceful shutdown checks on this development PC.
- A private snapshot of the provided E: Office reference (0.5.8) was migrated and checked: 126 existing scholars and 126 grants remained, existing values were compared, integrity was OK and no foreign-key errors were found. E: was not updated.
- Packaged browser checks used synthetic data only: dashboard summaries, lazy reports, report results/page controls, profile contract assessments, education edit/save and keyboard confirmation. A narrow mobile profile view was readable without horizontal page overflow. Token contrast checks passed. This is not a full screen-reader certification or a completed 200% browser-zoom test.
- The unavailable lockfile version for dom-accessibility-api was corrected to the existing verified 0.5.16 archive. Clean locked dependency installation passed. The refreshed npm audit reported zero vulnerabilities; OSV reported none for 36 pinned Python packages. Advisory results are time-specific, not proof of absence.
- The final packaged updater rehearsal from 0.5.8 to 0.5.11 passed with an unchanged database fingerprint and isolated workflow verification. Earlier injected/observed failures restored the old runtime without replacing the database. Child DLL/module paths are isolated and maintenance errors do not block on hidden dialogs.

The fresh-database benchmark exposed a planner-dependent graduation lookup. It was replaced with a distinct scholar/program graduation join, with a regression ensuring repeated graduations cannot multiply assessment rows or hide a different program's overdue grant.

## Remaining acceptance work

The actual Office PC has not been accessed or updated. Test its first launch and recent records after running the update there; verify an off-device restore on an isolated destination. Device encryption/protection remains unverified. Organization-controlled signing, an authorized private remote with an actual CI run, full keyboard/zoom/screen-reader acceptance, and independent clean-PC acceptance remain open. The internal executable is unsigned.

The dependency inventory records versions/licences/hashes; formal SBOM conformance is not certified. Two dependency deprecation warnings in backend tests and a deprecated frontend test dependency remain tracked. No remote repository has been created or published.

See PERFORMANCE_0.5.11.md for the completed packaged scale results; raw evidence and installation receipts are retained privately with the audit. Directory and dashboard budgets must be assessed separately from heavier report detail work; this release does not claim every large report completes within two seconds.
