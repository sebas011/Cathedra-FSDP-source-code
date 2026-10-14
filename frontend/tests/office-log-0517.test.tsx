import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { createMemoryRouter, Link, RouterProvider } from "react-router-dom";
import OfficeLogPanel from "../src/components/OfficeLogPanel";
import type { OfficeLogItem, OfficeLogPage } from "../src/api/officeLog";

const api = vi.hoisted(() => ({ getOfficeLogs: vi.fn(), addOfficeLog: vi.fn(), exportOfficeLogs: vi.fn() }));
const auth = vi.hoisted(() => ({ getCurrentUser: vi.fn(), getExpiredUser: vi.fn(), UnconfirmedOperationError: class extends Error {} }));
vi.mock("../src/api/officeLog", () => api);
vi.mock("../src/api/client", () => auth);
const empty: OfficeLogPage = { items: [], total: 0, page: 1, page_size: 20 };
const entry: OfficeLogItem = { id: 1, scholar_id: 9, scholar_name: "TEST SCHOLAR", user_id: 2, username: "officeUser", occurred_on: "2026-10-12", created_at: "2026-10-12T01:00:00", entry_type: "Note", note: "RECORDED NOTE" };
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(yes => { resolve = yes; });
  return { promise, resolve };
}
function mount(scholarId?: number) {
  const router = createMemoryRouter([
    { path: "/", element: <><Link to="/away">Leave log</Link><OfficeLogPanel scholarId={scholarId} /></> },
    { path: "/away", element: <h1>Another page</h1> },
  ]);
  const view = render(<RouterProvider router={router} />);
  return { ...view, router };
}
async function edit(note = "a document was received") {
  fireEvent.click(await screen.findByRole("button", { name: "Add log entry" }));
  fireEvent.change(screen.getByLabelText("Log note"), { target: { value: note } });
}
beforeEach(() => {
  vi.resetAllMocks();
  auth.getCurrentUser.mockReturnValue({ id: 2, username: "officeUser", role: "staff" });
  auth.getExpiredUser.mockReturnValue(null);
  api.getOfficeLogs.mockResolvedValue(empty);
  api.addOfficeLog.mockResolvedValue(entry);
  api.exportOfficeLogs.mockResolvedValue(undefined);
});

test("profile log saves uppercase document movement with authenticated author left to the server", async () => {
  mount(9); await edit();
  fireEvent.change(screen.getByLabelText("Entry type"), { target: { value: "Document transferred" } });
  fireEvent.change(screen.getByLabelText("Entry date"), { target: { value: "2026-10-11" } });
  fireEvent.change(screen.getByLabelText("Document (optional)"), { target: { value: "completion certificate" } });
  fireEvent.change(screen.getByLabelText("From department (optional)"), { target: { value: "fsdp" } });
  fireEvent.change(screen.getByLabelText("To department (optional)"), { target: { value: "hrmo" } });
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await screen.findByText("Log entry saved.");
  expect(api.addOfficeLog).toHaveBeenCalledWith({ scholar_id: 9, occurred_on: "2026-10-11", entry_type: "Document transferred", note: "A DOCUMENT WAS RECEIVED", document_name: "COMPLETION CERTIFICATE", from_department: "FSDP", to_department: "HRMO" }, expect.stringMatching(/^[a-f0-9-]{36}$/));
  expect((screen.getByLabelText("Log note") as HTMLTextAreaElement).value).toBe("");
  expect(api.getOfficeLogs).toHaveBeenLastCalledWith(expect.objectContaining({ scholar_id: 9, page: 1 }));
});

test("general log supports optional context and date without requiring scholar identifiers", async () => {
  mount(); await edit("office note");
  fireEvent.change(screen.getByLabelText("Entry date"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await screen.findByText("Log entry saved.");
  expect(api.addOfficeLog).toHaveBeenCalledWith(expect.objectContaining({ scholar_id: null, occurred_on: null, note: "OFFICE NOTE", document_name: null, from_department: null, to_department: null }), expect.any(String));
});

test("blank notes are rejected locally without imposing document or department requirements", async () => {
  mount(); await edit("  ");
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Enter a note"));
  expect(api.addOfficeLog).not.toHaveBeenCalled();
});

test("viewers can read immutable entries without write controls", async () => {
  auth.getCurrentUser.mockReturnValue({ role: "viewer" });
  api.getOfficeLogs.mockResolvedValue({ ...empty, total: 1, items: [entry] });
  mount(9);
  await screen.findByText("RECORDED NOTE");
  expect(screen.getByRole("link", { name: "TEST SCHOLAR" }).getAttribute("href")).toBe("/fsdp/9");
  expect(screen.getByText(/Recorded by officeUser/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Add log entry" })).toBeNull();
  expect(screen.queryByRole("button", { name: /Delete|Edit entry/ })).toBeNull();
});

test("unconfirmed saves keep draft and retry identity, and confirmed next entry gets a fresh identity", async () => {
  api.addOfficeLog.mockRejectedValueOnce(new Error("Save was not confirmed"));
  mount(); await edit("keep this note");
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await screen.findByText("Save was not confirmed");
  const firstKey = api.addOfficeLog.mock.calls[0][1];
  expect((screen.getByLabelText("Log note") as HTMLTextAreaElement).value).toBe("KEEP THIS NOTE");
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await screen.findByText("Log entry saved.");
  expect(api.addOfficeLog.mock.calls[1][1]).toBe(firstKey);
  fireEvent.change(screen.getByLabelText("Log note"), { target: { value: "second entry" } });
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await waitFor(() => expect(api.addOfficeLog).toHaveBeenCalledTimes(3));
  expect(api.addOfficeLog.mock.calls[2][1]).not.toBe(firstKey);
});

test("pending save blocks duplicate submission and navigation until confirmation", async () => {
  const pending = deferred<OfficeLogItem>();
  api.addOfficeLog.mockReturnValue(pending.promise);
  const { router } = mount(); await edit();
  const form = screen.getByRole("form", { name: "General office-log entry" });
  fireEvent.submit(form); fireEvent.submit(form);
  expect(api.addOfficeLog).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("link", { name: "Leave log" }));
  await screen.findByRole("heading", { name: "Saving the log entry" });
  expect(screen.getByRole("button", { name: "Leave without saving" }).hasAttribute("disabled")).toBe(true);
  expect(router.state.location.pathname).toBe("/");
  fireEvent.click(screen.getByRole("button", { name: "Stay here" }));
  await act(async () => { pending.resolve(entry); await pending.promise; });
  fireEvent.click(screen.getByRole("link", { name: "Leave log" }));
  await screen.findByRole("heading", { name: "Another page" });
});

test("uncertain saves freeze the original payload and can retry it exactly", async () => {
  api.addOfficeLog.mockRejectedValueOnce(new auth.UnconfirmedOperationError("Connection interrupted"));
  mount(); await edit("original entry");
  fireEvent.click(screen.getByRole("button", { name: "Save log entry" }));
  await screen.findByText("Connection interrupted");
  expect(screen.getByLabelText("Log note").hasAttribute("disabled")).toBe(true);
  expect(screen.getByLabelText("Entry type").hasAttribute("disabled")).toBe(true);
  expect(screen.getByLabelText("Document (optional)").hasAttribute("disabled")).toBe(true);
  const firstAttempt = api.addOfficeLog.mock.calls[0];
  fireEvent.click(screen.getByRole("button", { name: "Retry same entry" }));
  await screen.findByText("Log entry saved.");
  expect(api.addOfficeLog.mock.calls[1]).toEqual(firstAttempt);
  expect(screen.getByLabelText("Log note").hasAttribute("disabled")).toBe(false);
});

test("session expiration during a log refresh preserves the same-account editor draft", async () => {
  mount(); await edit("unsaved office note");
  auth.getCurrentUser.mockReturnValue(null);
  auth.getExpiredUser.mockReturnValue({ id: 2, username: "officeUser", role: "staff" });
  api.getOfficeLogs.mockRejectedValueOnce(new Error("Sign in again"));
  fireEvent.click(screen.getByRole("button", { name: "Refresh log" }));
  await screen.findByText("Sign in again");
  expect((screen.getByLabelText("Log note") as HTMLTextAreaElement).value).toBe("UNSAVED OFFICE NOTE");
  auth.getCurrentUser.mockReturnValue({ id: 2, username: "officeUser", role: "staff" });
  auth.getExpiredUser.mockReturnValue(null);
  fireEvent.click(screen.getByRole("button", { name: "Retry log" }));
  await screen.findByText("No log entries recorded.");
  expect((screen.getByLabelText("Log note") as HTMLTextAreaElement).value).toBe("UNSAVED OFFICE NOTE");
});

test("closing a dirty editor requires explicit discard and leaves saved entries intact", async () => {
  api.getOfficeLogs.mockResolvedValue({ ...empty, total: 1, items: [entry] });
  mount(); await edit();
  fireEvent.click(screen.getByRole("button", { name: "Close log editor" }));
  await screen.findByRole("dialog", { name: "Discard your changes?" });
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect(screen.getByLabelText("Log note")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Close log editor" }));
  fireEvent.click(await screen.findByRole("button", { name: "Discard changes" }));
  await waitFor(() => expect(screen.queryByLabelText("Log note")).toBeNull());
  expect(screen.getByText("RECORDED NOTE")).toBeTruthy();
  expect(api.addOfficeLog).not.toHaveBeenCalled();
});

test("new filters reset pagination and stale responses cannot replace the current scope", async () => {
  api.getOfficeLogs.mockResolvedValue({ ...empty, total: 21, items: [entry] });
  mount(); await screen.findByText("RECORDED NOTE");
  fireEvent.click(screen.getByRole("button", { name: "Next log entries" }));
  await waitFor(() => expect(api.getOfficeLogs).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
  await screen.findByText("Page 2 of 2");
  const oldScope = deferred<OfficeLogPage>();
  api.getOfficeLogs.mockReturnValueOnce(oldScope.promise).mockResolvedValue({ ...empty, total: 1, items: [{ ...entry, note: "CURRENT SCOPE" }] });
  fireEvent.change(screen.getByLabelText("Search office log"), { target: { value: "first" } });
  fireEvent.change(screen.getByLabelText("Search office log"), { target: { value: "second" } });
  await screen.findByText("CURRENT SCOPE");
  expect(api.getOfficeLogs).toHaveBeenLastCalledWith(expect.objectContaining({ search: "second", page: 1 }));
  await act(async () => { oldScope.resolve({ ...empty, total: 1, items: [{ ...entry, note: "STALE SCOPE" }] }); await oldScope.promise; });
  expect(screen.queryByText("STALE SCOPE")).toBeNull();
  expect(screen.getByText("CURRENT SCOPE")).toBeTruthy();
});

test("load errors can be retried and log HTML stays plain text", async () => {
  api.getOfficeLogs.mockRejectedValueOnce(new Error("Log unavailable")).mockResolvedValue({ ...empty, total: 1, items: [{ ...entry, note: "<img src=x onerror=alert(1)>" }] });
  const { container } = mount();
  await screen.findByText("Log unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Retry log" }));
  await screen.findByText("<img src=x onerror=alert(1)>");
  expect(container.querySelector("img")).toBeNull();
});
