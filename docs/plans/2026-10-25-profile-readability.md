# 0.5.25 — Dashboard and scholar profile readability

## Problem

The current-scholar-status chart uses a small fixed donut inside a taller dashboard card. Education and grant history also compete with the profile sidebar for reading space, while collapsed education entries conceal basic qualification details. Production browser checks also reproduced an older profile stylesheet loading after shared scholar styles when navigating from the directory, incorrectly constraining the main record area to 300 pixels.

## Implementation

1. Enlarge and center the status donut, give its legend the available card width, and keep chart values and accessible labels intact. Adapt the chart and legend arrangement to the card width.
2. Load profile base styles and scholar overrides once in a fixed entry-point order. Give Education and Programs & grants the full profile content width. Keep supporting scholar information reachable without crowding the record sections.
3. Make education details immediately readable, with clearer degree, institution and graduation-year hierarchy. Improve grant application and annual-record spacing without changing application grouping or business rules.
4. Preserve keyboard disclosure behavior, profile-tab navigation, printing, all existing fields and optional values, and narrow-screen layouts.

## Verification

- Run relevant chart, profile, disclosure/printing and workflow regression tests, formatting and both TypeScript checks.
- Inspect the running production build on desktop and mobile using fictional records, including long qualification/program text, several applications and expanded annual grants. Check for clipped content and page-level horizontal overflow.
- Build a fresh 0.5.25 Windows package and verify its manifest and bundled startup/workflow checks. Update the development runtime only through the guarded, data-preserving installation path.

## Scope and delivery

This is a presentation-only patch. Database schema remains 16; no migration, calculation, dependency or reporting contract changes are planned. Existing scholar records and the local Google connection must be preserved. Keep the published 0.5.24 release immutable; prepare the separate 0.5.25 patch with independent exact-revision CI, release checksum and fresh-download checks before publishing.
