import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, createMemoryRouter, RouterProvider } from "react-router-dom";
import PaybackFollowUp from "../src/components/PaybackFollowUp";
import DashboardReports from "../src/components/DashboardReports";

const followUp = vi.hoisted(() => ({ getPayback: vi.fn(), downloadPayback: vi.fn() }));
const reports = vi.hoisted(() => ({
  getFsdpReport: vi.fn(),
  getFsdpReportOptions: vi.fn(),
  downloadFsdpReport: vi.fn(),
}));
vi.mock("../src/api/payback", () => followUp);
vi.mock("../src/api", () => reports);
const rows = [
  "Recorded Payback",
  "Payback review",
  "In grace period",
  "Completion date missing",
].map((attention, index) => ({
  scholar_id: index + 1,
  participation_id: index + 1,
  scholar_name: `Scholar ${index + 1}`,
  department: "CAS",
  program_name: "Annual program",
  academic_year: "2025-2026",
  recorded_status: index === 0 ? "Payback" : "On Going",
  contract_completed_on: index === 3 ? null : "2020-01-01",
  grace_ends_on: index === 3 ? null : "2023-01-01",
  attention,
  days_remaining: index === 2 ? 300 : null,
}));
beforeEach(() => {
  vi.resetAllMocks();
  followUp.getPayback.mockResolvedValue({
    as_of: "2026-10-07",
    items: rows,
    scholar_counts: Object.fromEntries(rows.map((row) => [row.attention, 1])),
    grant_counts: {},
  });
  followUp.downloadPayback.mockResolvedValue(undefined);
  reports.getFsdpReportOptions.mockResolvedValue({
    departments: [],
    ranks: [],
    delivering_heis: [],
    grant_types: ["Thesis Grant"],
    statuses: ["Deferred"],
  });
  reports.getFsdpReport.mockResolvedValue({
    items: [],
    total: 0,
    missing_requirements: 0,
    status_counts: {},
    grant_type_counts: {},
  });
});

test("default payback actions, missing-date list and scoped CSV use selected category", async () => {
  render(
    <MemoryRouter initialEntries={["/?department=CAS&start_academic_year=2025-2026"]}>
      <PaybackFollowUp />
    </MemoryRouter>,
  );
  const table = await screen.findByRole("region", { name: "Contract assessment records" });
  expect(within(table).getByText("Scholar 1")).toBeTruthy();
  expect(within(table).getByText("Scholar 2")).toBeTruthy();
  expect(within(table).queryByText("Scholar 4")).toBeNull();
  expect(followUp.getPayback).toHaveBeenCalledWith("CAS", "2025-2026", "Payback action", 1);
  fireEvent.click(screen.getByRole("button", { name: "Completion date missing: 1 scholars" }));
  const missingTable = await screen.findByRole("region", { name: "Contract assessment records" });
  expect(within(missingTable).getByText("Scholar 4")).toBeTruthy();
  expect(within(missingTable).getByText("Not calculated")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Export follow-up CSV" }));
  await waitFor(() =>
    expect(followUp.downloadPayback).toHaveBeenCalledWith(
      "CAS",
      "2025-2026",
      "Completion date missing",
    ),
  );
});

test("failed contract request retries without showing false zero counts", async () => {
  followUp.getPayback.mockRejectedValueOnce(new Error("Service unavailable"));
  render(
    <MemoryRouter>
      <PaybackFollowUp />
    </MemoryRouter>,
  );
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByRole("region", { name: "Contract assessment records" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry contract assessment" }));
  await screen.findByRole("region", { name: "Contract assessment records" });
  expect(followUp.getPayback).toHaveBeenCalledTimes(2);
});

test("recorded custom report choices remain selectable and affect report scope", async () => {
  const router = createMemoryRouter([{ path: "/", element: <DashboardReports /> }], {
    initialEntries: ["/"],
  });
  render(<RouterProvider router={router} />);
  await screen.findByRole("option", { name: "Thesis Grant" });
  fireEvent.change(screen.getByLabelText("Grant type"), { target: { value: "Thesis Grant" } });
  fireEvent.change(screen.getByLabelText("Scholar status"), { target: { value: "Deferred" } });
  await waitFor(() =>
    expect(reports.getFsdpReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ grant_type: "Thesis Grant", status: "Deferred" }),
    ),
  );
});
