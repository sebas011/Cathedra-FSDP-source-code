# Cathedra FSDP 0.5.4 validation

Reference-driven redesign implemented using the frontend-design skill and the approved 2026-10-04 plan. Calendar and separately scoped backend feature additions are excluded.

## Delivered

Light sidebar and green selected navigation, floating account toolbar, local brand mark, compact typography and panel hierarchy. Consistent dashboard metrics, scholar directory with readable identity/IDs and pagination, profile section links, grouped forms, monitoring grouped by requirement attention, visible removable report filters, accounts with role/status badges, separated backup/restore/export navigation, readiness and activity tables, settings and an offline searchable guide.

The existing green is #176247. The implementation replaces rules in the three active design stylesheets; no parallel registry theme or external component framework was added. Earlier staged visual experiments are superseded.

## Verification

- Backend: 134 tests passed, with two existing dependency deprecation warnings.
- Frontend: 114 tests passed across 20 files. New coverage exercises guide body search, combined categories/search, recovery guidance visibility, report filter removal with preserved URL/view state, and all monitoring requirement groups including undated/manual items.
- Test and production TypeScript checks, backend static checks and locked dependency verification passed.
- Clean Vite production build and PyInstaller desktop package passed.
- Packaged startup, nested route, clean seed, version/product/data identity, persistence and release checks passed. Runtime inventory verifies 141 files.
- 73 browser route/layout observations: all fifteen protected task routes at desktop, tablet and mobile widths, plus representative repeated checks. No page-wide overflow or unexpected alerts appeared. Wide tables remain in named scroll regions.
- Browser checks verified mobile drawer focus, Escape and focus restoration; local guide search opens matching answers and keeps recovery guidance visible.
- Browser save verified a synthetic scholar through the namesake confirmation; both grants and all three requirements remained visible after a server-backed reload.
- Main semantic color pairs meet AA text contrast; input border exceeds 3:1. This is a targeted check, not a complete accessibility certification.
- All 51 Python source/test files in the backend are byte-identical to the baseline. Routes, API modules, hooks, utilities and print stylesheet are also unchanged. No schema migration or data conversion is introduced.

Evidence: evidence-0.5.4/build-054.log, evidence-0.5.4/source-and-contrast-checks.json and evidence-0.5.4/visual-checks/route-checks.json. Screenshots use synthetic preview records, never the live personnel database.

## Installation

Installed version 0.5.4 in the main project and in C:\Users\rodia\Desktop\Project\Releases\Cathedra-FSDP-0.5.0-Office. The Office folder retains its requested name; its contents identify version 0.5.4.

Main package inventory and the installed desktop smoke check passed, including backup/restore and clean shutdown with Python and Node unavailable on PATH. The source database SHA-256 is unchanged. A verified protected database backup and source/runtime rollback archives were retained. The Office database transfer passed integrity and foreign-key checks and preserved all non-session records; sessions were cleared only in the transfer copy. Its packaged smoke check also passed.

The user explicitly approved restricting main-project access to their Windows account, SYSTEM and administrators. Installation permission verification passed without violations. Final installation evidence is in evidence-0.5.4/installed-smoke.json, installation.log, office-transfer.json and office-smoke.json; the installation manifest records backup/archive locations and source hashes.

Separate-office-PC acceptance, printer-specific output and Windows scaling remain environment-specific checks before broader rollout.