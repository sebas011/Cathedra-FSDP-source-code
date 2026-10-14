# Current system documentation

**Product:** Cathedra FSDP  
**Documented:** 14 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.19; database schema 13<br>
**Status:** implementation-derived documentation; see [baseline and evidence](README.md).

## Start here

These documents describe the implemented Cathedra FSDP application and the remaining work needed to operate and maintain it. They are not a specification for a replacement application. Existing IDs, records, permissions and recovery behavior remain the baseline.

| Document | Audience | Purpose |
|---|---|---|
| [Product requirements](PRODUCT_REQUIREMENTS.md) | Office staff, product owner | Scope, user needs, business rules and acceptance criteria |
| [App flow](APP_FLOW.md) | Office staff, testers, developers | Navigation, record workflows, session recovery and safe updates |
| [Design brief](DESIGN_BRIEF.md) | Designers, frontend developers | Current visual language, page hierarchy, charts and interaction rules |
| [Technical requirements](TECHNICAL_REQUIREMENTS.md) | Developers, release maintainers | Architecture, API permissions, configuration, safeguards and verification |
| [Backend schema](BACKEND_SCHEMA.md) | Backend developers, data maintainers | Actual schema, relationships, field dictionary and migrations |
| [Implementation plan](IMPLEMENTATION_PLAN.md) | Maintainer, product owner | Delivered work, remaining implementation stages and release gates |

## What “current” means

| Item | Observed state | Interpretation |
|---|---|---|
| Current source | 0.5.19 | Implements the 14 October updater inventory/residue repair. Schema13, grouped CSV and business features remain. Full420-backend/185-frontend regression and production/frozen checks passed. |
| Development installation | Verified runtime 0.5.19 | New and retained18 manifests verified. Working database bytes and all434 first-party files at installation boundary preserved; later reports are intentional documentation changes. |
| Release source | `improvement-source`, branch `codex/audit-improvements` | Isolated source tested and packaged before installation. |
| Office update delivery | Verified `Cathedra-FSDP-0.5.19-Update`, published14 October | All147 runtime files and separate documentation inventory verified. Pristine/residue native PS5.1 upgrades passed. Actual Office retry remains separate. |
| GitHub delivery | Verified private v0.5.19 release, published14 October | Named ZIP and two supporting assets downloaded back with matching hashes. No working database/accounts/backups uploaded. Version18 retained; latest-release page selects19. |
| Last verified E: transfer | `E:\Cathedra-FSDP-0.5.17-Update` | Historical transfer, not an Office installation. E: is currently disconnected; 0.5.18 has not been transferred. |
| Historical E: reference | `E:\Cathedra-FSDP`, last inspected version 0.5.8 | This reference database is preserved. No fresh inspection of the disconnected drive or actual Office PC is claimed. |
| Current schema | Migration 13; 15 tables and 112 columns inspected in memory | Adds optional grant graduation/case tracking and Office Log storage; normalizes Graduated to Completed without merging identities. |

Schema inventories are obtained from disposable in-memory models and migrations. No live Office database is opened to produce these documents. API permissions are checked from route dependencies; screen and business behavior are checked from current source and synthetic verification. Personal records and credentials are not included. Historical version18 passed a pristine upgrade but missed this reported condition. Version19 passed420 backend/185 frontend tests and separate pristine/residue native updates with retained records, recovery archives, rollback and database hashes.

## Recorded verification, not new certification

See [0.5.19 validation](../VALIDATION_0.5.19.md) for observed repair/regression/package/upgrade results as gates complete. Actual Office-device retry/acceptance remains separate. Earlier [0.5.18 validation](../VALIDATION_0.5.18.md), [0.5.17 validation](../VALIDATION_0.5.17.md) and [0.5.16 validation](../VALIDATION_0.5.16.md) remain historical evidence.

The local GitHub Actions workflow exists, but no successful remote workflow run is asserted here. Separate Office-PC acceptance, clean-PC testing, device encryption confirmation, signing and assistive-technology acceptance remain external verification tasks.

## Approved terms and optional dates

**1st, 2nd, 3rd and Summer** remain supported. The later Summer addition and the owner’s explicit 9 October confirmation supersede the older three-term-only request. See [the decision record](DECISIONS.md). No Summer records are removed or reinterpreted.

Start/end grant dates are absent from the main grant editor but remain optional compatibility columns and API fields. This satisfies the option to make them optional; their presence is not presented as a new required workflow.

Graduation date and contract completion are separate optional facts on each annual grant. Outcome and Open/Closed case state are independent. The approved [12 October findings](../plans/2026-10-12-user-findings.md) supersede Graduated as the current outcome label with Completed, while preserving legacy input compatibility and historical migration ledger names. New business-record text is uppercased on entry; credentials and historical program identities are not mass-renamed.

## Document ownership and maintenance

The project maintainer updates schema and technical documents whenever models, migrations, permissions, endpoints or configuration change. The product owner reviews business-rule and workflow changes. The designer/frontend maintainer updates the design brief after interface changes. Update the baseline version/date and evidence links together; do not replace a current document with an obsolete release note.

This set takes precedence over older narrative release notes for its stated baseline. Older notes remain historical evidence, including the root README's older release heading.

See the existing [Office Guide](../OFFICE_GUIDE.md), [developer guide](../DEVELOPER_GUIDE.md), [export schemas](../EXPORT_SCHEMAS.md) and [release history](../RELEASE_HISTORY.md) for supporting procedures and historical changes.
