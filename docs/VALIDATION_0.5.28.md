# Cathedra FSDP 0.5.28 verification

Date: 31 October 2026 (Asia/Manila). Source schema: 19.

The shared-workspace implementation uses two separate Google spreadsheet files and explicit reviewed synchronization. Offline tests use fictional records and simulated Google APIs. Subsequent owner-approved live setup created the bridge and two empty files; no Office records have been uploaded.

## Observed checks

- Two independent SQLite computers: complete business-record round trip, retained local IDs/accounts, independent edits, explicit same-scholar conflict choices, revision rejection, immutable retry, lost-response recovery, malformed-result recovery, local-apply failure, restored-checkpoint review and Office Log identity retention.
- API: pending operations block business writes and disconnect; shared mode blocks the older report import/export controls; canonical reporting excludes unsent local changes and includes profile remarks.
- Transport: only the configured Google deployment receives the credential; ContentService redirects use a fresh GET without credential/body, and non-Google redirects are rejected.
- Google script offline tests: private/protected separate files, atomic storage/receipt changes, stale writers, exact receipt replay, unknown outcome handling, revocation, sharing/protection drift, Unicode chunking and literal reporting cells.
- Final frontend run: all 308 tests passed, including 14 shared-workspace tests. Coverage: 86.66% lines, 76.69% branches. Test and production types, formatting and production build passed.
- Final backend run: all 703 tests passed. Combined statement/branch coverage was 90.26%, exceeding the 87% release threshold. Static checks and formatting passed. Regression found and fixed copied cloud identifiers in annual-grant duplication; copies now get new identities. Historical fixtures accurately omit schema-19 additions when testing older migrations.
- All eight production Google-script contract tests passed offline. The live Google response omits false/zero defaults for protected ranges. The checker now accepts those defaults while still rejecting warning-only, bounded, partly unprotected or non-owner-editable ranges. This compatibility fix changes only the supplied Google script and its tests; the native runtime is unchanged. Build inputs remain constrained; no new third-party dependencies were added.
- Production browser acceptance with fictional records: pending indicator, complete conflict comparison with program names, explicit choice, confirmation and successful sync verified. No browser console errors or horizontal overflow observed. Screenshot (local historical evidence; excluded from source snapshot).

## Native delivery and acceptance

Native build and persisted-workflow checks passed with pinned inputs. PowerShell and the bundled Python verifier independently confirmed all 152 runtime files. The bundled inventory check did not access the database. See [package evidence](analysis/LOCAL_PACKAGE_VALIDATION_0.5.28.json).

A fictional 0.5.27/schema-18 installation updated through the supported Windows PowerShell 5.1 command to 0.5.28/schema-19. Its nine scholars, twelve grants, two accounts, historical values/IDs, Summer records, history details and encrypted dummy Google configuration were retained. Database bytes were unchanged during runtime replacement; protected snapshot and migration rehearsal passed. Native startup, shutdown, CSV, daily/deletion backups and new history were verified. See [upgrade evidence](analysis/UPGRADE_VALIDATION_0.5.28.json).

Guarded development installation passed. The retained working database and encrypted Google connection were byte-for-byte unchanged during runtime replacement. A private copy rehearsed its schema-16-to-19 upgrade, preserving every existing field and migration-history row; the working database itself migrates protectively at its next normal startup. Source files were preserved during installation. See [installation evidence](analysis/LOCAL_INSTALLATION_VALIDATION_0.5.28.json).

Office delivery assembly verifies every runtime hash, the empty schema-19 seed, absence of working records and credentials, and a byte-for-byte ZIP round trip before copying a new release folder. The owner setup files are supplied under `google/shared-workspace` with a top-level setup guide. The existing Office database must be retained when updating. The refreshed delivery includes the Google protected-range compatibility fix.

Owner-approved live authorization and deployment version 4 passed. Initial read-only checks confirmed owner-only storage, three protected tabs, revision zero, no records, no registered devices and an uninitialized workspace. An unregistered device read was rejected without returning records. Subsequent explicit approval registered the development PC with initialization disabled. Authenticated status and read requests passed production snapshot validation; storage remained empty and uninitialized. The working database bytes were preserved, no local business records were replaced, and the development PC has not joined the workspace. See [sanitized live evidence](analysis/LIVE_GOOGLE_SETUP_0.5.28.json). Initial cloud population must be performed explicitly from the authoritative Office PC. The [0.5.28 Office release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.28) and its public download are verified. The [exact-source Windows workflow](https://github.com/sebas011/Cathedra-FSDP-source-code/actions/runs/41258977591) passed the measured 703 backend, 308 interface and eight bridge tests, dependency checks and native packaging. See [publication evidence](analysis/GITHUB_PUBLICATION_VALIDATION_0.5.28.json). Actual Office-PC acceptance remains separate.

Plan: [shared workspace](plans/2026-10-31-shared-workspace.md). Protocol: [shared contract](current/SHARED_WORKSPACE_PROTOCOL.md). Owner setup: [Google bridge guide](../google/shared-workspace/README.md).
