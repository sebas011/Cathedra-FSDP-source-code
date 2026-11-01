import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import axe from "axe-core";
import SharedWorkspacePanel from "../src/components/SharedWorkspacePanel";
import SharedWorkspaceStatus from "../src/components/SharedWorkspaceStatus";
import BackupExportPage from "../src/pages/BackupExportPage";
import { UnconfirmedOperationError } from "../src/api/client";
import {
  disconnectedSharedWorkspace,
  joinedSharedWorkspace,
  sharedPreview,
} from "./sharedWorkspaceFixtures";
import { administrator } from "./fixtures";

const api = vi.hoisted(() => ({
  getSharedWorkspaceStatus: vi.fn(),
  configureSharedWorkspace: vi.fn(),
  checkSharedWorkspace: vi.fn(),
  disconnectSharedWorkspace: vi.fn(),
  previewSharedWorkspace: vi.fn(),
  applySharedWorkspace: vi.fn(),
  retrySharedWorkspace: vi.fn(),
  publishSharedWorkspaceReport: vi.fn(),
  notifySharedWorkspaceChanged: vi.fn(),
}));
vi.mock("../src/api/sharedWorkspace", () => ({
  ...api,
  sharedWorkspaceChangedEvent: "cathedra-shared-workspace-changed",
}));
const maintenance = vi.hoisted(() => ({ getCurrentUser: vi.fn(), getMaintenanceStatus: vi.fn() }));
vi.mock("../src/api", () => maintenance);
const legacy = vi.hoisted(() => ({ getGoogleSheetsStatus: vi.fn() }));
vi.mock("../src/api/googleSheets", () => legacy);
const applied = {
  state: "ready",
  revision: 4,
  uploaded: 1,
  downloaded: 0,
  conflicts: 0,
  replayed: false,
  message: "Reviewed records retained.",
};
const maintenanceStatus = (count: number) => ({
  database_status: "healthy",
  database_file: "cathedra.db",
  database_size_bytes: 1024,
  fsdp_records: count,
  backup_count: 0,
  latest_backup_at: null,
  backups: [],
});

beforeEach(() => {
  vi.resetAllMocks();
  api.getSharedWorkspaceStatus.mockResolvedValue(joinedSharedWorkspace());
  api.configureSharedWorkspace.mockResolvedValue({
    ...joinedSharedWorkspace(),
    connected: false,
    joined: false,
  });
  api.checkSharedWorkspace.mockResolvedValue(joinedSharedWorkspace());
  api.disconnectSharedWorkspace.mockResolvedValue(disconnectedSharedWorkspace());
  api.previewSharedWorkspace.mockResolvedValue(sharedPreview());
  api.applySharedWorkspace.mockResolvedValue(applied);
  api.retrySharedWorkspace.mockResolvedValue({ ...applied, replayed: true });
  api.publishSharedWorkspaceReport.mockResolvedValue({
    rows: 17,
    synced_at: "2026-10-31T08:00:00Z",
    spreadsheet_url: "https://docs.google.com/spreadsheets/d/fictional-report/edit",
    revision: 4,
  });
  maintenance.getCurrentUser.mockReturnValue(administrator);
  maintenance.getMaintenanceStatus.mockResolvedValue(maintenanceStatus(12));
  legacy.getGoogleSheetsStatus.mockResolvedValue({
    configured: false,
    connected: false,
    spreadsheet_id: null,
    worksheet: "CATHEDRA REPORT",
    last_sync_at: null,
    connection_state: "idle",
    message: null,
  });
});

function showPanel(
  callbacks: {
    onApplied?: () => void;
    onPendingChange?: (pending: boolean) => void;
    onModeChange?: (configured: boolean | null) => void;
  } = {},
) {
  return render(
    <MemoryRouter>
      <SharedWorkspacePanel {...callbacks} />
    </MemoryRouter>,
  );
}
async function openPreview() {
  await screen.findByRole("button", { name: "Sync workspace" });
  fireEvent.click(screen.getByRole("button", { name: "Sync workspace" }));
  await screen.findByRole("heading", { name: "Review shared changes" });
}
function reviewAndApply() {
  fireEvent.click(screen.getByRole("button", { name: "Review shared save" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply reviewed shared changes" }));
}

test("saving setup stays local and shows only read-only registration details", async () => {
  api.getSharedWorkspaceStatus.mockResolvedValue(disconnectedSharedWorkspace());
  showPanel();
  await screen.findByRole("button", { name: "Save shared connection" });
  fireEvent.change(screen.getByLabelText("Owner's Google bridge address"), {
    target: { value: joinedSharedWorkspace().endpoint },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save shared connection" }));
  const fingerprint = await screen.findByRole("textbox", {
    name: "Device registration fingerprint",
  });
  expect((fingerprint as HTMLInputElement).readOnly).toBe(true);
  expect((fingerprint as HTMLInputElement).value).toBe("a".repeat(64));
  expect(api.configureSharedWorkspace).toHaveBeenCalledWith(joinedSharedWorkspace().endpoint);
  expect(api.checkSharedWorkspace).not.toHaveBeenCalled();
  expect(api.previewSharedWorkspace).not.toHaveBeenCalled();
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
  expect(localStorage.length + sessionStorage.length).toBe(0);
});

test("first Office upload requires an explicit mode, acknowledgement and confirmation", async () => {
  api.getSharedWorkspaceStatus.mockResolvedValue({
    ...joinedSharedWorkspace(),
    joined: false,
    initialized: false,
    can_initialize: true,
    state: "disconnected",
  });
  api.previewSharedWorkspace.mockResolvedValue({ ...sharedPreview(), mode: "initialize" });
  showPanel();
  await screen.findByRole("button", { name: "Review first Office upload" });
  expect(api.previewSharedWorkspace).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Review first Office upload" }));
  await screen.findByRole("heading", { name: "Review first Office upload" });
  expect(api.previewSharedWorkspace).toHaveBeenCalledWith("initialize");
  const acknowledgement = screen.getByRole("checkbox", { name: /authoritative Office computer/ });
  expect((acknowledgement as HTMLInputElement).checked).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Review shared save" }));
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
  expect(
    screen.queryByRole("dialog", { name: "Initialize shared storage from this Office computer?" }),
  ).toBeNull();
  fireEvent.click(acknowledgement);
  reviewAndApply();
  await screen.findByText(/Shared changes saved/);
  expect(api.applySharedWorkspace).toHaveBeenCalledTimes(1);
});

test("joining describes the local replacement and never chooses initialization automatically", async () => {
  api.getSharedWorkspaceStatus.mockResolvedValue({
    ...joinedSharedWorkspace(),
    joined: false,
    can_initialize: true,
    state: "disconnected",
  });
  api.previewSharedWorkspace.mockResolvedValue({ ...sharedPreview(), mode: "join" });
  showPanel();
  await screen.findByRole("button", { name: "Review joining shared storage" });
  expect(screen.queryByRole("button", { name: "Review first Office upload" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Review joining shared storage" }));
  await screen.findByRole("checkbox", {
    name: /Local business records will be backed up and replaced/,
  });
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
});

test("all whole-record conflicts need an explicit local or shared choice", async () => {
  const first = sharedPreview().items[0];
  const second = {
    ...first,
    key: "55555555-5555-4555-8555-555555555555",
    kind: "program" as const,
    label: "FICTIONAL PROGRAM",
  };
  api.previewSharedWorkspace.mockResolvedValue({
    ...sharedPreview(),
    items: [
      { ...first, conflict: true, direction: "conflict" },
      { ...second, conflict: true, direction: "conflict" },
    ],
    conflicts: [first.key, second.key],
    counts: { local: 12, shared: 12, upload: 0, download: 0, conflicts: 2 },
  });
  showPanel();
  await openPreview();
  expect(screen.getAllByRole("radio").every((radio) => !(radio as HTMLInputElement).checked)).toBe(
    true,
  );
  fireEvent.click(screen.getByRole("button", { name: "Review shared save" }));
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
  fireEvent.click(
    within(screen.getByRole("group", { name: /version of FICTIONAL SCHOLAR/ })).getByLabelText(
      "Keep this computer's version",
    ),
  );
  fireEvent.click(
    within(screen.getByRole("group", { name: /version of FICTIONAL PROGRAM/ })).getByLabelText(
      "Keep shared storage's version",
    ),
  );
  reviewAndApply();
  await screen.findByText(/Shared changes saved/);
  expect(api.applySharedWorkspace).toHaveBeenCalledWith(sharedPreview().preview_id, {
    [first.key]: "local",
    [second.key]: "shared",
  });
});

test("a double confirmation sends one save and notifies once", async () => {
  let resolve!: (value: unknown) => void;
  api.applySharedWorkspace.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const onApplied = vi.fn();
  showPanel({ onApplied });
  await openPreview();
  fireEvent.click(screen.getByRole("button", { name: "Review shared save" }));
  const confirm = screen.getByRole("button", { name: "Apply reviewed shared changes" });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(api.applySharedWorkspace).toHaveBeenCalledTimes(1);
  expect(onApplied).not.toHaveBeenCalled();
  await act(async () => {
    resolve(applied);
  });
  expect(onApplied).toHaveBeenCalledTimes(1);
});

test("an unconfirmed save uses the persisted retry instead of a second apply", async () => {
  api.applySharedWorkspace.mockRejectedValue(new UnconfirmedOperationError("Result not confirmed"));
  const onApplied = vi.fn();
  showPanel({ onApplied });
  await openPreview();
  api.getSharedWorkspaceStatus.mockResolvedValue({ ...joinedSharedWorkspace(), state: "pending" });
  reviewAndApply();
  await screen.findByRole("button", { name: "Retry earlier sync" });
  expect(onApplied).not.toHaveBeenCalled();
  expect(
    (screen.getByRole("button", { name: "Disconnect this computer" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  api.getSharedWorkspaceStatus.mockResolvedValue({ ...joinedSharedWorkspace(), state: "ready" });
  fireEvent.click(screen.getByRole("button", { name: "Retry earlier sync" }));
  await screen.findByText(/Earlier sync confirmed/);
  expect(api.retrySharedWorkspace).toHaveBeenCalledTimes(1);
  expect(api.applySharedWorkspace).toHaveBeenCalledTimes(1);
  expect(onApplied).toHaveBeenCalledTimes(1);
});

test("a pending request is recoverable after loading a fresh window", async () => {
  api.getSharedWorkspaceStatus.mockResolvedValue({ ...joinedSharedWorkspace(), state: "pending" });
  showPanel();
  await screen.findByRole("button", { name: "Retry earlier sync" });
  expect(api.previewSharedWorkspace).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Sync workspace" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Save shared connection" })).toBeNull();
});

test("stale save failures retain the preview without claiming success", async () => {
  api.applySharedWorkspace.mockRejectedValue(
    new Error("Another computer saved newer records. Refresh the preview."),
  );
  const onApplied = vi.fn();
  showPanel({ onApplied });
  await openPreview();
  reviewAndApply();
  await screen.findByText(/Another computer saved newer records/);
  expect(screen.getByRole("heading", { name: "Review shared changes" })).toBeTruthy();
  expect(onApplied).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Refresh shared preview" }));
  await waitFor(() => expect(api.previewSharedWorkspace).toHaveBeenCalledTimes(2));
});

test("expired previews cannot be applied", async () => {
  api.previewSharedWorkspace.mockResolvedValue({
    ...sharedPreview(),
    expires_at: "2020-01-01T00:00:00Z",
  });
  showPanel();
  await openPreview();
  await screen.findByText(/This preview has expired/);
  expect(
    (screen.getByRole("button", { name: "Review shared save" }) as HTMLButtonElement).disabled,
  ).toBe(true);
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
});

test("shared reporting reads canonical storage after its own confirmation", async () => {
  showPanel();
  await screen.findByRole("button", { name: "Update shared report" });
  fireEvent.click(screen.getByRole("button", { name: "Update shared report" }));
  expect(api.publishSharedWorkspaceReport).not.toHaveBeenCalled();
  expect(screen.getByText(/does not upload local pending edits/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Replace shared report" }));
  await screen.findByText(/Shared report updated: 17 rows/);
  expect(api.publishSharedWorkspaceReport).toHaveBeenCalledTimes(1);
  expect(api.applySharedWorkspace).not.toHaveBeenCalled();
});

test("shared mode hides legacy report writers and refreshes the maintenance count after save", async () => {
  maintenance.getMaintenanceStatus
    .mockResolvedValueOnce(maintenanceStatus(12))
    .mockResolvedValue(maintenanceStatus(13));
  const router = createMemoryRouter([{ path: "/backup-export", element: <BackupExportPage /> }], {
    initialEntries: ["/backup-export"],
  });
  render(<RouterProvider router={router} />);
  await screen.findByRole("button", { name: "Sync workspace" });
  expect(screen.queryByRole("button", { name: "Update Google Sheet" })).toBeNull();
  expect(legacy.getGoogleSheetsStatus).not.toHaveBeenCalled();
  await openPreview();
  reviewAndApply();
  await waitFor(() =>
    expect(
      within(screen.getByRole("region", { name: "Record counts" })).getByText("13"),
    ).toBeTruthy(),
  );
  expect(api.applySharedWorkspace).toHaveBeenCalledTimes(1);
  expect(maintenance.getMaintenanceStatus).toHaveBeenCalledTimes(2);
});

test("an unknown shared mode keeps legacy reporting unavailable until status is known", async () => {
  api.getSharedWorkspaceStatus.mockRejectedValue(new Error("Connection status unavailable"));
  const onModeChange = vi.fn();
  showPanel({ onModeChange });
  await screen.findByText("Connection status unavailable");
  expect(onModeChange).toHaveBeenCalledWith(null);
});

test("setup and preview controls have accessible names and relationships", async () => {
  const { container } = showPanel();
  await openPreview();
  const result = await axe.run(container, {
    runOnly: {
      type: "rule",
      values: [
        "button-name",
        "link-name",
        "label",
        "aria-valid-attr-value",
        "aria-valid-attr",
        "duplicate-id-aria",
      ],
    },
  });
  expect(result.violations).toEqual([]);
});

test("header polling keeps the last known shared state when connectivity fails", async () => {
  showHeader();
  await screen.findByRole("link", { name: "Changes waiting to sync" });
  api.getSharedWorkspaceStatus.mockRejectedValue(new Error("Offline"));
  window.dispatchEvent(new Event("cathedra-shared-workspace-changed"));
  await screen.findByRole("link", { name: "Shared status unavailable" });
});

function showHeader() {
  return render(
    <MemoryRouter>
      <SharedWorkspaceStatus admin />
    </MemoryRouter>,
  );
}
