import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, test, vi } from "vitest";
import DashboardReports from "../src/components/DashboardReports";
import type { FsdpReport } from "../src/types";

const api = vi.hoisted(() => ({
  getFsdpReport: vi.fn(),
  getFsdpReportOptions: vi.fn(),
  downloadFsdpReport: vi.fn(),
}));
vi.mock("../src/api", () => api);
function Query() {
  return <output aria-label="Current query">{useLocation().search}</output>;
}

test("removing a filter chip preserves the other filters and report view", async () => {
  const report: FsdpReport = {
    total: 0,
    items: [],
    missing_requirements: 0,
    status_counts: { "On Going": 0, Graduated: 0, Payback: 0, Withdrawn: 0 },
    grant_type_counts: {
      "Full Scholarship": 0,
      "Partial Scholarship": 0,
      "Dissertation Aid": 0,
      Others: 0,
    },
  };
  api.getFsdpReport.mockResolvedValue(report);
  api.getFsdpReportOptions.mockResolvedValue({
    departments: ["CAS"],
    ranks: [],
    delivering_heis: [],
  });
  render(
    <MemoryRouter initialEntries={["/?department=CAS&missing_requirements=true&view=directory"]}>
      <DashboardReports />
      <Query />
    </MemoryRouter>,
  );
  await waitFor(() => expect(api.getFsdpReport).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button", { name: "Remove department filter" }));
  await waitFor(() =>
    expect(api.getFsdpReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ department: "", missing_requirements: true }),
    ),
  );
  const query = new URLSearchParams(screen.getByLabelText("Current query").textContent || "");
  expect(query.has("department")).toBe(false);
  expect(query.get("missing_requirements")).toBe("true");
  expect(query.get("view")).toBe("directory");
  fireEvent.click(screen.getByRole("button", { name: "Remove missing requirements filter" }));
  await waitFor(() =>
    expect(api.getFsdpReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ missing_requirements: false }),
    ),
  );
});
