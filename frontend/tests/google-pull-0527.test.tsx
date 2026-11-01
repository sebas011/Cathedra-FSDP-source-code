import { disconnectedSharedWorkspace } from "./sharedWorkspaceFixtures";
vi.mock("../src/api/sharedWorkspace", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/sharedWorkspace")>();
  return { ...actual, getSharedWorkspaceStatus: async () => disconnectedSharedWorkspace() };
});
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import axe from "axe-core";
import GoogleSheetPull from "../src/components/GoogleSheetPull";
import GoogleSheetsPanel from "../src/components/GoogleSheetsPanel";
import BackupExportPage from "../src/pages/BackupExportPage";
import { UnconfirmedOperationError } from "../src/api/client";
import type { GooglePullPreview, GooglePullResult } from "../src/api/googlePull";
import { administrator } from "./fixtures";

const api = vi.hoisted(() => ({ previewGoogleSheetPull: vi.fn(), applyGoogleSheetPull: vi.fn() }));
vi.mock("../src/api/googlePull", () => api);
const connection = vi.hoisted(() => ({
  getGoogleSheetsStatus: vi.fn(),
  configureGoogleSheets: vi.fn(),
  connectGoogleSheets: vi.fn(),
  disconnectGoogleSheets: vi.fn(),
  syncGoogleSheets: vi.fn(),
}));
vi.mock("../src/api/googleSheets", () => connection);
const maintenance = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getMaintenanceStatus: vi.fn(),
}));
vi.mock("../src/api", () => maintenance);

const completed = {
  scholars_created: 0,
  scholars_updated: 1,
  grants_created: 0,
  grants_updated: 1,
  scholar_ids: [5],
  replayed: false,
};

function preview(): GooglePullPreview {
  return {
    preview_id: "synthetic-preview-one",
    fetched_at: "2026-10-30T10:00:00Z",
    expires_at: "2099-10-30T10:15:00Z",
    worksheet: "CATHEDRA REPORT",
    warnings: [],
    profiles: [
      {
        key: "profile-one",
        row: 2,
        fields: {
          name: "EXISTING SCHOLAR",
          age: 0,
          tenure_years: 0,
          department: "CAS",
          rank: null,
          profile_remarks: null,
        },
        education_text: "BACHELOR OF ARTS · EXAMPLE COLLEGE",
        suggested_scholar_id: 5,
        grants: [
          {
            key: "grant-one",
            row: 2,
            fields: {
              program_name: "EXAMPLE MASTERS",
              status: "Incomplete",
              remarks: "REVISED GRANT REMARK",
            },
            suggested_participation_id: 11,
          },
        ],
      },
    ],
    matches: [
      {
        id: 5,
        name: "EXISTING SCHOLAR",
        revision: 7,
        fields: {
          name: "EXISTING SCHOLAR",
          age: 42,
          tenure_years: 4,
          department: "CAS",
          rank: null,
          profile_remarks: "PREVIOUS PROFILE REMARK",
        },
        grants: [
          {
            id: 11,
            fields: {
              program_name: "EXAMPLE MASTERS",
              status: "On Going",
              start_term: "1st",
              start_academic_year: "2021",
              remarks: "PREVIOUS GRANT REMARK",
            },
          },
        ],
      },
    ],
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  api.previewGoogleSheetPull.mockResolvedValue(preview());
  api.applyGoogleSheetPull.mockResolvedValue(completed);
  connection.getGoogleSheetsStatus.mockResolvedValue({
    configured: true,
    connected: true,
    spreadsheet_id: "synthetic-reporting-sheet",
    worksheet: "CATHEDRA REPORT",
    last_sync_at: null,
    connection_state: "connected",
    message: null,
  });
  maintenance.getCurrentUser.mockReturnValue(administrator);
  maintenance.getMaintenanceStatus.mockResolvedValue({
    database_status: "healthy",
    database_file: "cathedra.db",
    database_size_bytes: 1024,
    fsdp_records: 12,
    backup_count: 0,
    latest_backup_at: null,
    backups: [],
  });
});

function showPull(
  disabled = false,
  onPendingChange = vi.fn(),
  onApplied: (result: GooglePullResult) => void = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <GoogleSheetPull
        disabled={disabled}
        onPendingChange={onPendingChange}
        onApplied={onApplied}
      />
    </MemoryRouter>,
  );
}

async function fetchPreview() {
  fireEvent.click(screen.getByRole("button", { name: "Pull from Google Sheet" }));
  await screen.findByText("0 of 1 scholars selected");
}

function selectProfile() {
  fireEvent.click(screen.getByRole("checkbox", { name: /EXISTING SCHOLAR/ }));
}

test("pull controls and the selected preview have valid accessible names and references", async () => {
  const { container } = showPull();
  const assertAccessible = async () => {
    const result = await axe.run(container, {
      runOnly: {
        type: "rule",
        values: [
          "button-name",
          "link-name",
          "label",
          "aria-valid-attr",
          "aria-valid-attr-value",
          "aria-required-attr",
          "aria-roles",
        ],
      },
    });
    expect(
      result.violations.map((item) => ({
        id: item.id,
        nodes: item.nodes.map((node) => node.html),
      })),
    ).toEqual([]);
  };
  await assertAccessible();
  await fetchPreview();
  selectProfile();
  await assertAccessible();
});

async function confirmApply() {
  fireEvent.click(screen.getByRole("button", { name: "Review selected changes" }));
  const dialog = await screen.findByRole("dialog", {
    name: "Apply selected Google Sheet changes?",
  });
  fireEvent.click(within(dialog).getByRole("button", { name: "Apply selected changes" }));
}

test("pulling reads a preview only, starts with no scholars selected and can close safely", async () => {
  const pending = vi.fn();
  showPull(false, pending);
  expect(api.previewGoogleSheetPull).not.toHaveBeenCalled();
  await fetchPreview();
  expect(api.previewGoogleSheetPull).toHaveBeenCalledTimes(1);
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  expect(
    (screen.getByRole("checkbox", { name: /EXISTING SCHOLAR/ }) as HTMLInputElement).checked,
  ).toBe(false);
  expect(
    screen.getByRole("button", { name: "Review selected changes" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(pending).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "Close preview" }));
  expect(screen.queryByText("0 of 1 scholars selected")).toBeNull();
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  await waitFor(() => expect(pending).toHaveBeenLastCalledWith(false));
});

test("selected existing records show zero and cleared remarks distinctly and require a final confirmation", async () => {
  const applied = vi.fn();
  showPull(false, vi.fn(), applied);
  await fetchPreview();
  expect(applied).not.toHaveBeenCalled();
  selectProfile();
  const profile = screen.getByRole("region", { name: "Profile comparison for sheet row 2" });
  const age = within(profile).getByRole("row", { name: /^Age / });
  expect(within(age).getByText("42")).toBeTruthy();
  expect(within(age).getByText("0")).toBeTruthy();
  const remarks = within(profile).getByRole("row", { name: /^Profile remarks / });
  expect(within(remarks).getByText("PREVIOUS PROFILE REMARK")).toBeTruthy();
  expect(within(remarks).getByText("Clears this field")).toBeTruthy();
  expect(screen.getByText("Existing education is kept")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Review selected changes" }));
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  fireEvent.click(await screen.findByRole("button", { name: "Keep reviewing" }));
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  expect(applied).not.toHaveBeenCalled();
  await confirmApply();
  await screen.findByText("Selected changes applied.");
  expect(applied).toHaveBeenCalledExactlyOnceWith(completed);
  expect(api.applyGoogleSheetPull).toHaveBeenCalledWith({
    preview_id: "synthetic-preview-one",
    profiles: [
      {
        key: "profile-one",
        scholar_id: 5,
        expected_revision: 7,
        grants: [{ key: "grant-one", participation_id: 11 }],
      },
    ],
  });
});

test("namesakes and unmatched grants require manual mapping before anything can be applied", async () => {
  const data = preview();
  data.profiles[0].suggested_scholar_id = null;
  data.profiles[0].grants[0].suggested_participation_id = null;
  data.matches.push({
    ...data.matches[0],
    id: 6,
    revision: 3,
    grants: [
      {
        id: 22,
        fields: { program_name: "EXAMPLE MASTERS", start_term: "2nd", start_academic_year: "2022" },
      },
    ],
  });
  api.previewGoogleSheetPull.mockResolvedValue(data);
  showPull();
  await fetchPreview();
  selectProfile();
  expect(
    screen.getByText("Several scholars have this name. Choose the intended record."),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Review selected changes" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Choose an existing or new scholar for sheet row 2.",
  );
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Scholar for row 2"), { target: { value: "id:6" } });
  fireEvent.click(screen.getByRole("button", { name: "Review selected changes" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Choose an existing grant or a new independent application",
  );
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Grant for sheet row 2"), { target: { value: "id:22" } });
  await confirmApply();
  await screen.findByText("Selected changes applied.");
  expect(api.applyGoogleSheetPull).toHaveBeenCalledWith({
    preview_id: "synthetic-preview-one",
    profiles: [
      {
        key: "profile-one",
        scholar_id: 6,
        expected_revision: 3,
        grants: [{ key: "grant-one", participation_id: 22 }],
      },
    ],
  });
});

test("a new independent application must be explicitly chosen for an existing scholar", async () => {
  const data = preview();
  data.profiles[0].grants[0].suggested_participation_id = null;
  api.previewGoogleSheetPull.mockResolvedValue(data);
  showPull();
  await fetchPreview();
  selectProfile();
  expect((screen.getByLabelText("Grant for sheet row 2") as HTMLSelectElement).value).toBe("");
  fireEvent.change(screen.getByLabelText("Grant for sheet row 2"), { target: { value: "new" } });
  expect(screen.getByText("New independent application", { exact: true })).toBeTruthy();
  await confirmApply();
  await screen.findByText("Selected changes applied.");
  expect(api.applyGoogleSheetPull.mock.calls[0][0].profiles[0].grants).toEqual([
    { key: "grant-one", participation_id: null },
  ]);
});

test("existing grant choices distinguish exact dates and ending periods for repeated programs", async () => {
  const data = preview();
  data.matches[0].grants[0].fields.start_date = "2021-06-01";
  data.matches[0].grants[0].fields.end_term = "Summer";
  data.matches[0].grants[0].fields.end_academic_year = "2022";
  data.matches[0].grants.push({
    id: 12,
    fields: {
      program_name: "EXAMPLE MASTERS",
      start_date: "2023-06-01",
      end_date: "2024-05-31",
    },
  });
  api.previewGoogleSheetPull.mockResolvedValue(data);
  showPull();
  await fetchPreview();
  selectProfile();
  const grants = screen.getByLabelText("Grant for sheet row 2");
  expect(
    within(grants).getByRole("option", {
      name: "EXAMPLE MASTERS · From 2021-06-01 · To Summer 2022 · Grant #11",
    }),
  ).toBeTruthy();
  expect(
    within(grants).getByRole("option", {
      name: "EXAMPLE MASTERS · From 2023-06-01 · To 2024-05-31 · Grant #12",
    }),
  ).toBeTruthy();
});

test("a confirmed conflict retains the reviewed selections and supports a fresh preview", async () => {
  api.applyGoogleSheetPull.mockRejectedValueOnce(new Error("A scholar changed after preview."));
  const applied = vi.fn();
  showPull(false, vi.fn(), applied);
  await fetchPreview();
  selectProfile();
  await confirmApply();
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "A scholar changed after preview.",
  );
  expect(
    (screen.getByRole("checkbox", { name: /EXISTING SCHOLAR/ }) as HTMLInputElement).checked,
  ).toBe(true);
  expect(screen.queryByText("Retry same selected changes")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Refresh preview" }));
  await screen.findByText("0 of 1 scholars selected");
  expect(api.previewGoogleSheetPull).toHaveBeenCalledTimes(2);
  expect(api.applyGoogleSheetPull).toHaveBeenCalledTimes(1);
  expect(applied).not.toHaveBeenCalled();
});

test("new profiles are visibly marked as new, keep education text readable and escape cell contents", async () => {
  const data = preview();
  data.matches = [];
  data.profiles[0].suggested_scholar_id = null;
  data.profiles[0].fields.profile_remarks = "<img src=x onerror=alert(1)>";
  api.previewGoogleSheetPull.mockResolvedValue(data);
  api.applyGoogleSheetPull.mockResolvedValue({
    ...completed,
    scholars_created: 1,
    scholars_updated: 0,
    grants_created: 1,
    grants_updated: 0,
  });
  showPull();
  await fetchPreview();
  selectProfile();
  expect(screen.getByText("Create a new scholar", { exact: true })).toBeTruthy();
  expect(screen.getByText("New education text entries")).toBeTruthy();
  expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeTruthy();
  expect(document.querySelector("img")).toBeNull();
  await confirmApply();
  await screen.findByText("Selected changes applied.");
  expect(api.applyGoogleSheetPull).toHaveBeenCalledWith({
    preview_id: "synthetic-preview-one",
    profiles: [
      {
        key: "profile-one",
        scholar_id: null,
        expected_revision: null,
        grants: [{ key: "grant-one", participation_id: null }],
      },
    ],
  });
});

test("disabled and repeated clicks cannot start duplicate preview or apply requests", async () => {
  const { rerender } = showPull(true);
  fireEvent.click(screen.getByRole("button", { name: "Pull from Google Sheet" }));
  expect(api.previewGoogleSheetPull).not.toHaveBeenCalled();
  rerender(
    <MemoryRouter>
      <GoogleSheetPull />
    </MemoryRouter>,
  );
  let finishPreview!: (value: GooglePullPreview) => void;
  api.previewGoogleSheetPull.mockReturnValue(
    new Promise((resolve) => {
      finishPreview = resolve;
    }),
  );
  const pull = screen.getByRole("button", { name: "Pull from Google Sheet" });
  fireEvent.click(pull);
  fireEvent.click(pull);
  expect(api.previewGoogleSheetPull).toHaveBeenCalledTimes(1);
  await act(async () => {
    finishPreview(preview());
  });
  selectProfile();
  let finishApply!: (value: typeof completed) => void;
  api.applyGoogleSheetPull.mockReturnValue(
    new Promise((resolve) => {
      finishApply = resolve;
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Review selected changes" }));
  const confirm = await screen.findByRole("button", { name: "Apply selected changes" });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(api.applyGoogleSheetPull).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Close preview" }).hasAttribute("disabled")).toBe(true);
  await act(async () => {
    finishApply(completed);
  });
  await screen.findByText("Selected changes applied.");
});

test("an unconfirmed apply locks choices and retries exactly the original payload", async () => {
  api.applyGoogleSheetPull.mockRejectedValueOnce(
    new UnconfirmedOperationError("Save confirmation was interrupted."),
  );
  let finishRetry!: (value: typeof completed) => void;
  api.applyGoogleSheetPull.mockReturnValueOnce(
    new Promise((resolve) => {
      finishRetry = resolve;
    }),
  );
  const pending = vi.fn();
  const applied = vi.fn();
  showPull(false, pending, applied);
  await fetchPreview();
  selectProfile();
  await confirmApply();
  await screen.findByText("Save confirmation was interrupted.");
  expect(applied).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Close preview" }).hasAttribute("disabled")).toBe(true);
  expect(screen.getByRole("button", { name: "Refresh preview" }).hasAttribute("disabled")).toBe(
    true,
  );
  expect(screen.getByLabelText("Scholar for row 2").hasAttribute("disabled")).toBe(true);
  const original = api.applyGoogleSheetPull.mock.calls[0][0];
  fireEvent.change(screen.getByLabelText("Scholar for row 2"), { target: { value: "new" } });
  const retry = screen.getByRole("button", { name: "Retry same selected changes" });
  fireEvent.click(retry);
  fireEvent.click(retry);
  expect(api.applyGoogleSheetPull).toHaveBeenCalledTimes(2);
  expect(api.applyGoogleSheetPull.mock.calls[1][0]).toEqual(original);
  expect(pending).toHaveBeenLastCalledWith(true);
  await act(async () => {
    finishRetry({ ...completed, replayed: true });
  });
  await screen.findByText("Earlier save confirmed.");
  expect(applied).toHaveBeenCalledExactlyOnceWith({ ...completed, replayed: true });
  await waitFor(() => expect(pending).toHaveBeenLastCalledWith(false));
});

test("a confirmed import refreshes maintenance record counts without repeating the save", async () => {
  const updatedStatus = {
    database_status: "healthy",
    database_file: "cathedra.db",
    database_size_bytes: 2048,
    fsdp_records: 13,
    backup_count: 0,
    latest_backup_at: null,
    backups: [],
  };
  const router = createMemoryRouter([{ path: "/backup-export", element: <BackupExportPage /> }], {
    initialEntries: ["/backup-export"],
  });
  render(<RouterProvider router={router} />);
  const counts = await screen.findByRole("region", { name: "Record counts" });
  expect(within(counts).getByText("12")).toBeTruthy();
  await screen.findByText("Google account connected.");
  await fetchPreview();
  selectProfile();
  expect(maintenance.getMaintenanceStatus).toHaveBeenCalledTimes(1);
  maintenance.getMaintenanceStatus.mockResolvedValue(updatedStatus);
  await confirmApply();
  await screen.findByText("Selected changes applied.");
  await waitFor(() => expect(within(counts).getByText("13")).toBeTruthy());
  expect(maintenance.getMaintenanceStatus).toHaveBeenCalledTimes(2);
  expect(api.applyGoogleSheetPull).toHaveBeenCalledTimes(1);
  expect(connection.getGoogleSheetsStatus).toHaveBeenCalledTimes(1);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Pull from Google Sheet" }).matches(":disabled"),
    ).toBe(false),
  );
});

test("a pull preview blocks pushing and changing the connection until closed", async () => {
  const pending = vi.fn();
  render(
    <MemoryRouter>
      <GoogleSheetsPanel onPendingChange={pending} />
    </MemoryRouter>,
  );
  await screen.findByText("Google account connected.");
  await fetchPreview();
  for (const name of [
    "Update Google Sheet",
    "Reconnect Google",
    "Refresh Google connection",
    "Disconnect Google",
    "Save connection details",
  ]) {
    expect(
      screen
        .getByRole("button", { name, hidden: name === "Save connection details" })
        .matches(":disabled"),
    ).toBe(true);
  }
  expect(pending).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "Close preview" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Update Google Sheet" }).hasAttribute("disabled"),
    ).toBe(false),
  );
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
  expect(connection.syncGoogleSheets).not.toHaveBeenCalled();
});

test("expired previews cannot apply and a fresh preview resets old selections", async () => {
  const data = preview();
  data.expires_at = "2000-01-01T00:00:00Z";
  api.previewGoogleSheetPull.mockResolvedValueOnce(data).mockResolvedValueOnce(preview());
  showPull();
  await fetchPreview();
  expect(
    await screen.findByText("This preview has expired. Refresh it before applying changes."),
  ).toBeTruthy();
  expect(screen.getByRole("checkbox", { name: /EXISTING SCHOLAR/ }).hasAttribute("disabled")).toBe(
    true,
  );
  fireEvent.click(screen.getByRole("button", { name: "Refresh preview" }));
  await waitFor(() =>
    expect(
      screen.getByRole("checkbox", { name: /EXISTING SCHOLAR/ }).hasAttribute("disabled"),
    ).toBe(false),
  );
  expect(screen.getByText("0 of 1 scholars selected")).toBeTruthy();
  expect(api.applyGoogleSheetPull).not.toHaveBeenCalled();
});
