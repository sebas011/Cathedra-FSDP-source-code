# Owner-controlled Google bridge

This folder is source for the optional Cathedra shared workspace. Nothing here deploys itself or uploads local records. The Office PC holds the authoritative first dataset. Develop and test with a separate empty workspace.

The owner runs the bridge; approved PCs authenticate with individual revocable device credentials. The storage spreadsheet is a newly created, owner-only file. Its three protected tabs are the canonical records, metadata and durable operation receipts. A separate spreadsheet is the readable sixteen-column report. Sharing that report does not share the storage file. Google owners can still edit their own protected files: keep the storage file closed and edit records through Cathedra.

## Owner setup

1. Create a standalone Google Apps Script project using the intended owner account. Keep the script project private. Copy `Code.js` into its script editor. Enable displaying the manifest and replace it with `appsscript.json`.
2. Enable the advanced **Google Sheets API v4** and **Google Drive API v3** services. If this project uses a standard Google Cloud project, enable both APIs there too.
3. Review the scopes before authorization. Sheets access creates and updates the two configured spreadsheets. `drive.file` audits only the newly app-created storage file; it does not request full Drive access. Email identifies the bridge owner. If `drive.file` cannot see the new file, stop and review the API/project setup rather than adding broader Drive access.
4. Run `setupWorkspace()` directly in the Apps Script editor. It creates a new storage file and a new report file. To use an existing report instead, temporarily add an owner-only wrapper such as `function ownerSetup() { return setupWorkspace("YOUR_REPORT_SPREADSHEET_ID"); }` and run it. Never supply the existing report as a storage file. Setup never adopts or overwrites an existing storage spreadsheet.
5. Review the returned storage/report addresses and workspace ID in the editor's function result/debugger. In Script Properties, the identifiers are stored as STORAGE_ID, REPORT_ID and WORKSPACE_ID. There are no device secrets there—only registration hashes. Confirm the storage Share panel is **Restricted** with only the owner. The bridge audits all Drive permission pages at setup and before every authenticated request, and refuses operation if storage is shared, trashed, transferred, placed in a shared drive, or its protection removed. It does not silently change an existing sharing policy.
6. If setup stops after creating a file, its partial STORAGE_ID marker remains. Inspect that new, empty file and the cause before retrying; do not remove markers merely to force a second setup. There are no records to recover until the explicit Office initialization.
7. Deploy as a **Web app**, executing as **Me / the owner**. The desktop transport needs the HTTPS `/macros/s/.../exec` URL. An anonymous-reachable deployment exposes only the authenticated endpoint: every data request still requires a registered device credential. Review this access setting before deploying. Google Workspace policy may prohibit that setting; do not bypass organizational policy. Keep the deployment URL and device registration details private.
8. In Cathedra's Shared workspace settings, save that deployment URL. Cathedra generates and Windows-encrypts its own private device credential and displays only its device ID and SHA-256 registration hash.
9. Register each intended PC by running an owner wrapper that calls `registerDevice("DEVICE_UUID", "SHA256_HASH", "OFFICE PC", true)` for the authoritative Office PC. For every other PC pass `false` as the final argument. The hash is not the credential. The raw device credential is never manually copied into the editor, included in a URL, logged, or stored in Sheets. Only the encrypted device file on its original PC stores it; requests send it over HTTPS to the bridge for comparison with the registration hash.
10. Test the connection in the app. On the Office PC create a local backup, verify the newest scholars, then explicitly choose **Initialize from this Office PC** against the empty shared workspace. Other PCs join and download the shared data after reviewing their local replacement and recovery copy. Connecting alone never seeds the cloud.
11. Keep `Code.js`, the manifest, and Google setup under owner control. Source updates need a new reviewed deployment version. Use `revokeDevice("DEVICE_UUID")` from an owner wrapper to revoke a lost/retired PC; revocation is checked again under the script lock so an operation waiting behind another device cannot continue with stale authorization.

## Synchronization and reporting

### Copyable owner setup wrappers

Add these functions below the supplied script, replace only the placeholders, select the desired function in the editor toolbar and click **Run**. The first function creates two new files. Its log contains only file addresses and the workspace ID, never scholar records or device credentials. Run it once, then review Script Properties and the storage file's Share panel.

```javascript
function ownerFirstSetup() {
  const setup = setupWorkspace();
  console.log(JSON.stringify({storage: setup.storage_url, report: setup.report_url, workspace: setup.workspace_id}));
}
function approveOfficeComputer() {
  registerDevice("PASTE_DEVICE_ID", "PASTE_REGISTRATION_HASH", "OFFICE PC", true);
}
function approveAnotherComputer() {
  registerDevice("PASTE_OTHER_DEVICE_ID", "PASTE_OTHER_REGISTRATION_HASH", "SECOND PC", false);
}
function retireComputer() {
  revokeDevice("PASTE_DEVICE_ID_TO_REVOKE");
}
```

For an existing reporting file, change only `setupWorkspace()` in `ownerFirstSetup` to `setupWorkspace("REPORT_FILE_ID")`. The ID is between `/d/` and `/edit` in its address. Do not run setup again on another script to reconnect a PC; all PCs must use the same deployed bridge and workspace. To deploy, choose **Deploy → New deployment → Web app**, execute as **Me**, and review the **Anyone** endpoint setting with the owner. This endpoint choice is required for the desktop's device authentication; it does not share the storage spreadsheet. Copy the URL ending in `/exec`, not the testing `/dev` address. After code updates, edit the existing deployment to a new version so its address remains stable.

### Routine Office workflow

1. Open Cathedra and sign in. Before editing, an administrator opens **Backup & Export → Shared storage & reporting → Sync workspace**, reviews and confirms incoming changes.
2. Staff enter and save records as usual. The status indicator shows that local changes are waiting to sync. Nothing is sent automatically.
3. The administrator syncs again. For each conflicting scholar, compare both versions (including grants and education) and explicitly choose **Keep local** or **Keep shared**. The entire profile is reconciled together.
4. Choose **Update shared report** to publish the confirmed shared records. Unsent local edits are excluded. Report edits never update the protected data file.
5. If a save is unconfirmed, keep the app's pending request and use **Retry saved operation**. Do not delete its database or connection files. After restart the same retry remains available. A revoked device with an unresolved operation must be reapproved before its outcome can be checked.

Each PC has local accounts; cloud registration authorizes the installation and records its label, while the actor name identifies the local account supplied by that installation. The owner trusts each approved PC to enforce its local account permissions. This is not centralized Google-user authentication. Keep the Windows account and Cathedra administrator access restricted to intended staff.

The app compares its last baseline, current local records and current cloud records. Different scholars can be combined. Changes to the same aggregate require a choice. The bridge checks global and record revisions under a Google script lock. Canonical values, metadata and a receipt are committed in one Sheets batch request. A network failure retains the exact request; retrying it cannot create duplicate operations. Tombstones prevent reuse of deleted identities. Office Log entries remain append-only.

The report is generated from a fresh canonical snapshot and checked against its revision before replacement. Only the CATHEDRA REPORT tab in the separate report file is changed. Report and storage updates are not a cross-file transaction. Manual report edits never change the canonical database automatically.

If you accidentally edit storage as its owner, stop syncing and use protected recovery/reconciliation. Do not delete receipts, tombstones, row chunks or metadata. If storage sharing or protections are changed, restore the reviewed owner-only configuration before syncing. The bridge does not treat Google Sheets as a general-purpose unlimited database: it stops before bounded transfer, record and row limits.

## Offline verification

Run the production script's offline contract tests with Node:

```text
node --test google/shared-workspace/tests/bridge.test.cjs
```

The tests inject fake Google APIs and a fake script lock. They do not create files, deploy a script, use Google credentials or send scholar records. Real Google authorization, policy, sharing, quota and Office-PC acceptance require separately observed setup checks.

## Google references

- [Execute as the owner](https://developers.google.com/apps-script/guides/web)
- [Script locks](https://developers.google.com/apps-script/reference/lock/lock-service)
- [Atomic Sheets batch updates](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate)
- [Per-file Drive access](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [Paginated Drive permission audit](https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions/list)
- [Protected-range limitations](https://support.google.com/docs/answer/1218656)
