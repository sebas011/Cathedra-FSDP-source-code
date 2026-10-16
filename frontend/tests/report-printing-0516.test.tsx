import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import {
  createMemoryRouter,
  Link,
  Outlet,
  RouterProvider,
  useSearchParams,
} from "react-router-dom";
import type { ReactNode } from "react";
import DashboardReports from "../src/components/DashboardReports";
import PaybackFollowUp from "../src/components/PaybackFollowUp";
import {
  PrintWorkspaceProvider,
  usePreparedPrint,
  usePrintWorkspace,
} from "../src/components/PrintWorkspace";
import FsdpDashboardPage from "../src/pages/FsdpDashboardPage";
import FsdpListPage from "../src/pages/FsdpListPage";
import { administrator, scholar } from "./fixtures";

const api = vi.hoisted(() => ({
  getFsdpReport: vi.fn(),
  getFsdpReportOptions: vi.fn(),
  downloadFsdpReport: vi.fn(),
  getFsdpAnalytics: vi.fn(),
  getFsdpRecords: vi.fn(),
  getFsdpSummary: vi.fn(),
  getCurrentUser: vi.fn(),
  deleteFsdpRecord: vi.fn(),
}));
const contracts = vi.hoisted(() => ({ getPayback: vi.fn(), downloadPayback: vi.fn() }));
vi.mock("../src/api", () => api);
vi.mock("../src/api/payback", () => contracts);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const scholars = Array.from({ length: 65 }, (_, index) => ({
  ...scholar,
  id: index + 1,
  name: `Report scholar ${index + 1}`,
}));
const actionItems = scholars.map((item) => ({
  scholar_id: item.id,
  scholar_name: item.name,
  department: "CAS",
  kind: "Contract",
  detail: "Annual program",
  attention: "Payback review",
}));
const contractRows = scholars.map((item) => ({
  scholar_id: item.id,
  scholar_name: item.name,
  department: "CAS",
  participation_id: item.id,
  program_name: "Annual program",
  academic_year: "2022-2023",
  recorded_status: "On Going",
  contract_completed_on: "2022-01-01",
  grace_ends_on: "2025-01-01",
  attention: "Payback review",
  days_remaining: null,
}));
const report = (items = scholars, actions = actionItems, total = 65) => ({
  total,
  items,
  action_items: actions,
  action_total: total,
  missing_requirements: 0,
  status_counts: { "On Going": total, Graduated: 0, Payback: 0 },
  grant_type_counts: {},
  department_totals: [],
});
const assessment = (items = contractRows, total = 65) => ({
  as_of: "2026-10-11",
  items,
  total,
  scholar_counts: { "Payback review": total },
  grant_counts: {},
});

function ScopeControls() {
  const [params, setParams] = useSearchParams();
  return (
    <>
      <button
        onClick={() => {
          const next = new URLSearchParams(params);
          next.set("department", "CCS");
          setParams(next);
        }}
      >
        Narrow shared scope
      </button>
      <button
        onClick={() => {
          const next = new URLSearchParams(params);
          next.set("view", "actions");
          setParams(next);
        }}
      >
        Change report view
      </button>
    </>
  );
}
function PrintControls() {
  const workspace = usePrintWorkspace()!;
  return (
    <>
      <button disabled={workspace.printing} onClick={() => void workspace.requestPrint()}>
        Prepare print
      </button>
      {workspace.error && <p role="alert">{workspace.error}</p>}
      <Link to="/elsewhere">Leave this page</Link>
    </>
  );
}
function PrintShell() {
  return (
    <PrintWorkspaceProvider>
      <PrintControls />
      <Outlet />
    </PrintWorkspaceProvider>
  );
}
function mount(element: ReactNode, path = "/") {
  const router = createMemoryRouter(
    [
      {
        element: <PrintShell />,
        children: [
          { path: "/", element },
          { path: "/elsewhere", element: <h1>Another page</h1> },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  const result = render(<RouterProvider router={router} />);
  return { router, ...result };
}
function DeferredPrint({ prepare }: { prepare: () => Promise<ReactNode> }) {
  const [params] = useSearchParams();
  usePreparedPrint(params.toString(), prepare);
  return (
    <>
      <ScopeControls />
      <h1>Current records</h1>
    </>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  api.getCurrentUser.mockReturnValue(administrator);
  api.getFsdpReportOptions.mockResolvedValue({
    departments: ["CAS", "CCS"],
    ranks: [],
    delivering_heis: [],
  });
  api.getFsdpReport.mockImplementation(async (filters) =>
    report(
      scholars.slice((Number(filters.page || 1) - 1) * 50, Number(filters.page || 1) * 50),
      actionItems.slice(
        (Number(filters.action_page || 1) - 1) * 50,
        Number(filters.action_page || 1) * 50,
      ),
    ),
  );
  contracts.getPayback.mockResolvedValue(assessment());
  api.getFsdpAnalytics.mockResolvedValue({
    scholars: 65,
    grants: 65,
    ongoing_scholars: 65,
    requirements_follow_up: 0,
    departments: [{ label: "CAS", count: 65 }],
    statuses: [{ label: "On Going", count: 65 }],
    grant_types: [],
    recent_scholars: [],
    options: { departments: ["CAS", "CCS"], start_academic_years: [] },
  });
  api.getFsdpSummary.mockResolvedValue({
    total: 65,
    ongoing: 65,
    graduated: 0,
    missing_requirements: 0,
  });
  api.getFsdpRecords.mockImplementation(async (_search, _status, page) => ({
    items: scholars.slice((page - 1) * 50, page * 50),
    total: 65,
    page,
    page_size: 50,
  }));
  vi.spyOn(window, "print").mockImplementation(() => {});
});

test.each(["filter", "view", "navigation", "unmount"])(
  "pending print is discarded after %s changes",
  async (kind) => {
    const pending = deferred<ReactNode>();
    const result = mount(<DeferredPrint prepare={() => pending.promise} />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare print" }));
    if (kind === "filter")
      fireEvent.click(screen.getByRole("button", { name: "Narrow shared scope" }));
    if (kind === "view")
      fireEvent.click(screen.getByRole("button", { name: "Change report view" }));
    if (kind === "navigation")
      fireEvent.click(screen.getByRole("link", { name: "Leave this page" }));
    if (kind === "unmount") result.unmount();
    await act(async () => {
      pending.resolve(<p>Old scope rows</p>);
      await pending.promise;
    });
    expect(window.print).not.toHaveBeenCalled();
    expect(document.querySelector("#prepared-print-document")).toBeNull();
    expect(document.body.classList.contains("prepared-print")).toBe(false);
    expect(screen.queryByText("Old scope rows")).toBeNull();
  },
);

test("printing mounts an isolated snapshot and always cleans up a print failure", async () => {
  mount(<DeferredPrint prepare={async () => <h1>Complete snapshot</h1>} />);
  vi.mocked(window.print).mockImplementation(() => {
    expect(document.body.classList.contains("prepared-print")).toBe(true);
    expect(document.querySelector("#prepared-print-document")?.textContent).toContain(
      "Complete snapshot",
    );
    throw new Error("Print unavailable");
  });
  fireEvent.click(screen.getByRole("button", { name: "Prepare print" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Print unavailable");
  expect(document.querySelector("#prepared-print-document")).toBeNull();
  expect(document.body.classList.contains("prepared-print")).toBe(false);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Prepare print" }).hasAttribute("disabled")).toBe(
      false,
    ),
  );
});

test.each(["directory", "actions"])(
  "shared scope resets %s from page two and retains the full action total",
  async (view) => {
    api.getFsdpReport.mockImplementation(async (filters) =>
      filters.department === "CCS"
        ? report(scholars.slice(0, 5), actionItems.slice(0, 5), 5)
        : report(
            scholars.slice((Number(filters.page) - 1) * 50, Number(filters.page) * 50),
            actionItems.slice(
              (Number(filters.action_page) - 1) * 50,
              Number(filters.action_page) * 50,
            ),
          ),
    );
    mount(
      <>
        <ScopeControls />
        <DashboardReports />
      </>,
      `/?view=${view}`,
    );
    const next = await screen.findByRole("button", {
      name: view === "directory" ? "Next results" : "Next actions",
    });
    fireEvent.click(next);
    await waitFor(() =>
      expect(api.getFsdpReport).toHaveBeenLastCalledWith(
        expect.objectContaining(view === "directory" ? { page: "2" } : { action_page: "2" }),
      ),
    );
    if (view === "actions") expect(await screen.findByText("65 items")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Narrow shared scope" }));
    await waitFor(() =>
      expect(api.getFsdpReport).toHaveBeenLastCalledWith(
        expect.objectContaining({ department: "CCS", page: "1", action_page: "1" }),
      ),
    );
    await waitFor(() =>
      expect(
        within(screen.getByRole("region", { name: "FSDP report results" })).getByText(
          "Report scholar 1",
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText("No records match the selected filters.")).toBeNull();
  },
);

test("overview action metric uses all 65 actions rather than the 50 loaded rows", async () => {
  mount(<DashboardReports />);
  const title = await screen.findByText("Needs action");
  expect(title.parentElement?.textContent).toBe("Needs action65");
});

test("report pages clamp after records disappear while preserving scope", async () => {
  let shrunk = false;
  api.getFsdpReport.mockImplementation(async (filters) =>
    shrunk
      ? report(Number(filters.page) === 1 ? scholars.slice(0, 5) : [], [], 5)
      : report(scholars.slice(0, 50)),
  );
  mount(<DashboardReports />, "/?view=directory");
  const next = await screen.findByRole("button", { name: "Next results" });
  shrunk = true;
  fireEvent.click(next);
  await screen.findByText("5 scholars");
  expect(api.getFsdpReport).toHaveBeenCalledWith(expect.objectContaining({ page: "2" }));
  expect(api.getFsdpReport).toHaveBeenLastCalledWith(expect.objectContaining({ page: "1" }));
  expect(screen.getByText("Page 1")).toBeTruthy();
  expect(screen.queryByText("No records match the selected filters.")).toBeNull();
});

test("shared scope resets contract assessment from page two", async () => {
  contracts.getPayback.mockImplementation(async (department, _year, _group, page) =>
    department === "CCS"
      ? assessment(contractRows.slice(0, 5), 5)
      : assessment(contractRows.slice((page - 1) * 50, page * 50)),
  );
  mount(
    <>
      <ScopeControls />
      <PaybackFollowUp />
    </>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Next assessment" }));
  await waitFor(() =>
    expect(contracts.getPayback).toHaveBeenLastCalledWith("", "", "Payback action", 2),
  );
  fireEvent.click(screen.getByRole("button", { name: "Narrow shared scope" }));
  await waitFor(() =>
    expect(contracts.getPayback).toHaveBeenLastCalledWith("CCS", "", "Payback action", 1),
  );
  expect(await screen.findByText("Report scholar 1")).toBeTruthy();
  expect(screen.getByText("Page 1")).toBeTruthy();
});

test("dashboard print includes full filtered reports, contracts and overview without replacing page two", async () => {
  api.getFsdpReport.mockImplementation(async (filters) =>
    filters.page
      ? report(scholars.slice((Number(filters.page) - 1) * 50, Number(filters.page) * 50))
      : report(),
  );
  mount(<FsdpDashboardPage />, "/?view=directory#dashboard-reports");
  fireEvent.click(await screen.findByRole("button", { name: "Next results" }));
  await waitFor(() =>
    expect(
      within(screen.getByRole("region", { name: "FSDP report results" })).getByText(
        "Report scholar 65",
      ),
    ).toBeTruthy(),
  );
  expect(
    within(screen.getByRole("region", { name: "FSDP report results" })).queryByText(
      "Report scholar 1",
    ),
  ).toBeNull();
  vi.mocked(window.print).mockImplementation(() => {
    const snapshot = document.querySelector<HTMLElement>("#prepared-print-document")!;
    expect(
      within(snapshot).getByRole("heading", { name: "Scholar development overview" }),
    ).toBeTruthy();
    expect(
      within(snapshot).getByRole("heading", { name: /Contract and payback assessment/ }),
    ).toBeTruthy();
    expect(within(snapshot).getAllByText("Report scholar 1")).toHaveLength(2);
    expect(within(snapshot).getAllByText("Report scholar 65")).toHaveLength(2);
  });
  fireEvent.click(screen.getByRole("button", { name: "Print dashboard" }));
  await waitFor(() => expect(window.print).toHaveBeenCalledTimes(1));
  expect(api.getFsdpReport).toHaveBeenLastCalledWith(
    expect.not.objectContaining({ page: expect.anything() }),
  );
  expect(contracts.getPayback).toHaveBeenLastCalledWith("", "", "Payback action");
  expect(
    within(screen.getByRole("region", { name: "FSDP report results" })).queryByText(
      "Report scholar 1",
    ),
  ).toBeNull();
  expect(screen.getByText("Page 2")).toBeTruthy();
  expect(document.querySelector("#prepared-print-document")).toBeNull();
});

test.each(["department", "chart order"])(
  "dashboard discards an old full snapshot after its %s changes",
  async (changed) => {
    const pending = deferred<ReturnType<typeof report>>();
    api.getFsdpReport.mockImplementation(async (filters) =>
      filters.page ? report(scholars.slice(0, 50)) : pending.promise,
    );
    mount(<FsdpDashboardPage />, "/?view=directory#dashboard-reports");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Print dashboard" }).hasAttribute("disabled")).toBe(
        false,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Print dashboard" }));
    await waitFor(() =>
      expect(api.getFsdpReport).toHaveBeenCalledWith(
        expect.not.objectContaining({ page: expect.anything() }),
      ),
    );
    if (changed === "department")
      fireEvent.change(screen.getByLabelText("Dashboard department"), { target: { value: "CCS" } });
    else fireEvent.change(screen.getByLabelText("Chart order"), { target: { value: "name" } });
    await act(async () => {
      pending.resolve(report());
      await pending.promise;
    });
    expect(window.print).not.toHaveBeenCalled();
    expect(document.querySelector("#prepared-print-document")).toBeNull();
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Print cancelled"),
    );
  },
);

test("directory print fetches every page without modifying the visible paged records", async () => {
  mount(<FsdpListPage />);
  await screen.findByText("Report scholar 1");
  expect(screen.queryByText("Report scholar 65")).toBeNull();
  vi.mocked(window.print).mockImplementation(() => {
    const snapshot = document.querySelector<HTMLElement>("#prepared-print-document")!;
    expect(within(snapshot).getByText("Report scholar 65")).toBeTruthy();
    expect(within(snapshot).getAllByRole("row")).toHaveLength(66);
  });
  fireEvent.click(screen.getByRole("button", { name: "Prepare print" }));
  await waitFor(() => expect(window.print).toHaveBeenCalledTimes(1));
  expect(api.getFsdpRecords).toHaveBeenLastCalledWith("", "", 2, "");
  expect(screen.queryByText("Report scholar 65")).toBeNull();
});

test("directory rejects an incomplete print when its contents change between pages", async () => {
  api.getFsdpRecords.mockImplementation(async (_search, _status, page) => ({
    items: page === 1 ? scholars.slice(0, 50) : scholars.slice(50, 64),
    total: page === 1 ? 65 : 64,
    page,
    page_size: 50,
  }));
  mount(<FsdpListPage />);
  await screen.findByText("Report scholar 1");
  fireEvent.click(screen.getByRole("button", { name: "Prepare print" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    expect.stringContaining("directory changed"),
  );
  expect(window.print).not.toHaveBeenCalled();
});
