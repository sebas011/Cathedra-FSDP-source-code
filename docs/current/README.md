# Current system documentation

**Product:** Cathedra FSDP  
**Documented:** 16 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.21; database schema 15<br>
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
| Current source | 0.5.21 | Verified audit repairs; see versioned validation and remediation report. |
| Development installation | Verified runtime0.5.21 | Source files and working DB bytes preserved; private schema13-to15 rehearsal passed. Live additive migration runs at next normal launch. |
| Release source | Isolated verified0.5.21 build | 494 backend and220 frontend unique cases passed across complete and focused runs;148-file runtime verified. |
| Office update package | Verified local0.5.21 package | 148 runtime files and23 delivery documents; no working database/accounts. Native PS5.1 synthetic update passed. Actual Office-PC acceptance remains separate. |
| GitHub delivery | Verified private v0.5.19 release, published14 October | Named ZIP and two supporting assets downloaded back with matching hashes. No working database/accounts/backups uploaded. Version18 retained; latest-release page selects19. |
| Last verified E: transfer | `E:\Cathedra-FSDP-0.5.17-Update` | Historical transfer, not an Office installation. E: is currently disconnected; 0.5.18 has not been transferred. |
| Historical E: reference | `E:\Cathedra-FSDP`, last inspected version 0.5.8 | This reference database is preserved. No fresh inspection of the disconnected drive or actual Office PC is claimed. |
| Current source schema | Migration 15; 15 tables and 117 model columns | Adds nullable session activity time. Old sessions require sign-in; scholar and grant records are not rewritten by this migration. |

Schema inventories are obtained from disposable in-memory models and migrations. No live Office database is opened to produce these documents. API permissions are checked from route dependencies; screen and business behavior are checked from current source and synthetic verification. Personal records and credentials are not included. Historical version18 passed a pristine upgrade but missed this reported condition. Version19 passed420 backend/185 frontend tests and separate pristine/residue native updates with retained records, recovery archives, rollback and database hashes.

## Recorded verification, not new certification

See [0.5.21 validation](../VALIDATION_0.5.21.md) for observed regression/package/upgrade and development installation results. Actual Office-device retry/acceptance remains separate. Earlier [0.5.18 validation](../VALIDATION_0.5.18.md), [0.5.17 validation](../VALIDATION_0.5.17.md) and [0.5.16 validation](../VALIDATION_0.5.16.md) remain historical evidence.

The development installation is verified at0.5.21. GitHub publications and actual Office-PC installations remain separate observed states; the local working database migrates protectively at its next normal startup.

The local GitHub Actions workflow exists, but no successful remote workflow run is asserted here. Separate Office-PC acceptance, clean-PC testing, device encryption confirmation, signing and assistive-technology acceptance remain external verification tasks.

## Approved terms and optional dates

**1st, 2nd, 3rd and Summer** remain supported. The later Summer addition and the owner’s explicit 9 October confirmation supersede the older three-term-only request. See [the decision record](DECISIONS.md). No Summer records are removed or reinterpreted.

Start/end grant dates are absent from the main grant editor but remain optional compatibility columns and API fields. This satisfies the option to make them optional; their presence is not presented as a new required workflow.

Graduation date and contract completion are separate optional facts on each annual grant. Outcome and Open/Closed case state are independent. The approved [12 October findings](../plans/2026-10-12-user-findings.md) supersede Graduated as the current outcome label with Completed, while preserving legacy input compatibility and historical migration ledger names. New business-record text is uppercased on entry; credentials and historical program identities are not mass-renamed.

In 0.5.21, repeated applications to the same catalog program can have separate application keys. Annual grants within one application share completion follow-up; another explicitly separate application does not inherit that completion. Existing grants with an unrecorded application key retain their previous same-program behavior until staff assign them explicitly. Hard-copy and soft-copy availability are independent Available/Not available/Not recorded facts and do not imply complete requirements or stored electronic documents. CSV columns remain unchanged.

## Document ownership and maintenance

The project maintainer updates schema and technical documents whenever models, migrations, permissions, endpoints or configuration change. The product owner reviews business-rule and workflow changes. The designer/frontend maintainer updates the design brief after interface changes. Update the baseline version/date and evidence links together; do not replace a current document with an obsolete release note.

This set takes precedence over older narrative release notes for its stated baseline. Older notes remain historical evidence, including the root README's older release heading.

See the existing [Office Guide](../OFFICE_GUIDE.md), [developer guide](../DEVELOPER_GUIDE.md), [export schemas](../EXPORT_SCHEMAS.md) and [release history](../RELEASE_HISTORY.md) for supporting procedures and historical changes.
