# Design brief

**Product:** Cathedra FSDP  
**Documented:** 16 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.21; database schema 15<br>
**Status:** implementation-derived documentation; see [baseline and evidence](README.md).

## Objective

Present scholar records and follow-up clearly in a calm office workspace. Preserve the institutional green, familiar local workflows and data meaning. Release 0.5.17 retains the established visual direction while improving grant entry, compact profile actions and general document logging. Definitions and operating guidance remain in the Guide.

Primary users are Office staff performing daily data entry and administrators overseeing programs, access and recovery. Priorities are readable hierarchy, comfortable spacing, quick navigation, clear save boundaries and faithful representation of recorded information.

## Visual foundation

The application uses React components, plain CSS and shared tokens. It does not depend on a purchased theme or third-party chart package. Dashboard charts are locally rendered SVG with text equivalents.

| Token / element | Current value | Use |
|---|---|---|
| Primary green | `#176247` | Primary actions, active navigation, key chart comparison |
| Hover green | `#104b35` | Hover/pressed primary actions |
| Soft green | `#e8f2ec` | Supporting surfaces and scholar initials |
| Deep green | `#163e2e` | Brand emphasis |
| Canvas | `#f5f7f4` | Workspace background |
| Surface | `#ffffff` | Cards, dialogs and controls |
| Ink | `#1b3028` | Main text |
| Muted | `#586860` | Supporting labels |
| Border | `#dce5de` | Surface boundaries |
| Control border | `#81958a` | Input boundaries |
| Warning / danger / info | `#86510c` / `#a52e40` / `#315d89` | Outcome and action states with text labels |
| Font | Segoe UI, system UI fallbacks | Familiar Windows reading experience |
| Base text | 16px | Body scale; individual table/control styles may differ |
| Common text scales | 12, 14, 16, 18, 24, 30px | Labels through headings |
| Spacing tokens | 8, 16, 24, 32, 40, 48, 64px | Consistent layout rhythm |
| Sidebar / content maximum | 256px / 1440px | Navigation and wide-screen workspace |
| Control / card / dialog radii | 8px / 10px / 14px | Rounded, restrained boundaries |
| Motion | 140ms ease | Short transitions; reduced-motion alternatives |

Page-specific cards may use different radii/padding; Dashboard analytics cards use a 14px radius and 28px padding on wide screens. Tokens are the source of truth rather than a claim that every rule uses exactly one token.

## Information hierarchy

Use one page heading, a clear primary action and a small set of context controls. Group related work into labelled sections. Identify scholar and grant counts by unit. Keep explanations in the searchable Office Guide; leave concise labels, errors, empty states and necessary field help close to the action they explain.

Do not add decorative growth statistics, forecast lines, maps, social controls, photos, billing/settings tabs or functionality unsupported by the application. Initials identify scholars without inventing portraits. A trend line requires a real time-indexed series; categorical totals alone do not justify one.

## Page composition

### Navigation and shell

A left sidebar groups Dashboard/FSDP, Office tools and Help. Active links are labelled and highlighted in green. The shell contains printing, current account and logout controls; collapsible/mobile navigation keeps the content accessible. Do not restore workload, projection, Needs Verification, standalone Reports or Calendar links.

### Dashboard

1. Page heading and Guide/report/add-scholar actions.
2. Scope filters for College / Staff, start academic year and chart order.
3. Four summary cards: Scholars, Grant records, Scholars on going and Requirements follow-up.
4. Full-width college/Staff comparison.
5. Status and grant-type composition cards.
6. Full-width ten-recent-scholars table.
7. Separate requirement follow-up and contract-assessment sections.
8. Expandable contract details and embedded reporting/export work.

The chart choice follows the question being answered:

| Data | Visualization | Reason | Text counterpart |
|---|---|---|---|
| Scholars by college / Staff | Vertical bars with zero baseline | Compare category magnitudes clearly | Named chart region and count list |
| Latest scholar statuses | Doughnut | Show each status's share of selected scholars | Label, count, percentage; total in ring |
| Grant types | Pie | Show composition of selected grant records | Label, count, percentage |

Zero/unknown categories remain represented as recorded rather than guessed. The pie handles one positive category as a full circle and an empty scope as an empty state. Grant-type colors remain stable when changing chart order. Small shares remain readable in the legend even if hard to distinguish visually. No chart relies on color alone.

### Directory and reports

Place search, filters, counts and actions consistently above results. Provide stable identity/profile links, readable status labels, pagination and clear no-results feedback. Preserve complete filtered printing/export. On smaller screens, tables scroll inside their own labelled region rather than widening the whole page.

Directory rows use stable case-insensitive alphabetical order of the full recorded name, with ID as a tie-breaker. This does not invent a surname field or reinterpret names. Show hard-copy and soft-copy availability separately using Available, Not available and Not recorded text rather than color alone.

### Scholar profile

Use an identity header and compact facts, followed by whole-profile remarks, education and annual grant history. Keep “Profile remarks” and “Grant remarks” visibly different. The full grant history has its own disclosure, in addition to individual program/year groups, so it need not dominate the page. Profile, education and grant actions use icons with accessible labels and tooltips; icons never rely on shape alone. Staff should not appear twice as redundant identity pills. COE/COED remain separate. Requirements and privileged change history support the profile without dominating its core information.

### Scholar editor

Use clear sections for Scholar Information, Education, Grants and Requirements. Distinguish finishing a subentry from persisting the scholar. Keep open drafts, errors and uncertain-save notices visible. Confirm discards/removals where implemented. Preserve explicit recorded unknowns and optional fields; do not turn completeness guidance into mandatory fields. Place grant outcome and case state after the remarks near Save Grant. Optional graduation and contract-completion dates have distinct labels. Display new record text in uppercase, format recognized consecutive academic-year ranges with a dash, complete a single four-digit year on blur/save and protect age/tenure from mouse-wheel changes while keeping normal keyboard editing available.

Use a single Program Applied input in grants and a separate optional Degree/Certification/Enhancement category. Keep funding in Type of Grant. Stack annual records by application, including repeat enrollments in the same program, with each application's overall period visible in its summary. Keep Copy for next year and New application distinct. Existing unassigned program history stays together until explicitly reviewed and reassigned.

### Office Log

Use a compact new-entry form and a paginated, filterable document register. Receipt/transfer information includes the document, optional scholar, date, from/to department and notes without introducing file-upload behavior. Author and scholar snapshots explain who recorded an entry and which scholar was linked at that time. Keep Office Log separate from administrator Activity History. Append-only entries have no misleading edit/delete controls.

Close the editor only after confirmed saving and return focus to Add log entry. Keep failed/uncertain drafts open. Stack saved entries as native keyboard-operable disclosures with date/type/document/scholar summaries; expand for full notes, movement and author. Profile printing temporarily expands the loaded log entries and restores their prior state, just as grant history does.

### Guide, settings and recovery

Guide has local search, topic filters and expandable articles; essential restore guidance remains visible. Settings use aligned labelled controls and separate privileged/destructive actions. Backup/readiness pages distinguish local snapshots, off-device review, protected backups and external device checks.

## Responsive and accessibility requirements

Current Dashboard composition cards share a row above 1400px and stack below it. Summary cards become two columns at 640px; composition charts and legends stack at that breakpoint. The college chart may scroll locally. Profile/table/dialog behavior follows their own CSS breakpoints; do not assume one breakpoint controls the entire app.

Maintain semantic headings, explicit control labels, keyboard focus visibility, modal focus behavior, labelled scroll regions, chart text equivalents and appropriate status/error announcements. Honor reduced motion. Verify both keyboard operation and text/zoom layouts. Existing automated accessibility checks are evidence of tested structure, not complete WCAG or screen-reader certification.

## Review acceptance

- Green remains `#176247`; meanings do not change during visual work.
- At desktop and 390px widths, no global horizontal overflow is introduced.
- Counts reconcile to their documented units and current filters.
- Subentry and whole-scholar save boundaries are unambiguous.
- Empty/loading/error/session-expired states remain usable.
- Guide explanations stay searchable; Dashboard does not regain “About these counts.”
- Privileged controls match backend enforcement.
- Printing hides navigation/actions while preserving relevant report/profile information.

Sources: [design tokens](../../frontend/src/design-tokens.css), [design system](../../frontend/src/design-system.css), [Dashboard CSS](../../frontend/src/dashboard.css), [profile CSS](../../frontend/src/profile.css), [Dashboard page](../../frontend/src/pages/FsdpDashboardPage.tsx), [Guide page](../../frontend/src/pages/ProductGuidePage.tsx). Mixed charts remain in 0.5.14.
