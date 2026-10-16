# Validation: 0.5.19

Implementation, local verification, development installation, Office-folder publication and GitHub delivery completed **14 October 2026, Asia/Manila**. Release **0.5.19**, schema **13** unchanged. Actual Office-PC retry remains separate.

The [updater inventory plan](plans/2026-10-14-updater-inventory.md) addresses inconsistent Windows tool identity/counting, fail-closed runtime enumeration, clean recovery archives for verified installed residue and clearer maintenance failure receipts. Incoming/new bundled-file integrity remains strict. Only declared runtime files are installed; optional unlisted tool documents/copies cannot substitute for required direct tools and are not installed from the incoming package.

## Diagnosis and implementation

The supplied traceback points to the existing-installation `verify_package(target)` call, before that attempt created a snapshot, journal or replacement. It does not disclose the actual extra filenames on the Office PC. The exact verified 0.5.18 ZIP reproduced a concrete verifier disagreement: changing only a physical tool filename's casing left all manifest bytes/hashes unchanged and PowerShell verified 147 files, while the old Python updater raised the reported inventory error. Nested tool copies also caused disagreement. Old recursive globbing could silently suppress denied subdirectory scans. See reproduction evidence (local historical evidence; excluded from this source snapshot).

Version19 uses consistent Windows identity, the same four required direct tools, complete runtime traversal with link/access failures refused, and diagnostics naming phase, selected root, counts and missing/unexpected paths. Every declared installed file must pass its size/hash checks. Missing or changed declared files cannot enter repair.

An existing installation may have unlisted runtime/tool residue. The updater preserves every such file, with its original relative path, under a private `data/updates/runtime-residue-...` archive. It constructs and verifies a clean manifest-only preceding-runtime archive, stages only declared incoming files, and verifies the final replacement. Residue is retained for recovery rather than executed or merged into the new runtime. The receipt reports archive path, file count and whether residue was repaired. Runtime rollback restores the verified preceding runtime and retains residue archives. The working database is never replaced by this operation.

Maintenance failures now produce a detailed private receipt and quiet exit1. A new `--verify-package` command checks the bundled runtime without selecting a data folder or opening a database. Production packaging requires this actual bundled check, alongside PowerShell and manifest verification. No business-rule/UI/export/schema change is introduced.

## Executed verification

| Check | Observed result |
|---|---|
| Backend regression | **420 passed**, 181.59 seconds; two existing dependency deprecation warnings. |
| Frontend regression | **185 passed** across 32 files, 60.20 seconds. |
| Static/production checks | Ruff includes the updater, launcher, backend and tests; application/test TypeScript and Vite production build passed. |
| Build inputs | Pinned dependencies and Windows x64 Python3.14.7 / Node26.8.1 verified. |
| Packaged runtime | **147 files** verified, clean schema13 seed, persistence/authentication/backup/restore/normal shutdown passed. The actual bundled verifier passed147 with `database_accessed: false`. |
| New regressions | 26 inventory/recovery and four maintenance-receipt cases included in the full run. Windows PowerShell/Python case/slash parity, duplicate aliases, nested tools, missing required entries, corruption, links and complete/fail-closed scans passed. Preflight failures preserve synthetic DB/state; residue copies, clean archives, rollback and failure handling passed. |
| Frozen pristine upgrade | Native Windows PowerShell5.1 version18/schema13 to version19/schema13 passed on disposable Office-style paths. Protected snapshot/rehearsal, prior failed receipt, runtime manifests and database bytes retained. |
| Frozen residue upgrade | Three unlisted old runtime/support files archived byte-identically at original relative paths; clean old/new runtime checks passed. Native explicit rollback to18 and retry to19 passed with unchanged database bytes. |
| Frozen CLI/extraction | Checksummed synthetic runtime ZIP extraction and uppercase physical tool/internal directory spelling passed. Unknown incoming bundled file refused with quiet exit1 and selected phase/root/path; no data folder or DB access. |
| Development installation | Runtime19 and retained18 archive verified; fresh-data smoke/restore/shutdown passed. Permissions audit checked6,396 items with no violations. |
| Documentation | Current identities, schema ceiling, local links and export contracts passed. |
| Office/GitHub delivery | Office update folder and private GitHub v0.5.19 release published and verified. ZIP and both supporting assets downloaded back after publication with matching hashes. Version18 packages/assets retained; no working records uploaded. |

There are **605 unique automated tests** in the complete run. Focused reruns are not added. Regression evidence (local historical evidence; excluded from this source snapshot) records actual counts/durations and final build/runtime hashes. No new coverage measurement, dependency-advisory refresh, remote CI run, whole-interface browser certification or actual Office-PC acceptance is claimed.

## Synthetic records and recovery

Both frozen upgrade cases retain three scholars, five annual grants, two accounts, manual education year2019 and three Summer grants. Record IDs, account/password hashes, historical text, every scholar/account API and all CSV bytes were unchanged after normal startup/shutdown, except ordinary login-session metadata. An existing failed-update receipt stayed byte-identical. Database integrity and protected rehearsal passed. The residue case separately proves native runtime rollback and retry. Injected workflow failure is covered by regression tests; the trusted frozen executable was not altered to inject that failure. See frozen upgrade evidence (local historical evidence; excluded from this source snapshot).

## Working development database

The source freeze matched **432 first-party files**. All **434 source/document files** present at the development installation boundary were preserved; later report finalization is intentional documentation work. Only executable, bundled runtime, runtime manifest and frontend build were replaced. Existing old tool bytes were verified/archive-copied from the retained version18 package while incoming tool source files were preserved.

Working database SHA-256 before and after replacement:

`209335cb803578581e7219e1f47c1daf9ea127be208f4c6a14e1c36256df63f0`

The database was neither replaced nor migrated by development installation. The installation receipt (local historical evidence; excluded from this source snapshot) records its protected snapshot and retained runtime. No live Office records were inspected or changed.

## Delivery and Office retry

Verified delivery folder: `C:\Users\rodia\Desktop\Project\Releases\Cathedra-FSDP-0.5.19-Update`, published14 October at20:13 Asia/Manila. Its147-file runtime manifest matches the tested build. Final reports use a separate documentation-only refresh and hash inventory. See folder publication evidence (local historical evidence; excluded from this source snapshot).

Private [GitHub v0.5.19 release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.19) published at20:15 Asia/Manila. All three final assets downloaded back and hash matched. ZIP contains152 files:147 runtime files, manifest, essential Office documents and ASUS-path retry guide. Empty seed has zero scholars, grants, education records, accounts or Office Log entries. Version18 release/assets and the prior documentation commit are retained; only four delivery documents were updated with a normal fast-forward push. See GitHub evidence (local historical evidence; excluded from this source snapshot).

ZIP SHA-256: `69c5dd80ef6f79ba870c8d774d4bc3f1231fe933d6eb17b8b94896742e067915`.

The corrected ZIP contains the tested runtime, essential Office guides, clear two-folder instructions and `docs/OFFICE_RETRY_0.5.19.txt`. Keep the user's original Office folder `C:\Users\ASUS\AppData\Local\Cathedra-FSDP` and its authoritative `data\cathedra.db`. Run the new updater against that folder with Cathedra closed. A preflight failure alone does not warrant deleting/resetting a journal or restoring an older database. Existing unfinished recovery state still requires supported recovery; new failures now identify the selected folder and affected paths.

The actual Office PC and E: are not changed by local verification. After retry, confirm version19, scholar total, newest additions, accounts and grants. See [Office Guide](OFFICE_GUIDE.md) and [actual-device acceptance](current/OFFICE_ACCEPTANCE.md).
