# Download Office updates from GitHub

## Corrected Office updater — 0.5.19

Use the private [0.5.19 release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.19) or [latest release](https://github.com/sebas011/Cathedra-FSDP/releases/latest). Download **Cathedra-FSDP-0.5.19-Update.zip** under Assets and extract it completely. The ZIP includes **UPDATE-INSTRUCTIONS.txt** and **docs/OFFICE_RETRY_0.5.19.txt** with the supplied ASUS Office paths. Select the actual folder containing the executable and tools if extraction creates a second nested folder.

The corrected updater verifies declared files, preserves unlisted installed runtime/tool leftovers privately, creates a clean verified preceding-runtime archive and installs only the incoming manifest's files. Missing/changed files and link/access failures remain blocked. Keep the original Office database at `C:\Users\ASUS\AppData\Local\Cathedra-FSDP\data\cathedra.db`; no working database or records are in this download. Make/download a backup, use Exit Cathedra, run the supplied updater against the original installation and reopen that original app afterward. Success reports version19, verified status and `database_replaced: false`.

Verified14 October2026:605 automated tests, both147-file package verifiers, native PS5.1 pristine/residue upgrades, residue archive hashes, explicit rollback/retry and unchanged synthetic database bytes. The published ZIP and both supporting assets were freshly downloaded and hash matched. See [version19 validation](VALIDATION_0.5.19.md) and GitHub delivery proof (local historical evidence; excluded from this source snapshot). Actual Office retry/record acceptance is still yours to verify after installation.

ZIP SHA-256: `69c5dd80ef6f79ba870c8d774d4bc3f1231fe933d6eb17b8b94896742e067915`.

## Historical 0.5.18 delivery

Cathedra FSDP 0.5.18 was published on 13 October 2026 to the private repository [sebas011/Cathedra-FSDP](https://github.com/sebas011/Cathedra-FSDP).

Use [the latest release](https://github.com/sebas011/Cathedra-FSDP/releases/latest) at the Office PC. Sign in to GitHub with an account that has access to the repository. The current [0.5.18 release](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.18) contains:

| Asset | Purpose |
|---|---|
| `Cathedra-FSDP-0.5.18-Update.zip` | Complete tested Windows application, updater and essential Office guides; 23,231,883 bytes |
| `UPDATE-INSTRUCTIONS.txt` | Standalone copy of the clear two-folder update walkthrough |
| `SHA256SUMS.txt` | SHA-256 checksum of the ZIP |

## On the Office PC

1. Open the latest release and download the named application ZIP under **Assets**. GitHub's **Code > Download ZIP** and **Source code** links contain delivery documentation, rather than the application.
2. Extract the ZIP completely. Inside the extracted `Cathedra-FSDP-0.5.18-Update` folder, open `UPDATE-INSTRUCTIONS.txt`.
3. Open the usual Office app, confirm your newest records, create and download a backup through Backup & Export, then use Exit Cathedra and wait for it to stop.
4. Follow the instructions. The first prompt is the **NEW extracted update folder**; the second is the **EXISTING Office app folder** containing `Cathedra FSDP.exe` and `data/cathedra.db`.
5. Confirm the updater reports `status: verified`, `version: 0.5.18` and `database_replaced: false`.
6. Reopen the **original Office app** through the usual shortcut and confirm its version, scholar total and recent additions.

The Office database remains authoritative. No working development/Office database, account records, backups or local installation receipts were uploaded. The verified empty seed inside `_internal/backend` is only for a new installation. Do not copy a development data folder over Office records. See [Office Guide](OFFICE_GUIDE.md) for recovery and operating details.

## Verification and future releases

The ZIP retains all 147 files from the tested 0.5.18 runtime manifest, plus the manifest and three essential Office documents. Every archived file passed a byte-for-byte round-trip check. The intentional seed has zero scholars, annual grants, education records, local accounts and Office Log entries. Each uploaded asset was downloaded from GitHub both before and after publication and its SHA-256 matched the local file.

ZIP SHA-256: `ac5191981e7f32ac2a7d322c633941acb8a599f29635534e0b8e7d5640a0f92e`.

See GitHub delivery evidence (local historical evidence; excluded from this source snapshot). The repository's default branch contains a download README, instructions, checksums and ignore rules. The application is in Release Assets; the development application's source/history remains in the local project. The original development Git history was not pushed or rewritten.

For each future prepared version, verify and package the application, retain only an empty runtime seed and essential Office guides, publish a new versioned release with a ZIP/checksum/instructions, download and verify its assets, and update the repository's delivery README. The latest-release page remains the stable download location. This publication does not create an automatic build schedule or claim that the actual Office PC has been updated.
