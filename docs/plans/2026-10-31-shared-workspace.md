# Shared workspace and separate report

Owner decisions: two separate Google spreadsheet files; concurrent editing from several PCs. Existing local records remain usable offline. Synchronization is explicitly reviewed, with a pending-changes indicator. The authoritative initial dataset lives on the separate Office PC, never the development database by default.

## Architecture

An owner-controlled Google Apps Script web app serializes writes with a script lock. It executes as its owner. The storage spreadsheet remains private to that owner, with owner-only protected tabs. Approved Cathedra installations use individual revocable device credentials, stored with Windows user encryption; only hashes are registered with the bridge. Owners can still edit their own Google files, so protection is an accidental-edit safeguard rather than an absolute owner lock.

Direct spreadsheet read-then-write is not a concurrency control. The bridge checks a workspace revision and individual record revisions while holding its script lock, then commits records, metadata and an operation receipt in one Sheets batchUpdate. Identical retries return an existing operation result. Deleted identities remain tombstones. Reporting is a separate projection; it never becomes the authoritative storage format.

The shared units are program catalog entries, whole scholar aggregates (including grants, requirements, structured education, manual education-year intent and suppression intent), and immutable Office Log entries. Local account/password/session data, OAuth/device secrets, backups, update state and historical local security/activity ledgers stay local. Shared operations retain device/actor provenance. Calculated values are derived locally from the shared facts.

## Local integration

Schema 19 adds permanent cloud UUID columns to six business tables and a single local shared-workspace state table. Old business values are preserved. Child identifiers are retained across downloading/reconciliation. Local integer IDs never serve as shared identities. Business changes mark the joined cache dirty within their transaction.

A three-way comparison uses the last shared baseline, current local facts and current cloud facts. Non-conflicting changes can be combined; whole-aggregate conflicts require an explicit local/shared choice. A preview is bound to its administrator, local fingerprint, workspace and server revision. Apply is an exclusive local maintenance operation: drain local requests, create a protected recovery copy, persist the immutable pending request before network access, then apply the acknowledged canonical result in one local transaction. There is no networking inside a SQLite writer transaction.

An unconfirmed remote write retains its request and blocks further business writes until the same request is resolved. A private checkpoint detects restored/replaced sync metadata. Connected shared workspaces cannot restore a whole SQLite backup in place: disconnect first and reconcile a restored copy, instead of publishing old data over the shared records.

Joining a populated workspace archives and replaces only local business data after explicit confirmation. Initializing an empty workspace requires an owner-authorized initializer device and confirmation that this is the authoritative Office PC. Credentials remain local in both cases. The report uses a freshly read canonical snapshot, a revision check and the existing sixteen-column projection. Local report upload/import controls are replaced by shared controls while shared mode is configured.

## Delivery gates

1. Implement and independently test the bridge protocol and fake Sheets atomic store, especially concurrent stale writes, rollback, replay, authentication and protection.
2. Implement/test UUID migration, complete serialization, reconciliation, local apply/preservation, restore/checkpoint handling and interrupted requests.
3. Add owner setup, join/initialize, preview/conflict choices, retry recovery, pending status and shared reporting UI. Keep user-facing text understandable.
4. Run focused and full regression, static/type/format, browser and native upgrade/package checks before runtime delivery.
5. Prepare concrete owner setup files and a detailed guide. No live records, new sharing permissions, deployment or initial upload are performed until the owner has reviewed the actual configuration. Office-PC initialization is a separate action using its current records.

## Primary references

- [Apps Script owner execution](https://developers.google.com/apps-script/guides/web)
- [Script locks](https://developers.google.com/apps-script/reference/lock/lock-service)
- [Atomic Sheets batch requests](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate)
- [Protection limitations](https://support.google.com/docs/answer/1218656)
