# Set up Google Sheets reporting

This guide covers Cathedra FSDP 0.5.23 and later. Complete the Google setup once, then connect each PC and Windows account that will send reports. Cathedra runs locally; no hosting is needed. Internet access is needed for Google sign-in and report updates.

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
5. Keep manually maintained work in other tabs. Cathedra manages the tab named **CATHEDRA REPORT** and replaces that tab's report values when you update it.

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

The selected permission lets an app read, create, edit and delete the consenting account's Google spreadsheets. It is broader than one workbook or tab. Cathedra's reporting code writes only the configured spreadsheet's **CATHEDRA REPORT** tab and does not request Drive-wide access. Google's [Sheets scope reference](https://developers.google.com/workspace/sheets/api/scopes) describes the permission.

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

Saving details and connecting do not send scholar records. **Update Google Sheet** becomes available after the account is connected and any edited connection details have been saved.

## 6. Send the report

1. Check that Cathedra contains the records you want to report.
2. Open **Backup & Export → Google Sheets report**.
3. If **Connection details** contains unsaved changes, choose **Save connection details** first.
4. Choose **Update Google Sheet**.
5. Review the replacement confirmation, then choose **Replace reporting tab** to send the report.
6. Wait for **Google report updated** and the successful update time. Avoid starting another update while one is pending.
7. Choose **Open reporting spreadsheet** and open **CATHEDRA REPORT**. The first update creates this tab if it does not exist.

Each update sends the full current scholar report, not just the table page visible in Cathedra. It clears stale report values, including former extra columns, and writes the replacement values in one atomic request. Other tabs remain unchanged. Cathedra writes literal values, so record text is not executed as a Google Sheets formula. Tab formatting and notes are not reset by this value replacement.

Updates are manual. Opening Cathedra or editing a scholar does not send a report automatically. Editing the Google report does not change Cathedra's local database. Keep manually maintained values outside **CATHEDRA REPORT**, and keep a database backup for recovery.

## 7. Read the 15-column report

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
| Program | The grant's program name. |
| Delivering HEI | The grant's effective delivering institution. |
| Grant type | Recorded grant type, with its Other detail when applicable. |
| Date started | Actual recorded start date in `YYYY-MM-DD`; otherwise the recorded starting term/year. |
| Date ended | Actual recorded end date in `YYYY-MM-DD`; otherwise the recorded ending term/year. |
| Extension | Recorded extension information. |
| Status | That grant's recorded outcome, such as On Going, Completed, Incomplete or Payback. |
| Remarks | Profile remarks and the grant's remarks. Labels distinguish Profile and Grant when both are present. |

The report is alphabetical by the full recorded scholar name. The first row for a scholar contains No. and the profile details beside the first grant. The following rows leave those profile cells blank and show each additional grant for the same scholar. A scholar without grants still has one profile row. Keep continuation rows together with their named scholar when sorting or filtering the sheet.

Profile remarks appear once for the scholar; each grant keeps its own remarks on its row. A missing value remains blank. A single recorded year such as **2021** stays a single year, and **Summer** remains a valid term. The report never invents a calendar date from an academic year or substitutes a completion deadline for an end date.

To make long education entries and remarks easier to read in Google Sheets, select the report cells and use **Format → Wrapping → Wrap**. Adjust column widths to your office's preferred view.

## 8. Set up the Office PC or another Windows account

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
