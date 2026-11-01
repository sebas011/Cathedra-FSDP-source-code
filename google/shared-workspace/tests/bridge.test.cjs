const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');
const clone = value => JSON.parse(JSON.stringify(value));

function harness() {
  const properties = {};
  const files = new Map();
  const state = { locked: false, busy: false, fail: null, public: false, omitDefaults: false, owner: 'owner@example.test' };
  const api = {
    create(body) {
      const id = 'test_file_' + files.size + '_123456789';
      files.set(id, { spreadsheetId: id, sheets: (body.sheets || []).map((sheet, index) => ({ properties: { sheetId: index, gridProperties: { rowCount: 100, columnCount: 16 }, ...clone(sheet.properties) }, protectedRanges: [], rows: [] })) });
      return clone(files.get(id));
    },
    get(id) {
      assert.ok(files.has(id));
      const result = clone(files.get(id));
      if (state.omitDefaults) for (const sheet of result.sheets) for (const range of sheet.protectedRanges) {
        if (range.range.sheetId === 0) delete range.range.sheetId;
        if (range.warningOnly === false) delete range.warningOnly;
        if (range.editors?.domainUsersCanEdit === false) delete range.editors.domainUsersCanEdit;
      }
      return result;
    },
    batchUpdate(body, id) {
      assert.ok(state.locked, 'every write holds the script lock');
      if (state.fail === 'before') { state.fail = null; throw new Error('network'); }
      const next = clone(files.get(id));
      for (const request of body.requests) {
        if (request.addSheet) next.sheets.push({ properties: clone(request.addSheet.properties), protectedRanges: [], rows: [] });
        else if (request.updateSheetProperties) {
          const props = request.updateSheetProperties.properties;
          Object.assign(next.sheets.find(s => s.properties.sheetId === props.sheetId).properties.gridProperties, props.gridProperties);
        } else if (request.addProtectedRange) {
          const range = request.addProtectedRange.protectedRange;
          next.sheets.find(s => s.properties.sheetId === range.range.sheetId).protectedRanges.push(clone(range));
        } else if (request.updateCells) {
          const cells = request.updateCells;
          const sheet = next.sheets.find(s => s.properties.sheetId === cells.range.sheetId);
          sheet.rows = cells.rows.map(row => row.values.map(cell => {
            const value = cell.userEnteredValue;
            assert.ok(!value || !('formulaValue' in value));
            return !value ? null : value.stringValue ?? value.numberValue;
          }));
        } else throw new Error('unsupported test request');
      }
      files.set(id, next);
      if (state.fail === 'after') { state.fail = null; throw new Error('lost response after commit'); }
      return {};
    },
    Values: { batchGet(id, options) { return { valueRanges: options.ranges.map(range => ({ values: clone(files.get(id).sheets.find(s => s.properties.title === range.replaceAll("'", '')).rows) })) }; } },
  };
  const sandbox = {
    module: { exports: {} }, Date, Map, Set, JSON, Math, Number, Object, Array,
    Utilities: { DigestAlgorithm: { SHA_256: 'sha256' }, Charset: { UTF_8: 'utf8' },
      computeDigest: (_, value) => Array.from(crypto.createHash('sha256').update(value).digest()),
      newBlob: value => ({ getBytes: () => Buffer.from(value) }), getUuid: () => crypto.randomUUID() },
    PropertiesService: { getScriptProperties: () => ({ getProperties: () => ({ ...properties }), getProperty: key => properties[key], setProperties: values => Object.assign(properties, values), setProperty: (key, value) => properties[key] = value, deleteProperty: key => delete properties[key] }) },
    Session: { getEffectiveUser: () => ({ getEmail: () => state.owner }), getActiveUser: () => ({ getEmail: () => state.owner }) },
    LockService: { getScriptLock: () => ({ tryLock: () => { if (state.locked || state.busy) return false; state.locked = true; return true; }, releaseLock: () => state.locked = false }) },
    Sheets: { Spreadsheets: api },
    Drive: { Files: { get: id => ({ id, mimeType: 'application/vnd.google-apps.spreadsheet', ownedByMe: true, trashed: false, owners: [{ emailAddress: state.owner }] }) }, Permissions: { list: () => ({ permissions: [{ type: 'user', role: 'owner', emailAddress: state.owner }, ...(state.public ? [{ type: 'anyone', role: 'reader' }] : [])] }) } },
    ContentService: { MimeType: { JSON: 'json' }, createTextOutput: value => ({ setMimeType: () => value }) },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'Code.js'), 'utf8'), sandbox);
  const code = sandbox.module.exports;
  code.setupWorkspace();
  const deviceId = crypto.randomUUID(), deviceKey = crypto.randomBytes(32).toString('base64url');
  code.registerDevice(deviceId, crypto.createHash('sha256').update(deviceKey).digest('hex'), 'OFFICE', true);
  const request = (command, args = {}, overrides = {}) => JSON.stringify({ protocol: code.test.protocol, device_id: deviceId, device_key: deviceKey, command, args, ...overrides });
  const dispatch = (command, args, overrides) => clone(code.test.dispatch(request(command, args, overrides)));
  const program = () => ({ key: crypto.randomUUID(), kind: 'program', value: { name: 'PROGRAM', canonical_key: null, delivering_hei: null, description: null } });
  const initialize = records => dispatch('initialize', { request_id: crypto.randomUUID(), actor: 'ADMIN', expected_revision: 0, records });
  return { code, files, state, properties, dispatch, program, initialize, deviceId, request };
}

test('owner setup makes separate files and protected empty storage without uploading', () => {
  const h = harness();
  assert.notEqual(h.properties.STORAGE_ID, h.properties.REPORT_ID);
  const result = h.dispatch('read');
  assert.equal(result.ok, true);
  assert.equal(result.result.snapshot.records.length, 0);
  assert.equal(result.result.initialized, false);
  assert.ok(h.files.get(h.properties.STORAGE_ID).sheets.every(s => s.protectedRanges.length === 1));
  assert.equal(JSON.parse(h.code.doGet()).ok, false);
});

test('commit, receipt and revisions are atomic; exact replay does not duplicate', () => {
  const h = harness(), program = h.program();
  assert.equal(h.initialize([program]).ok, true);
  const args = { request_id: crypto.randomUUID(), actor: 'ADMIN', expected_revision: 1, changes: [{ ...program, expected_revision: 1, value: { ...program.value, description: 'CHANGED' } }] };
  h.state.fail = 'after';
  const lost = h.dispatch('commit', args);
  assert.equal(lost.error.outcome, 'unknown');
  const replay = h.dispatch('commit', args);
  assert.equal(replay.result.replayed, true);
  assert.equal(replay.result.snapshot.revision, 2);
  const changed = clone(args); changed.changes[0].value.description = 'OTHER';
  assert.equal(h.dispatch('commit', changed).error.outcome, 'unknown');
  assert.equal(h.dispatch('commit', { ...args, request_id: crypto.randomUUID() }).error.outcome, 'not_committed');
});

test('failed atomic request retains original storage and can retry', () => {
  const h = harness();
  const args = { request_id: crypto.randomUUID(), actor: 'ADMIN', expected_revision: 0, records: [h.program()] };
  h.state.fail = 'before';
  assert.equal(h.dispatch('initialize', args).error.outcome, 'unknown');
  assert.equal(h.dispatch('read').result.revision, 0);
  assert.equal(h.dispatch('initialize', args).result.snapshot.revision, 1);
});

test('two stale writers cannot overwrite, lock contention retains uncertain request', () => {
  const h = harness(), program = h.program(); h.initialize([program]);
  const write = name => ({ request_id: crypto.randomUUID(), actor: name, expected_revision: 1, changes: [{ ...program, expected_revision: 1, value: { ...program.value, name } }] });
  assert.equal(h.dispatch('commit', write('FIRST')).ok, true);
  const second = h.dispatch('commit', write('SECOND'));
  assert.equal(second.error.code, 'conflict'); assert.equal(second.error.outcome, 'not_committed');
  h.state.busy = true;
  assert.equal(h.dispatch('commit', write('SECOND')).error.outcome, 'unknown');
});

test('revocation, sharing changes and removed protection fail closed even on retries', () => {
  const h = harness(); h.initialize([h.program()]);
  const args = { request_id: crypto.randomUUID(), actor: 'ADMIN', expected_revision: 1, changes: [] };
  h.state.public = true;
  assert.equal(h.dispatch('read').ok, false);
  assert.equal(h.dispatch('commit', args).error.outcome, 'unknown');
  h.state.public = false;
  h.files.get(h.properties.STORAGE_ID).sheets[0].protectedRanges = [];
  assert.equal(h.dispatch('read').ok, false);
  h.code.revokeDevice(h.deviceId);
  const result = h.dispatch('commit', args);
  assert.equal(result.error.code, 'unauthorized'); assert.equal(result.error.outcome, 'unknown');
});

test('Unicode chunks round trip, formulas stay literal, report never changes storage', () => {
  const h = harness(), program = h.program(); program.value.description = '𐐀😀é'.repeat(12000);
  assert.equal(h.initialize([program]).ok, true);
  assert.equal(h.dispatch('read').result.snapshot.records[0].value.description, program.value.description);
  const before = JSON.stringify(h.files.get(h.properties.STORAGE_ID));
  const table = [Array.from(h.code.test.reportHeaders), ['=IMPORTXML("example")', ...Array(15).fill(null)]];
  assert.equal(h.dispatch('report', { expected_revision: 1, table }).ok, true);
  assert.equal(JSON.stringify(h.files.get(h.properties.STORAGE_ID)), before);
  assert.equal(h.dispatch('report', { expected_revision: 0, table }).error.code, 'conflict');
});

test('missing fields, dangling program references and malformed dates are rejected before commit', () => {
  const h = harness(), program = h.program(); delete program.value.description;
  assert.equal(h.initialize([program]).error.outcome, 'not_committed');
  const good = h.program(); assert.equal(h.initialize([good]).ok, true);
  const snapshot = h.dispatch('read').result.snapshot;
  snapshot.records[0].changed_at = '2026-02-31T00:00:00Z';
  assert.throws(() => h.code.test.validateSnapshot(snapshot));
});

test('Google omitted false/zero defaults retain whole-sheet owner protection; bounds and warning-only remain rejected', () => {
  const h = harness();
  h.state.omitDefaults = true;
  assert.equal(h.dispatch('status').ok, true);
  const protection = h.files.get(h.properties.STORAGE_ID).sheets[0].protectedRanges[0];
  protection.warningOnly = true;
  assert.equal(h.dispatch('status').ok, false);
  protection.warningOnly = false;
  protection.range.endRowIndex = 1;
  assert.equal(h.dispatch('status').ok, false);
  delete protection.range.endRowIndex;
  protection.unprotectedRanges = [{sheetId: 0, endRowIndex: 1}];
  assert.equal(h.dispatch('status').ok, false);
  delete protection.unprotectedRanges;
  protection.editors.users.push('other@example.test');
  assert.equal(h.dispatch('status').ok, false);
});
