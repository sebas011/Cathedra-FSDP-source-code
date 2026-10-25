# Release 0.5.25 validation

Verified locally on 25 October 2026, Asia/Manila. This presentation patch fixes the status chart and scholar profile readability. Schema 16, record values, business calculations, credentials and reporting contracts are unchanged.

## Interface and regression checks

All 262 frontend tests passed across 40 files. Coverage: 82.45% statements, 74.93% branches, 77.80% functions and 85.82% lines. Formatting, production/test type checks and production builds passed. The updated disclosure tests cover default visibility, annual grant expansion/collapse and restoration of individual states after printing.

Production browser checks reproduced the route-dependent stylesheet conflict that squeezed profile records into a 300-pixel column. Loading base profile styles and scholar overrides once, in a fixed entry-point order, resolved it. Both direct reload and navigation from the directory now use the full record width. Education details are visible initially; the latest grant application and annual record open initially. Supporting information remains below those records. The status donut measures 250 pixels on desktop and 240 pixels on a 390-pixel phone layout, with a readable full-width legend. Neither view has page-level horizontal overflow.

The 45 backend runtime source files matched their tested 0.5.24 hashes. The full backend suite was not rerun for this frontend-only patch. See [current regression evidence](analysis/REGRESSION_VALIDATION_0.5.25.json) and [prior backend verification](VALIDATION_0.5.24.md).

## Native package and installation

The constrained Windows package built successfully with an empty schema 16 seed and 147 verified runtime files. Startup, saved-data persistence, backup/restore, session handling and shutdown checks passed. Both Windows PowerShell 5.1 and PowerShell 7 checks passed without separate Python/Node runtimes on PATH. The bundled Python inventory verifier also passed without opening a database.

The guarded development installation completed as 0.5.25 after a protected snapshot and private preservation rehearsal. Working database bytes, the encrypted Google connection and existing first-party source files were preserved during replacement. Permission audits passed after restoring the previously approved owner/SYSTEM/administrators policy to browser-cache files. Private snapshots, paths, credentials and installation receipts remain excluded from update assets. See [local package evidence](analysis/LOCAL_PACKAGE_VALIDATION_0.5.25.json).

## Delivery and limits

The immutable [0.5.24 publication](analysis/GITHUB_PUBLICATION_VALIDATION_0.5.24.json) is historical evidence. Source publication, its exact-revision [GitHub workflow](https://github.com/sebas011/Cathedra-FSDP-source-code/actions), and the [0.5.25 Office download](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.25) are verified separately. The local evidence above does not claim that those remote gates have already passed. Actual Office-PC acceptance, physical printing, full screen-reader testing and live Google transmission were not performed here.

See the [readability plan](plans/2026-10-25-profile-readability.md), [current design brief](current/DESIGN_BRIEF.md), education preview (local historical evidence; excluded from this source snapshot) and grant preview (local historical evidence; excluded from this source snapshot). Browser evidence uses fictional scholars only.
