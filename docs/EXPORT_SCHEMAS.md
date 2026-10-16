# Current export schemas — 0.5.21

All five CSV downloads include a UTF-8 signature so Excel can recognize accented names. Headers, grouped scholar/grant rows and spreadsheet formula protection remain unchanged by this encoding update.

Current rules take precedence over the historical notes retained below. [Machine-readable header contracts](current/EXPORT_CONTRACTS.json) are checked against actual API output in the regression suite. CSV access requires sign-in; staff and admin can export. Backups remain privileged.

- Directory: header first; one row per annual grant, grouped by scholar. The first row contains the scholar's profile fields and first grant; continuation rows leave the 13 scholar/profile cells blank and contain one further grant each. A scholar with no grants has one profile row with blank grant cells. Profile Remarks and grant Remarks are distinct.
- Education: header first; one row per achievement. It does not contain Profile Remarks. Joining education to annual grants externally can multiply counts.
- Payback: first row is `Cathedra contract and payback follow-up,As of,<assessment date>`; second row is the record header. Keep each scholar's matching grants together; continuation rows leave Scholar, Scholar ID and Department blank. Complete filtered results match paged/unpaged JSON; category summaries in JSON remain department/year-wide.
- Dashboard report: title row, scholar/follow-up metadata row, blank separator, department totals, blank separator, actions, blank separator, scholar/grant detail. Section lengths vary. Locate headers rather than assuming a fixed detail-row offset. Department outcomes count scholars by latest status; detail counts annual grants. In the detail section, the first row contains eight scholar/profile fields and the first matching grant; continuation rows leave those eight cells blank and contain one matching grant each. Other sections retain their existing row format.
- Office Log: header first; one row per operational entry, ordered by event date and ID descending. Search/type/scholar filters apply to the complete export rather than the displayed page. Snapshot author/scholar names are distinct from editable document/note text.

Affiliation is one of eight colleges, Staff or Unknown. Personnel is Faculty for a college, Staff for another known affiliation, or Unknown when missing. Summer is retained. Completed replaces the former Graduated outcome; Transferred and Payback pending contract remain supported recorded outcomes, while calculated Payback review is separate. Open/Closed case state is independent. Dates/years remain optional. New editable business text is uppercase; unchanged historical values and actor credentials can retain their recorded case.

## Reading grouped scholar rows

A row with a scholar name starts that scholar's group. Each following row with empty scholar/profile cells belongs to the preceding named scholar, until the next named scholar appears. There are no extra blank separator rows between scholars. Within each scholar, grants use a consistent oldest-to-newest academic-year/term order, with the grant ID breaking ties. Every grant retains its own term, academic year, contract-completion date, graduation date, recorded outcome, case status and remarks. Report and payback groups include only grants matching their selected scope.

For example, selected directory columns would look like this:

| Scholar ID | Name | Program | Start Academic Year | Recorded Grant Status | Graduation Date | Case Status |
|---|---|---|---|---|---|---|
| 101 | MARIA SANTOS | MASTER OF EDUCATION | 2024-2025 | On Going | | Open |
| | | MASTER OF EDUCATION | 2025-2026 | Completed | 2026-06-14 | Closed |
| 102 | JUAN REYES | DOCTOR OF PHILOSOPHY | 2025-2026 | On Going | | Open |

Keep continuation rows together with their named scholar when sorting or filtering a spreadsheet. Blank profile cells mean “same scholar as above”; an empty optional grant cell means that grant has no recorded value. Scholar IDs distinguish people with the same name. A parser that needs a value on every grant row can carry forward only the profile columns within the current detail section; do not carry forward grant dates, outcomes, case state or remarks. All matching records are exported, regardless of the displayed table page.

Current directory and education exports omit origin/tracking columns: Source, Legacy Start Date, Legacy End Date and Source Program ID. The readable exports do not change stored historical metadata, account data or record identities.

## Ordered headers

### Directory

Endpoint: `/api/v1/maintenance/exports/fsdp.csv`

Records:

```csv
Scholar ID,Name,Age,Education Background,Missing Requirements,Department,Rank / position,Personnel Type,Current Scholar Status,Tenure (years),Created At,Updated At,Profile Remarks,Program,Delivering HEI,Start Term,Start Academic Year,End Term,End Academic Year,Contract Completion Date,Grant Type,Grant Other,Recorded Grant Status,Extension,Remarks,Graduation Date,Case Status
```

### Education

Endpoint: `/api/v1/maintenance/exports/education.csv`

Records:

```csv
Scholar ID,Name,Education ID,Level,Degree,Institution,Graduation Year
```

### Payback

Endpoint: `/api/v1/fsdp/payback.csv`

Records:

```csv
Scholar,Scholar ID,Department,Program,Grant ID,Academic year,Recorded status,Contract completed,Grace ends,Follow-up
```

### Report

Endpoint: `/api/v1/fsdp/report.csv`

Department Totals:

```csv
Department,Scholars,On-going,Completed,Payback,Withdrawn,Did Not Avail,Transferred,Payback pending contract,Requirements follow-up (scholars)
```

Actions:

```csv
Needs action,Scholar,Department,Detail,Follow-up
```

Records:

```csv
Name,Rank / position,Department,Age,Tenure (years),Education background,Current scholar status,Profile Remarks,Program applied,Delivering HEI,Type of grant,Start Term,Start Academic Year,End Term,End Academic Year,Contract Completion Date,Extension,Remarks,Recorded grant status,Graduation Date,Case Status
```

### Office Log

Endpoint: `/api/v1/office-logs/export.csv`

Records:

```csv
ID,Occurred On,Created At,Entry Type,Scholar ID,Scholar,Note,Document,From Department,To Department,Recorded By
```

All writers preserve Unicode, embedded line breaks and spreadsheet formula protection. CSV is a report, not a recovery backup. Store exports privately. The current directory contains 27 columns, education seven and report detail 21; payback and Office Log headers remain unchanged. Report detail keeps terms and academic years in separate columns and includes the actual optional contract-completion and graduation dates. External spreadsheets should use header names and section boundaries; compatibility aggregate aliases are not extra counts.

## Historical notes

### Export schemas in 0.5.11

FSDP directory CSV has one row per annual grant, or one row with blank grant fields for a scholar with no grants. Its fields include Scholar ID, Name, Age, Education Background, Missing Requirements, Department, Rank / position, Personnel Type, Current Scholar Status, Tenure (years), Source, Created At, Updated At, Program, Delivering HEI, Start Term, Start Academic Year, End Term, End Academic Year, Legacy Start Date, Legacy End Date, Contract Completion Date, Grant Type, Grant Other, Recorded Grant Status, Extension and Remarks.

Education CSV has one row per education entry: Scholar ID, Name, Education ID, Level, Degree, Institution, Graduation Year and Source Program ID. Education rows are not joined to annual grant rows; joining them externally without care can multiply counts.

Dashboard report and payback CSV exports include every matching record regardless of the table page. Cathedra's Print actions prepare a separate complete scoped snapshot before opening the print dialog. Dashboard printing includes its overview, selected report view and contract category even when the on-screen disclosures are collapsed. Report summary totals and action counts cover all matching scholars. Native browser Ctrl+P prints currently loaded content and carries a visible-view label; use the application Print action or CSV for complete results.

All CSV writers retain formula protection and Unicode content. Header names changed from Rank/Status to Rank / position/Recorded Grant Status; update external consumers. No CSV is a complete recovery backup. Use verified SQLite snapshots for recovery, and store exports privately.


## Version 0.5.12

Profile Remarks is an optional whole-scholar text field, separate from grant Remarks. The directory and Dashboard report exports include a distinct Profile Remarks column. Line breaks are retained and spreadsheet formula protection remains enabled. A client that omits the new field does not erase existing remarks; an explicit empty field clears them.

College / Staff uses CIT, CAS, COED, COE, CCJ, COF, CBMA, CCS and Staff. Other affiliations become Staff and personnel type Staff; original affiliation labels are retained in Profile Remarks. College personnel types remain as recorded. The first startup makes a protected recovery snapshot before migration 10, preserves scholar/grant identities and grant remarks, and updates only affected profile revisions. Keep Office data when installing an update.

Dashboard explanations are available in the searchable Office Guide. The overview compares colleges and Staff with vertical bars, shows scholar status proportions in a doughnut, and shows grant-type proportions in a pie. Counts and percentages remain visible beside the composition charts. Recent scholars and follow-up have separate sections; chart scrolling stays within the chart region.
