# Current system documentation

**Product:** Cathedra FSDP  
**Documented:** 24 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.24; database schema 16<br>
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
| Current source | 0.5.24; schema 16 | Paper & Ink production integration. Measured checks are recorded in [0.5.24 validation](../VALIDATION_0.5.24.md). |
| Development installation | Verified 0.5.24 | Database bytes and the existing encrypted Google connection were preserved. |
| Office update package | Verified local 0.5.24 package; 149 runtime files | No working records or Google credentials are distributed. |
| GitHub delivery | [Versioned release channel](https://github.com/sebas011/Cathedra-FSDP/releases/tag/v0.5.23) | Public delivery and source workflow results are verified separately from local package checks. |
| Current source schema | Migration 16; 15 tables and 120 model columns | Three nullable grant fields; no historical facts are rewritten. |
| Actual Office-PC acceptance | Unverified | Local tests do not certify the separate Office PC. |

Schema inventories are obtained from disposable in-memory models and migrations. No live Office database is opened to produce these documents. API permissions are checked from route dependencies; screen and business behavior are checked from current source and synthetic verification. Personal records and credentials are not included. Historical version18 passed a pristine upgrade but missed this reported condition. Version19 passed420 backend/185 frontend tests and separate pristine/residue native updates with retained records, recovery archives, rollback and database hashes.

## Recorded verification, not new certification

See [0.5.21 validation](../VALIDATION_0.5.21.md) for observed regression/package/upgrade and development installation results. Actual Office-device retry/acceptance remains separate. Earlier [0.5.18 validation](../VALIDATION_0.5.18.md), [0.5.17 validation](../VALIDATION_0.5.17.md) and [0.5.16 validation](../VALIDATION_0.5.16.md) remain historical evidence.

The development installation was verified at 0.5.23; see [0.5.23 validation](../VALIDATION_0.5.23.md) for this update. GitHub publications and actual Office-PC installations remain separate observed states; the local working database migrates protectively at its next normal startup.

The published 0.5.21 source workflow passed. A green run for that release does not certify 0.5.23; this publication needs its own remote result. Separate Office-PC acceptance, clean-PC testing, device encryption confirmation, signing and assistive-technology acceptance remain external verification tasks.

## Approved terms and optional dates

**1st, 2nd, 3rd and Summer** remain supported. The later Summer addition and the owner’s explicit 9 October confirmation supersede the older three-term-only request. See [the decision record](DECISIONS.md). No Summer records are removed or reinterpreted.

The optional actual program start date is available in the grant editor to calculate allowed duration; the previous end-date compatibility field remains optional in the API. This satisfies the option to make them optional; their presence is not presented as a new required workflow.

Graduation date and contract completion are separate optional facts on each annual grant. Outcome and Open/Closed case state are independent. The approved [12 October findings](../plans/2026-10-12-user-findings.md) supersede Graduated as the current outcome label with Completed, while preserving legacy input compatibility and historical migration ledger names. New business-record text is uppercased on entry; credentials and historical program identities are not mass-renamed.

In 0.5.21, repeated applications to the same catalog program can have separate application keys. Annual grants within one application share completion follow-up; another explicitly separate application does not inherit that completion. Existing grants with an unrecorded application key retain their previous same-program behavior until staff assign them explicitly. Hard-copy and soft-copy availability are independent Available/Not available/Not recorded facts and do not imply complete requirements or stored electronic documents. CSV detail exports append optional completion and payment facts in 0.5.22.

## Document ownership and maintenance

The project maintainer updates schema and technical documents whenever models, migrations, permissions, endpoints or configuration change. The product owner reviews business-rule and workflow changes. The designer/frontend maintainer updates the design brief after interface changes. Update the baseline version/date and evidence links together; do not replace a current document with an obsolete release note.

This set takes precedence over older narrative release notes for its stated baseline. Older notes remain historical evidence, including the root README's older release heading.

See the existing [Office Guide](../OFFICE_GUIDE.md), [developer guide](../DEVELOPER_GUIDE.md), [export schemas](../EXPORT_SCHEMAS.md) and [release history](../RELEASE_HISTORY.md) for supporting procedures and historical changes.

See [0.5.22 validation](../VALIDATION_0.5.22.md) for the current implementation checks. Google delivery requires one-time configuration and account consent. The user confirmed a successful live update on 21 October 2026. That private connection and its records are excluded from publication; the new layout is checked with synthetic data.

## Completion and reporting update (0.5.22)

Calendar years stay literal: 2021 remains 2021; 2021-2022 remains an explicit academic-year range. Uppercase record controls preserve cursor/selection and multiline composition. Incomplete is an additional known grant outcome. The optional program start date and whole allowed duration produce a completion deadline; an explicit optional deadline takes priority, including for shorter programs. Previous completion dates remain a fallback. Grace runs three calendar years from the effective deadline, including its final day. Repayment progress (Not recorded, Unpaid, Partially paid, Fully paid) is separate from outcome and case status.

The administrator can configure and connect Google reporting from Backup & Export, then explicitly confirm a one-way replacement of the CATHEDRA REPORT tab. Other tabs are preserved. Connection credentials are Windows-user encrypted outside SQLite. Internet and OAuth setup are needed for cloud delivery; offline records work independently. See [setup](../GOOGLE_SHEETS_SETUP.md) and [validation](../VALIDATION_0.5.22.md).

## Google report update (0.5.23)

Google reporting uses a dedicated [fifteen-column contract](GOOGLE_REPORT_CONTRACT.json) rather than the full CSV table. Each scholar is numbered once and their grants remain on consecutive rows. The report retains recorded education, tenure in years, exact dates or recorded academic periods, each grant's outcome and clearly labeled profile/grant remarks. Existing CSV exports and schema16 are unchanged. Setup, approved test accounts, spreadsheet editing access and per-PC sign-in are described in the [detailed guide](../GOOGLE_SHEETS_SETUP.md). See [0.5.23 validation](../VALIDATION_0.5.23.md) for observed delivery status.

## Paper & Ink release (0.5.24)

The latest source integrates the new interface into the existing application. The historical 0.5.23 installation and delivery rows above describe their recorded verification; they are not a claim that the new release is installed or published. Consult [0.5.24 validation](../VALIDATION_0.5.24.md) and its publication receipt for the current measured state. No working Office database, account or Google connection is a software update asset.

The development runtime is now verified at 0.5.24 with preserved database/Google state. The 588 backend and 261 frontend checks, native build and synthetic Office upgrade are recorded in [0.5.24 validation](../VALIDATION_0.5.24.md); remote publication and intended Office-PC acceptance remain separate evidence.
