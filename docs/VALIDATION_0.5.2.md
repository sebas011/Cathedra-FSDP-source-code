# Cathedra FSDP 0.5.2 validation

## Implemented behavior

- Complete grant and requirement registers can be replaced in one scholar save. Mandatory current revision, duplicate child-ID validation, ownership checks, and transactional rollback remain active.
- Separate scholars can share an identical name. Advisory name matching and explicit UI confirmation remain; each scholar retains independent IDs, grants, requirements, revisions and activity history. Migration 5 removes only the name-only unique index and retains the searchable name index.
- Manual requirement flags produce a separate follow-up action in the management report and its CSV export. The flag represents additional work beyond the requirement register.
- Department requirement follow-up counts scholars once using the same predicate as the report and analytics totals. UI and CSV explicitly label the unit as scholars.

## Verification

- Backend regression suite: 134 passed, including 13 new workflow scenarios; two existing dependency deprecation warnings.
- Frontend regression suite: 94 passed across 17 files, including explicit identical-name confirmation coverage.
- Backend static checks and pinned build inputs: passed.
- Frontend application and test TypeScript checks, and production build: passed.
- Migration rehearsal: migrations through 5 applied to a separate copy of the office database. Every existing row and relationship was preserved; SQLite integrity and foreign key checks passed. Rehearsal saved at update-archives/0.5.2/migration-rehearsal.db.
- Packaged executable: workflow acceptance checks and prior integrity safeguards passed. Standalone startup, persistence, backup, restore, session revocation, and shutdown passed under Windows PowerShell 5.1 with Python and Node absent from PATH. Installed workflow and standalone checks also passed using temporary synthetic data.
- Installation completed: source and runtime hashes verified, office database hash unchanged, and access restrictions reapplied. Final audit is recorded in evidence-0.5.2/permission-final-052.log.

## Release and recovery

The installer saves source/runtime rollback archives and a verified database snapshot before replacing the stopped application. It verifies all copied source hashes, the runtime manifest, the unchanged office database hash, and reapplies owner/SYSTEM/administrator access restrictions. Installation details and artifact paths are recorded in docs/INSTALLATION_MANIFEST_0.5.2.json.

Migration 5 is applied on the next normal launch; installation does not launch against or edit office records. Earlier migrations run first if the office database has not yet been opened by 0.5.1. Downgrade requires restoring the corresponding older runtime and its pre-upgrade database snapshot; preserve any new records before considering a downgrade.

The standalone package is tested with Python and Node absent from PATH. A separate clean-PC test is not certified by these local checks.


Installer hardening: the permission helper accepts the installer’s existing data-lock stream so the lock remains held during access restriction. A fixture verified that another handle could not acquire the lock after the helper returned. The initial lock-conflict attempt rolled back; the final installation passed.
