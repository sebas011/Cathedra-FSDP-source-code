# Development and verification

Install development dependencies with `python -m pip install -r backend/requirements-dev.txt -r desktop/requirements-build.txt -c backend/constraints-win-py314.txt`. Runtime requirements exclude test and quality tools. Frontend formatting uses the exact locked Prettier version: `npm run format` and `npm run format:check`. Python formatting uses `python -m ruff format backend/app backend/tests desktop/run_cathedra.py desktop/office_update.py desktop/maintenance_checks.py`; CI checks the same scope. `npm run test:coverage` records frontend coverage; the measured acceptance floor is maintained in the Vitest configuration. A remote green run is separate evidence from local checks.

Publisher trust: the package manifest detects runtime corruption and the updater refuses mismatches. It does not independently authenticate the publisher. For an unsigned ZIP, obtain its SHA-256 digest through the trusted release channel before extraction and compare it with `tools/verify-download.ps1 -Archive '<download.zip>' -ExpectedSha256 '<published digest>'`. A checksum shipped only inside the same untrusted download is insufficient. Organization Authenticode signing remains available when a trusted certificate is supplied. Pinning action revisions and using read-only workflow permissions follows [GitHub's guidance](https://docs.github.com/en/actions/reference/security/secure-use); the exact local formatter follows [Prettier's installation guidance](https://prettier.io/docs/install).

Local login throttling intentionally precedes password verification and cannot isolate a malicious process running as the same Windows owner. If legitimate login is temporarily throttled, close Cathedra normally and reopen the service or wait for the displayed retry interval. Do not change the database or bypass password checks. Keep separate Windows accounts and the approved installation permissions. Raw database backups contain private records and account hashes; store off-device copies privately. Passphrase-encrypted backup support requires a separate key/recovery design.

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

Local source history is retained separately. A reviewed 0.5.19 source snapshot was published to https://github.com/sebas011/Cathedra-FSDP-source-code on 14 October; subsequent working changes require a separately verified source publication. Databases, logs, local credentials, generated packages and identifiable office-import notes are excluded. After installing updated source on this development PC, run the locked dependency installation before development; the packaged Office app does not require it.

Use `tools/update-office.ps1` with a verified current update package. The supported updater uses the current transactional upgrade service for its private rehearsal. Migration preservation is covered by current backend upgrade tests. The retired `tools/verify_office_migration.py` remains as a safe-stop compatibility helper; never use it as an Office acceptance gate.

For an additional read/export consistency check, use `tools/check_records.py` with a private database copy and a new, non-existent workspace directory. It creates another SQLite backup using a read-only source connection and runs the app only against that isolated workspace. Its four endpoint checks reconcile scholar and grant identities, complete report/action totals, summary status totals, payback grant/distinct-scholar totals and all report CSV section headers from `docs/current/EXPORT_CONTRACTS.json`. HTTP 200 alone does not pass. An empty database is valid only when the saved identity snapshot is also empty. Intended schema additions and classification changes are permitted; scholar/grant identities and grant ownership must be preserved.

For 0.5.17/schema 13, summary and department JSON expose equal `completed`/legacy `graduated` totals while status-count maps and CSV use Completed once. The checker reconciles both aggregate values against canonical outcomes; it does not add them. Directory/report CSV append Graduation Date and Case Status. Office Log has its own ordered export contract and append-only API. Its optional UUID Idempotency-Key binds an immutable normalized payload to the author; do not substitute an arbitrary retry payload after an uncertain response. Test log create/read/export, linked-scholar deletion snapshots, recovery inclusion and role/session enforcement only with synthetic data.

```powershell
python ./tools/check_records.py --app '.' --database '<private-copy.db>' --workspace '<new-isolated-directory>'
```

Successful responses are saved as private `responses.json` inside that workspace. They can contain scholar data and must not be committed or shared publicly. This developer helper does not replace the portable Office smoke test or intended-PC acceptance.
