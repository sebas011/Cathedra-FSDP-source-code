/* Cathedra shared workspace v1. Deploy only after reviewing README.md.
 * Device secrets are never stored in Sheets or logged. All writes serialize
 * through one script lock, then one atomic Sheets batch for canonical storage.
 */
const CATHEDRA_PROTOCOL = "cathedra-shared-v1";
const CATHEDRA_LIMITS = { bytes: 8 * 1024 * 1024, records: 20000, rows: 100000, chunk: 12000 };
const CATHEDRA_TABS = ["CAT_META", "CAT_RECORDS", "CAT_RECEIPTS"];
const CATHEDRA_HEADERS = [
  ["protocol", "workspace_id", "revision", "initialized"],
  ["key", "kind", "revision", "part", "parts", "sha256", "json"],
  ["device_id", "request_id", "digest", "committed_revision", "created_at"],
];
const CATHEDRA_REPORT_HEADERS = [
  "No.", "Name", "Age", "Tenure", "Department", "Rank/position", "Previous degree",
  "Profile remarks", "Program", "Delivering HEI", "Grant type", "Date started",
  "Date ended", "Extension", "Status", "Remarks",
];
const CATHEDRA_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const CATHEDRA_FIELDS = {
  program: ["name", "canonical_key", "delivering_hei", "description"],
  scholar: ["name", "age", "previous_degree", "missing_requirements", "has_hard_copy", "has_soft_copy", "department", "personnel_type", "rank", "tenure", "tenure_years", "tenure_note", "profile_remarks", "created_at", "updated_at", "participations", "education", "requirements", "suppressed_program_keys"],
  participation: ["cloud_key", "program_key", "delivering_hei", "start_date", "end_date", "contract_completed_on", "allowed_duration_years", "completion_due_on", "payback_payment_status", "graduation_date", "case_status", "start_term", "start_academic_year", "end_term", "end_academic_year", "status", "grant_type", "program_category", "application_key", "grant_other", "extension", "remarks"],
  education: ["cloud_key", "source_program_key", "level", "degree", "institution", "graduation_year", "graduation_year_manual"],
  requirement: ["cloud_key", "requirement_name", "due_date", "is_complete", "completed_at", "remarks"],
  office_log: ["scholar_key", "scholar_name", "username", "occurred_on", "created_at", "entry_type", "note", "document_name", "from_department", "to_department"],
};

function cathedraError_(code, message) {
  const error = new Error(message);
  error.cathedraCode = code;
  return error;
}
function cathedraRequire_(condition, message, code) {
  if (!condition) throw cathedraError_(code || "invalid", message);
}
function cathedraObject_(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function cathedraStable_(value) {
  if (Array.isArray(value)) return "[" + value.map(cathedraStable_).join(",") + "]";
  if (cathedraObject_(value)) return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + cathedraStable_(value[key])).join(",") + "}";
  return JSON.stringify(value);
}
function cathedraHash_(value) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, value, Utilities.Charset.UTF_8)
    .map((byte) => (byte & 255).toString(16).padStart(2, "0")).join("");
}
function cathedraBytes_(value) { return Utilities.newBlob(value).getBytes().length; }
function cathedraEqual_(left, right) { return cathedraStable_(left) === cathedraStable_(right); }
function cathedraConstantTime_(left, right) {
  let difference = left.length ^ right.length;
  for (let i = 0; i < 64; i += 1) difference |= (left.charCodeAt(i) || 0) ^ (right.charCodeAt(i) || 0);
  return difference === 0;
}
function cathedraInteger_(value, minimum) { return Number.isSafeInteger(value) && value >= minimum; }
function cathedraUuid_(value) { return typeof value === "string" && CATHEDRA_UUID.test(value); }
function cathedraFields_(value, kind) {
  cathedraRequire_(cathedraObject_(value), "A record must contain an object.");
  cathedraRequire_(Object.keys(value).length === CATHEDRA_FIELDS[kind].length && Object.keys(value).every((key) => CATHEDRA_FIELDS[kind].includes(key)), "A record contains missing or unsupported fields.");
}
function cathedraDate_(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.slice(0, 4) === "0000") return false;
  const date = new Date(value + "T00:00:00Z");
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
function cathedraTime_(value) {
  return typeof value === "string" && cathedraDate_(value.slice(0, 10)) && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?$/.test(value);
}
function cathedraScalars_(value) {
  const dates = ["start_date", "end_date", "contract_completed_on", "completion_due_on", "graduation_date", "due_date", "occurred_on"];
  const times = ["created_at", "updated_at", "completed_at"];
  const booleans = ["missing_requirements", "has_hard_copy", "has_soft_copy", "graduation_year_manual", "is_complete"];
  const required = ["name", "missing_requirements", "created_at", "updated_at", "case_status", "status", "level", "degree", "institution", "graduation_year_manual", "requirement_name", "is_complete", "username", "occurred_on", "entry_type", "note", "cloud_key", "program_key"];
  Object.keys(value).forEach((key) => {
    const item = value[key];
    if (["participations", "education", "requirements", "suppressed_program_keys"].includes(key)) return;
    if (item === null) { cathedraRequire_(!required.includes(key), "A required stored field cannot be null."); return; }
    if (dates.includes(key)) cathedraRequire_(cathedraDate_(item), "A recorded date cannot be represented.");
    else if (times.includes(key)) cathedraRequire_(cathedraTime_(item), "A recorded timestamp cannot be represented.");
    else if (booleans.includes(key)) cathedraRequire_(typeof item === "boolean", "A recorded flag must be true, false or blank.");
    else if (["age", "allowed_duration_years"].includes(key)) cathedraRequire_(Number.isSafeInteger(item), "A recorded number cannot be represented exactly.");
    else if (key === "tenure_years") cathedraRequire_(typeof item === "number" && Number.isFinite(item), "Tenure must be a finite number or blank.");
    else cathedraRequire_(typeof item === "string", "A recorded text value cannot be represented.");
  });
}

function cathedraValidateSnapshot_(snapshot) {
  cathedraRequire_(cathedraObject_(snapshot) && snapshot.protocol === CATHEDRA_PROTOCOL && cathedraUuid_(snapshot.workspace_id), "The workspace identity is invalid.");
  cathedraRequire_(Object.keys(snapshot).length === 5 && Object.keys(snapshot).every(key => ["protocol", "workspace_id", "revision", "initialized", "records"].includes(key)), "Unexpected snapshot fields.");
  cathedraRequire_(cathedraInteger_(snapshot.revision, 0) && typeof snapshot.initialized === "boolean", "The workspace revision is invalid.");
  cathedraRequire_(Array.isArray(snapshot.records) && snapshot.records.length <= CATHEDRA_LIMITS.records, "The workspace exceeds its record limit.");
  cathedraRequire_(snapshot.initialized || (snapshot.revision === 0 && snapshot.records.length === 0), "An uninitialized workspace contains records.");
  cathedraRequire_(cathedraBytes_(cathedraStable_(snapshot)) <= CATHEDRA_LIMITS.bytes, "The workspace exceeds its transfer limit.");
  const records = new Map();
  const identities = new Set();
  const programNames = new Set();
  const programKeys = new Set();
  snapshot.records.forEach((record) => {
    cathedraRequire_(cathedraObject_(record) && cathedraUuid_(record.key) && !identities.has(record.key), "A shared identity is invalid or duplicated.");
    cathedraRequire_(Object.keys(record).length === 6 && Object.keys(record).every(key => ["key", "kind", "revision", "value", "origin", "changed_at"].includes(key)), "Unexpected record fields.");
    cathedraRequire_(["program", "scholar", "office_log"].includes(record.kind) && cathedraInteger_(record.revision, 1) && record.revision <= snapshot.revision, "A shared record revision or kind is invalid.");
    cathedraRequire_(record.value === null || cathedraObject_(record.value), "A shared record value is invalid.");
    cathedraRequire_(cathedraObject_(record.origin) && typeof record.origin.device_label === "string" && typeof record.origin.actor === "string" && cathedraTime_(record.changed_at), "Shared operation provenance is invalid.");
    cathedraRequire_(Object.keys(record.origin).length === 2, "Unexpected record origin fields.");
    identities.add(record.key);
    records.set(record.key, record);
  });
  const reference = (key, kind, allowDeleted) => {
    const target = records.get(key);
    cathedraRequire_(cathedraUuid_(key) && target && target.kind === kind && (allowDeleted || target.value !== null), "A shared record references a missing or deleted identity.");
  };
  snapshot.records.forEach((record) => {
    const value = record.value;
    if (value === null) {
      cathedraRequire_(record.kind !== "office_log", "Office Log records cannot be deleted.");
      return;
    }
    cathedraFields_(value, record.kind);
    cathedraScalars_(value);
    if (record.kind === "program" || record.kind === "scholar") cathedraRequire_(typeof value.name === "string" && value.name.trim(), "Name is required.");
    if (record.kind === "program") {
      cathedraRequire_(!programNames.has(value.name), "Two program entries have the same name.");
      programNames.add(value.name);
      if (value.canonical_key != null) {
        cathedraRequire_(!programKeys.has(value.canonical_key), "Two program entries have the same catalog identity.");
        programKeys.add(value.canonical_key);
      }
    } else if (record.kind === "scholar") {
      ["participations", "education", "requirements", "suppressed_program_keys"].forEach((key) => cathedraRequire_(Array.isArray(value[key]), "Scholar detail lists are required."));
      const child = (item, kind) => {
        cathedraFields_(item, kind);
        cathedraScalars_(item);
        cathedraRequire_(cathedraUuid_(item.cloud_key) && !identities.has(item.cloud_key), "A child identity is invalid or duplicated.");
        identities.add(item.cloud_key);
      };
      value.participations.forEach((item) => { child(item, "participation"); reference(item.program_key, "program", false); });
      value.education.forEach((item) => { child(item, "education"); if (item.source_program_key !== null && item.source_program_key !== undefined) reference(item.source_program_key, "program", false); });
      value.requirements.forEach((item) => child(item, "requirement"));
      cathedraRequire_(new Set(value.suppressed_program_keys).size === value.suppressed_program_keys.length, "An education suppression is duplicated.");
      value.suppressed_program_keys.forEach((key) => reference(key, "program", false));
    } else if (value.scholar_key !== null && value.scholar_key !== undefined) reference(value.scholar_key, "scholar", true);
  });
}

function cathedraProperties_() { return PropertiesService.getScriptProperties(); }
function cathedraConfig_() {
  const saved = cathedraProperties_().getProperties();
  cathedraRequire_(cathedraUuid_(saved.WORKSPACE_ID) && /^[A-Za-z0-9_-]{10,200}$/.test(saved.STORAGE_ID || "") && /^[A-Za-z0-9_-]{10,200}$/.test(saved.REPORT_ID || "") && saved.STORAGE_ID !== saved.REPORT_ID && typeof saved.OWNER_EMAIL === "string" && saved.OWNER_EMAIL.includes("@"), "The owner must finish workspace setup.", "unavailable");
  cathedraRequire_(Session.getEffectiveUser().getEmail().toLowerCase() === saved.OWNER_EMAIL.toLowerCase(), "Deploy this bridge to execute as its owner.", "unavailable");
  return saved;
}
function cathedraAuthorize_(request) {
  const forbidden = () => { throw cathedraError_("unauthorized", "This device is not authorized for the shared workspace."); };
  if (!cathedraUuid_(request.device_id) || typeof request.device_key !== "string" || !/^[A-Za-z0-9_-]{43,128}$/.test(request.device_key)) forbidden();
  const raw = cathedraProperties_().getProperty("DEVICE_" + request.device_id);
  let device;
  try { device = JSON.parse(raw || "null"); } catch (_) { forbidden(); }
  const supplied = cathedraHash_(request.device_key);
  if (!device || typeof device.hash !== "string" || !cathedraConstantTime_(supplied, device.hash)) forbidden();
  if (typeof device.label !== "string" || typeof device.can_initialize !== "boolean") forbidden();
  return device;
}

function cathedraPrivateStorage_(config) {
  // drive.file covers only this app-created file. Failure is closed: do not
  // broaden to full Drive or silently remove other people's permissions.
  let file;
  try {
    file = Drive.Files.get(config.STORAGE_ID, { fields: "id,mimeType,trashed,ownedByMe,owners(emailAddress),driveId" });
  } catch (_) {
    throw cathedraError_("unavailable", "Enable Drive API and drive.file access for the newly created storage file. Do not broaden Drive access.");
  }
  const owner = config.OWNER_EMAIL.toLowerCase();
  cathedraRequire_(file.mimeType === "application/vnd.google-apps.spreadsheet" && !file.trashed && !file.driveId && file.ownedByMe === true && Array.isArray(file.owners) && file.owners.length === 1 && (file.owners[0].emailAddress || "").toLowerCase() === owner, "Storage must be a private spreadsheet owned by the bridge owner.", "unavailable");
  let token;
  const tokens = new Set();
  const permissions = [];
  for (let page = 0; page < 100; page += 1) {
    const options = { pageSize: 100, fields: "nextPageToken,permissions(id,type,role,emailAddress,deleted)" };
    if (token) options.pageToken = token;
    const result = Drive.Permissions.list(config.STORAGE_ID, options);
    cathedraRequire_(result && Array.isArray(result.permissions), "Storage sharing could not be verified.", "unavailable");
    permissions.push(...result.permissions);
    if (!result.nextPageToken) { token = null; break; }
    token = result.nextPageToken;
    cathedraRequire_(typeof token === "string" && !tokens.has(token), "Storage sharing pagination could not be verified.", "unavailable");
    tokens.add(token);
  }
  cathedraRequire_(!token && permissions.length === 1 && permissions[0].type === "user" && permissions[0].role === "owner" && permissions[0].deleted !== true && (permissions[0].emailAddress || "").toLowerCase() === owner, "Storage sharing must be Restricted, with only its owner. Review sharing before syncing.", "unavailable");
}
function cathedraSheets_(id) {
  const response = Sheets.Spreadsheets.get(id, { fields: "sheets(properties,protectedRanges)" });
  cathedraRequire_(response && Array.isArray(response.sheets), "Spreadsheet metadata could not be verified.", "unavailable");
  return response.sheets;
}
function cathedraStorageTabs_(config) {
  const sheets = cathedraSheets_(config.STORAGE_ID);
  const owner = config.OWNER_EMAIL.toLowerCase();
  return CATHEDRA_TABS.map((title) => {
    const found = sheets.filter((sheet) => sheet.properties.title === title);
    cathedraRequire_(found.length === 1 && found[0].properties.sheetType !== "DATA_SOURCE", "A required storage tab is missing or duplicated.", "unavailable");
    const sheet = found[0];
    // Google omits protobuf defaults: sheetId 0 can be {}, and warningOnly
    // false can be absent. Bounded ranges and warning-only protection still fail.
    const protectedSheet = (sheet.protectedRanges || []).some((range) => range.range && (range.range.sheetId === undefined ? 0 : range.range.sheetId) === sheet.properties.sheetId && Object.keys(range.range).every((key) => key === "sheetId") && (range.warningOnly === undefined || range.warningOnly === false) && (!range.unprotectedRanges || range.unprotectedRanges.length === 0) && range.editors && !range.editors.domainUsersCanEdit && (!range.editors.groups || range.editors.groups.length === 0) && (range.editors.users || []).every((email) => email.toLowerCase() === owner));
    cathedraRequire_(protectedSheet, "Owner-only protection must remain enabled on every storage tab.", "unavailable");
    return sheet.properties;
  });
}
function cathedraReadStore_(config, tabs) {
  const response = Sheets.Spreadsheets.Values.batchGet(config.STORAGE_ID, { ranges: CATHEDRA_TABS.map((title) => "'" + title + "'"), valueRenderOption: "UNFORMATTED_VALUE" });
  cathedraRequire_(response && Array.isArray(response.valueRanges) && response.valueRanges.length === 3, "Storage rows could not be read.", "unavailable");
  const values = response.valueRanges.map((range, index) => {
    const rows = range.values || [];
    cathedraRequire_(rows.length > 0 && cathedraEqual_(rows[0], CATHEDRA_HEADERS[index]) && rows.length <= CATHEDRA_LIMITS.rows, "Storage headings or capacity are invalid.", "unavailable");
    return rows;
  });
  const meta = values[0];
  cathedraRequire_(meta.length === 2 && meta[1].length === 4 && meta[1][0] === CATHEDRA_PROTOCOL && meta[1][1] === config.WORKSPACE_ID && /^(0|[1-9]\d*)$/.test(String(meta[1][2])) && ["true", "false"].includes(String(meta[1][3])), "Storage metadata has changed unexpectedly.", "unavailable");
  const snapshot = { protocol: CATHEDRA_PROTOCOL, workspace_id: config.WORKSPACE_ID, revision: Number(meta[1][2]), initialized: String(meta[1][3]) === "true", records: [] };
  const groups = new Map();
  values[1].slice(1).forEach((row) => {
    cathedraRequire_(row.length === 7 && cathedraUuid_(row[0]) && typeof row[6] === "string" && /^[a-f0-9]{64}$/.test(row[5]), "A storage chunk is malformed.", "unavailable");
    const part = Number(row[3]); const count = Number(row[4]);
    cathedraRequire_(cathedraInteger_(part, 0) && cathedraInteger_(count, 1) && part < count && count < CATHEDRA_LIMITS.rows && Array.from(row[6]).length <= CATHEDRA_LIMITS.chunk, "A storage chunk count is invalid.", "unavailable");
    if (!groups.has(row[0])) groups.set(row[0], { kind: row[1], revision: Number(row[2]), count, hash: row[5], chunks: new Map() });
    const group = groups.get(row[0]);
    cathedraRequire_(group.kind === row[1] && group.revision === Number(row[2]) && group.count === count && group.hash === row[5] && !group.chunks.has(part), "Storage chunks disagree or are duplicated.", "unavailable");
    group.chunks.set(part, row[6]);
  });
  cathedraRequire_(groups.size <= CATHEDRA_LIMITS.records, "Storage exceeds its record limit.", "unavailable");
  groups.forEach((group, key) => {
    cathedraRequire_(group.chunks.size === group.count, "A storage chunk is missing.", "unavailable");
    const serialized = Array.from({ length: group.count }, (_, index) => group.chunks.get(index)).join("");
    cathedraRequire_(cathedraHash_(serialized) === group.hash, "Storage checksum verification failed.", "unavailable");
    let record;
    try { record = JSON.parse(serialized); } catch (_) { throw cathedraError_("unavailable", "A stored record cannot be decoded."); }
    cathedraRequire_(record.key === key && record.kind === group.kind && record.revision === group.revision, "A storage identity does not match its chunks.", "unavailable");
    snapshot.records.push(record);
  });
  snapshot.records.sort((left, right) => left.key.localeCompare(right.key));
  cathedraValidateSnapshot_(snapshot);
  const receipts = new Map();
  values[2].slice(1).forEach((row) => {
    cathedraRequire_(row.length === 5 && cathedraUuid_(row[0]) && cathedraUuid_(row[1]) && /^[a-f0-9]{64}$/.test(row[2]) && cathedraInteger_(Number(row[3]), 0) && Number(row[3]) <= snapshot.revision && cathedraTime_(row[4]), "A shared operation receipt is malformed.", "unavailable");
    const key = row[0] + ":" + row[1];
    cathedraRequire_(!receipts.has(key), "A shared operation receipt is duplicated.", "unavailable");
    receipts.set(key, { digest: row[2], revision: Number(row[3]) });
  });
  return { snapshot, receipts, tabs, receiptRows: values[2] };
}
function cathedraLiteral_(value) {
  if (value === null || value === undefined) return {};
  return { userEnteredValue: typeof value === "number" ? { numberValue: value } : { stringValue: String(value) } };
}
function cathedraReplace_(sheet, rows) {
  const columns = Math.max(1, ...rows.map((row) => row.length));
  const requests = [];
  const grid = sheet.gridProperties || {};
  const rowCount = Math.max(rows.length, grid.rowCount || 1);
  const columnCount = Math.max(columns, grid.columnCount || 1);
  if (rowCount !== grid.rowCount || columnCount !== grid.columnCount) requests.push({ updateSheetProperties: { properties: { sheetId: sheet.sheetId, gridProperties: { rowCount, columnCount } }, fields: "gridProperties.rowCount,gridProperties.columnCount" } });
  requests.push({ updateCells: { range: { sheetId: sheet.sheetId }, rows: rows.map((row) => ({ values: row.map(cathedraLiteral_) })), fields: "userEnteredValue" } });
  return requests;
}
function cathedraRecordRows_(snapshot) {
  const rows = [CATHEDRA_HEADERS[1]];
  snapshot.records.forEach((record) => {
    const serialized = cathedraStable_(record);
    const points = Array.from(serialized);
    const count = Math.max(1, Math.ceil(points.length / CATHEDRA_LIMITS.chunk));
    const hash = cathedraHash_(serialized);
    for (let part = 0; part < count; part += 1) rows.push([record.key, record.kind, record.revision, part, count, hash, points.slice(part * CATHEDRA_LIMITS.chunk, (part + 1) * CATHEDRA_LIMITS.chunk).join("")]);
  });
  cathedraRequire_(rows.length <= CATHEDRA_LIMITS.rows, "Storage exceeds its chunk-row capacity.");
  return rows;
}
function cathedraMetadata_(config, device, snapshot) {
  return { protocol: CATHEDRA_PROTOCOL, workspace_id: config.WORKSPACE_ID, revision: snapshot.revision, initialized: snapshot.initialized, device_label: device.label, can_initialize: device.can_initialize, storage_url: "https://docs.google.com/spreadsheets/d/" + config.STORAGE_ID + "/edit", report_url: "https://docs.google.com/spreadsheets/d/" + config.REPORT_ID + "/edit" };
}
function cathedraCommit_(config, device, request, store, context) {
  const args = request.args;
  cathedraRequire_(cathedraUuid_(args.request_id) && typeof args.actor === "string" && args.actor.length > 0 && args.actor.length <= 80 && cathedraInteger_(args.expected_revision, 0), "The shared operation identity is invalid.");
  const digest = cathedraHash_(cathedraStable_({ command: request.command, args }));
  const previous = store.receipts.get(request.device_id + ":" + args.request_id);
  if (previous) {
    cathedraRequire_(cathedraConstantTime_(digest, previous.digest), "This operation ID was already used with different changes.", "conflict");
    return { snapshot: store.snapshot, committed_revision: previous.revision, replayed: true };
  }
  context.mayHaveCommitted = false; // Healthy, locked receipt lookup proves no earlier commit.
  cathedraRequire_(args.expected_revision === store.snapshot.revision, "The shared workspace changed. Refresh and review again.", "conflict");
  const initializing = request.command === "initialize";
  if (initializing) cathedraRequire_(device.can_initialize && !store.snapshot.initialized && store.snapshot.records.length === 0 && args.expected_revision === 0, "Only the authorized Office initializer can initialize an empty workspace.", "conflict");
  else cathedraRequire_(store.snapshot.initialized, "Initialize from the authoritative Office PC first.", "conflict");
  const changes = initializing ? args.records : args.changes;
  cathedraRequire_(Array.isArray(changes) && changes.length <= CATHEDRA_LIMITS.records, "The shared change list is invalid.");
  const indexed = new Map(store.snapshot.records.map((record) => [record.key, record]));
  const seen = new Set();
  let changed = initializing;
  const now = new Date().toISOString();
  const nextRevision = store.snapshot.revision + 1;
  cathedraRequire_(cathedraInteger_(nextRevision, 1), "The workspace revision limit has been reached.");
  changes.forEach((change) => {
    cathedraRequire_(cathedraObject_(change) && cathedraUuid_(change.key) && !seen.has(change.key) && ["program", "scholar", "office_log"].includes(change.kind), "A shared change identity is invalid or duplicated.");
    cathedraRequire_(Object.keys(change).every((key) => ["key", "kind", "value", "expected_revision"].includes(key)) && Object.prototype.hasOwnProperty.call(change, "value"), "A shared change contains unsupported fields.");
    seen.add(change.key);
    const existing = indexed.get(change.key);
    if (!initializing) cathedraRequire_(cathedraInteger_(change.expected_revision, 0) && change.expected_revision === (existing ? existing.revision : 0), "A shared record changed. Refresh and review again.", "conflict");
    cathedraRequire_(!existing || existing.kind === change.kind, "A shared identity cannot change its record kind.", "conflict");
    cathedraRequire_(!initializing || change.value !== null, "Initialization cannot contain deleted identities.");
    cathedraRequire_(existing || change.value !== null, "A missing record cannot be deleted.");
    cathedraRequire_(!existing || existing.value !== null || change.value === null, "A deleted identity cannot be reused. Create a new record instead.", "conflict");
    if (existing && existing.kind === "office_log") cathedraRequire_(cathedraEqual_(existing.value, change.value), "Office Log entries are append-only.", "conflict");
    if (!existing || !cathedraEqual_(existing.value, change.value)) {
      changed = true;
      indexed.set(change.key, { key: change.key, kind: change.kind, revision: nextRevision, value: change.value, origin: { device_label: device.label, actor: args.actor }, changed_at: now });
    }
  });
  const snapshot = { protocol: CATHEDRA_PROTOCOL, workspace_id: config.WORKSPACE_ID, revision: changed ? nextRevision : store.snapshot.revision, initialized: true, records: Array.from(indexed.values()).sort((left, right) => left.key.localeCompare(right.key)) };
  cathedraValidateSnapshot_(snapshot);
  const receiptRows = store.receiptRows.concat([[request.device_id, args.request_id, digest, snapshot.revision, now]]);
  cathedraRequire_(receiptRows.length <= CATHEDRA_LIMITS.rows, "Storage exceeds its operation-receipt capacity.");
  const meta = [CATHEDRA_HEADERS[0], [CATHEDRA_PROTOCOL, config.WORKSPACE_ID, snapshot.revision, String(snapshot.initialized)]];
  const rows = [meta, cathedraRecordRows_(snapshot), receiptRows];
  const requests = [];
  rows.forEach((values, index) => requests.push(...cathedraReplace_(store.tabs[index], values)));
  context.mayHaveCommitted = true;
  Sheets.Spreadsheets.batchUpdate({ requests, includeSpreadsheetInResponse: false }, config.STORAGE_ID);
  return { snapshot, committed_revision: snapshot.revision, replayed: false };
}
function cathedraReport_(config, args, snapshot, context) {
  cathedraRequire_(snapshot.initialized && args.expected_revision === snapshot.revision, "The shared workspace changed. Refresh the shared report.", "conflict");
  cathedraRequire_(Array.isArray(args.table) && args.table.length >= 1 && args.table.length <= CATHEDRA_LIMITS.rows && cathedraEqual_(args.table[0], CATHEDRA_REPORT_HEADERS), "The shared reporting columns are invalid.");
  args.table.forEach((row) => cathedraRequire_(Array.isArray(row) && row.length === CATHEDRA_REPORT_HEADERS.length && row.every((value) => value === null || typeof value === "string" && Array.from(value).length <= 24000 || typeof value === "number" && Number.isFinite(value)), "A reporting cell cannot be represented."));
  const sheets = cathedraSheets_(config.REPORT_ID);
  const matching = sheets.filter((sheet) => sheet.properties.title === "CATHEDRA REPORT");
  cathedraRequire_(matching.length <= 1 && (!matching.length || matching[0].properties.sheetType !== "DATA_SOURCE"), "Use a normal CATHEDRA REPORT tab.");
  const requests = [];
  let sheet;
  if (matching.length) sheet = matching[0].properties;
  else {
    const id = Math.max(-1, ...sheets.map((item) => item.properties.sheetId)) + 1;
    sheet = { sheetId: id, title: "CATHEDRA REPORT", gridProperties: { rowCount: 1, columnCount: 16 } };
    requests.push({ addSheet: { properties: sheet } });
  }
  requests.push(...cathedraReplace_(sheet, args.table));
  context.mayHaveCommitted = true;
  Sheets.Spreadsheets.batchUpdate({ requests, includeSpreadsheetInResponse: false }, config.REPORT_ID);
  return { rows: args.table.length - 1, synced_at: new Date().toISOString(), spreadsheet_url: "https://docs.google.com/spreadsheets/d/" + config.REPORT_ID + "/edit", revision: snapshot.revision };
}
function cathedraDispatch_(raw) {
  const context = { mayHaveCommitted: false };
  let lock;
  let acquired = false;
  try {
    cathedraRequire_(typeof raw === "string" && cathedraBytes_(raw) <= CATHEDRA_LIMITS.bytes, "The shared request exceeds its transfer limit.");
    let request;
    try { request = JSON.parse(raw); } catch (_) { throw cathedraError_("invalid", "The shared request cannot be decoded."); }
    cathedraRequire_(cathedraObject_(request) && request.protocol === CATHEDRA_PROTOCOL && ["status", "read", "initialize", "commit", "report"].includes(request.command) && cathedraObject_(request.args), "The shared request is invalid.");
    context.mayHaveCommitted = ["commit", "initialize"].includes(request.command);
    lock = LockService.getScriptLock();
    acquired = lock.tryLock(15000);
    cathedraRequire_(acquired, "Another computer is syncing. Wait and retry.", "busy");
    const device = cathedraAuthorize_(request);
    const config = cathedraConfig_();
    cathedraPrivateStorage_(config);
    const tabs = cathedraStorageTabs_(config);
    const store = cathedraReadStore_(config, tabs);
    let result;
    if (request.command === "status" || request.command === "read") {
      cathedraRequire_(Object.keys(request.args).length === 0, "This request does not accept arguments.");
      result = cathedraMetadata_(config, device, store.snapshot);
      if (request.command === "read") result.snapshot = store.snapshot;
    } else if (request.command === "report") result = cathedraReport_(config, request.args, store.snapshot, context);
    else result = cathedraCommit_(config, device, request, store, context);
    return { ok: true, result };
  } catch (error) {
    const known = Boolean(error && error.cathedraCode);
    return { ok: false, error: { code: known ? error.cathedraCode : "unavailable", message: known ? error.message : "The shared operation was not confirmed. Retry the same request.", outcome: context.mayHaveCommitted || !known ? "unknown" : "not_committed" } };
  } finally {
    if (acquired) lock.releaseLock();
  }
}
function doPost(event) {
  const response = cathedraDispatch_(event && event.postData && event.postData.contents);
  return ContentService.createTextOutput(JSON.stringify(response)).setMimeType(ContentService.MimeType.JSON);
}
function doGet() {
  return ContentService.createTextOutput(JSON.stringify({ ok: false, error: { code: "unauthorized", message: "Use the authorized Cathedra application.", outcome: "not_committed" } })).setMimeType(ContentService.MimeType.JSON);
}

function cathedraOwner_() {
  const effective = Session.getEffectiveUser().getEmail();
  const active = Session.getActiveUser().getEmail();
  cathedraRequire_(effective && active && effective.toLowerCase() === active.toLowerCase(), "Run owner setup directly in the Apps Script editor.");
  const configured = cathedraProperties_().getProperty("OWNER_EMAIL");
  cathedraRequire_(!configured || configured.toLowerCase() === active.toLowerCase(), "Only the original bridge owner can change setup.");
  return active;
}
function setupWorkspace(existingReportId) {
  const owner = cathedraOwner_();
  const lock = LockService.getScriptLock();
  cathedraRequire_(lock.tryLock(15000), "Another workspace operation is running.", "busy");
  try {
    const properties = cathedraProperties_();
    if (properties.getProperty("WORKSPACE_ID")) {
      const config = cathedraConfig_();
      cathedraPrivateStorage_(config);
      const store = cathedraReadStore_(config, cathedraStorageTabs_(config));
      return cathedraMetadata_(config, { label: "OWNER SETUP", can_initialize: false }, store.snapshot);
    }
    cathedraRequire_(!properties.getProperty("STORAGE_ID") && !properties.getProperty("REPORT_ID"), "Partial setup requires owner review before retrying.");
    cathedraRequire_(existingReportId === undefined || existingReportId === null || existingReportId === "" || /^[A-Za-z0-9_-]{10,200}$/.test(existingReportId), "Use an existing report spreadsheet ID or leave it blank.");
    if (existingReportId) cathedraSheets_(existingReportId);
    const storage = Sheets.Spreadsheets.create({ properties: { title: "Cathedra Shared Data — OWNER ONLY" }, sheets: CATHEDRA_TABS.map((title, index) => ({ properties: { title, sheetId: index, gridProperties: { rowCount: index === 0 ? 2 : 100, columnCount: CATHEDRA_HEADERS[index].length, frozenRowCount: 1 } } })) });
    cathedraRequire_(storage && /^[A-Za-z0-9_-]{10,200}$/.test(storage.spreadsheetId || ""), "Google did not confirm the new storage file.", "unavailable");
    // Persist the newly created identity before further setup. If authorization
    // or permissions fail, retain this marker for owner review; never create a
    // second storage file automatically or adopt an arbitrary existing file.
    properties.setProperties({ STORAGE_ID: storage.spreadsheetId, OWNER_EMAIL: owner });
    const workspaceId = Utilities.getUuid().toLowerCase();
    const reportId = existingReportId || Sheets.Spreadsheets.create({ properties: { title: "Cathedra Reporting" }, sheets: [{ properties: { title: "CATHEDRA REPORT", gridProperties: { rowCount: 100, columnCount: 16, frozenRowCount: 1 } } }] }).spreadsheetId;
    cathedraRequire_(/^[A-Za-z0-9_-]{10,200}$/.test(reportId || "") && reportId !== storage.spreadsheetId, "The report must be a separate spreadsheet.");
    properties.setProperty("REPORT_ID", reportId);
    const config = { STORAGE_ID: storage.spreadsheetId, REPORT_ID: reportId, OWNER_EMAIL: owner, WORKSPACE_ID: workspaceId };
    cathedraPrivateStorage_(config);
    const requests = [];
    const initial = [
      [CATHEDRA_HEADERS[0], [CATHEDRA_PROTOCOL, workspaceId, 0, "false"]],
      [CATHEDRA_HEADERS[1]], [CATHEDRA_HEADERS[2]],
    ];
    initial.forEach((rows, index) => {
      requests.push(...cathedraReplace_({ sheetId: index, gridProperties: { rowCount: index === 0 ? 2 : 100, columnCount: CATHEDRA_HEADERS[index].length } }, rows));
      requests.push({ addProtectedRange: { protectedRange: { range: { sheetId: index }, description: "Cathedra canonical storage — edit through the app only", warningOnly: false, editors: { users: [owner], groups: [], domainUsersCanEdit: false } } } });
    });
    Sheets.Spreadsheets.batchUpdate({ requests, includeSpreadsheetInResponse: false }, config.STORAGE_ID);
    properties.setProperty("WORKSPACE_ID", workspaceId);
    const store = cathedraReadStore_(config, cathedraStorageTabs_(config));
    return cathedraMetadata_(config, { label: "OWNER SETUP", can_initialize: false }, store.snapshot);
  } finally { lock.releaseLock(); }
}
function registerDevice(deviceId, keyHash, label, canInitialize) {
  cathedraOwner_();
  cathedraConfig_();
  cathedraRequire_(cathedraUuid_(deviceId) && typeof keyHash === "string" && /^[a-f0-9]{64}$/.test(keyHash) && typeof label === "string" && label.trim().length > 0 && label.length <= 80 && typeof canInitialize === "boolean", "Enter the app's device ID, SHA-256 registration hash, label and initializer choice.");
  const lock = LockService.getScriptLock();
  cathedraRequire_(lock.tryLock(15000), "Another workspace operation is running.", "busy");
  try {
    cathedraProperties_().setProperty("DEVICE_" + deviceId, JSON.stringify({ hash: keyHash, label: label.trim(), can_initialize: canInitialize }));
    return { registered: true, device_id: deviceId, device_label: label.trim(), can_initialize: canInitialize };
  } finally { lock.releaseLock(); }
}
function revokeDevice(deviceId) {
  cathedraOwner_();
  cathedraRequire_(cathedraUuid_(deviceId), "Enter the device ID to revoke.");
  const lock = LockService.getScriptLock();
  cathedraRequire_(lock.tryLock(15000), "Another workspace operation is running.", "busy");
  try { cathedraProperties_().deleteProperty("DEVICE_" + deviceId); return { revoked: true, device_id: deviceId }; }
  finally { lock.releaseLock(); }
}

if (typeof module !== "undefined" && module.exports) module.exports = {
  doPost, doGet, setupWorkspace, registerDevice, revokeDevice,
  test: { dispatch: cathedraDispatch_, validateSnapshot: cathedraValidateSnapshot_, stable: cathedraStable_, hash: cathedraHash_, recordRows: cathedraRecordRows_, headers: CATHEDRA_HEADERS, reportHeaders: CATHEDRA_REPORT_HEADERS, protocol: CATHEDRA_PROTOCOL },
};
