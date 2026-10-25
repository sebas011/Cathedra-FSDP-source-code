import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ScholarHistory from "../src/components/ScholarHistory";
import BackupReviewPanel from "../src/components/BackupReviewPanel";
import type { ActivityEvent, MaintenanceStatus } from "../src/types";

const history = vi.hoisted(() => ({ getScholarHistory: vi.fn() }));
const maintenance = vi.hoisted(() => ({ recordBackupReview: vi.fn() }));
vi.mock("../src/api/fsdp", () => history);
vi.mock("../src/api/maintenance", () => maintenance);
beforeEach(() => vi.resetAllMocks());

test("history loads only when expanded and supports recovery from errors", async () => {
  history.getScholarHistory
    .mockRejectedValueOnce(new Error("History unavailable"))
    .mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
  render(<ScholarHistory scholarId={3} />);
  expect(history.getScholarHistory).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Change history" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("No attributable changes recorded.");
  expect(history.getScholarHistory).toHaveBeenCalledWith(3, 1);
});

const event: ActivityEvent = {
  id: 1,
  username: "office-admin",
  action: "Updated FSDP #3",
  area: "FSDP",
  created_at: "2026-10-24 16:30:00",
  record_type: "scholars",
  record_id: 3,
  operation: "Updated",
  changed_fields: ["rank"],
};

test("legacy history keeps field names without inventing previous values", async () => {
  history.getScholarHistory.mockResolvedValue({
    items: [event],
    total: 1,
    page: 1,
    page_size: 20,
  });
  render(<ScholarHistory scholarId={3} />);
  fireEvent.click(screen.getByRole("button", { name: "Change history" }));
  await screen.findByText("rank");
  expect(screen.queryByText("View previous and new values")).toBeNull();
  expect(screen.queryByText("Not recorded")).toBeNull();
});

test("history comparisons preserve unknown, false, zero and empty text distinctly", async () => {
  history.getScholarHistory.mockResolvedValue({
    items: [
      {
        ...event,
        change_details: [
          { field: "has_hard_copy", before: null, after: false },
          { field: "tenure_years", before: 0, after: 4.5 },
          { field: "profile_remarks", before: "", after: "DOCUMENT RECEIVED" },
        ],
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  });
  const { container } = render(<ScholarHistory scholarId={3} />);
  fireEvent.click(screen.getByRole("button", { name: "Change history" }));
  const summary = await screen.findByText("View previous and new values");
  const disclosure = summary.closest("details")!;
  expect(disclosure.open).toBe(false);
  fireEvent.click(summary);
  expect(disclosure.open).toBe(true);
  expect(screen.getByText("Hard copy")).toBeTruthy();
  expect(screen.getByText("Not recorded")).toBeTruthy();
  expect(screen.getByText("No")).toBeTruthy();
  expect(screen.getByText("0")).toBeTruthy();
  expect(screen.getByText("4.5")).toBeTruthy();
  expect(screen.getByText("Empty text")).toBeTruthy();
  expect(screen.getAllByText("Previous")).toHaveLength(3);
  expect(screen.getAllByText("New")).toHaveLength(3);
  expect(container.querySelectorAll(".change-value-group")).toHaveLength(3);
});

test("history comparison previews escape markup and identify truncated values", async () => {
  history.getScholarHistory.mockResolvedValue({
    items: [
      {
        ...event,
        change_details: [
          {
            field: "profile_remarks",
            before: "<script>alert('old')</script>",
            after: '<img src=x onerror="alert(1)">',
            after_truncated: true,
          },
        ],
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  });
  const { container } = render(<ScholarHistory scholarId={3} />);
  fireEvent.click(screen.getByRole("button", { name: "Change history" }));
  fireEvent.click(await screen.findByText("View previous and new values"));
  expect(screen.getByText("<script>alert('old')</script>")).toBeTruthy();
  expect(screen.getByText('<img src=x onerror="alert(1)">')).toBeTruthy();
  expect(screen.getByText("Preview truncated")).toBeTruthy();
  expect(container.querySelector("script, img")).toBeNull();
});

test("history pagination retains the scholar and requests the selected page", async () => {
  history.getScholarHistory
    .mockResolvedValueOnce({ items: [event], total: 21, page: 1, page_size: 20 })
    .mockResolvedValueOnce({
      items: [{ ...event, id: 21, changed_fields: ["age"] }],
      total: 21,
      page: 2,
      page_size: 20,
    });
  render(<ScholarHistory scholarId={3} />);
  fireEvent.click(screen.getByRole("button", { name: "Change history" }));
  fireEvent.click(await screen.findByRole("button", { name: "Next" }));
  await screen.findByText("Page 2 of 2");
  expect(history.getScholarHistory).toHaveBeenLastCalledWith(3, 2);
  await screen.findByText("age");
  expect(screen.getByRole("button", { name: "Next" }).hasAttribute("disabled")).toBe(true);
});

const status: MaintenanceStatus = {
  database_status: "healthy",
  database_file: "cathedra.db",
  database_size_bytes: 1,
  fsdp_records: 0,
  backup_count: 1,
  latest_backup_at: null,
  backup_retention: null,
  backups: [
    {
      filename: "cathedra-backup-example.db",
      created_at: "2026-10-03T00:00:00Z",
      size_bytes: 1,
      protected: true,
    },
  ],
};

test("recovery review requires explicit copy confirmation and retains it on failure", async () => {
  maintenance.recordBackupReview
    .mockRejectedValueOnce(new Error("Review failed"))
    .mockResolvedValue({ recorded: true });
  const reload = vi.fn().mockResolvedValue(undefined);
  render(<BackupReviewPanel status={status} reload={reload} disabled={false} />);
  const save = screen.getByRole("button", { name: "Record recovery review" });
  expect(save.hasAttribute("disabled")).toBe(true);
  fireEvent.change(screen.getByLabelText("Backup reviewed"), {
    target: { value: status.backups[0].filename },
  });
  expect(save.hasAttribute("disabled")).toBe(true);
  const copy = screen.getByRole("checkbox", {
    name: "I copied this backup to private off-device storage.",
  });
  fireEvent.click(copy);
  fireEvent.click(save);
  await screen.findByText("Review failed");
  expect((copy as HTMLInputElement).checked).toBe(true);
  fireEvent.click(save);
  await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
  expect(maintenance.recordBackupReview).toHaveBeenLastCalledWith(
    status.backups[0].filename,
    false,
  );
  expect((copy as HTMLInputElement).checked).toBe(false);
});
