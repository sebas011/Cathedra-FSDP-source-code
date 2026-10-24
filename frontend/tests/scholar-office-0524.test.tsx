import { beforeEach, expect, test, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import FsdpDetailPage from "../src/pages/FsdpDetailPage";
import FsdpListPage from "../src/pages/FsdpListPage";
import { administrator, scholar } from "./fixtures";
import { scholarStep } from "./scholarSteps";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
  getFsdpRecords: vi.fn(),
  getFsdpSummary: vi.fn(),
  deleteFsdpRecord: vi.fn(),
  getCurrentUser: vi.fn(),
}));
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => ({ getScholarNameMatches: async () => [] }));
vi.mock("../src/api/client", async (original) => ({
  ...(await original<typeof import("../src/api/client")>()),
  getCurrentUser: () => ({ ...administrator, role: "staff" }),
}));
vi.mock("../src/api/officeLog", () => ({
  getOfficeLogs: async () => ({ items: [], total: 0, page: 1, page_size: 50 }),
}));

function open(element: React.ReactElement, path = "/fsdp/new") {
  const router = createMemoryRouter(
    [
      { path: "/fsdp/new", element },
      { path: "/fsdp/:id/edit", element },
      { path: "/fsdp/:id", element },
      { path: "/fsdp", element },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}
beforeEach(() => {
  vi.resetAllMocks();
  api.getFsdpRecord.mockResolvedValue(scholar);
  api.createFsdpRecord.mockResolvedValue(scholar);
  api.updateFsdpRecord.mockResolvedValue(scholar);
  api.getFsdpRecords.mockResolvedValue({ items: [scholar], total: 1, page: 1, page_size: 50 });
  api.getFsdpSummary.mockResolvedValue({
    total: 1,
    ongoing: 0,
    graduated: 0,
    missing_requirements: 0,
  });
  api.getCurrentUser.mockReturnValue({ ...administrator, role: "staff" });
});

test("four-step entry makes one atomic name-only save after review", async () => {
  open(<FsdpFormPage />);
  expect(screen.getByRole("heading", { name: "Scholar Information" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Save Scholar" })).toBeNull();
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), {
    target: { value: "New scholar" },
  });
  for (let step = 2; step <= 4; step++) {
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    fireEvent(screen.getByRole("button", { name: "Continue" }), click);
    // A browser must not run a form activation after Continue becomes the Save control.
    expect(click.defaultPrevented).toBe(true);
    expect(
      screen
        .getByRole("button", { name: new RegExp(`^Step ${step}:`) })
        .getAttribute("aria-current"),
    ).toBe("step");
    expect(api.createFsdpRecord).not.toHaveBeenCalled();
  }
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.createFsdpRecord).toHaveBeenCalledTimes(1));
  expect(api.createFsdpRecord.mock.calls[0][0]).toMatchObject({
    name: "NEW SCHOLAR",
    education: [],
    participations: [],
    requirements: [],
  });
});

test("open education stays mounted and blocks changing steps until staged", () => {
  open(<FsdpFormPage />);
  scholarStep(2);
  fireEvent.click(screen.getByRole("button", { name: "Add education" }));
  const degree = screen.getByRole("textbox", { name: "Degree" });
  fireEvent.change(degree, { target: { value: "Bachelor of Science" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByRole("alert").textContent).toContain("Save or cancel the open education");
  expect(screen.getByRole("textbox", { name: "Degree" })).toBe(degree);
  expect((degree as HTMLInputElement).value).toBe("BACHELOR OF SCIENCE");
  fireEvent.click(screen.getByRole("button", { name: "Save education" }));
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByRole("heading", { name: "FSDP Grants" })).toBeTruthy();
  scholarStep(2);
  expect(
    within(screen.getByRole("region", { name: "Scholar education" })).getByText(
      "BACHELOR OF SCIENCE",
    ),
  ).toBeTruthy();
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});

test("Enter from identity opens review instead of committing without review", () => {
  const { container } = render(
    <RouterProvider router={createMemoryRouter([{ path: "*", element: <FsdpFormPage /> }])} />,
  );
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), {
    target: { value: "Review first" },
  });
  fireEvent.submit(container.querySelector("form")!);
  expect(screen.getByRole("heading", { name: "Review scholar record" })).toBeTruthy();
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});

test.each([
  {
    step: 2,
    add: "Add education",
    field: "Degree",
    save: "Save education",
    heading: "Education background",
  },
  {
    step: 3,
    add: "Add Grant",
    field: "Program Applied *",
    save: "Save Grant",
    heading: "FSDP Grants",
  },
])(
  "Enter inside an open step $step entry keeps the editor reachable before name is entered",
  ({ step, add, field, save, heading }) => {
    open(<FsdpFormPage />);
    scholarStep(step);
    fireEvent.click(screen.getByRole("button", { name: add }));
    const input = screen.getByRole("textbox", { name: field });
    fireEvent.change(input, { target: { value: "Retained nested draft" } });
    fireEvent.submit(input.closest("form")!);
    expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    expect(screen.getByRole("textbox", { name: field })).toBe(input);
    expect((input as HTMLInputElement).value).toBe("RETAINED NESTED DRAFT");
    expect(screen.getByRole("alert").textContent).toContain("Save or cancel the open");
    fireEvent.click(screen.getByRole("button", { name: save }));
    scholarStep(1);
    expect(screen.getByRole("textbox", { name: "Name *" })).toBeTruthy();
    expect(api.createFsdpRecord).not.toHaveBeenCalled();
  },
);

test("review sends missing name back to the visible identity step", () => {
  open(<FsdpFormPage />);
  scholarStep(4);
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  expect(screen.getByRole("textbox", { name: "Name *" })).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain("enter the scholar’s name");
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});

test("profile tabs support arrows and retain independent copy availability", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    has_hard_copy: false,
    has_soft_copy: null,
    education: [
      {
        id: 1,
        degree: "BACHELOR OF SCIENCE",
        level: "Bachelor’s",
        institution: "UNIVERSITY",
        graduation_year: "2010",
      },
    ],
  });
  open(<FsdpDetailPage />, "/fsdp/1");
  const overview = await screen.findByRole("tab", { name: "Overview" });
  overview.focus();
  fireEvent.keyDown(overview, { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByRole("tab", { name: /^Education/ }));
  expect(screen.getByRole("heading", { name: "Education background" })).toBeTruthy();
  expect(screen.getByText("BACHELOR OF SCIENCE")).toBeTruthy();
  fireEvent.keyDown(document.activeElement!, { key: "End" });
  expect(
    screen.getByRole("tab", { name: /^Programs & grants/ }).getAttribute("aria-selected"),
  ).toBe("true");
  expect(document.getElementById("profile-panel-education")?.hidden).toBe(true);
  expect(screen.getByText("Not available")).toBeTruthy();
  expect(screen.getAllByText("Not recorded").length).toBeGreaterThan(0);
});

test("directory search receives focus on utility navigation without clearing filters", async () => {
  const router = open(<FsdpListPage />, "/fsdp#directory-search");
  const search = screen.getByRole("textbox", { name: "Search scholars" });
  await waitFor(() => expect(document.activeElement).toBe(search));
  fireEvent.change(search, { target: { value: "Demo" } });
  await act(async () => {
    await router.navigate("/fsdp#directory-search");
  });
  expect((search as HTMLInputElement).value).toBe("Demo");
  expect(screen.getByText(/Hard: Not recorded/)).toBeTruthy();
});

test("filter refresh keeps keyboard focus after a utility search visit", async () => {
  open(<FsdpListPage />, "/fsdp#directory-search");
  await screen.findByText(scholar.name);
  const filter = screen.getByRole("combobox", { name: "Filter scholars by status" });
  filter.focus();
  fireEvent.change(filter, { target: { value: "Completed" } });
  await waitFor(() => expect(api.getFsdpRecords).toHaveBeenLastCalledWith("", "Completed", 1, ""));
  await screen.findByText(scholar.name);
  expect(document.activeElement).toBe(filter);
});

test("profile printing expands qualifications from a hidden tab and restores each disclosure", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    education: [
      {
        id: 1,
        degree: "FIRST DEGREE",
        level: "Bachelor’s",
        institution: "FIRST UNIVERSITY",
        graduation_year: "2010",
      },
      {
        id: 2,
        degree: "SECOND DEGREE",
        level: "Master’s",
        institution: "SECOND UNIVERSITY",
        graduation_year: "2015",
      },
    ],
  });
  const { container } = render(
    <RouterProvider
      router={createMemoryRouter([{ path: "/fsdp/:id", element: <FsdpDetailPage /> }], {
        initialEntries: ["/fsdp/1"],
      })}
    />,
  );
  await screen.findByRole("heading", { name: scholar.name });
  const qualifications = [
    ...container.querySelectorAll<HTMLDetailsElement>(".office-education-list details"),
  ];
  expect(qualifications).toHaveLength(2);
  qualifications[0].open = true;
  const original = qualifications.map((entry) => entry.open);
  expect(container.querySelector<HTMLDivElement>("#profile-panel-education")?.hidden).toBe(true);
  act(() => {
    window.dispatchEvent(new Event("beforeprint"));
    window.dispatchEvent(new Event("beforeprint"));
  });
  expect(qualifications.every((entry) => entry.open)).toBe(true);
  expect(qualifications[1].textContent).toContain("SECOND UNIVERSITY");
  expect(qualifications[1].textContent).toContain("2015");
  act(() => {
    window.dispatchEvent(new Event("afterprint"));
  });
  expect(qualifications.map((entry) => entry.open)).toEqual(original);
});
