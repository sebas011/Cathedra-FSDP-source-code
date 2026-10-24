import { useState, type ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import AppShell from "../src/components/AppShell";
import SessionRecovery from "../src/components/SessionRecovery";
import BackupExportPage from "../src/pages/BackupExportPage";
import FsdpListPage from "../src/pages/FsdpListPage";
import { useUnsavedChanges } from "../src/hooks/useUnsavedChanges";
import { getLogoutWarning, setLogoutWarning } from "../src/api/client";
import type { MaintenanceStatus } from "../src/types";
import { administrator, scholar } from "./fixtures";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getServiceHealth: vi.fn(),
  clearSession: vi.fn(),
  signOut: vi.fn(),
  exitDesktop: vi.fn(),
  getMaintenanceStatus: vi.fn(),
  restoreDatabase: vi.fn(),
  deleteDatabaseBackup: vi.fn(),
  setBackupProtection: vi.fn(),
  createDatabaseBackup: vi.fn(),
  downloadDatabaseBackup: vi.fn(),
  downloadExport: vi.fn(),
  getFsdpRecords: vi.fn(),
  getFsdpSummary: vi.fn(),
  deleteFsdpRecord: vi.fn(),
  signIn: vi.fn(),
  saveSession: vi.fn(),
}));
vi.mock("../src/api", () => ({ ...api, releaseVersion: "test" }));
vi.mock("../src/components/BackupReviewPanel", () => ({ default: () => null }));

const status: MaintenanceStatus = {
  database_status: "healthy",
  database_file: "synthetic.db",
  database_size_bytes: 1,
  fsdp_records: 1,
  backup_count: 2,
  latest_backup_at: null,
  backup_retention: null,
  backups: [
    {
      filename: "cathedra-backup-older.db",
      created_at: "2026-10-01T00:00:00Z",
      size_bytes: 1,
      protected: false,
      pinned: false,
    },
    {
      filename: "cathedra-backup-newest.db",
      created_at: "2026-10-02T00:00:00Z",
      size_bytes: 1,
      protected: true,
      pinned: true,
    },
  ],
};

function openPage(page: ReactNode) {
  const router = createMemoryRouter(
    [
      { path: "/review", element: page },
      { path: "/login", element: <h1>Sign in destination</h1> },
    ],
    { initialEntries: ["/review"] },
  );
  return { ...render(<RouterProvider router={router} />), router };
}

function openShell(page: ReactNode = <h1>Dashboard content</h1>) {
  const router = createMemoryRouter(
    [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: page },
          { path: "/fsdp", element: <h1>Scholar directory destination</h1> },
        ],
      },
      { path: "/login", element: <h1>Sign in destination</h1> },
    ],
    { initialEntries: ["/"] },
  );
  return { ...render(<RouterProvider router={router} />), router };
}

function Draft({ pending = false }: { pending?: boolean }) {
  const [text, setText] = useState("");
  useUnsavedChanges(text, pending);
  return (
    <label>
      Synthetic draft
      <input value={text} onChange={(event) => setText(event.target.value)} />
    </label>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  setLogoutWarning("");
  api.getCurrentUser.mockReturnValue(administrator);
  api.getServiceHealth.mockResolvedValue({
    status: "ok",
    product: "fsdp",
    release_version: "test",
    desktop_mode: true,
  });
  api.getMaintenanceStatus.mockResolvedValue(status);
  api.getFsdpRecords.mockResolvedValue({ items: [scholar], total: 1, page: 1, page_size: 50 });
  api.getFsdpSummary.mockResolvedValue({
    total: 1,
    ongoing: 1,
    graduated: 0,
    missing_requirements: 0,
  });
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
});

test("page render errors keep navigation usable, hide error details, and allow an in-place retry", async () => {
  let broken = true;
  function Page() {
    if (broken) throw new Error("synthetic private payload must not reach the page");
    return <h1>Recovered page content</h1>;
  }
  vi.spyOn(console, "error").mockImplementation(() => {});
  openShell(<Page />);
  await screen.findByRole("heading", { name: "This page could not be displayed" });
  expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeTruthy();
  expect(screen.queryByText(/synthetic private payload/)).toBeNull();
  const reload = vi.fn();
  const browserWindow = window;
  vi.stubGlobal(
    "window",
    new Proxy(browserWindow, {
      get: (target, key) => (key === "location" ? { reload } : Reflect.get(target, key)),
    }),
  );
  try {
    fireEvent.click(screen.getByRole("button", { name: "Reload Cathedra" }));
  } finally {
    vi.stubGlobal("window", browserWindow);
  }
  expect(reload).toHaveBeenCalledTimes(1);
  broken = false;
  fireEvent.click(screen.getByRole("button", { name: "Try this page again" }));
  await screen.findByRole("heading", { name: "Recovered page content" });
});

test("changing pages clears the failed boundary and returning loads the recovered page", async () => {
  let broken = true;
  function Page() {
    if (broken) throw new Error("synthetic render failure");
    return <h1>Dashboard recovered after navigation</h1>;
  }
  vi.spyOn(console, "error").mockImplementation(() => {});
  openShell(<Page />);
  await screen.findByRole("heading", { name: "This page could not be displayed" });
  fireEvent.click(screen.getByRole("link", { name: "Scholars" }));
  await screen.findByRole("heading", { name: "Scholar directory destination" });
  broken = false;
  fireEvent.click(screen.getByRole("link", { name: "Overview" }));
  await screen.findByRole("heading", { name: "Dashboard recovered after navigation" });
});

test("scholar deletion requires an explicit dialog choice, preserves cancelled records, and submits once", async () => {
  api.deleteFsdpRecord.mockRejectedValue(new Error("Synthetic delete failure"));
  openPage(<FsdpListPage />);
  const trigger = await screen.findByRole("button", { name: `Delete scholar ${scholar.name}` });
  trigger.focus();
  fireEvent.click(trigger);
  let dialog = await screen.findByRole("dialog", { name: "Delete scholar?" });
  expect(dialog.textContent).toContain(
    "their grant and requirement records? This cannot be undone.",
  );
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Keep scholar" }));
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep scholar" }));
  expect(api.deleteFsdpRecord).not.toHaveBeenCalled();
  expect(document.activeElement).toBe(trigger);
  fireEvent.click(trigger);
  dialog = await screen.findByRole("dialog", { name: "Delete scholar?" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Delete scholar" }));
  await screen.findByText("Synthetic delete failure");
  expect(api.deleteFsdpRecord).toHaveBeenCalledExactlyOnceWith(scholar.id, scholar.revision);
  expect(screen.getByRole("link", { name: scholar.name })).toBeTruthy();
});

test("backup deletion cancellation preserves the backup and acceptance targets the confirmed filename", async () => {
  openPage(<BackupExportPage />);
  const trigger = await screen.findByRole("button", { name: "Delete Older Backup" });
  fireEvent.click(trigger);
  let dialog = await screen.findByRole("dialog", { name: "Permanently delete this backup?" });
  expect(dialog.textContent).toContain("cathedra-backup-older.db? This cannot be undone.");
  fireEvent(dialog, new Event("cancel", { cancelable: true }));
  expect(api.deleteDatabaseBackup).not.toHaveBeenCalled();
  fireEvent.click(trigger);
  dialog = await screen.findByRole("dialog", { name: "Permanently delete this backup?" });
  fireEvent.change(screen.getByRole("combobox", { name: "Backup to download or restore" }), {
    target: { value: "cathedra-backup-newest.db" },
  });
  fireEvent.click(within(dialog).getByRole("button", { name: "Delete backup" }));
  await screen.findByText(
    "The selected older backup was deleted. Protected backups were not changed.",
  );
  expect(api.deleteDatabaseBackup).toHaveBeenCalledExactlyOnceWith("cathedra-backup-older.db");
});

test("restore warns about safety backups and sign-out, cancels safely, and blocks duplicate acceptance", async () => {
  let finish!: () => void;
  api.restoreDatabase.mockReturnValue(
    new Promise<void>((resolve) => {
      finish = resolve;
    }),
  );
  const { router } = openPage(<BackupExportPage />);
  const trigger = await screen.findByRole("button", { name: "Restore Selected Backup" });
  fireEvent.click(trigger);
  let dialog = await screen.findByRole("dialog", { name: "Restore this backup?" });
  expect(dialog.textContent).toContain(
    "safety backup of the current records. All sessions will be signed out.",
  );
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep current records" }));
  expect(api.restoreDatabase).not.toHaveBeenCalled();
  fireEvent.click(trigger);
  dialog = await screen.findByRole("dialog", { name: "Restore this backup?" });
  const accept = within(dialog).getByRole("button", { name: "Restore backup" });
  fireEvent.click(accept);
  fireEvent.click(accept);
  await waitFor(() =>
    expect(api.restoreDatabase).toHaveBeenCalledExactlyOnceWith("cathedra-backup-older.db"),
  );
  expect(window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))).toBe(false);
  await act(async () => finish());
  await screen.findByRole("heading", { name: "Sign in destination" });
  expect(router.state.location.pathname).toBe("/login");
  expect(api.clearSession).toHaveBeenCalledTimes(1);
});

test("unpinning backup protection can be cancelled and explicitly accepted", async () => {
  openPage(<BackupExportPage />);
  await screen.findByRole("button", { name: "Restore Selected Backup" });
  fireEvent.change(screen.getByRole("combobox", { name: "Backup to download or restore" }), {
    target: { value: "cathedra-backup-newest.db" },
  });
  const trigger = screen.getByRole("button", { name: "Unpin Backup" });
  fireEvent.click(trigger);
  let dialog = await screen.findByRole("dialog", { name: "Remove backup protection?" });
  expect(dialog.textContent).toContain("unless it is the newest backup");
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep protection" }));
  expect(api.setBackupProtection).not.toHaveBeenCalled();
  fireEvent.click(trigger);
  dialog = await screen.findByRole("dialog", { name: "Remove backup protection?" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Remove protection" }));
  await waitFor(() =>
    expect(api.setBackupProtection).toHaveBeenCalledExactlyOnceWith(
      "cathedra-backup-newest.db",
      false,
    ),
  );
});

test("cancelled logout preserves the unsaved draft and accepted logout retains revocation warnings", async () => {
  api.signOut.mockRejectedValue(new Error("Synthetic service unavailable"));
  const { router } = openShell(<Draft />);
  fireEvent.change(screen.getByRole("textbox", { name: "Synthetic draft" }), {
    target: { value: "Keep this draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  let dialog = await screen.findByRole("dialog", { name: "Discard your changes?" });
  expect(dialog.textContent).toContain("Discard unsaved changes and log out?");
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep editing" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog", { name: "Discard your changes?" })).toBeNull(),
  );
  expect(api.signOut).not.toHaveBeenCalled();
  expect((screen.getByRole("textbox", { name: "Synthetic draft" }) as HTMLInputElement).value).toBe(
    "Keep this draft",
  );
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  dialog = await screen.findByRole("dialog", { name: "Discard your changes?" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Discard changes" }));
  await screen.findByRole("heading", { name: "Sign in destination" });
  expect(api.signOut).toHaveBeenCalledTimes(1);
  expect(api.clearSession).toHaveBeenCalledTimes(1);
  expect(router.state.location.state.logoutWarning).toContain("did not confirm session revocation");
  expect(getLogoutWarning()).toContain("Accounts & Access");
});

test("logout rechecks pending saves after asynchronous discard confirmation", async () => {
  let setPending!: (pending: boolean) => void;
  function Page() {
    const [pending, updatePending] = useState(false);
    setPending = updatePending;
    return <Draft pending={pending} />;
  }
  openShell(<Page />);
  fireEvent.change(screen.getByRole("textbox", { name: "Synthetic draft" }), {
    target: { value: "Unsaved" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  const dialog = await screen.findByRole("dialog", { name: "Discard your changes?" });
  act(() => setPending(true));
  fireEvent.click(within(dialog).getByRole("button", { name: "Discard changes" }));
  await screen.findByText("Wait for the current save to finish before leaving.");
  expect(api.signOut).not.toHaveBeenCalled();
  expect(api.clearSession).not.toHaveBeenCalled();
});

test("exit can be cancelled without losing drafts and accepted once after the warning", async () => {
  let finish!: () => void;
  api.exitDesktop.mockReturnValue(
    new Promise<void>((resolve) => {
      finish = resolve;
    }),
  );
  const close = vi.spyOn(window, "close").mockImplementation(() => {});
  openShell(<Draft />);
  fireEvent.change(screen.getByRole("textbox", { name: "Synthetic draft" }), {
    target: { value: "Keep before exiting" },
  });
  const trigger = await screen.findByRole("button", { name: "Exit Cathedra" });
  fireEvent.click(trigger);
  let dialog = await screen.findByRole("dialog", { name: "Exit Cathedra?" });
  expect(dialog.textContent).toContain("Finish and save any open changes first.");
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep Cathedra open" }));
  expect(api.exitDesktop).not.toHaveBeenCalled();
  expect((screen.getByRole("textbox", { name: "Synthetic draft" }) as HTMLInputElement).value).toBe(
    "Keep before exiting",
  );
  fireEvent.click(trigger);
  dialog = await screen.findByRole("dialog", { name: "Exit Cathedra?" });
  const accept = within(dialog).getByRole("button", { name: "Exit Cathedra" });
  fireEvent.click(accept);
  fireEvent.click(accept);
  await waitFor(() => expect(api.exitDesktop).toHaveBeenCalledTimes(1));
  await act(async () => finish());
  await screen.findByRole("heading", { name: "Cathedra has stopped" });
  expect(close).toHaveBeenCalledTimes(1);
  expect(api.clearSession).toHaveBeenCalledTimes(1);
});

test("session recovery discard cancellation keeps the recovery password and accepting clears the session", async () => {
  render(<SessionRecovery user={administrator} />);
  const recovery = await screen.findByRole("dialog", { name: "Sign in again to keep editing" });
  const password = within(recovery).getByLabelText("Password") as HTMLInputElement;
  fireEvent.change(password, { target: { value: "synthetic-password" } });
  const trigger = within(recovery).getByRole("button", { name: "Discard and sign in" });
  fireEvent.click(trigger);
  let confirmation = await screen.findByRole("dialog", { name: "Discard unsaved work?" });
  fireEvent(confirmation, new Event("cancel", { cancelable: true }));
  expect(api.clearSession).not.toHaveBeenCalled();
  expect(password.value).toBe("synthetic-password");
  fireEvent.click(trigger);
  confirmation = await screen.findByRole("dialog", { name: "Discard unsaved work?" });
  fireEvent.click(within(confirmation).getByRole("button", { name: "Discard and sign in" }));
  expect(api.clearSession).toHaveBeenCalledTimes(1);
});
