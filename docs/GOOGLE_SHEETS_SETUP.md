# Set up Google Sheets reporting

This guide covers Cathedra FSDP 0.5.27. Earlier releases support report delivery but do not include the reviewed pull workflow below. Complete the Google setup once, then connect each PC and Windows account that will send reports. Cathedra runs locally; no hosting is needed. Internet access is needed for Google sign-in, report updates and pulling a preview.

If this PC already reports **Google account connected**, go to [Send the report](#6-send-the-report). Installing an app update preserves its local Google connection. A replacement PC or Windows account needs its own connection.

## Before you start

Have these ready:

- A Cathedra **administrator** login.
- A Google account approved for the office's reporting work.
- A separate Google spreadsheet that this account **owns or can edit**.
- Permission to create or manage a Google Cloud project. An organization may require its administrator to do this part.

The Google Cloud account manages the connection setup. The Google account selected during **Connect Google** must also have access to the reporting spreadsheet. Adding a test user does not give that user access to a spreadsheet; those are separate settings.

## 1. Prepare the reporting spreadsheet

1. Sign into [Google Sheets](https://sheets.google.com/) with the intended reporting account.
2. Create a blank spreadsheet or choose a separate existing reporting spreadsheet. Give it a recognizable name, such as **Cathedra FSDP Reporting**.
3. Open **Share**. Confirm that the account you will select during Google sign-in is listed as **Owner** or **Editor**. If another account owns the file, its owner must grant the reporting account Editor access.
4. Copy the spreadsheet address from the browser. Cathedra accepts the full address or the spreadsheet ID between `/d/` and `/edit`.
5. Keep other manually maintained work in separate tabs. Cathedra manages **CATHEDRA REPORT** and replaces its values when you choose Update Google Sheet. If you edit this report for a later pull into Cathedra, review/apply those edits before sending another replacement.

Use your office's sharing rules for confidential records. Google explains its roles and sharing controls in [Share files from Google Drive](https://support.google.com/drive/answer/2494822).

## 2. Create a Google Cloud project and enable Sheets

1. Open [Google Cloud Console](https://console.cloud.google.com/) and sign in with the account allowed to manage the integration.
2. Open the project selector beside the Google Cloud logo. Select an approved existing project, or choose **New project**.
3. For a new project, enter a name such as **Cathedra FSDP**, choose the organization/location if required, and choose **Create**.
4. Select that project after creation. Check the project name at the top before continuing; the API and OAuth client must belong to the same project.
5. Open **APIs & Services → Library**, search for **Google Sheets API**, and open its product page.
6. Choose **Enable**. If it is already enabled, the page offers management controls instead.

You do not need to install Python or run Google's sample program to use the packaged Cathedra app. See Google's [project setup](https://developers.google.com/workspace/guides/create-project) and [Sheets API quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python) for the Cloud setup screens.

## 3. Configure Google Auth platform

1. In the same project, open **Google Auth platform → Branding**. Choose **Get started** if the project is not configured yet.
2. Enter **Cathedra FSDP** as the app name. Select your support email and provide the requested contact email.
3. Choose an audience. For a personal Gmail account, use **External**. Use **Internal** only when your Google Workspace organization offers it and the intended users belong to that organization.
4. Review the required Google terms, finish the setup, and save/create the configuration.
5. For an **External** app whose publishing status is **Testing**, open **Audience → Test users → Add users**. Enter the exact Google account that will connect Cathedra, then save. Repeat for each authorized reporting account.
6. Open **Data Access → Add or remove scopes**. Select or enter `https://www.googleapis.com/auth/spreadsheets`, then update and save the selection.

Follow [Google's OAuth consent setup](https://developers.google.com/workspace/guides/configure-oauth-consent) if the project uses a different setup screen.

The selected permission lets an app read, create, edit and delete the consenting account's Google spreadsheets. It is broader than one workbook or tab. Cathedra reads and writes only the configured spreadsheet's **CATHEDRA REPORT** tab and does not request Drive-wide access. Google's [Sheets scope reference](https://developers.google.com/workspace/sheets/api/scopes) describes the permission.

External/Testing is useful for an approved test, but Google's refresh token for this Sheets connection expires after **seven days**. Plan to reconnect while testing. A long-term office deployment needs the organization's appropriate audience, publishing and verification decisions; changing a local Cathedra setting does not complete Google's verification. See [Google's refresh-token expiration rules](https://developers.google.com/identity/protocols/oauth2#expiration).

## 4. Download the Desktop connection file

1. Open **Google Auth platform → Clients → Create client** in the same project.
2. Choose **Desktop app** as the application type.
3. Give the client a name, such as **Cathedra FSDP Desktop**, and choose **Create**.
4. Use **Download JSON** or the download control for that client. Keep the downloaded `.json` file in a private location where you can find it again.
5. Leave the file unchanged. Cathedra expects Google's downloaded Desktop OAuth configuration.

Choose a Desktop OAuth client, not a Web application client, service account key or API key. Do not paste the client secret into a message or commit the JSON file to GitHub. Google's [credential guide](https://developers.google.com/workspace/guides/create-credentials#desktop-app) describes Desktop clients.

## 5. Save the connection in Cathedra

1. Open the Cathedra installation on the PC that will send reports and sign in as an **administrator**.
2. Select **Backup & Export** in the sidebar.
3. Select the **Google Sheets report** section shortcut near the top, or scroll to that card.
4. Expand **Connection details** if necessary.
5. Paste your spreadsheet address into **Reporting spreadsheet URL or ID**.
6. Under **Google Desktop credentials JSON**, choose the downloaded file.
7. Choose **Save connection details**. Wait for **Connection details saved**.
8. Choose **Connect Google**. The default browser opens Google's sign-in page.
9. Select the Google account that has Owner or Editor access to your spreadsheet. Review the requested spreadsheet permission and complete Google's consent flow.
10. Return to Cathedra and wait for **Google account connected**. A browser page saying sign-in was received is an intermediate step; Cathedra must finish saving the connection before it is ready.

The sign-in window lasts three minutes. If it expires, choose **Connect Google** again. You do not need to recreate the Cloud project or download a new JSON file for an ordinary retry.

Saving details and connecting do not send scholar records or import sheet values. **Update Google Sheet** becomes available after the account is connected and any edited connection details have been saved.

## 6. Send the report

1. Check that Cathedra contains the records you want to report.
2. Open **Backup & Export → Google Sheets report**.
3. If **Connection details** contains unsaved changes, choose **Save connection details** first.
4. Choose **Update Google Sheet**.
5. Review the replacement confirmation. If the Google report contains edits you want to keep locally, cancel and complete [Pull and review sheet changes](#8-pull-and-review-sheet-changes) first. Otherwise choose **Replace reporting tab** to send the report.
6. Wait for **Google report updated** and the successful update time. Avoid starting another update while one is pending.
7. Choose **Open reporting spreadsheet** and open **CATHEDRA REPORT**. The first update creates this tab if it does not exist.

Each update sends the full current scholar report, not just the table page visible in Cathedra. It clears stale report values, including former extra columns, and writes the replacement values in one atomic request. Other tabs remain unchanged. Cathedra writes literal values, so record text is not executed as a Google Sheets formula. Tab formatting and notes are not reset by this value replacement.

Updates are manual. Opening Cathedra or editing a scholar does not send a report automatically. Editing the Google report does not automatically change Cathedra's local database. Only an administrator's reviewed pull applies selected sheet values locally. Keep unrelated manual work outside **CATHEDRA REPORT**, and keep a database backup for recovery.

## 7. Read the 16-column report

Google Sheets reporting has this column order. The downloadable CSV reports retain their separate, fuller [export formats](EXPORT_SCHEMAS.md).

| Column | What appears |
| --- | --- |
| No. | Scholar sequence number, starting at 1 in the alphabetical report. This is not the internal scholar ID. |
| Name | Scholar name. |
| Age | Recorded age; blank when not recorded. |
| Tenure | Recorded tenure in years, including a valid zero. |
| Department | The scholar's college or Staff classification; Unknown when affiliation is not recorded. |
| Rank/position | Recorded rank or position. |
| Previous degree | All recorded education-background entries, separated by line breaks. Available level, institution and graduation year accompany the degree. Older previous-degree text is used when no education entries exist. |
| Profile remarks | Whole-profile remarks, once on the scholar's named row (column H). |
| Program | The grant's program name. |
| Delivering HEI | The grant's effective delivering institution. |
| Grant type | Recorded grant type, with its Other detail when applicable. |
| Date started | Actual recorded start date in `YYYY-MM-DD`; otherwise the recorded starting term/year. |
| Date ended | Actual recorded end date in `YYYY-MM-DD`; otherwise the recorded ending term/year. |
| Extension | Recorded extension information. |
| Status | That grant's recorded outcome, such as On Going, Completed, Incomplete or Payback. |
| Remarks | Only this annual grant's remarks (column P). |

The report is alphabetical by the full recorded scholar name. The first row for a scholar contains No. and the profile details beside the first grant. The following rows leave those profile cells blank and show each additional grant for the same scholar. A scholar without grants still has one profile row. Keep continuation rows together with their named scholar when sorting or filtering the sheet.

Profile remarks appear once in H for the scholar; P contains each grant's own remarks on its row. For a scholar without grants, H still contains profile remarks and P stays blank. A missing value remains blank. A single recorded year such as **2021** stays a single year, and **Summer** remains a valid term. The report never invents a calendar date from an academic year or substitutes a completion deadline for an end date.

To make long education entries and remarks easier to read in Google Sheets, select the report cells and use **Format → Wrapping → Wrap**. Adjust column widths to your office's preferred view.

## 8. Pull and review sheet changes

Use this when approved edits in **CATHEDRA REPORT** should be added to your local Cathedra records. It is a manual review, not automatic synchronization.

1. Check that you are using the Office installation containing the current records. Create a local database backup before a large import so you have a complete recovery point.
2. In Google Sheets, keep the exact report headings and column order above. Keep each named scholar row immediately followed by their additional grant rows. Do not sort only part of the table. The **No.** column is a report sequence, not a local record ID.
3. Open **Backup & Export → Google Sheets report** as a Cathedra administrator. Confirm the intended saved spreadsheet and connected Google account. Save any edited connection details first.
4. Choose **Pull from Google Sheet**. Cathedra reads the existing **CATHEDRA REPORT** tab and shows **Review Google Sheet changes**. This step writes neither local records nor Google values. If the tab does not exist, send an initial report first or prepare it with the exact headings; pulling does not create a tab.
5. Review the **Current** and **Google Sheet** values for a scholar. Nothing is selected automatically. Choose the correct existing scholar or explicitly create a new scholar. An exact unique name can suggest a match, but namesakes require your decision. Changing a name does not prove that it is a different person.
6. Review each grant row. Select the correct existing annual grant to update it, or explicitly choose a new independent application. Where the same program and period repeat, choose deliberately. A new imported grant receives its own application identity; it is not automatically grouped as another year of an existing application. Uncheck grant rows you do not want to apply.
7. Select the profiles you have reviewed. Choose **Review selected changes**, read the confirmation, then choose **Apply selected changes**. Up to 100 selected profiles are saved as one batch. A successful result shows the created/updated counts.
8. Reopen a few affected local profiles and confirm the intended notes, dates, outcomes and application grouping. When ready, a later **Update Google Sheet** sends the complete current local report back to the reporting tab.

### What is retained, changed or cleared

- Existing education entries, requirements, hard/soft-copy facts, unselected grants, application identity, repayment progress, case state, deadlines and other unreported details stay intact. Records absent from the sheet are not deleted.
- For a new profile, each nonblank **Previous degree** line is retained as a text education entry. Cathedra does not guess its institution, degree level or graduation year. Existing education is retained instead of replaced by a flattened report cell.
- A present blank **Age**, **Tenure**, **Rank/position**, **Profile remarks** or grant **Remarks** cell clears that reported field when selected. A recorded zero remains zero. Read the comparison before confirming. A blank **Department** means the profile's affiliation becomes Unknown under the existing classification rule.
- Blank **Status**, **Date started** or **Date ended** cells preserve existing facts. An exact `YYYY-MM-DD` value updates only the exact date; a term/year label updates only the represented period details. Hidden academic periods and optional completion/payment facts are not erased by the report's display choice.
- The older fifteen-column report is accepted for its other fields. Its combined **Remarks** cannot be reliably separated, so existing profile/grant remarks remain unchanged. Send the new sixteen-column report when you are ready to use separate remark columns.

### Conflicts, expiry and retry

A preview is valid for twenty minutes and belongs to the administrator who fetched it. Choose **Refresh preview** when it expires, then review and select again. If another edit or restore has changed a captured target, the complete selected batch is rejected: refresh and compare the latest values instead of overwriting them.

If the save result is uncertain, use the provided identical retry. Cathedra remembers a confirmed batch and returns its original result instead of applying it twice, including after a server restart. Changing the selected records for the same attempt causes a conflict. A refreshed preview is a new review, so first check whether an uncertain previous batch was already saved. Closing/reloading the review loses unsaved choices, not committed records.

The preview reads at most 2,000 report data rows; split larger work into reviewed batches or use the normal local workflow. Applying selected changes does not update Google or refresh the report's last-send time. While a preview is open, finish or discard it before changing the Google destination or sending a replacement report.

## 9. Set up the Office PC or another Windows account

1. Update the existing Office installation using the supported update instructions in [GitHub Office updates](GITHUB_OFFICE_UPDATES.md). Preserve its existing `data` folder and scholar database.
2. Open that installation using the Windows account that normally runs Cathedra.
3. Repeat [Save the connection in Cathedra](#5-save-the-connection-in-cathedra) on that PC. An approved Desktop client JSON may be reused, but each Windows account must complete Google sign-in itself.
4. If the Google account differs from the one used during development, confirm its test-user/organization eligibility and its Editor or Owner access to the reporting spreadsheet.
5. Send the first Office report only after confirming that this is the installation containing the current Office records.

Cathedra encrypts its saved connection and continuing-access token for the current Windows user in `data/google-connection.bin`. That encrypted file is not portable to another PC or Windows account. It is excluded from database backups, update packages and GitHub source. Do not replace an Office database or copy a development connection file as part of Google setup.

Ordinary app updates preserve the connection already saved on that PC. **Disconnect Google** forgets the local token. To remove Google's permission too, use Google Account → Security → Third-party connections and remove the app's access.

## Troubleshooting

### “Access blocked” or “developer-approved testers” during sign-in

1. In Google Cloud Console, select the project that owns the downloaded Desktop client.
2. Open **Google Auth platform → Audience**.
3. If the app is External/Testing, add the exact sign-in email under **Test users** and save.
4. Return to Cathedra and choose **Connect Google** or **Reconnect Google** to start a fresh sign-in. Select that same account.

Test-user approval controls who can authorize the app. It does not share the spreadsheet with that account.

### Google is connected, but the reporting sheet cannot be opened or updated

1. Open the saved spreadsheet address in a browser using the same Google account selected for Cathedra.
2. Check that it is the intended file. In **Share**, confirm Owner or Editor access; Viewer access cannot update the report.
3. If a different account owns the file, ask its owner to grant the reporting account Editor access. Confirm access to the file itself, not just that the Google account exists.
4. If Cathedra has the wrong spreadsheet address, edit **Connection details** and save the correct one. You can change the target while retaining the same client and authorized account.
5. If the wrong Google account was connected, choose **Reconnect Google** and select the intended account. Test-user approval and file access must both apply to that account.

The Google message **The caller does not have permission** indicates a file-access denial; downloading the same client JSON again does not grant access to the spreadsheet.

### Sheets API disabled, missing permission or organization policy

1. Check that **Google Sheets API** is enabled in the project owning the Desktop client, not a different selected Cloud project.
2. Confirm the configured Sheets scope in **Google Auth platform → Data Access**, then reconnect and review the spreadsheet permission in Google's consent page.
3. If Google reports an organization restriction, contact the organization's administrator. Its policy may restrict account use, app authorization or external file sharing.

### Connection expired, revoked or cannot be unlocked

- For an expired or revoked Google permission, choose **Reconnect Google**. External/Testing refresh tokens for this integration expire after seven days.
- On a replacement PC or under another Windows account, select the Desktop JSON and configure/sign in again. Copying `google-connection.bin` does not transfer the connection.
- If Cathedra cannot read an old encrypted connection, explicitly save valid Desktop credentials again or use **Forget Google connection**, then configure and connect. Keep the original scholar database unchanged.

### Sign-in timed out or the browser did not open

Finish within the three-minute sign-in window. If it expires, start a fresh connection from Cathedra. Check that Windows has a working default browser and that the PC can reach Google. After a failed status check, use **Refresh Google connection** before retrying.

### An update failed or its result is uncertain

Check **CATHEDRA REPORT** before retrying, then retry when the network is available. Cathedra displays a successful update time only after Google confirms delivery. A failed report update does not clear your local database. For reports exceeding the app's single-update size limit, use the local CSV export.

## Official references

- [Google Cloud project setup](https://developers.google.com/workspace/guides/create-project)
- [Google Sheets API and Desktop setup quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)
- [Google Auth platform audience, test users and scopes](https://developers.google.com/workspace/guides/configure-oauth-consent)
- [Create Desktop OAuth credentials](https://developers.google.com/workspace/guides/create-credentials#desktop-app)
- [Google Sheets permission scopes](https://developers.google.com/workspace/sheets/api/scopes)
- [Share a spreadsheet and choose roles](https://support.google.com/drive/answer/2494822)
- [Google refresh-token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
- [UpdateCells values and clearing behavior](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#UpdateCellsRequest)

### Pull fails, has no tab or finds unexpected headings

Confirm that the connected account can open the saved spreadsheet and that **CATHEDRA REPORT** exists as a normal grid tab. Use exactly the sixteen-column headings shown above, or retain the original fifteen-column Cathedra order. Do not add data after the report columns. Keep Name on each scholar's first row and continuation grant rows directly below it. Each grant row with details needs Program. Correct the indicated source row, then pull a fresh preview; a failed preview has saved no local records.

### A pull says the selected records changed

Refresh the preview and compare the latest local values. Another edit or a restore may have changed the captured profile even if its name looks the same. The rejected batch is not partially applied. For an uncertain result, use the provided identical retry before starting a different batch.
