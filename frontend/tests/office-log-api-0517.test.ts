import { beforeEach, expect, test, vi } from "vitest";
import { addOfficeLog, exportOfficeLogs, getOfficeLogs } from "../src/api/officeLog";
const api = vi.hoisted(() => ({ request: vi.fn(), download: vi.fn() }));
vi.mock("../src/api/client", () => api);
beforeEach(() => vi.resetAllMocks());
test("log export uses the complete matching scope without limiting to the current page", () => {
  exportOfficeLogs({
    scholar_id: 9,
    search: "josé & docs",
    entry_type: "Document transferred",
    page: 3,
  });
  const [path, filename] = api.download.mock.calls[0];
  const query = new URL(path, "http://localhost").searchParams;
  expect(query.get("scholar_id")).toBe("9");
  expect(query.get("search")).toBe("josé & docs");
  expect(query.get("entry_type")).toBe("Document transferred");
  expect(query.has("page")).toBe(false);
  expect(filename).toBe("cathedra-office-log.csv");
});
test("list requests retain pagination and write requests retain exact retry identifiers", () => {
  getOfficeLogs({ page: 2, search: "100%_literal", entry_type: "" });
  const query = new URL(api.request.mock.calls[0][0], "http://localhost").searchParams;
  expect(query.get("page")).toBe("2");
  expect(query.get("search")).toBe("100%_literal");
  expect(query.has("entry_type")).toBe(false);
  addOfficeLog(
    { note: "SAME PAYLOAD", entry_type: "Note" },
    "00112233-4455-6677-8899-aabbccddeeff",
  );
  expect(api.request).toHaveBeenLastCalledWith("/office-logs", {
    method: "POST",
    body: JSON.stringify({ note: "SAME PAYLOAD", entry_type: "Note" }),
    headers: { "Idempotency-Key": "00112233-4455-6677-8899-aabbccddeeff" },
  });
});
