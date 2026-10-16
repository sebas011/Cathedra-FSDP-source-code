# Office updater inventory repair — 14 October 2026

Target: release 0.5.19, schema 13 unchanged. The supplied traceback identifies `verify_package(target)` in the existing Office installation at `C:\Users\ASUS\AppData\Local\Cathedra-FSDP`, before snapshot, journal creation or runtime replacement. Incoming 0.5.18 PowerShell verification passed. No actual Office records are available to or accessed by this development task.

## Diagnosis

The old Python verifier filters discovered tool basenames using case-sensitive matching and recursively counts nested copies of the four known tools. PowerShell uses four fixed direct paths with Windows case-insensitive identity. A renamed physical tool can pass all manifest hashes and PowerShell verification but fail the Python count; additional nested tool copies can also cause disagreement. Old `Path.rglob` silently suppresses directory enumeration errors. The same generic exception obscures which incoming/installed/staged/replaced runtime failed.

The Office traceback narrows the failure to installed inventory, but does not identify its actual extra or differently spelled files. Existing installations created by merged copies can retain unlisted frontend/cache/runtime files. Those files must be preserved separately while every declared old file's size/hash is verified; an incoming download with unknown bundled files must remain rejected.

## Implementation

1. Normalize Windows identities consistently, require all direct root/tools entries, enumerate internal/tools trees completely with access/link errors refused, and preserve strict incoming/new manifest checks.
2. For an existing installation only, validate all declared files, preserve all unlisted runtime/tool files under the private updates directory, construct and verify a clean manifest-only preceding-runtime archive, and stage a clean incoming runtime. Include archive/count/repair information in the update receipt. Never replace or restore the working database as part of this repair.
3. Report selected root, phase, counts and missing/unexpected paths in failure details. Stop maintenance commands quietly with exit code 1 and a detailed private receipt. Explain preflight failures separately from genuinely interrupted replacement; preserve journals and do not suggest automatic database restoration.
4. Add a bundled package-verification command that opens no database, and require it in the production build, alongside PowerShell and manifest verification.

## Verification and delivery

Reproduce the old mismatch against the exact verified 0.5.18 ZIP using filename casing only. Exercise aliases, nested copies, omitted required tools, extra/corrupt/missing files, unreadable directories and links. Verify residue archive bytes, clean preceding/new runtimes, rollback protections, and unchanged synthetic database bytes. Run regression/static/type/build checks and Windows PowerShell 5.1 frozen upgrades from pristine and residue-bearing installations under Office-style paths.

Publish a new versioned 0.5.19 application-only ZIP and checksum to the existing private GitHub Releases repository. Keep 0.5.18 assets/history intact. Download the final assets back and verify their hashes. The user's Office database and existing recovery files remain authoritative; actual Office retry is separate from local synthetic verification.

## Executed results

605 complete-run tests, static/type/production checks, both147-file verifiers, pristine and residue native PS5.1 frozen upgrades, archive byte comparisons, explicit runtime rollback/retry and data-preserving development installation passed. Corrected19 Office folder and private GitHub release were published14 October; all final assets downloaded back and hash matched. Actual Office retry remains separate. See [final validation](../VALIDATION_0.5.19.md) for receipts and limits.
