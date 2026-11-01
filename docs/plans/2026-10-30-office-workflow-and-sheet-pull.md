# Office workflow and Google Sheets pull — 0.5.27

## Approved changes

1. Make the independently scrolling sidebar navigation easier to see and drag, including short windows, collapsed navigation and Windows high-contrast mode.
2. Existing scholars can save all pending changes directly from Identity, Education or Programs & grants. Keep the same atomic aggregate save, revision checks, nested-entry guards and uncertain-save recovery. New profiles retain guided Review.
3. Give profile remarks their own Google report column H. The report becomes sixteen columns; grant remarks remain at P. Preserve one row per grant and profile facts only on the first row. CSV contracts stay unchanged.
4. The owner chose a pull preview for both new scholars and updates. Pull reads only the configured reporting tab; it never automatically applies values or writes back to Google.

## Reconciliation and data preservation

The report number is an ordinal, not a record ID. Suggest an existing scholar only when its normalized name is unique. Suggest an existing annual grant only when program and recorded periods identify it uniquely. The preview lets an administrator explicitly select another existing profile/grant or add a new profile/application. Ambiguous matches require a choice; selected targets cannot appear twice in one apply request.

Show previous and new reported values. Preserve all fields absent from the report, all unselected grants and existing education, requirements, application grouping, deadlines, case/payment outcomes and document availability. New education text is retained as separate text entries without guessing institution/year structure. An explicitly new grant starts an independent application. Older fifteen-column reports can supply their other facts, but their combined remarks must not overwrite separate notes.

An expiring, user-bound in-memory snapshot supplies immutable reviewed values. Apply uses a single SQLite writer transaction, verifies the captured target revision and checks new-name conflicts again. Schema 18 adds only a durable import receipt so retrying an uncertain response cannot duplicate an already committed batch, including after a service restart. Existing history capture stays in the same transaction. Changing the selection after an already committed attempt is rejected.

## Verification

Use offline Google transport fixtures and disposable databases only. Cover source bounds/header parsing, zero/blank values, same-name and repeated-program ambiguity, preservation of unreported facts, cross-scholar grant IDs, target changes, atomic rollback and durable retries. Verify quick save without Review, nested draft blocking, sidebar scrolling at short heights, and full preview/confirmation behavior on desktop and a narrow layout. Run regression/static/build gates, protected schema-17 upgrade rehearsal and native package checks before replacing the local runtime. No live scholar transmission or Office database replacement is part of development verification.
