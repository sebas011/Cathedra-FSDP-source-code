# Design brief

**Product:** Cathedra FSDP  
**Documented:** 25 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.26; database schema 17<br>
**Status:** 0.5.26 selective blueprint improvements; current gates are tracked in [validation](../VALIDATION_0.5.26.md). Completed 0.5.25 readability work remains historical evidence.

## Visual identity

Paper & Ink supersedes the previous green interface. The design uses a dark ink navigation rail (#172A3A), warm canvas (#F6F5F1), white working surfaces, cobalt actions (#3156D8) and local Georgia display headings with Segoe UI/system body text. Teal (#087365), amber (#916012) and red (#B54343) distinguish positive, attention and critical states with visible text. Control borders (#8794A3) are stronger than decorative rules (#D9DEE5). Fonts, icons, styles and charts work without a CDN or external font request.

Reusable spacing, radii, type sizes and semantic colors live in design-tokens.css. Shared controls, navigation, dialogs, errors and tables use design-system.css and design-workspace.css; local dashboard, scholar and management styles own their page compositions. Use restrained rules and whitespace, readable values and compact actions. Preserve visible focus, reduced motion, labels, zoom and keyboard access.

## Shell and navigation

Workspace links lead to Overview, Scholars and Office log. Management contains the permitted program, reporting, activity and account tools. Staff retain their own account security controls. Office Guide and System Readiness remain reachable. A utility Find scholar action focuses the real directory search; Ctrl/Cmd+K uses the same route. Mobile navigation retains focus management and Escape handling. Health/identity checks, session recovery, sign out, print and desktop Exit Cathedra remain functional.

## Dashboard and reporting

Use a summary strip for people, annual grants, current outcomes and follow-up measures, each with its own unit. The registration line shows a real rolling twelve-month calendar series in Philippine time, including a documented prior-period cumulative baseline. Missing/future dates are not invented. Affiliation columns compare the eight colleges plus Staff/Unknown; outcome composition represents people using their current grant outcome. The ten most recently added scholars provide direct profile access. Tables accompany charts.

Reporting and contract assessment remain integrated into the dashboard rather than separate routes. Scope stays visible and exports/printing query the complete authorized scope. Follow-up categories may overlap and calculated review is distinct from recorded Payback and repayment progress. Business explanations remain in the searchable Office Guide; do not restore the old About these counts block.

## Scholar workspaces

The directory emphasizes identity, affiliation, current outcome, application/grant counts and hard/soft-copy facts. Keep alphabetical order, name-word prefix search, filters, pagination and clear profile actions. Wide tables scroll within labelled focusable regions rather than making the entire page scroll sideways.

Profiles use an identity band, compact facts and clear education/application sections. Multiple applications to the same program remain distinct; each application groups its annual grants. Profile remarks, grant remarks, requirements, document-copy availability and permitted history remain individually accessible. Collapsed entries retain summaries and keyboard operation. Printing expands relevant content without losing the previous disclosure state.

The editor presents identity, education, programs/grants and final review as four steps over one owned draft. Step navigation is not a partial save. Nested education and grant editors stage their entries; only final Save scholar writes the complete aggregate. Preserve optimistic revision conflicts, stable keys, idempotent uncertain retries, unknown optional values, caret/selection/IME handling, session recovery and explicit discard decisions. Name and each included grant's Program Applied remain the essential fields; do not introduce a completeness barrier.

## Supporting workflows

Office Log retains append-only entries, confirmed save/close behavior and compact disclosures. Program catalog uses a distinct editor and readable catalog surface while preserving revisions and duplicate semantics. Backup, restore, recovery review and Google synchronization retain explicit destinations, confirmations and progress/error handling. Account pages retain credentials and role enforcement. Guide search and essential recovery instructions remain available; system readiness reports observed states without invented guarantees.

## Acceptance and limits

Check actual desktop/mobile layouts, no page-level horizontal overflow, readable input boundaries, keyboard focus, chart alternatives, draft retention and all sensitive workflow confirmations. Automated structural checks do not certify complete WCAG, screen-reader or intended Office-PC acceptance. See the [integration plan](../plans/2026-10-24-paper-office.md) and [release validation](../VALIDATION_0.5.24.md). The original interactive design kit (local historical evidence; excluded from this source snapshot) remains fictional and independent from production data. This release keeps React/FastAPI; it does not install the proposed HTML/HTMX adapter.

## Readability refinement (0.5.25)

The current-status donut uses more of its dashboard card, with a larger chart and a readable legend arranged for the available width. Education and Programs & grants receive the full profile content width; supporting scholar information remains reachable without squeezing these records. Education details are visible on entry, with degree, institution and graduation year given a clearer hierarchy. Grant application summaries and annual records retain their grouping, disclosures and print behavior with more reading space. These are presentation changes, not changes to stored records, status calculations or reporting contracts.

See the [readability plan](../plans/2026-10-25-profile-readability.md) and [0.5.25 validation](../VALIDATION_0.5.25.md). Packaging, installation and publication must be reported from their own measured results; the 0.5.24 results do not certify this patch.


## Selected blueprint improvements (0.5.26)

Administrator profile history offers an optional Previous/New comparison with wrapped text, visible truncation and explicit Not recorded, No, 0 and empty-text values. Historical events remain metadata-only. Grant history and dashboard follow-up include a keyboard-operable Assessment details disclosure with the case-specific reason, deadline basis and assessed-on date; internal rule codes are not displayed. General instructions remain in the Guide. Existing profile reading space and education/application disclosure behavior are retained. See [0.5.26 validation](../VALIDATION_0.5.26.md) for actual interface checks.
