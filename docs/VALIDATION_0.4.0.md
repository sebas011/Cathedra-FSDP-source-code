# Cathedra FSDP 0.4.0 — quality and recovery validation

Date: 3 October 2026. Scope: local Windows FSDP only; Faculty and old ScholarDesk are untouched.

## Changes

| Area | Delivered change | Safety boundary |
| --- | --- | --- |
| Scholar entry | Advisory similar-name API and explicit confirmation before save | No auto-merge; existing exact-name/revision guards remain. Failed checks retain the draft and do not write. Form stays disabled while a decision is pending. |
| Scholar profile | Expandable administrator-only paginated history | Actor, time, operation and field names only. Child-removal history survives; unknown old deleted links remain unknown. |
| Backup & Export | Seven-day snapshot reminder and persisted recovery reviews | Copy/restore are administrator attestations tied to a verified backup hash, not automatic external tests. Staff cannot submit or read review details. |
| Directory | Literal wildcard search; existing per-account filter/page/scroll memory retained | No new state framework or changes to saved scholar data. |
| Protection guidance | Read-only Windows diagnostic and office-guide instructions | Never changes encryption or retrieves keys; an inaccessible check is unverified. |
| Release tooling | Fresh isolated backend test directory; explicit import classification | Avoids conflicting Windows ownership between sandbox and release-builder temporary directories. |

## Automated evidence

- Backend: 105 tests passed, including new similarity, literal-search, removed-child attribution, pagination, backup-review validation, stale reminder and staff-denied cases.
- Frontend: 89 existing/new workflow tests plus three directory memory/scroll regressions passed (92 total). Search/page/account isolation, malformed memory and deferred scroll restoration are covered.
- Ruff and TypeScript checks passed before packaging; locked release inputs verified.
- Protected office-copy migration passed versions 1 → 2 → 3 with SQLite integrity and foreign-key checks. Every original value is compared, allowing only explicit institution preservation and new scholar-history attribution.
- Preserved counts: 126 scholars, 126 grants, 92 reusable programs, one account and two existing activity events. Original live database SHA-256 unchanged during rehearsal.
- Desktop package inventory verified all 143 runtime files. Disposable packaged checks passed CRUD, name matching/self-exclusion, paginated scholar history, explicit recovery attestation, restore/session revocation, integrity and graceful shutdown. Consult INSTALLATION_MANIFEST_0.4.0.json and VALIDATION_0.4.0.json for final installation outcomes.
- Installed 0.4.0: all 191 copied source-file hashes and 143 runtime files verified. Restrictive permissions checked across 2,965 installed paths with no violations. Independent installed workflows and Windows PowerShell 5.1 no-Python/no-Node restore/shutdown tests passed. The live database stayed byte-identical and port 8101 is closed after checks.
- Protected pre-update snapshot: data/backups/cathedra-protected-before-0.4.0-20261003-104349.db. Matching source/runtime ZIP rollback locations are recorded in INSTALLATION_MANIFEST_0.4.0.json; archives are restricted to the same Windows owner, SYSTEM and administrators.

## Rollback and remaining acceptance

Keep the protected pre-update database and matching 0.3.9 runtime/source archives. First real launch runs migrations on the live database; reverting afterward requires the matching database snapshot, not only the executable. Do not discard subsequent office edits.

The previous VeraCrypt external backup/recovery rehearsal remains valid historical evidence, not evidence that future backups or this PC's live disk are encrypted. The working-drive diagnostic returned UNVERIFIED because Windows denied status access. Verify protection in Windows Manage BitLocker; never share passwords/recovery keys.

A separate office/clean Windows PC is unavailable; actual installation acceptance there remains open. The build is unsigned; trusted publisher signing and independent review are not represented as completed. Manual narrow-window/zoom/printing acceptance is distinct from automated tests.
