# Development and verification

Use Windows x64, PowerShell 7, 64-bit Python 3.14.7 and Node 26.8.1 with the checked-in constraints/lockfile. Do not use Office databases in tests or source control. The build script verifies runtime versions, platform and Python pointer width before installing dependencies or packaging. The runtime-only check permits dependency installation; the following check verifies installed package pins. Build and development package verifiers require PowerShell 7 explicitly. Portable Office smoke/update commands also support Windows PowerShell 5.1.

```powershell
pwsh -File ./desktop/build-split-release.ps1 -Python '<python-path>' -Node '<node-path>'
./tools/office-smoke.ps1 -Package './desktop/release/Cathedra FSDP'
```

Run the packaged workflow in both Windows PowerShell 5.1 and PowerShell 7. It uses temporary synthetic data and checks startup, setup, scholar/grant creation, backup, restore, session revocation and graceful shutdown without developer runtimes on PATH.

The build includes backend regressions/static checks, locked npm installation, test/source type checks, frontend regressions/build, clean-seed creation and manifest verification. CI configuration exists; actual remote CI runs require an authorised repository destination.

The bundled executable supports --benchmark <new-directory> --maintenance-result <private-json-file>. It generates file-backed synthetic 1k/5k/10k datasets and records timings, query count, response bytes and Windows process working-set high-water marks (including setup and preceding checks). Five samples report a maximum rather than an established p95. The intended Office hardware needs its own acceptance check.

Program PUT requires If-Match from ProgramRead.revision. Scholar creation supports Idempotency-Key as a UUID; clients must retain the original key and immutable payload after uncertain responses. The ledger stores an account-scoped digest and non-reusable result ID, not a second scholar payload. Keys are not automatically pruned. Partial education omission preserves entries; submitted removal of an existing generated entry records suppression. Restore IDs must belong to existing suppressions.

Schema upgrades reserve a SQLite write transaction across validation, verified snapshot and migration. Snapshot failure stops writes; migration failure rolls back the explicit transaction. Startup and updater rehearsal share this service. Runtime file replacement and live data migration are separate operations.

Optional organisation code signing: pass -SigningCertificateThumbprint with a certificate already in the current user certificate store. No signing secret is embedded in source or packages. Without a certificate, keep the package labelled as an unsigned internal build.

Important acceptance: keyboard/zoom/contrast and screen-reader checks, clean intended Office-PC launch, encryption status, off-device restore rehearsal, actual private CI and organisation signing remain evidence requirements. Passing automated tests alone does not certify them. Known test-client dependency deprecation warnings are tracked and do not affect the packaged application.

The current source snapshot is published at https://github.com/sebas011/Cathedra-FSDP-source-code. Local development history and Office data are not published. Databases, logs, local credentials, generated packages and identifiable office-import notes are excluded. After installing updated source on this development PC, run the locked dependency installation before development; the packaged Office app does not require it.

The old `verify_office_migration.py` and fixed-path `install_tested_fsdp.ps1` are historical tools. The supported updater uses the current transactional upgrade service for its private rehearsal. Migration preservation is covered by current backend upgrade tests; never use the retired comparison helper as an Office acceptance gate.

For an additional read/export consistency check, use `tools/check_records.py` with a private database copy and a new, non-existent workspace directory. It creates another SQLite backup using a read-only source connection and runs the app only against that isolated workspace. Its four endpoint checks reconcile scholar and grant identities, complete report/action totals, summary status totals, payback grant/distinct-scholar totals and all report CSV section headers from `docs/current/EXPORT_CONTRACTS.json`. HTTP 200 alone does not pass. An empty database is valid only when the saved identity snapshot is also empty. Intended schema additions and classification changes are permitted; scholar/grant identities and grant ownership must be preserved.

For 0.5.17/schema 13, summary and department JSON expose equal `completed`/legacy `graduated` totals while status-count maps and CSV use Completed once. The checker reconciles both aggregate values against canonical outcomes; it does not add them. Directory/report CSV append Graduation Date and Case Status. Office Log has its own ordered export contract and append-only API. Its optional UUID Idempotency-Key binds an immutable normalized payload to the author; do not substitute an arbitrary retry payload after an uncertain response. Test log create/read/export, linked-scholar deletion snapshots, recovery inclusion and role/session enforcement only with synthetic data.

```powershell
python ./tools/check_records.py --app '.' --database '<private-copy.db>' --workspace '<new-isolated-directory>'
```

Successful responses are saved as private `responses.json` inside that workspace. They can contain scholar data and must not be committed or shared publicly. This developer helper does not replace the portable Office smoke test or intended-PC acceptance.
