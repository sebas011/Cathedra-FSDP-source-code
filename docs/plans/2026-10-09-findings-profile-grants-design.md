# Findings implementation plan — 0.5.14

Approved scope: implement the ten items in Findings-for-FSDP.txt. Personnel rule confirmed by the user: CIT, CAS, COED, COE, CCJ, COF, CBMA and CCS imply Faculty; other known affiliations imply Staff; missing affiliation implies Unknown.

## Read-only audit and change inventory

- `backend/app/graduated_education.py`: currently only recorded Graduated outcomes add education, without a graduation year. Add conservative offline remark evidence and associated years. Preserve manual corrections, matching entries and durable removal suppression. Neither academic/contract dates nor arbitrary years establish graduation.
- `backend/app/college_classification.py`, schemas, API and reporting: replace editable personnel classification with the approved derived rule, including consistent Unknown filtering/export. Preserve historical affiliation text in profile remarks.
- `backend/app/migrations.py`: migration 11 backfills reliable education evidence and personnel classifications, transactionally, with affected scholar revisions advanced. Existing database upgrade safety snapshots remain in effect. No tables or historical grants are deleted.
- Contract assessment, follow-up, report and status selectors: add explicit Payback pending contract and Transferred outcomes. Keep Payback manual, with calculated Payback review separate. Pending contracts remain visible in action queues and exports.
- `frontend/src/pages/FsdpDetailPage.tsx`, profile CSS: put scholar facts before profile remarks, group annual grants by program ID, and make each program and annual grant collapsible. Preserve all individual outcomes and remarks. Show annual year/type/status in collapsed summaries.
- Scholar form and GrantEntry: align paired fields, move profile remarks after age/tenure, use read-only derived personnel, compact program duplication beside its input, and support copying an annual grant into the next academic year under the same program. Reset completion/outcome/remarks when making the new annual draft. Distinguish copying a program catalog entry from adding another year to the same program.
- Education UI, Guide and current documentation: explain evidence rules, manual payback, miscellaneous outcomes, annual recording and Unknown classification. Keep explanations in Guide rather than Dashboard.
- Backend/frontend tests: cover evidence precision, corrections/removal, migration idempotence, personnel consistency, pending payback, annual copying and accessible collapsing.

## Execution sequence

1. Implement domain rules and migration with focused regression tests.
2. Implement profile/form layout, annual history and status selectors.
3. Update documentation and version; run backend and frontend checks, production build and packaged startup/update smoke checks.
4. Rehearse migration against a private database copy, preserving IDs, grants, remarks and manual data.
5. Install tested runtime while Cathedra is closed, preserving the development data folder. Prepare the latest app-only Office update; archive older release artifacts outside Releases without losing their data.

## Acceptance criteria

- Affirmative graduation remarks can add one completed program and its clearly associated year; negative, expected or ambiguous evidence does not. Existing education corrections/removals survive saves and upgrades.
- Personnel is Faculty, Staff or Unknown based on affiliation, in forms, profiles, filters and exports.
- Final Payback is never assigned automatically. Pending contracts have their own recorded outcome and follow-up category.
- A three-year program can have Full, Partial and Aid records under one program, with distinct years and individual outcomes. Copying a year does not duplicate the catalog program or carry graduation remarks into an unfinished grant.
- Age and tenure precede profile remarks; grant fields align; program duplication stays compact; keyboard-accessible summaries collapse lengthy history.
- Office databases are never replaced by the development database or the empty installer seed.
