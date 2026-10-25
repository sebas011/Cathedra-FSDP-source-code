# Cathedra UI/UX redesign plan

Date: 2026-10-04
Status: Implemented for 0.5.4, excluding the calendar and separately scoped feature options. See docs/VALIDATION_0.5.4.md for validation and installation evidence.
Baseline: Current project VERSION is 0.5.3. The earlier 0.5.4 visual experiment remains staged separately. This reference-driven proposal replaces that experiment as the recommended design direction, without installing either design.

## Goal and boundaries

Give the entire application a cohesive, modern office interface while preserving Cathedra's green (#176247), existing records, core functions, routes, roles, offline operation, and recovery protections. Improve how staff find scholars, understand grant status, review requirements, create reports, and perform maintenance.

Use the supplied demos as references for layout and interaction patterns. Build original components in the existing React/TypeScript application. No template purchase, copied proprietary assets, Vue migration, Bootstrap migration, or new backend capability is required by this plan. Fonts and icons must work without an internet connection.

Applied skill: frontend-design (local historical evidence; excluded from this source snapshot). Its design approach informs the palette, layout alternatives, shared components, and visual review.

## Research evidence

All eleven supplied URLs were attempted with web retrieval and browser inspection. Ten rendered usable demo content. Flowbite rendered its preview header, but its embedded application remained blank; it is not a verified component reference. Screenshots are in ../design-research/2026-10-04/reference-research/. This is a design inspection, not an accessibility certification or a test of each demo's backend.

| Reference | Observed pattern | Application to Cathedra | Boundary |
|---|---|---|---|
| [Vuexy calendar](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/app-calendar.html) | Mini-calendar and category filters beside month/week/day/list views. | A possible later read-only view of recorded requirement deadlines and exact grant dates. | Keep undated and academic-term records in a separate list. Do not infer dates or introduce event creation in the visual redesign. |
| [Vuexy logistics dashboard](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/app-logistics-dashboard.html) | Compact summary cards above a large status breakdown and operational panels. | Scholar/grant summaries, existing outcome distributions, and prominent follow-up work. | Use actual endpoint totals. Do not add unsupported historical trends, maps, or fabricated percentages. |
| [Vuexy user list](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/app-user-list.html) | Summary row, separate filters, search/export/add toolbar, identity column, badges, pagination, and expandable responsive details. | A clear scholar directory with search/status controls, readable scholar identity, and explicit row actions. | Only expose filters, export, sorting, or page-size options supported by the relevant workflow/API. No bulk deletion. |
| [Vuexy permissions](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/app-access-permission.html) | A compact permission table with assigned-role badges and dedicated actions. | Make the existing admin/staff distinction and account actions easier to understand. | Preserve current authorization. Do not introduce an editable permission system. |
| [Vuexy profile](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/pages-profile-user.html) | Identity header, section navigation, facts panel, and a wider activity area. | Scholar header and identity facts beside grants, requirements, and recorded history. | Use initials rather than invented photos; omit social, location, and connection controls absent from Cathedra. |
| [Vuexy account settings](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/pages-account-settings-account.html) | Settings navigation, aligned two-column fields, save/reset controls, and a separate account deletion area. | Group existing account/security controls and separate high-impact account operations. | Preserve current fields, password rules, role restrictions, and confirmations. Do not add billing or profile-upload features. |
| [Vuexy FAQ](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/pages-faq.html) | Help search, category navigation, and accordions. | Searchable Office Guide organized around real staff tasks. | Search local guide content; retain critical recovery instructions visibly accessible. No invented support contact. |
| [Vuexy analytics cards](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/cards-analytics.html) | Several compact combinations of a number, explanation, and chart. | A small, consistent set of summary cards with clear units and accessible chart alternatives. | Distinguish grants from unique scholars. Use charts only where the data supports them. |
| [Vuexy advanced tables](https://demos.pixinvent.com/vuexy-html-admin-template/html/vertical-menu-template/tables-datatables-advanced.html) | Server-sourced tables, search, advanced filters, and responsive detail patterns. | Standardize directory/report/monitoring table controls and result counts. | Preserve server pagination and latest-request protections. Never sort or filter only one fetched page while presenting it as the whole dataset. |
| [Flowbite application preview](https://flowbite.com/application-ui/preview/) | Preview shell loaded; embedded application did not render. | No specific layout or interaction adopted from this URL. | Revisit only if the preview becomes available. |
| [Velzon dashboard](https://themesbrand.com/velzon/html/master/index.html) | Summary tiles, large analytics panels, contextual report actions, operational tables, and an activity rail. | Strengthen dashboard hierarchy and put relevant actions next to their panels. | Avoid its large multi-level navigation and unrelated commerce metrics. Demo overlays partly obstructed the captured view. |

Research screenshots: vuexy-calendar.png, vuexy-logistics.png, vuexy-users.png, vuexy-permissions.png, vuexy-profile.png, vuexy-account.png, vuexy-faq.png, vuexy-analytics.png, vuexy-tables.png, flowbite-preview.png, velzon-dashboard.png.

## Design direction

Considered three directions:

1. Recommended: a light Vuexy-inspired admin workspace, with Cathedra green replacing the demo's purple. Strongest fit for forms, tables, and record management.
2. A dark-sidebar Velzon-inspired workspace. Useful dashboard hierarchy, but its denser navigation consumes attention in Cathedra's smaller route set.
3. The earlier serif registry experiment. Distinctive, but less aligned with the user's new references and consistent table-heavy office work.

Choose direction 1 and borrow Velzon's ordering of summary, analysis, and work queues. Use a white sidebar, green active item, quiet canvas, clear sans-serif headings, compact panels, and useful whitespace. Keep page-specific actions close to their content. A large dashboard greeting, decorative gradient cover, global search, notification bell, and theme customizer are unnecessary for the current scope.

### Tokens and component contract

| Token | Proposed value |
|---|---|
| Primary / hover | #176247 / #104b35, preserving existing green |
| Selected background | #e8f2ec |
| Canvas / panel | #f5f7f4 / #ffffff |
| Text / secondary text | #1b3028 / #586860 |
| Panel border / input border | #dce5de / #81958a |
| Warning / danger | Existing #86510c / #a52e40 with readable text labels |
| Typography | Local Segoe UI, system-ui, sans-serif; body 14-16px; page titles 26-30px; section titles 18-20px |
| Spacing | 4, 8, 12, 16, 24, 32px scale; 24px desktop content padding |
| Corners / elevation | 8px controls, 10px panels; light shadow for major panels only |
| Controls | At least 40px tall; touch-oriented controls 44px; clear focus ring |
| Table density | Approximately 48-56px rows; long values wrap where appropriate |

These are proposed implementation values, not a claim that the references pass contrast requirements. Verify all final text, borders, charts, focus, and selected states against WCAG AA. Color must accompany a text label or other non-color cue.

Shared patterns: PageHeader, MetricCard, StatusBadge, FilterBar, TableToolbar, TableRegion, ResultPagination, FormSection, RecordHeader, ActionFooter, EmptyState, LoadingState, ErrorState, and existing safe modal behavior. Adapt current components before creating duplicates.

## Information architecture and wireframes

Retain routes and role visibility. Keep existing workspace, office tools, and help groups; simplify their presentation. FSDP remains the directory entry with monitoring and grant review available in its workspace navigation. Settings contains the existing account controls. Mobile navigation keeps its focus trap and close behavior.

```text
Dashboard
[Cathedra sidebar] [Page title                         account controls]
                   [Existing scope filters]
                   [Scholars] [Grants] [Existing status / follow-up totals]
                   [Outcome / department breakdown] [Attention needed]
                   [Relevant records or existing work queue             ]

Scholar directory
[Cathedra sidebar] [FSDP scholars                         Add scholar]
                   [Search                    Status          Clear]
                   [Result count                    supported actions]
                   [Scholar identity | Department | Status | Actions]
                   [Records / page information               Previous Next]

Scholar record
[Cathedra sidebar] [Back to directory]
                   [Initials  Name / scholar ID / department       Edit]
                   [Facts panel] [Grants / requirements / recorded history]
                                 [Grant summary and detail sections        ]
```

Dashboard attention panels must reuse available monitoring data and links; do not invent a combined queue endpoint. Preserve accurate labels when two panels count different entities.

## Screen-by-screen redesign

| Screen / route | Planned treatment | Behavior to preserve |
|---|---|---|
| Login /login | Clear brand, focused sign-in form, visible validation and service status; compact mobile layout. | Authentication, session expiry, required password change, and recovery behavior. |
| Shell / all protected routes | White navigation, green selection, consistent page title/action area, clear account controls and service banner. | Role visibility, print/logout/desktop exit, dirty-form guards, session recovery overlay and inert background. |
| Dashboard / | Summary cards, existing scope controls, outcome/department panels, clearly prioritized follow-up links. | Existing analytics scope and definitions; no false trends or new calculations disguised as stored data. |
| Directory /fsdp | Unified search/status toolbar, readable identity column, consistent result count and pagination. | Existing search and server pagination; namesakes remain distinguishable by IDs and other existing facts. |
| Scholar /fsdp/:id | Compact identity header, facts column, grants and requirements in the main column; strong edit affordance. | Every existing field, grant, requirement, and detail action; no hidden critical records. |
| New/edit scholar /fsdp/new and /fsdp/:id/edit | Grouped form sections, repeatable grant cards, explicit add/remove controls, sticky safe action footer. | Full collection replacement semantics, unsaved-change guard, validation, conflict checks, and legacy term handling. Avoid a wizard that changes save semantics. |
| Monitoring /fsdp/monitoring | Severity summaries, distinct overdue/due-soon/manual-follow-up sections, readable deadlines and update links. | Real dates versus academic terms, manual follow-up inclusion, and existing count definitions. |
| Grant review /fsdp/grant-review | Compact review summary, aligned fields, clear pending/saved states and review actions. | Current filters, update/review workflow, and pending-operation guards. |
| Reports /reports | Dedicated filter panel, visible active filters, result summary, report table and existing export/print actions. | Department/rank/status/grant type/HEI/requirements filters, URL state, correct totals and exports. Preserve legacy redirects. |
| Verification /verification | Clear criteria, results and exceptions with existing actions next to each result. | Current verification rules and data access. |
| Settings /settings | Group existing settings by task with concise descriptions and clear scope. | Current preferences and constraints; no decorative settings without an effect. |
| Accounts /settings/accounts | Account list, role/status badges, separate account/security forms and clearly separated sensitive actions. | Admin/staff restrictions, case-insensitive usernames, password rules, session controls, and forced password-change flow. |
| Backup /backup-export | Separate backup/export and restore areas; display existing review information and operation progress in sequence. | Restore review, confirmations, pending guards, route/unload/logout/exit blocking and database validation. |
| Readiness /system-readiness | Distinguish service/database health from operation errors; show actionable checks and retry/status controls. | Latest-request guard, version mismatch warning, recovery block, and truthful database status. |
| Activity /activity | Consistent activity table with readable actor/action/date and existing detail controls. | Admin-only visibility and current audit data semantics. |
| Office Guide /office-guide | Task categories, locally searchable guidance, accessible accordions, prominent recovery topics. | Complete current guidance and offline availability. |
| Print views | Preserve dedicated print layout, titles, table headers, scope and readable monochrome output. | Existing print content and page handling; screen navigation stays excluded. |

## Responsive and interaction requirements

- Desktop: 240-256px navigation and flexible main content. At medium widths, collapse appropriate secondary layout columns. Preserve the current 760px mobile navigation behavior initially; adjust only after testing.
- Narrow screens: cards stack; filters and action groups wrap; forms become one column. Keep identity and essential actions usable. Wide tables remain in labelled keyboard-scrollable regions; optional expandable secondary detail is allowed only if no information or action disappears.
- Preserve visible labels, keyboard order, focus restoration, Escape handling, modal focus traps and disabled/pending states. Errors must be announced and associated with their fields. Never rely on an icon-only tooltip for a critical action.
- Distinguish empty database, no matches, loading, unavailable service, forbidden access and update conflict. Give a relevant next action without clearing entered work.
- Avoid hover-only controls, automatic animation, remote font requests and added decorative motion. Respect reduced motion.

## Implementation sequence and acceptance gates

### 1. Inventory and foundation

Capture the current routes and workflows with synthetic data. Inventory active CSS imports and existing shared components. Implement tokens, typography, shell and common states in isolation. Consolidate competing active styles rather than layering another global override file.

Exit: login, shell and navigation work at desktop and narrow widths; admin/staff and recovery states remain correct; original green is retained.

### 2. Daily work

Redesign directory, scholar detail and new/edit forms first. These establish the table and form conventions used throughout the app. Exercise multiple grants, multiple requirements, duplicate names, long text, empty fields, legacy terms and conflicting updates.

Exit: staff can find a scholar, inspect all grants, edit and save without losing fields or weakening protections; keyboard operation remains usable.

### 3. Monitoring and reports

Apply the same patterns to monitoring, grant review, reports and verification; then compose the dashboard from supported data. Verify query state, totals, pagination, export and print against baseline output.

Exit: overdue and undated/manual-follow-up records remain distinguishable; unique-scholar and grant counts match the current behavior; exports and printed reports preserve content.

### 4. Administration and help

Redesign settings, accounts, backups, readiness, activity and guide. Test the backup/restore operation states and navigation guards, including refresh after restore review. Keep role management within the existing model.

Exit: every route is visually consistent and existing operation safeguards still hold. Help content remains available offline.

### 5. Validation and release preparation

Run the existing backend/frontend suites, type checking, production build and packaging checks. Add targeted behavioral coverage only where interactions change. Perform visual and keyboard checks around 1440, 1024, 768 and 390px widths, including long tables/forms and print preview. Compare representative exports and record payloads to the baseline.

Exit: all changed workflows pass; no unexpected database/schema changes; packaged runtime reports the intended version; offline assets load; persistence and startup pass on an isolated data copy. Only then prepare an Office release update, preserving its database and backup and following the established safe application-close requirement. The subsequent implementation request includes release preparation; the calendar remains excluded.

## Deferred options requiring separate scope

Read-only deadline calendar, new global filters/sorting, configurable permissions, notifications, bulk actions and editable calendar events are separate feature decisions. A visual redesign does not authorize those changes. If a deadline calendar is later selected, first audit actual date coverage and provide an undated queue and accessible list view.

## Completion criteria

The redesign is complete when every listed screen shares the same visual language; existing tasks remain available and accurate; mobile and keyboard use are verified; reports and print retain their content; authentication, conflicts, permissions, unsaved work and maintenance guards remain intact; and an isolated packaged build passes validation. Deployment readiness is established by those checks, not by appearance alone.

