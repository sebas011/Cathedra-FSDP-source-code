# Cathedra FSDP 0.5.3 validation

## Repairs

- Pending backup, restore, export and recovery-review operations use the shared navigation, unload, logout and desktop-exit guard. Conflicting maintenance controls stay disabled through the operation and status refresh. Successful restore explicitly permits its sign-out redirect; failed operations release the guard and retain feedback.
- Readiness commits only the newest request result and ignores obsolete/unmounted requests. Refresh is disabled while the current check is pending.
- Backup operation errors and status-load errors are separate. Export failures do not change a healthy database heading or badge; status refresh failures remove healthy feedback.
- Grant editor validation rejects unsupported new terms before closing. Unchanged imported terms are preserved only for the same saved grant, compared with the immutable server-loaded baseline.

## Verification

- 134 backend tests passed; two existing dependency deprecation warnings.
- 109 frontend tests passed across 18 files, including 15 new maintenance/readiness/editor regression cases.
- Regression coverage includes route navigation, beforeunload, logout, desktop exit, successful restore sign-out, failed restore recovery, child review pending propagation through refresh, independent health feedback, StrictMode response ordering, valid aliases, and unchanged/modified imported terms.
- Frontend application/test TypeScript, backend static checks, pinned build inputs and production build passed.
- Desktop package build and packaged persistence/backup/restore/session-revocation/shutdown checks passed under Windows PowerShell 5.1 with Python and Node absent from PATH.
- Installation completed. Installed synthetic workflow/integrity and standalone backup/restore checks passed; source and runtime hashes match staging, and the office database hash is unchanged. Access restrictions were reapplied; final audit is saved in evidence-0.5.3/permission-final-053.log.

## Installation and recovery

No new database migration is introduced. Any earlier pending migrations through 5 still run at the next normal office launch. The installer does not launch against office data. It verifies a database snapshot, saves source/runtime rollback archives, copies tested source and package together, reapplies access restrictions while retaining the installer data lock, and checks source/runtime hashes and unchanged office database hash.

Artifact paths and final results are recorded in docs/INSTALLATION_MANIFEST_0.5.3.json. Evidence is saved in docs/evidence-0.5.3. A separate clean-PC run and comprehensive contrast/screen-reader audit are not certified by the local tests.

Skills used: brainstorming, senior-frontend, and code-reviewer from C:\Users\rodia\Desktop\AI\.claude\skills. Design: docs/plans/2026-10-03-frontend-fixes-design.md.
