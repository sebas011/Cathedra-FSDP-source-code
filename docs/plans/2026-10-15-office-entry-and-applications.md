# Office entry and repeated program applications

Baseline: source/runtime 0.5.19, schema 13. Requested 15 October 2026.

## Read-only findings

- `OfficeLogPanel` resets its editor after a confirmed save but leaves it open; each entry occupies a full card.
- `GrantEntry` includes an Existing program catalog selector as well as Program Applied. Existing grant IDs already retain program identity without that selector.
- Scholar profiles do not distinguish hard-copy availability from soft-copy availability. Neither state can be inferred from existing records.
- Grant history groups only by program ID, so repeated applications to the same program cannot be distinguished. Annual copying preserves the program but does not express a new application.
- Funding type and program nature are different facts. Certification and enhancement should be supported without replacing Full/Partial Scholarship or Thesis/Dissertation Aid.
- The directory orders the stored full name directly; mixed case and surrounding whitespace can disrupt alphabetical order. Pagination must happen after normalized ordering.

## Implementation sequence

1. Close the log editor only after confirmed persistence; retain uncertain request retry protections. Present entries as compact accessible disclosures and preserve complete printing.
2. Remove the Existing program selector. Retain program identity on edits and copies. Keep ambiguity checks in the API; never silently merge historical program identities.
3. Add independent nullable hard-copy and soft-copy flags. Existing records remain Not recorded, not implicitly No. Expose the flags in profile editing, profile display and directory.
4. Add optional program category (Degree, Certification, Enhancement), separately from funding type.
5. Identify applications independently of the catalog program: repeated applications get separate keys; annual entries within an application share a key. Preserve existing program IDs, grant IDs, dates, outcomes and nullable historical grouping. Offer distinct Add annual grant and New application actions. Allow existing rows to be assigned deliberately rather than infer a split from incomplete historical dates.
6. Apply normalized alphabetical ordering before pagination and consistently in directory exports.
7. Update guides, schema/API/export contracts where changed, release identity, and validation evidence. Test migration preservation, API round trips, grouping/copy semantics, log confirmation, filters and alphabetical pagination. Build and verify an isolated clean package; never use the working Office database as a test fixture.

## Confirmed decisions

- The owner confirmed that each application has its own completion/payback assessment. Annual entries share completion only inside their application; old nullable groups retain existing grouping until deliberately reassigned.
- “For work” means the Office Log form. No work-history module is added.

## Data and operational safeguards

Only Name and Program Applied remain essential business fields. Copy availability and category are optional. Migration is additive, protected by the existing snapshot/transaction workflow. No historical scholar/grant is deleted, renamed or automatically merged. Update package contains a clean seed only; existing installation records remain authoritative.

## Verification plan

- Backend integration: nullable migration, independent copy states, omission preservation, normalized directory pagination/export and categories.
- Frontend interactions: save-close versus uncertain-save, repeat applications versus annual additions, optional flags, removed selector, collapsed histories and full printing.
- Full existing backend/frontend regression, static/type checks, production build, package manifest and bundled verifier.
- Synthetic old-to-new upgrade with records, accounts and Summer retained. Actual Office-PC acceptance remains separate.

## Executed result

Implemented as 0.5.20/schema14. The final complete runs passed 440 backend and195 frontend tests, static/type checks, production build, clean seed,149-file manifest and actual bundled verifier. A native PS5.1 synthetic update retained old records, accounts and Summer; normal startup migrated13to14 and verified independent copy flags/application payback. Installed development runtime20 after a protected snapshot/private migration rehearsal, with working database bytes and448 first-party files preserved during replacement. See [validation](../VALIDATION_0.5.20.md). Local Office package delivery is verified separately; actual Office-PC acceptance and any later GitHub publication remain separate operations.
