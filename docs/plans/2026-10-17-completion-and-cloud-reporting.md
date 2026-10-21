# Completion, repayment and cloud reporting implementation plan

Date: 17 October 2026, Asia/Manila. Target: 0.5.22, schema 16.

## Confirmed decisions

The owner confirmed that three years of grace follow the allowed completion deadline. A program starting 1 June 2021 with three allowed years therefore has a deadline of 1 June 2024; grace includes 1 June 2027 and calculated review starts 2 June 2027. Google delivery replaces a separate reporting sheet from Cathedra, rather than merging into an operational spreadsheet.

## Implementation sequence

1. Preserve literal calendar years such as 2021. Keep explicit academic-year ranges, custom text, partial values and Summer. Annual copy advances the recorded form; new applications do not force a calendar year into an academic range.
2. Replace uppercase-on-change handlers with shared record controls that preserve selection, multiline position and composition input. Keep uppercase storage policy and unchanged historical values.
3. Add Incomplete to known grant outcomes and all relevant filters, counts, exports and display controls. Keep custom historical outcomes accepted.
4. Add nullable allowed duration (whole years), exact completion deadline and repayment progress with an additive migration. Reuse the existing optional actual start date. Calculate the deadline from an explicit date first, then start plus duration, then the previous completion-date fact. Never infer exact dates from year/term labels or rewrite old data.
5. Track repayment as Not recorded, Unpaid, Partially paid or Fully paid, separately from outcome and Open/Closed. Payment progress neither invents a payment ledger nor clears recorded Payback. Each annual grant retains its own facts; a later application clears copied deadlines and repayment progress.
6. Add an administrator-only manual Google report action. Use Google Desktop OAuth with loopback callback, state and PKCE. Keep the refresh token in a Windows-user-encrypted local file, outside the database. Share only the directory report, written as literal cells in the fixed CATHEDRA REPORT tab. Replace values and remove stale values atomically; preserve all other tabs. Do not introduce automatic startup/background uploads.
7. Document setup in the Guide and a delivery document. Explain the reporting tab's replacement behavior, OAuth consent scope, internet requirement and the separate status of live Google acceptance.
8. Verify optional-field preservation, migrations from supported old schemas, leap anniversaries, grace boundaries, application isolation, payment states, multiline editing and literal years. Mock Google networking for deterministic authorization/update/error tests; test real Windows encryption locally. Run existing suites, formatting, type checks, documentation contracts and packaged synthetic workflows before installing the runtime.

## Boundaries and recovery

The working development and Office databases are not test fixtures. Migration 16 adds three nullable columns and leaves previous field values untouched. Runtime replacement preserves the installation's data folder and creates a recoverable runtime archive. Do not publish Google client credentials, connection files, accounts or working records in an update package or source repository.

The Sheets authorization scope is broader than the one tab the implementation writes. A per-file Picker-based authorization would reduce that scope but needs additional Google frontend configuration; this iteration uses an explicit separate reporting spreadsheet and clearly documents consent. Google setup and a real authorized update remain acceptance steps when the owner supplies their OAuth client/account and destination. Disconnect removes the locally saved token; revocation is also available in Google Account settings.

## Acceptance

- 2021 remains 2021 on blur/save and export; an explicit 2021-2022 remains a range.
- Typing and replacing text on the first line retains the cursor there, including uppercase expansion and composition.
- Incomplete is selectable and can enter calculated review under the confirmed rule.
- Payment progress survives edit/read/export; older omitted fields preserve existing facts.
- Explicit deadlines override derived deadlines; missing dates remain unassessable. Completed clears calculated review within the same application only. Transferred and Withdrawn remain eligible.
- Google update requires administrator access and explicit replacement confirmation. A failed Google operation does not report successful delivery. No unrelated spreadsheet tab is included in the write request.
- Report and database are separate: Google edits do not change Cathedra and report delivery is not a backup.

Annual copies in the same application retain an explicitly recorded program start/duration/deadline rule, so another funding year does not move that program deadline. Payment progress, graduation, previous completion dates, end dates and outcome are reset for review. When no new program completion rule is recorded, the former actual-start clearing behavior is retained. New application clears program start, duration, deadline and payment progress; existing historical records are never mass-rewritten.
