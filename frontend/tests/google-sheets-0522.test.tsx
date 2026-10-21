import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import GoogleSheetsPanel from "../src/components/GoogleSheetsPanel";
import type { GoogleSheetsStatus } from "../src/api/googleSheets";
import BackupExportPage from "../src/pages/BackupExportPage";
import { administrator } from "./fixtures";

const api = vi.hoisted(() => ({
  configureGoogleSheets: vi.fn(),
  connectGoogleSheets: vi.fn(),
  disconnectGoogleSheets: vi.fn(),
  getGoogleSheetsStatus: vi.fn(),
  syncGoogleSheets: vi.fn(),
}));
vi.mock("../src/api/googleSheets", () => api);
const maintenanceApi = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getMaintenanceStatus: vi.fn(),
  clearSession: vi.fn(),
  createDatabaseBackup: vi.fn(),
  deleteDatabaseBackup: vi.fn(),
  downloadDatabaseBackup: vi.fn(),
  downloadExport: vi.fn(),
  restoreDatabase: vi.fn(),
  setBackupProtection: vi.fn(),
}));
vi.mock("../src/api", () => maintenanceApi);

const sheetId = "synthetic-reporting-sheet-12345";
const sheetUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/edit`;
const configured: GoogleSheetsStatus = {
  configured: true,
  connected: false,
  spreadsheet_id: sheetId,
  worksheet: "CATHEDRA REPORT",
  last_sync_at: null,
  connection_state: "idle",
  message: null,
};
const connected: GoogleSheetsStatus = {
  ...configured,
  connected: true,
  connection_state: "connected",
};
const credentials = {
  installed: {
    client_id: "synthetic.apps.googleusercontent.com",
    client_secret: "synthetic-local-secret",
    redirect_uris: ["http://localhost"],
  },
};

beforeEach(() => {
  vi.resetAllMocks();
  api.getGoogleSheetsStatus.mockResolvedValue(configured);
  api.configureGoogleSheets.mockResolvedValue(configured);
  api.connectGoogleSheets.mockResolvedValue({ ...configured, connection_state: "waiting" });
  api.disconnectGoogleSheets.mockResolvedValue(configured);
  api.syncGoogleSheets.mockResolvedValue({
    rows: 4,
    synced_at: "2026-10-17T03:00:00Z",
    spreadsheet_url: sheetUrl,
  });
  maintenanceApi.getCurrentUser.mockReturnValue(administrator);
  maintenanceApi.getMaintenanceStatus.mockResolvedValue({
    database_status: "healthy",
    database_file: "cathedra.db",
    database_size_bytes: 1,
    fsdp_records: 1,
    backup_count: 0,
    latest_backup_at: null,
    backup_retention: null,
    backups: [],
  });
});

function showPanel(onPendingChange = vi.fn()) {
  return render(
    <MemoryRouter>
      <GoogleSheetsPanel onPendingChange={onPendingChange} />
    </MemoryRouter>,
  );
}

function chooseFile(contents: string) {
  const file = new File([contents], "desktop-client.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: () => Promise.resolve(contents) });
  fireEvent.change(screen.getByLabelText("Google Desktop credentials JSON"), {
    target: { files: [file] },
  });
}

test("initial setup saves a chosen target and JSON in memory without sending a report", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue({
    ...configured,
    configured: false,
    spreadsheet_id: null,
  });
  showPanel();
  await screen.findByText(
    "Save your reporting spreadsheet and Desktop credentials, then connect Google.",
  );
  expect(
    screen.getByRole("link", { name: "Connection setup and guide" }).getAttribute("href"),
  ).toBe("/office-guide#cloud-reporting");
  fireEvent.change(screen.getByLabelText("Reporting spreadsheet URL or ID"), {
    target: { value: sheetUrl },
  });
  chooseFile(JSON.stringify(credentials));
  await screen.findByText("Credentials selected: desktop-client.json");
  fireEvent.click(screen.getByRole("button", { name: "Save connection details" }));
  await waitFor(() =>
    expect(api.configureGoogleSheets).toHaveBeenCalledWith(sheetUrl, credentials),
  );
  await screen.findByText("Connection details saved.");
  expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  expect(api.connectGoogleSheets).not.toHaveBeenCalled();
  expect(screen.queryByText("Credentials selected: desktop-client.json")).toBeNull();
  expect(JSON.stringify(Object.values(sessionStorage))).not.toContain("synthetic-local-secret");
  expect(JSON.stringify(Object.values(localStorage))).not.toContain("synthetic-local-secret");
});

test("invalid JSON is rejected locally and credentials cannot accidentally configure a target", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue({
    ...configured,
    configured: false,
    spreadsheet_id: null,
  });
  showPanel();
  await screen.findByText(
    "Save your reporting spreadsheet and Desktop credentials, then connect Google.",
  );
  fireEvent.change(screen.getByLabelText("Reporting spreadsheet URL or ID"), {
    target: { value: sheetUrl },
  });
  chooseFile("[1,2]");
  await screen.findByRole("alert");
  expect(
    screen.getByRole("button", { name: "Save connection details" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(api.configureGoogleSheets).not.toHaveBeenCalled();
});

test("a failed configuration preserves the chosen target and credentials for retry", async () => {
  api.configureGoogleSheets.mockRejectedValueOnce(new Error("Google details were not saved."));
  showPanel();
  await screen.findByText(
    "Connection details saved. Connect your Google account to update the report.",
  );
  fireEvent.click(screen.getByText("Connection details"));
  chooseFile(JSON.stringify(credentials));
  await screen.findByText("Credentials selected: desktop-client.json");
  fireEvent.click(screen.getByRole("button", { name: "Save connection details" }));
  await screen.findByText("Google details were not saved.");
  expect((screen.getByLabelText("Reporting spreadsheet URL or ID") as HTMLInputElement).value).toBe(
    sheetUrl,
  );
  expect(screen.getByText("Credentials selected: desktop-client.json")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Save connection details" }));
  await waitFor(() => expect(api.configureGoogleSheets).toHaveBeenCalledTimes(2));
  expect(api.configureGoogleSheets).toHaveBeenLastCalledWith(sheetUrl, credentials);
});

test("a sheet update requires explicit replacement confirmation and supports cancellation", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue(connected);
  showPanel();
  await screen.findByText("Google account connected.");
  fireEvent.click(screen.getByRole("button", { name: "Update Google Sheet" }));
  await screen.findByRole("dialog", { name: "Replace the Google report?" });
  expect(
    screen.getByText(/replaces all report values in its CATHEDRA REPORT tab/).textContent,
  ).toContain("Other tabs are unchanged");
  expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep existing report" }));
  expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Update Google Sheet" }));
  fireEvent.click(await screen.findByRole("button", { name: "Replace reporting tab" }));
  await screen.findByText("Google report updated: 4 grant and scholar rows.");
  expect(api.syncGoogleSheets).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/Last successful update: Not updated yet/)).toBeNull();
  expect(
    screen.getByRole("link", { name: "Open reporting spreadsheet" }).getAttribute("href"),
  ).toBe(sheetUrl);
});

test("an update failure retains the last successful timestamp and offers an explicit retry", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue({
    ...connected,
    last_sync_at: "2026-10-16T02:00:00Z",
  });
  api.syncGoogleSheets.mockRejectedValueOnce(new Error("Google could not be reached."));
  showPanel();
  await screen.findByText("Google account connected.");
  const previous = screen.getByText(/Last successful update:/).textContent;
  fireEvent.click(screen.getByRole("button", { name: "Update Google Sheet" }));
  fireEvent.click(await screen.findByRole("button", { name: "Replace reporting tab" }));
  await screen.findByText("Google could not be reached.");
  expect(screen.getByText(/Last successful update:/).textContent).toBe(previous);
  expect(screen.queryByText(/Google report updated/)).toBeNull();
  expect(screen.getByRole("button", { name: "Update Google Sheet" }).hasAttribute("disabled")).toBe(
    false,
  );
});

test("an unsaved target change blocks connecting and updating until the details are saved", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue(connected);
  showPanel();
  await screen.findByText("Google account connected.");
  fireEvent.click(screen.getByText("Connection details"));
  fireEvent.change(screen.getByLabelText("Reporting spreadsheet URL or ID"), {
    target: { value: "different-sheet-12345" },
  });
  expect(screen.getByRole("button", { name: "Update Google Sheet" }).hasAttribute("disabled")).toBe(
    true,
  );
  expect(screen.getByRole("button", { name: "Reconnect Google" }).hasAttribute("disabled")).toBe(
    true,
  );
  expect(
    screen.getByRole("link", { name: "Open reporting spreadsheet" }).getAttribute("href"),
  ).toBe(sheetUrl);
});

test("browser sign-in polls until connected and keeps the parent informed while waiting", async () => {
  const pending = vi.fn();
  showPanel(pending);
  await screen.findByText(
    "Connection details saved. Connect your Google account to update the report.",
  );
  vi.useFakeTimers();
  try {
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Connect Google" }));
    });
    expect(screen.getByText(/Complete Google sign-in/)).toBeTruthy();
    expect(pending).toHaveBeenLastCalledWith(true);
    api.getGoogleSheetsStatus.mockResolvedValue(connected);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(screen.getByText("Google account connected.")).toBeTruthy();
    expect(pending).toHaveBeenLastCalledWith(false);
    expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  } finally {
    vi.useRealTimers();
  }
});

test("status read failures can be refreshed and disconnecting never changes the report", async () => {
  api.getGoogleSheetsStatus
    .mockRejectedValueOnce(new Error("Connection status unavailable."))
    .mockResolvedValue(connected);
  showPanel();
  await screen.findByText("Connection status unavailable.");
  fireEvent.click(screen.getByRole("button", { name: "Refresh Google connection" }));
  await screen.findByText("Google account connected.");
  fireEvent.click(screen.getByRole("button", { name: "Disconnect Google" }));
  await screen.findByText("Google account disconnected from this app.");
  expect(api.disconnectGoogleSheets).toHaveBeenCalledTimes(1);
  expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Update Google Sheet" }).hasAttribute("disabled")).toBe(
    true,
  );
});

test("an unreachable sign-in status cannot leave the page locked indefinitely", async () => {
  const pending = vi.fn();
  showPanel(pending);
  await screen.findByText(
    "Connection details saved. Connect your Google account to update the report.",
  );
  vi.useFakeTimers();
  try {
    api.getGoogleSheetsStatus.mockReturnValue(new Promise(() => {}));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Connect Google" }));
    });
    expect(pending).toHaveBeenLastCalledWith(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(240000);
    });
    expect(
      screen.getByText(
        "Google sign-in status was not confirmed. Refresh the connection before trying again.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Refresh Google connection" }).hasAttribute("disabled"),
    ).toBe(false);
    expect(pending).toHaveBeenLastCalledWith(false);
  } finally {
    vi.useRealTimers();
  }
});

test("a corrupt saved connection can be forgotten even when its status cannot be loaded", async () => {
  api.getGoogleSheetsStatus.mockRejectedValue(
    new Error("The saved connection cannot be unlocked."),
  );
  api.disconnectGoogleSheets.mockResolvedValue({
    ...configured,
    configured: false,
    spreadsheet_id: null,
  });
  showPanel();
  await screen.findByText("The saved connection cannot be unlocked.");
  expect(screen.getByLabelText("Reporting spreadsheet URL or ID")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Forget Google connection" }));
  await screen.findByText("Google account disconnected from this app.");
  expect(api.disconnectGoogleSheets).toHaveBeenCalledTimes(1);
  expect(api.syncGoogleSheets).not.toHaveBeenCalled();
  expect(screen.queryByText("The saved connection cannot be unlocked.")).toBeNull();
});

test("ordinary staff cannot see the cloud reporting panel or request its connection status", async () => {
  maintenanceApi.getCurrentUser.mockReturnValue({ ...administrator, role: "staff" });
  const router = createMemoryRouter([{ path: "*", element: <BackupExportPage /> }]);
  render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { name: "Backup & Export" });
  expect(screen.queryByRole("heading", { name: "Google Sheets report" })).toBeNull();
  expect(api.getGoogleSheetsStatus).not.toHaveBeenCalled();
});

test("an administrator's active sheet update blocks backup operations and navigation until confirmed", async () => {
  api.getGoogleSheetsStatus.mockResolvedValue(connected);
  let finish!: (value: unknown) => void;
  api.syncGoogleSheets.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const router = createMemoryRouter(
    [
      { path: "/maintenance", element: <BackupExportPage /> },
      { path: "/away", element: <h1>Away</h1> },
    ],
    { initialEntries: ["/maintenance"] },
  );
  render(<RouterProvider router={router} />);
  await screen.findByText("Google account connected.");
  fireEvent.click(screen.getByRole("button", { name: "Update Google Sheet" }));
  fireEvent.click(await screen.findByRole("button", { name: "Replace reporting tab" }));
  await waitFor(() => expect(api.syncGoogleSheets).toHaveBeenCalled());
  expect(screen.getByRole("button", { name: "Create Backup" }).hasAttribute("disabled")).toBe(true);
  expect(window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))).toBe(false);
  await act(async () => {
    await router.navigate("/away");
  });
  await screen.findByRole("dialog", { name: "Finishing the operation" });
  expect(router.state.location.pathname).toBe("/maintenance");
  fireEvent.click(screen.getByRole("button", { name: "Stay here" }));
  await act(async () => {
    finish({ rows: 4, synced_at: "2026-10-17T03:00:00Z", spreadsheet_url: sheetUrl });
  });
  await screen.findByText("Google report updated: 4 grant and scholar rows.");
  expect(window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))).toBe(true);
});
