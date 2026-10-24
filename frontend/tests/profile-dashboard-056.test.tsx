import { scholarStep, saveScholarForm } from "./scholarSteps";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import FsdpDashboardPage from "../src/pages/FsdpDashboardPage";
import FsdpDetailPage from "../src/pages/FsdpDetailPage";
import ProductGuidePage from "../src/pages/ProductGuidePage";
import { scholar, administrator } from "./fixtures";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
  getFsdpAnalytics: vi.fn(),
  getFsdpReport: vi.fn(),
  getFsdpReportOptions: vi.fn(),
  downloadFsdpReport: vi.fn(),
}));
const catalog = vi.hoisted(() => ({
  duplicateProgram: vi.fn(),
  getScholarNameMatches: vi.fn(),
  getScholarHistory: vi.fn(),
}));
vi.mock("../src/api/officeLog", () => ({
  getOfficeLogs: async () => ({ items: [], total: 0, page: 1, page_size: 50 }),
}));
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => catalog);
vi.mock("../src/api/programs", () => ({ getPrograms: async () => [] }));
vi.mock("../src/api/client", () => ({ getCurrentUser: () => administrator }));

const grant = {
  id: 1,
  program_id: 4,
  name: "Annual program",
  delivering_hei: "University",
  start_date: "2025-08-01",
  end_date: null,
  start_term: "1st",
  start_academic_year: "2025-2026",
  end_term: "3rd",
  end_academic_year: "2025-2026",
  grant_type: "Full Scholarship",
  grant_other: null,
  status: "On Going",
  extension: null,
  remarks: null,
};
function open(element: React.ReactElement, path = "/fsdp/1/edit") {
  const router = createMemoryRouter(
    [
      { path: "/fsdp/:id/edit", element },
      { path: "/fsdp/:id", element },
      { path: "/", element },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}
beforeEach(() => {
  vi.resetAllMocks();
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    tenure_years: 5.5,
    education: [
      {
        id: 1,
        level: "Bachelor’s",
        degree: "BS",
        institution: "University",
        graduation_year: "2010",
      },
    ],
    participations: [grant],
  });
  api.updateFsdpRecord.mockResolvedValue(scholar);
  catalog.getScholarNameMatches.mockResolvedValue([]);
  catalog.getScholarHistory.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    pages: 0,
  });
});

test("education rows and fractional years save with independent copied annual grants", async () => {
  open(<FsdpFormPage />);
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(2);
  await screen.findByRole("button", { name: "Edit education 1" });
  fireEvent.click(screen.getByRole("button", { name: "Add education" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Degree" }), {
    target: { value: "Master of Science" },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "Degree level" }), {
    target: { value: "Master’s" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save education" }));
  scholarStep(3);
  fireEvent.click(
    within(screen.getByRole("row", { name: /Annual program/ })).getByRole("button", {
      name: /^Copy for next year /,
    }),
  );
  expect(screen.queryByLabelText("Start date")).toBeNull();
  const term = screen.getByRole("combobox", { name: "Start Term" }) as HTMLSelectElement;
  expect(Array.from(term.options).map((option) => option.value)).toEqual([
    "",
    "1st",
    "2nd",
    "3rd",
    "Summer",
  ]);
  fireEvent.change(screen.getByLabelText("Start year / academic year"), {
    target: { value: "2026-2027" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));
  saveScholarForm();
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  const payload = api.updateFsdpRecord.mock.calls[0][1];
  expect(payload.education).toHaveLength(2);
  expect(payload.tenure_years).toBe(5.5);
  expect(payload.participations).toHaveLength(2);
  expect(payload.participations[0].start_academic_year).toBe("2025-2026");
  expect(payload.participations[1].start_academic_year).toBe("2026-2027");
  expect(payload.participations[1].id).toBeUndefined();
  expect(payload.participations[1].start_date).toBeNull();
});

test("new application retains the program without creating a catalog copy", async () => {
  open(<FsdpFormPage />);
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(3);
  fireEvent.click(await screen.findByRole("button", { name: "New application" }));
  expect((screen.getByLabelText("Program Applied *") as HTMLInputElement).value).toBe(
    "Annual program",
  );
  expect((screen.getByLabelText("Start year / academic year") as HTMLInputElement).value).toBe(
    "2026-2027",
  );
  fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));
  saveScholarForm();
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  const grants = api.updateFsdpRecord.mock.calls[0][1].participations;
  expect(grants).toHaveLength(2);
  expect(grants[1].source_program_id).toBe(4);
  expect(grants[1].application_key).toBeTruthy();
  expect(catalog.duplicateProgram).not.toHaveBeenCalled();
});

test("profile remarks are displayed separately and edits preserve grant remarks", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    profile_remarks: "Whole profile note\nSecond line",
    participations: [{ ...grant, remarks: "Annual grant note" }],
  });
  open(<FsdpDetailPage />, "/fsdp/1");
  await screen.findByRole("heading", { name: "Profile remarks" });
  expect(screen.getByText(/Whole profile note/)).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: /^Programs & grants/ }));
  expect(screen.getByText("Annual grant note")).toBeTruthy();
  expect(screen.getByText("Grant remarks")).toBeTruthy();
});

test("editor saves whole-profile remarks and restricts affiliations to eight colleges and Staff", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    profile_remarks: "Previous note",
    participations: [{ ...grant, remarks: "Annual grant note" }],
  });
  open(<FsdpFormPage />);
  const remarks = await screen.findByRole("textbox", { name: "Profile remarks" });
  expect((remarks as HTMLTextAreaElement).value).toBe("Previous note");
  fireEvent.change(remarks, { target: { value: "Updated whole profile note" } });
  const college = screen.getByRole("combobox", { name: "College / Staff" }) as HTMLSelectElement;
  expect(Array.from(college.options).map((option) => option.value)).toEqual([
    "CIT",
    "CAS",
    "COED",
    "COE",
    "CCJ",
    "COF",
    "CBMA",
    "CCS",
    "Staff",
    "Unknown",
  ]);
  fireEvent.change(college, { target: { value: "Staff" } });
  expect((screen.getByRole("textbox", { name: "Personnel type" }) as HTMLInputElement).value).toBe(
    "Staff",
  );
  saveScholarForm();
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  const payload = api.updateFsdpRecord.mock.calls[0][1];
  expect(payload.profile_remarks).toBe("UPDATED WHOLE PROFILE NOTE");
  expect(payload.department).toBe("Staff");
  expect(payload.participations[0].remarks).toBe("Annual grant note");
});

test("count explanations are searchable in the Office Guide", async () => {
  open(<ProductGuidePage />, "/");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Contract and payback counts" },
  });
  expect(screen.getByText(/grace period is three calendar years/)).toBeTruthy();
  expect(screen.getByText(/does not change a grant/)).toBeTruthy();
});

test("profile displays multiple qualifications and tenure in years", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    tenure_years: 5.5,
    education: [
      { id: 1, level: "Bachelor’s", degree: "BS", institution: "A", graduation_year: null },
      { id: 2, level: "Master’s", degree: "MS", institution: "B", graduation_year: null },
    ],
    participations: [],
  });
  open(<FsdpDetailPage />, "/fsdp/1");
  await screen.findByRole("heading", { name: scholar.name });
  expect(
    await screen.findByText(
      `${(5.5).toLocaleString(undefined, { maximumFractionDigits: 6 })} years`,
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: /^Education/ }));
  expect(screen.getByText("BS")).toBeTruthy();
  expect(screen.getByText("MS")).toBeTruthy();
});

test("dashboard includes recent scholars and reporting with shared scope", async () => {
  api.getFsdpAnalytics.mockResolvedValue({
    scholars: 1,
    grants: 1,
    ongoing_scholars: 1,
    requirements_follow_up: 0,
    statuses: [],
    departments: [],
    grant_types: [],
    options: { departments: ["CAS"], start_academic_years: ["2026-2027"] },
    recent_scholars: [scholar],
  });
  api.getFsdpReportOptions.mockResolvedValue({
    departments: ["CAS"],
    ranks: [],
    delivering_heis: [],
  });
  api.getFsdpReport.mockResolvedValue({
    total: 1,
    missing_requirements: 0,
    status_counts: { "On Going": 1, Graduated: 0, Payback: 0, Withdrawn: 0 },
    department_totals: [],
    action_items: [],
    items: [scholar],
  });
  const router = open(<FsdpDashboardPage />, "/");
  await screen.findByRole("heading", { name: "10 most recently added scholars" });
  expect(screen.queryByText("About these counts")).toBeNull();
  expect(screen.getByRole("heading", { name: "Scholars by college / Staff" })).toBeTruthy();
  fireEvent.click(screen.getByText("Dashboard reports and exports"));
  expect(await screen.findByRole("heading", { name: "Dashboard reports" })).toBeTruthy();
  expect(
    within(screen.getByRole("region", { name: "Recently added scholars" })).getByText(scholar.name),
  ).toBeTruthy();
  fireEvent.change(screen.getByRole("combobox", { name: "Dashboard department" }), {
    target: { value: "CAS" },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "Grant start academic year" }), {
    target: { value: "2026-2027" },
  });
  await waitFor(() =>
    expect(api.getFsdpReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ department: "CAS", start_academic_year: "2026-2027" }),
    ),
  );
  expect(router.state.location.pathname).toBe("/");
  fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
  await waitFor(() =>
    expect(api.downloadFsdpReport).toHaveBeenCalledWith(
      expect.objectContaining({ department: "CAS", start_academic_year: "2026-2027" }),
    ),
  );
});

test("contract date persists while annual copy starts with no completion or outcome", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    participations: [{ ...grant, status: "Payback", contract_completed_on: "2020-01-01" }],
  });
  open(<FsdpFormPage />);
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(3);
  const row = await screen.findByRole("row", { name: /Annual program/ });
  fireEvent.click(within(row).getByRole("button", { name: /^Copy for next year / }));
  expect(
    (
      (await screen.findByLabelText(
        "Previously recorded completion date (optional)",
      )) as HTMLInputElement
    ).value,
  ).toBe("");
  expect((screen.getByLabelText("Status") as HTMLSelectElement).value).toBe("On Going");
  fireEvent.change(screen.getByLabelText("Previously recorded completion date (optional)"), {
    target: { value: "2025-06-30" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));
  saveScholarForm();
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  const payload = api.updateFsdpRecord.mock.calls[0][1];
  expect(payload.participations[0].contract_completed_on).toBe("2020-01-01");
  expect(payload.participations[0].status).toBe("Payback");
  expect(payload.participations[1].contract_completed_on).toBe("2025-06-30");
  expect(payload.participations[1].status).toBe("On Going");
});
