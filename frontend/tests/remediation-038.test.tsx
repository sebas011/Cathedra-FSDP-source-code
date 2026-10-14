import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import App from "../src/App";
import AccountSecurityPage from "../src/pages/AccountSecurityPage";
import DashboardReports from "../src/components/DashboardReports";
import { clearSession, getCurrentUser, request, requestResponse, saveSession } from "../src/api/client";
import { administrator, scholar } from "./fixtures";

const api = vi.hoisted(() => ({ signIn: vi.fn(), signOut: vi.fn(), getFsdpRecord: vi.fn(), getServiceHealth: vi.fn(), getAccountStatus: vi.fn(), getUsers: vi.fn(), createUser: vi.fn(), getFsdpReport: vi.fn(), getFsdpReportOptions: vi.fn() }));
vi.mock("../src/api", async original => ({ ...await original<typeof import("../src/api")>(), ...api }));

beforeEach(() => {
  vi.resetAllMocks(); clearSession();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  api.getFsdpRecord.mockResolvedValue(scholar);
  api.getServiceHealth.mockResolvedValue({ status: "ok", product: "fsdp" });
  api.getAccountStatus.mockResolvedValue({ setup_required: false });
  api.getUsers.mockResolvedValue([administrator]);
});

test("expired-session sign-in preserves the same scholar draft without resubmitting", async () => {
  saveSession({ token: "synthetic", user: administrator });
  render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }], { initialEntries: ["/fsdp/1/edit"] })} />);
  const name = await screen.findByRole("textbox", { name: "Name *" });
  fireEvent.change(name, { target: { value: "Draft retained" } });
  act(() => clearSession(true));
  await screen.findByRole("dialog", { name: "Sign in again to keep editing" });
  api.signIn.mockResolvedValue({ token: "new-synthetic", user: administrator });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue editing" }));
  await waitFor(() => expect(screen.queryByRole("dialog", { name: "Sign in again to keep editing" })).toBeNull());
  expect((name as HTMLInputElement).value).toBe("DRAFT RETAINED");
  expect(screen.getByRole("textbox", { name: "Name *" })).toBe(name);
  expect(api.getFsdpRecord).toHaveBeenCalledTimes(1);
});

test("recovery refuses a different account identity", async () => {
  saveSession({ token: "synthetic", user: administrator });
  render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }], { initialEntries: ["/fsdp/1/edit"] })} />);
  await screen.findByRole("textbox", { name: "Name *" });
  act(() => clearSession(true));
  api.signIn.mockResolvedValue({ token: "different", user: { ...administrator, id: 999 } });
  fireEvent.change(await screen.findByLabelText("Password"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue editing" }));
  await screen.findByText("This account requires a new sign-in. Discard this draft to continue securely.");
  expect(getCurrentUser()).toBeNull();
});

test("unconfirmed logout survives navigation and clears local credentials", async () => {
  saveSession({ token: "synthetic", user: administrator });
  api.signOut.mockRejectedValue(new Error("Disconnected"));
  render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }], { initialEntries: ["/fsdp/1/edit"] })} />);
  await screen.findByRole("textbox", { name: "Name *" });
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  await screen.findByText(/The local service did not confirm session revocation/);
  expect(getCurrentUser()).toBeNull();
  expect(api.signOut).toHaveBeenCalledTimes(1);
});

test("account inputs freeze during submission and reset only after confirmation", async () => {
  saveSession({ token: "synthetic", user: administrator });
  let finish!: (value: typeof administrator) => void;
  api.createUser.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <AccountSecurityPage /> }])} />);
  const username = screen.getByLabelText("Username") as HTMLInputElement;
  const form = username.closest("form")!;
  fireEvent.change(username, { target: { value: "office-test" } });
  fireEvent.change(form.querySelector('[name="password"]')!, { target: { value: "synthetic-password" } });
  fireEvent.submit(form);
  await waitFor(() => expect(username.matches(":disabled")).toBe(true));
  expect(api.createUser).toHaveBeenCalledWith("office-test", "synthetic-password", "staff");
  await act(async () => finish({ ...administrator, id: 100, username: "office-test" }));
  expect(username.value).toBe("");
  expect(username.matches(":disabled")).toBe(false);
});

test.each(["json", "blob"] as const)("timeout also bounds stalled %s consumption", async kind => {
  vi.useFakeTimers();
  vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, status: 200, [kind]: () => new Promise(() => {}) } as unknown as Response);
  try {
    const rejected = expect(requestResponse("/synthetic", undefined, response => response[kind]())).rejects.toThrow("did not confirm");
    await vi.advanceTimersByTimeAsync(30000);
    await rejected;
  } finally { vi.useRealTimers(); }
});

test("login failure during recovery does not discard the expired identity", async () => {
  saveSession({ token: "synthetic", user: administrator });
  clearSession(true);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Username or password is incorrect." }), { status: 401 }));
  await expect(request("/auth/login", { method: "POST" })).rejects.toThrow("incorrect");
  const { getExpiredUser } = await import("../src/api/client");
  expect(getExpiredUser()?.id).toBe(administrator.id);
});


test("staff logout warning offers an administrator recovery path", async () => {
  saveSession({ token: "synthetic", user: { ...administrator, role: "staff" } });
  api.signOut.mockRejectedValue(new Error("Disconnected"));
  render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }], { initialEntries: ["/fsdp/1/edit"] })} />);
  await screen.findByRole("textbox", { name: "Name *" });
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  await screen.findByText(/ask an administrator to sign out your sessions/);
  expect(getCurrentUser()).toBeNull();
});

test("report scope survives switching report views", async () => {
  api.getFsdpReport.mockResolvedValue({ total: 0, items: [], status_counts: { "On Going": 0, Graduated: 0, Payback: 0, Withdrawn: 0 }, action_items: [], department_totals: [] });
  api.getFsdpReportOptions.mockResolvedValue({ departments: ["CAS"], ranks: [], delivering_heis: [] });
  const router = createMemoryRouter([{ path: "/", element: <DashboardReports /> }], { initialEntries: ["/?department=CAS&view=directory"] });
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(api.getFsdpReport).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button", { name: "Follow-up actions" }));
  expect(new URLSearchParams(router.state.location.search).get("department")).toBe("CAS");
  expect(api.getFsdpReport).toHaveBeenCalledWith(expect.objectContaining({ department: "CAS" }));
});
