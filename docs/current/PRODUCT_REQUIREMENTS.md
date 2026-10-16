# Product requirements

**Product:** Cathedra FSDP  
**Documented:** 16 October 2026, Asia/Manila<br>
**Baseline:** release 0.5.21; database schema 15<br>
**Status:** implementation-derived documentation; see [baseline and evidence](README.md).

## Purpose and users

Cathedra FSDP is a local Windows workspace for maintaining Faculty and Staff Development Program scholars, academic programs, annual grant records, education, requirements, contract follow-up, document receipts/transfers and office reporting. Its working database belongs to the Office installation. A software update must preserve the Office's latest records.

Two application roles exist: **staff** and **admin**. Staff maintain scholar records and use reporting. Administrators additionally manage programs, accounts, deletion, backups/restore, and activity history. “Staff” as a scholar affiliation/personnel classification is separate from the `staff` account role.

## Product boundary

Included: authentication, Dashboard, scholar directory/editor/profile, Office Log, program catalog in Settings, Backup & Export, System Readiness, Activity History, Accounts & Access and searchable offline Office Guide.

Excluded from the current product: faculty workload administration, expenses/salary projection, the old legacy record module and Needs Verification tool, a standalone Reports page, and a calendar. Historical private archives are recovery material, not active product modules.

The application is designed for a local service and local database. Network sharing, hosted multi-user operation, email/SMS reminders, document upload/storage, automatic collection of repayments and automated eligibility decisions are not implemented product features.

## Implemented requirements and acceptance criteria

| ID | Requirement | Current acceptance criterion |
|---|---|---|
| PRD-01 | Secure local access | Existing users sign in; an empty installation requires the private first-admin setup token. Protected actions require a valid active account session. |
| PRD-02 | Maintain scholars with lightweight business validation | Name is required. Each added grant requires Program Applied. Scholars can be saved before a grant is available; optional educational and administrative information can remain unrecorded. |
| PRD-03 | Distinguish people with similar names | Search matches the start of name words; save-time name matches are warnings requiring review, never automatic merges. Separate people may share a name. |
| PRD-04 | Maintain multiple education entries | Bachelor’s, Master’s, Ph.D. or other entries can be stored separately with degree, institution and optional graduation year. |
| PRD-05 | Show tenure in years | Numeric years support fractional values; convertible historical years/months are interpreted as years. Unconvertible source text remains available as a note rather than a guessed duration. |
| PRD-06 | Separate whole-profile and grant notes | Profile remarks apply to the scholar; grant remarks apply only to their grant. Editing one must not erase the other. CSV exports have distinct columns. |
| PRD-07 | Use eight colleges plus Staff | CIT, CAS, COED, COE, CCJ, COF, CBMA and CCS are the college set. Every other known affiliation becomes Staff; missing information becomes Unknown. COED and COE remain different. |
| PRD-08 | Preserve annual grants | A scholar can have several grants for one program, with separate years, terms, status and remarks. There is no scholar/program uniqueness rule that collapses annual grants. |
| PRD-09 | Duplicate programs and grants | Administrators can duplicate a program or copy a grant. A copied grant starts On Going, clears actual date fields and remains editable for its intended year. |
| PRD-10 | Derive overall status from the latest grant | Directory and Dashboard status use the most recent grant by starting academic year, term order, then grant ID. Profile history preserves each grant's individual status. |
| PRD-11 | Identify contract follow-up | Optional actual contract completion starts three calendar years of grace. An unfinished program moves to Payback review after that grace period, without automatically changing its recorded status. |
| PRD-12 | Integrate reports in Dashboard | Dashboard reports support scoped totals, follow-up/results views, print and complete filtered CSV. There is no separate Reports route. |
| PRD-13 | Show useful overview analytics | Counts distinguish scholars from grants. College bars, a status doughnut and a grant-type pie use actual scoped totals. Ten newest scholars are listed. |
| PRD-14 | Follow up on requirements | A manual flag or an incomplete requirement marks follow-up. An unflagged profile is not a certified complete file. |
| PRD-15 | Protect concurrent saves and retries | Stale edits are rejected; an uncertain create retry uses the original account-scoped request key and payload. Existing records must not be silently overwritten. |
| PRD-16 | Recover and update safely | Administrators create compatible backups and restore them through protected recovery procedures. Runtime updates preserve the destination database. |
| PRD-17 | Explain behavior in the Office Guide | Dashboard count explanations and product guidance are searchable offline in the Guide; the Dashboard keeps concise labels and functional feedback. |
| PRD-18 | Preserve access boundaries | Admin-only actions are enforced at the API, not solely by hiding frontend controls. Temporary-password accounts must change their password before accessing records. |
| PRD-19 | Use uppercase editable record text | Newly submitted scholar, education, grant, program and Office Log text is uppercased consistently. Account usernames/passwords and established identity values are not bulk-renamed. System enum labels keep their canonical display values. |
| PRD-20 | Separate outcome and case state | Completed replaces Graduated as the canonical grant outcome. Each grant also has an independent Open/Closed case state; closing a case does not imply completion or repayment. |
| PRD-21 | Record graduation facts optionally | Each grant can have an optional graduation date. A Completed program can create linked education without a date or recognizable remark; dates and manual education intent remain separate. |
| PRD-22 | Record office document work | Staff/admin can append document-receipt or transfer entries with optional scholar linkage, date, document description, departments and notes. The Office Log is distinct from administrator change history and does not store uploaded documents. |
| PRD-23 | Track physical and electronic copies separately | Hard copy and soft copy are independent optional Available/Not available/Not recorded profile facts shown in the directory/profile. Neither implies complete requirements or a stored attachment. |
| PRD-24 | Separate repeated applications within one program | Annual records can share one application; a later enrollment receives a distinct application identity and overall period. Completion does not clear another application's calculated follow-up. Historical unassigned records are preserved until explicitly assigned. |
| PRD-25 | Support certification and enhancement programs | Optional program category distinguishes Degree, Certification and Enhancement independently of grant funding type. Name and Program Applied remain the essential identifiers. |
| PRD-26 | Present a predictable directory and compact log | Directory pages are ordered by case-insensitive trimmed full name then ID. Confirmed log saves close the editor; compact saved rows expand their full details. Uncertain drafts stay open. |

## Business rules

### Identity and affiliation

Scholar ID is the identity; name is not a unique key. Deleted scholar IDs are not reused, including across restore. Every noncollege affiliation, including IIT or campus-specific Staff labels, is represented as **Staff**. Migration 10 retains a noncanonical former label in profile remarks. Personnel is derived: college means Faculty, other known affiliation means Staff, missing information means Unknown.

### Education and graduation

A recorded Completed grant or a direct affirmative current-program graduation claim can add a linked education achievement. Graduated is accepted as a compatibility alias and migrated to Completed. A Completed program does not require a recognizable remark to be added to education. Its optional graduation date can supply a year; explicit manual year edits/clears and education removal remain authoritative. Historical/third-party/different-degree claims are not attributed to the grant. Remark-derived full dates must be valid and nonfuture; ambiguous numeric dates remain for review, and year-only evidence does not invent a day. Duplicate matching degree/institution achievements are avoided. If staff remove an automatically generated achievement, the suppression remains until explicitly restored; a later save must not recreate it automatically. Manual entries are not replaced by inferred ones.

### Terms and dates

Current implementation accepts 1st, 2nd, 3rd and Summer, plus an unrecorded value. Summer is retained by the later requirement and the owner’s explicit confirmation; the older three-term-only policy is superseded. A recognized consecutive year range, including 20262027, formats as 2026-2027. The grant editor infers the following year from a complete single four-digit year on blur or Save Grant; partial, custom or nonconsecutive values remain saveable. Grant start/end dates are optional compatibility data and are not compulsory editor inputs. Contract completion and graduation dates are separate optional facts. Term/year or closing a case does not invent either date. Annual grant copying clears all actual dates, including graduation, and extension; it retains remarks for review and begins an Open case with an On Going outcome.

### Contract assessment

Classification order is important:

1. Recorded Payback remains Recorded Payback, even if another grant for that program is Completed.
2. Recorded Payback pending contract remains pending even if another grant for that program is Completed.
3. Did Not Avail remains outside unfinished-program follow-up.
4. Any recorded Completed grant for the same scholar, **same program ID and same application identity** clears calculated follow-up for that application's other annual grants, subject to the recorded repayment categories above. Separate applications to the same program remain independent. Existing unassigned grants retain the previous same-program rule among those unassigned records until staff explicitly assign them. Education inferred from remarks alone does not clear assessment. Open/Closed case state does not override these recorded outcome rules.
5. Missing completion date produces Completion date missing, not a guessed deadline.
6. A future completion date produces Contract not completed.
7. Through the third anniversary, including that final day, the grant is In grace period. The next day starts Payback review.

For a 29 February completion, the three-year anniversary uses 28 February in the target year. Example: completion on 9 October 2023 stays in grace through 9 October 2026; review begins 10 October 2026. A duplicated program has a new ID; same-program graduation clearing does not automatically extend to that new program.

Recorded outcome changes remain office decisions. Calculated review does not establish a repayment amount, issue a demand, or change a grant to Payback. An administrator/staff member reviews the evidence and records the appropriate outcome.

### Application history and copies

Copy for next year retains the same application; New application creates a distinct enrollment group under the same program and clears prior remarks and completion facts. A suggested period must be reviewed before saving. Existing historical records are never automatically split by year gaps, repeated names or contract dates. Program category is separate from funding type, so a Certification or Enhancement program can still have any applicable grant funding type. New category, copy flags and dates remain optional. Document-copy availability is a profile fact; it does not certify requirements or create an attachment.

### Counts and filters

The Dashboard year filter selects scholars with a grant starting in that year and scopes grant counts to those matching grants. The scholar status doughnut still uses each selected scholar's latest grant over their complete history. College counts and statuses count scholars once; grant-type counts count grants. Contract categories count a scholar once within each category; one scholar with different grants can appear in several categories, so those totals are not additive.

## Permissions summary

| Capability | Staff | Admin |
|---|---|---|
| View Dashboard, scholars, profiles and Guide | Yes | Yes |
| Create/edit scholars, education, requirements and grant drafts | Yes | Yes |
| View reports, print and export scholar/education CSV | Yes | Yes |
| Read/export Office Log and append document receipt/transfer entries | Yes | Yes |
| Change own password | Yes | Yes |
| Resolve/create a missing typed program name during an authorized scholar save | Yes | Yes |
| Direct catalog management/duplication; privileged grant duplication | No | Yes |
| Delete a scholar | No | Yes |
| Manage accounts and revoke sessions | No | Yes |
| Create/download/protect/delete backups, record recovery review, restore | No | Yes |
| Read Activity History and scholar change history | No | Yes |
| View readiness/maintenance status | Yes | Yes |

## Success measures and limits

Acceptance means an Office user can find a scholar, update the intended record, preserve annual history and notes, review contract follow-up, produce the complete filtered report, and update software without losing newer data. Evidence must include the intended Office computer and real office acceptance; local automated checks alone do not provide that sign-off.

Read-only completeness filters and missing-data labels help review records. The product does not require every optional field to be filled before saving. Technical type, relationship, permission and revision checks still protect integrity.

Sources: [schemas](../../backend/app/schemas.py), [FSDP API](../../backend/app/api/fsdp.py), [current grant rules](../../backend/app/current_grant.py), [contract rules](../../backend/app/contract_rules.py), [classification](../../backend/app/college_classification.py), [education generation](../../backend/app/graduated_education.py), [routes](../../frontend/src/App.tsx).

## 0.5.14 acceptance additions

- Each annual grant retains its own academic year, type, outcome, dates and remarks under one program ID. Copy for next year opens an independent draft and clears previous graduation/payback evidence.
- Program and annual history are collapsible; printing expands the full history temporarily.
- Personnel is automatic from affiliation. Unknown is available without forcing an invented department.
- Graduation evidence never edits a grant outcome. Negative, expected, future or ambiguous statements are skipped; manual corrections and durable education removal are preserved.
- Payback pending contract and Transferred are available in status filters, forms, counts and exports. Final Payback remains manual.

## 0.5.17 acceptance additions

- Record text is stored in uppercase when newly entered or edited; authentication credentials and historical program names are not mass-transformed.
- Outcome, Open/Closed case state and optional graduation date are distinct fields on each annual grant. Existing Graduated outcomes become Completed without changing their identities.
- Status and case controls follow grant remarks so finishing data entry does not require scrolling back to the top. Icon actions retain accessible names, numeric fields ignore accidental wheel changes and the whole grant history can collapse.
- General Office Log entries are append-only, can remain unlinked to a scholar, retain author and optional scholar-name snapshots and support complete filtered CSV export.
