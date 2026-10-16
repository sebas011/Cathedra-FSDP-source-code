# Office operation and safe updates

## Sign-in and recovery copies

Cathedra locks after 30 minutes without user activity. Sign in again with the same account to resume unfinished forms. Background updates do not keep an unattended session open; the absolute sign-in limit remains 12 hours.

On first-time setup, the private code appears in a local dialog. It is never included in the browser address. Existing accounts use the normal sign-in page. If setup has not been completed and the code is lost, close and reopen Cathedra to obtain a new code.

Startup saves a verified daily recovery copy. The newest 14 unpinned daily copies and 30 unpinned pre-delete copies are kept; manual and pinned copies remain until explicitly managed. Deleting a scholar first creates a verified recovery copy and stops if that copy fails. Copy backups to private off-device storage as well; local copies do not protect against losing the computer.

Transferred and Withdrawn grants remain eligible for calculated payback review when unfinished and past the three-year grace period. Recorded Payback remains visible independently of calculated review.

## Daily work

Name and Program Applied are essential fields. Dates, years, personnel classification and education detail remain optional. The directory uses the newest grant for the overall scholar status, with year, term and record ID determining order. Individual grant statuses stay in the profile. Name search matches the beginning of each name word.

The directory is alphabetical by the full recorded name, ignoring case and surrounding spaces, with scholar ID breaking ties. Names are not automatically rearranged into surname order. Hard copy and Soft copy are independent optional profile choices: Available, Not available or Not recorded. A scholar can have only one kind of copy, both or neither. These facts appear on the directory/profile and do not mark requirements complete or upload files. Existing unchecked records remain Not recorded.

Use separate annual grants for multi-year participation. A specific optional contract completion date starts the three-calendar-year grace period. Its final day is included; review starts the following day. Recorded Completed in the same application clears computed follow-up across its annual grants; a separate later application in the same program remains independent. Older unassigned records retain their previous same-program scope until reviewed and assigned. Recorded Payback and Payback pending contract stay visible. Did Not Avail does not become an overdue candidate. Missing dates cannot be calculated and are never guessed. Open/Closed case status is separate and does not override the recorded outcome.

## Program applications and annual grants

Use the single Program Applied field to enter the program name. Its catalog identity is resolved when saving; the separate Existing program selector has been removed. Keep established program names consistent. Program category optionally distinguishes Degree, Certification and Enhancement; Type of Grant still describes funding and remains separate.

Use **Copy for next year** for another annual grant in the same application. Use **New application** for a later enrollment in the same program. For example, the 1st 2021-2022 to 2nd 2022-2023 application can stack separately from the 1st 2023-2024 to 2nd 2024-2025 application, while each keeps its own annual grant rows. The new-application draft proposes the next period after the previous end year and clears prior remarks/outcome/actual dates; review its proposed terms/years before saving. Save Grant finishes the draft; Save Scholar persists it. Administrators have the copy/new-application actions.

Each application summary shows its overall period. The Application control can associate a reviewed grant with the intended group. Existing unassigned records stay together under their original program until explicitly assigned; the upgrade never guesses application boundaries from a gap in years or a repeated program name. Do not duplicate the program catalog merely to separate a later enrollment. Completing one explicit application does not clear another application's calculated contract follow-up.

## Compact Office Log entries

After a confirmed log save, the editor closes and focus returns to Add log entry. Failed or uncertain saves leave the original draft open for a safe retry. Saved entries stack as compact date/type/document/scholar rows; expand a row for notes, departments and author. Entries remain append-only, and a correction uses a subsequent explanatory entry.

Confirmed saving clears active log search/type filters and returns to the first page. The register remains ordered by event date, so a backdated entry can appear on a later page. Log CSV includes all entries matching its filters. Printing temporarily expands all entries on the loaded page and restores their previous state afterward; it does not load other pages.

Automatically added education is labelled in the editor. Remove and Save Scholar to retain its removal. Select Restore for the removed program and save to restore it. Corrected manual entries are retained; graduation years are extracted only from clear associated graduation remarks. Manual years and removals are preserved.

If a new scholar save is not confirmed, the original details remain frozen. Retry Save Scholar to check the same request. Do not open a new form and recreate it before checking the directory. Requests are retained for the life of the local database; no automatic request-ledger deletion occurs. The same key is scoped to its original account. A deleted result is reported rather than recreated.

Create a local backup at least weekly and keep a private off-device copy. Make a verified backup immediately before a major change. CSV files are reports, not complete recovery backups. Database backups include accounts and must be stored privately. Review an isolated restore separately.

## Read scholar and grant CSV files

Scholar-directory, Dashboard report detail and contract follow-up exports keep all of a scholar's matching grants together, with one grant per row. The first row shows the scholar's name and profile information beside the first grant. Following rows leave the scholar/profile cells empty and show the next grant for that same scholar. The next named row starts another scholar. No extra blank row separates scholars. A scholar with no grants has one profile row in directory and report detail, with empty grant fields.

Read each grant's own terms, academic years, dates, outcome, case status and remarks across its row. Empty scholar cells mean the same scholar as above; an empty optional grant field means no value was recorded for that grant. Keep continuation rows with their named scholar when sorting or filtering a spreadsheet. Exports include all matching records, even when the screen shows only one page. In Dashboard CSV, find the scholar/grant detail header after the totals and follow-up sections; those summary sections keep their existing layout.

Profile Remarks and grant Remarks stay in separate columns. Education and Office Log exports keep one complete row per education entry or log entry. Store files privately and use a database backup, rather than CSV, for recovery. See [current export columns](EXPORT_SCHEMAS.md) for the full ordered headers.

## Update the Office PC

Perform these steps on the **Office PC**. There are two separate folders: the **new update folder** you transferred, and the **existing Office app folder** containing the newest scholar records. The updater installs application files into the existing folder and keeps its database.

1. Copy the complete `Cathedra-FSDP-0.5.20-Update` folder from the transfer drive to the Office Desktop. Keep its name and all contents, including `_internal`, `tools` and `docs`. Do not paste it into the existing Office app folder. If it arrived as a ZIP, extract it first.
2. Open the Office app you normally use and confirm that its newest scholars are present. As an administrator, open **Backup & Export**, click **Create Backup**, choose that newest backup and click **Download Selected Backup**. Keep the downloaded backup privately outside the app folder. Note the scholar total and a couple of recently added scholars for comparison afterward.
3. Find the existing app folder in File Explorer. If you use a desktop shortcut, right-click it, open **Properties** and choose **Open File Location**. The installation folder contains `Cathedra FSDP.exe` and `data\cathedra.db`. Copy the folder address from File Explorer's address bar; select the folder above `data`, not the `data` folder itself.
4. Save any edits. Use **Exit Cathedra** inside the app, confirm exit, wait for **Cathedra has stopped**, then close its window.
5. Press **Windows + R**, type `powershell`, then press Enter. Copy the entire command block below, paste it into PowerShell and press Enter. It asks for the two folder addresses: first the NEW update folder, then the EXISTING Office app folder. For each, copy its address from File Explorer, paste it at the prompt and press Enter. Folder paths can contain spaces; do not add an executable filename.

```powershell
& {
    $updateFolder = (Read-Host 'Paste the NEW Cathedra-FSDP-0.5.20-Update folder address').Trim().Trim('"')
    $officeFolder = (Read-Host 'Paste the EXISTING Office app folder address').Trim().Trim('"')
    if (-not (Test-Path -LiteralPath (Join-Path $updateFolder 'tools\update-office.ps1') -PathType Leaf)) { throw 'The NEW folder must contain tools\update-office.ps1. Select the extracted update folder.' }
    if (-not (Test-Path -LiteralPath (Join-Path $officeFolder 'data\cathedra.db') -PathType Leaf)) { throw 'The EXISTING folder must contain data\cathedra.db. Select the folder containing your current Office app.' }
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $updateFolder 'tools\update-office.ps1') -Installation $officeFolder
}
```

6. Let the updater finish. Successful output includes `"status": "verified"`, `"version": "0.5.19"` and `"database_replaced": false`. It checks file hashes, locks the existing data, makes a protected snapshot, rehearses migration on a private copy when needed, retains the old runtime and checks the replacement using synthetic data. Runtime replacement does not migrate the working database. No Python or Node installation is required.
7. Open **the existing Office app** again through your usual shortcut or its original `Cathedra FSDP.exe`. Allow its first startup to finish any protected migration required by your older installation. Confirm version **0.5.19**, the scholar total, your recent additions, accounts, profile remarks and annual grants. Export a scholar with multiple grants: the first row should show the scholar and first grant, followed by one row per remaining grant. The former Graduated label remains Completed, and **Office log** remains available. Keep the backup and recovery archive until these checks pass.

The update folder contains an empty seed for new installations, not your Office records. Do not copy a development `data` folder or replace the Office `data\cathedra.db` manually.

If PowerShell shows an error, keep the full message and receipt path. A missing-database message usually means the wrong existing folder was selected. An active-app message requires exiting Cathedra normally before retrying. If the app is already on 0.5.20, confirm that version in the existing app instead of forcing another update. For other failures, retain the data and recovery files and review the message before attempting recovery. Do not restore an older database just to replace application files.

Supported source versions begin at 0.5.4 and must have a valid FSDP product/history and runtime manifest. Wrong products, downgrades, active apps, missing databases, linked folders and damaged packages stop safely. The update journal and receipts are inside the existing data folder; recovery snapshots are inside its backups folder. No project database is part of the update payload.

Version 0.5.19 also handles unlisted runtime/tool leftovers in an existing installation. Every declared old file must still match its recorded size and hash. The updater constructs a clean verified preceding-runtime archive, separately preserves all leftovers under `data\updates\runtime-residue-...`, and installs only the incoming manifest's runtime files. Its receipt records `existing_runtime_residue_repaired`, `runtime_residue_files` and `runtime_residue_archive`. Do not manually delete old runtime files or edit the manifest to bypass an error. Missing or changed declared files require review rather than automatic residue repair.

A verifier failure during preflight can occur before a new `update-state.json`, snapshot or replacement exists. The error now identifies the phase and selected folder and lists affected paths. Keep any existing journal and receipt. A failed preflight does not by itself require `-Rollback`; that option is for a recorded interrupted replacement or supported deliberate runtime rollback. Never delete/reset a journal or restore an older database merely to retry an application update.

## Recovery

An interrupted file replacement can be rolled back by rerunning the new package updater with -Rollback. Runtime rollback is allowed only while the active database exactly matches the pre-replacement identity/hash; it never restores an old database automatically. An interrupted replacement must be resolved before another update.

Once migration or later Office edits occur, automatic old-runtime rollback is refused. Close the app and retain the current database plus protected snapshot. Before work resumes, an administrator may restore the matching old runtime and verified pre-upgrade database together. After new edits, use a reviewed forward repair or deliberate recovery that preserves those edits. Never restore an older snapshot just to fix an application-file problem.

A failed required snapshot stops migration. An existing data folder containing recovery/settings files but no database does not silently reseed. Free space must accommodate staged/new/old runtimes and database copies.

## Private diagnostics

Size-limited operations logs live under data/diagnostics. Backup and recovery events are available in Backup & Export > Maintenance history, and persist across database restore. This local journal is not tamper-proof and cannot reconstruct actions from older releases.


## Version 0.5.12

Profile Remarks is an optional whole-scholar text field, separate from grant Remarks. The directory and Dashboard report exports include a distinct Profile Remarks column. Line breaks are retained and spreadsheet formula protection remains enabled. A client that omits the new field does not erase existing remarks; an explicit empty field clears them.

College / Staff uses CIT, CAS, COED, COE, CCJ, COF, CBMA, CCS and Staff. Other affiliations become Staff and personnel type Staff; original affiliation labels are retained in Profile Remarks. College personnel types remain as recorded. The first startup makes a protected recovery snapshot before migration 10, preserves scholar/grant identities and grant remarks, and updates only affected profile revisions. Keep Office data when installing an update.

Dashboard explanations are available in the searchable Office Guide. The overview compares colleges and Staff with vertical bars, shows scholar status proportions in a doughnut, and shows grant-type proportions in a pie. Counts and percentages remain visible beside the composition charts. Recent scholars and follow-up have separate sections; chart scrolling stays within the chart region.

## Profile and annual grants in 0.5.14

Personnel type follows affiliation: eight colleges mean Faculty, other known affiliations mean Staff, and missing information means Unknown. Profile remarks follow the scholar facts. Grant history groups years under one program and each group/annual record can be expanded. Printing temporarily expands all records.

For a multi-year program, retain the same Program Applied, make a separate grant for each academic year, and choose each year’s grant type. Copy for next year advances recognized year ranges, resets outcome to On Going and clears completion dates and extension; remarks are retained for review. Duplicate program is only for a distinct catalog program.

Use Payback pending contract while the repayment contract is being arranged. Record final Payback after the office completes that contract; the system never assigns it automatically. Transferred is another available recorded outcome.

Clear affirmative remarks such as Graduated in 2022 or Graduation year: 2022 add the program to education. Negative, expected, uncertain and future graduation statements are skipped. End periods and contract dates do not prove graduation. Education extraction never changes recorded grant status or payback obligations.

## Evidence and filtering corrections in 0.5.15

Summer remains supported alongside 1st/2nd/3rd. Education inference accepts direct current-program graduation claims. Remarks about a previous degree, another person or a different qualification are skipped. Explicit full dates must be valid and cannot be future dates; ambiguous numeric dates remain for review. A year-only statement does not invent a day. Saving unsupported remarks is still allowed.

Existing education and manual corrections are preserved. Review and correct/remove an achievement in the existing editor when necessary; do not delete all automatically linked entries. A maintainer has a read-only snapshot review tool described in the technical requirements. A flagged entry may still be a valid historical achievement.

Recorded Payback and Payback pending contract take precedence over completion within an application. Education inferred from remarks does not change recorded status or payback assessment. Category counts describe the college/year scope; paged results, complete results and CSV share the selected category.

Staff can select an existing program or create a missing typed program name during Save Scholar. Use the existing-program selector for subsequent annual grants. Direct catalog administration and duplication are available to administrators in Settings → Programs. If older equivalent names are flagged, select the correct existing identity; no grant history is merged automatically.

## Education-year edits and printing in 0.5.16

An explicit correction or clear of an automatically generated education year remains in effect after saving and reopening. Other graduation evidence and each grant's recorded outcome remain separate.

Use Cathedra's Print buttons to prepare all matching directory records, or the Dashboard overview with the selected report and contract results. Preparation does not replace the table page you are viewing. Changing filters or leaving the page cancels a pending print; start again from the desired view. Browser Ctrl+P prints only the currently loaded content and includes that label. Review the preview before printing on the Office printer.

Use the [Office acceptance checklist](current/OFFICE_ACCEPTANCE.md) after updating the actual Office PC. That acceptance remains open until checked there. See [current export contracts](EXPORT_SCHEMAS.md) for report columns.

## Record entry and Office Log in 0.5.17

New or edited scholar/program details, education, remarks and Office Log text use capital letters. Existing stored identities are not mass-renamed, and usernames/passwords keep their original case. Enter eight academic-year digits, such as 20262027, to obtain 2026-2027; recognized consecutive ranges with common separators also format with a dash. A complete single four-digit year gains its following year when leaving the field or saving the grant. Partial/custom optional year information can still be saved.

Grant outcome appears after remarks near Save Grant. Choose Completed for the former Graduated outcome; it adds the current program to education even if the remarks do not contain recognizable graduation words. A grant's optional Graduation date is separate from Contract completed; an associated year is added only where it does not replace a manual education choice. Record Payback or Payback pending contract only after the appropriate office review. Choose Open or Closed for the grant's case independently; closing the case does not prove completion or repayment.

Profile, education and grant actions use icons; their labels/tooltips identify each action. Age and tenure ignore accidental wheel changes and remain editable with the keyboard. Collapse the whole grant history when you need more room. Copy for next year retains the program and remarks, advances a recognized year range, starts On Going/Open and clears all actual dates and extension. Review the copied remarks for that year's context. Finish Save Grant, then Save Scholar to persist that draft.

Use Office Log for a general note, a document received or a document transferred. Enter a description, optional document name, from/to departments and scholar link; an omitted date uses today's date. Saving adds the entry immediately, with your account identity and a scholar-name snapshot where linked. Entries are append-only: record a correction in another entry. After an uncertain response, retry the original entry rather than changing its details or recreating it. Search/type/scholar filters apply to paged review and complete CSV export. Office Log records movements and notes; it does not upload or store document files and does not replace administrator Activity History.
