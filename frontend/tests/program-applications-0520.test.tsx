import { scholarStep, saveScholarForm } from "./scholarSteps";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useState } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import GrantEntry from "../src/components/GrantEntry";
import ProgramGrantHistory, { groupAnnualGrants } from "../src/components/ProgramGrantHistory";
import { copyAnnualGrant } from "../src/utils/annualGrant";
import { applicationPeriod, newProgramApplication } from "../src/utils/grantApplications";
import { DocumentCopyFields } from "../src/components/DocumentCopies";
import type { ParticipationInput } from "../src/types";
import { administrator, scholar } from "./fixtures";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
}));
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => ({ getScholarNameMatches: async () => [] }));
vi.mock("../src/api/client", () => ({ getCurrentUser: () => administrator }));
const grant: ParticipationInput = {
  id: 8,
  source_program_id: 4,
  application_key: "first",
  program_category: "Degree",
  program_name: "MASTER OF SCIENCE",
  delivering_hei: "UNIVERSITY",
  start_date: null,
  end_date: null,
  contract_completed_on: "2023-05-31",
  graduation_date: "2023-05-31",
  case_status: "Closed",
  start_term: "1st",
  start_academic_year: "2021-2022",
  end_term: "2nd",
  end_academic_year: "2022-2023",
  grant_type: "Full Scholarship",
  grant_other: "",
  status: "Completed",
  extension: "OLD EXTENSION",
  remarks: "OLD APPLICATION",
};
const readGrant = { ...grant, id: 8, program_id: 4, name: grant.program_name };
beforeEach(() => vi.clearAllMocks());

test("annual continuation retains application while a repeat starts after its previous end and clears old outcomes", () => {
  expect(copyAnnualGrant(grant).application_key).toBe("first");
  const repeat = newProgramApplication(grant);
  expect(repeat.application_key).not.toBe("first");
  expect(repeat).toMatchObject({
    source_program_id: 4,
    program_category: "Degree",
    start_term: "1st",
    start_academic_year: "2023-2024",
    end_term: "2nd",
    end_academic_year: "2024-2025",
    status: "On Going",
    case_status: "Open",
    graduation_date: null,
    contract_completed_on: null,
    remarks: "",
    extension: "",
  });
  expect(repeat.id).toBeUndefined();
  expect(grant.status).toBe("Completed");
});

test("same program retains distinct applications and legacy grouping without losing any annual record", () => {
  const groups = groupAnnualGrants([
    readGrant,
    { ...readGrant, id: 9, application_key: "second", start_academic_year: "2023-2024" },
    { ...readGrant, id: 10, application_key: "first", start_academic_year: "2022-2023" },
    { ...readGrant, id: 11, application_key: null },
    { ...readGrant, id: 12, application_key: null },
  ]);
  expect(groups).toHaveLength(3);
  expect(groups.map((group) => group.length).sort()).toEqual([1, 2, 2]);
  expect(applicationPeriod([readGrant])).toBe("1st 2021-2022 — 2nd 2022-2023");
});

test("latest application is readable immediately and all grant disclosures can expand, collapse and print", () => {
  const { container } = render(
    <ProgramGrantHistory
      grants={[
        readGrant,
        { ...readGrant, id: 9, application_key: "second", start_academic_year: "2023-2024" },
        { ...readGrant, id: 10, application_key: "second", start_academic_year: "2024-2025" },
      ]}
    />,
  );
  const applications = container.querySelectorAll<HTMLDetailsElement>(".program-history");
  const entries = [...container.querySelectorAll<HTMLDetailsElement>("details")];
  expect(applications).toHaveLength(2);
  expect(applications[0].open).toBe(true);
  expect(applications[1].open).toBe(false);
  expect(applications[0].querySelector<HTMLDetailsElement>(".annual-grant")?.open).toBe(true);
  expect(applications[0].textContent).toContain("2024-2025");
  fireEvent.click(screen.getByRole("button", { name: "Expand all grants" }));
  expect(entries.every((entry) => entry.open)).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Collapse all grants" }));
  expect(entries.every((entry) => !entry.open)).toBe(true);
  act(() => window.dispatchEvent(new Event("beforeprint")));
  expect(entries.every((entry) => entry.open)).toBe(true);
  act(() => window.dispatchEvent(new Event("afterprint")));
  expect(entries.every((entry) => !entry.open)).toBe(true);
});

test("renewing a multi-row application uses the whole application's span", () => {
  const first = { ...grant, end_academic_year: "2021-2022" };
  const last = {
    ...grant,
    id: 9,
    start_academic_year: "2022-2023",
    end_academic_year: "2022-2023",
  };
  expect(newProgramApplication(first, [first, last])).toMatchObject({
    start_academic_year: "2023-2024",
    end_academic_year: "2024-2025",
  });
});

test("choosing an application's annual stack retains its existing program identity", () => {
  const update = vi.fn();
  render(
    <GrantEntry
      draft={{ ...grant, source_program_id: undefined, application_key: "new" }}
      applications={[{ key: "first", programId: 4, label: "1st 2021-2022 — 2nd 2022-2023" }]}
      update={update}
      error=""
      editing={false}
      save={() => {}}
      cancel={() => {}}
    />,
  );
  fireEvent.change(screen.getByLabelText("Application"), { target: { value: "0" } });
  expect(update).toHaveBeenLastCalledWith({ application_key: "first", source_program_id: 4 });
});

test("grant editor omits existing-program selector and keeps program category separate from funding", () => {
  const update = vi.fn();
  render(
    <GrantEntry draft={grant} update={update} error="" editing save={() => {}} cancel={() => {}} />,
  );
  expect(screen.queryByLabelText("Existing program")).toBeNull();
  fireEvent.change(screen.getByLabelText("Program category"), {
    target: { value: "Certification" },
  });
  expect(update).toHaveBeenLastCalledWith({ program_category: "Certification" });
  fireEvent.change(screen.getByLabelText("Program category"), { target: { value: "Enhancement" } });
  expect(update).toHaveBeenLastCalledWith({ program_category: "Enhancement" });
  expect((screen.getByLabelText("Type of Grant") as HTMLSelectElement).value).toBe(
    "Full Scholarship",
  );
});

test("document copies distinguish unknown, available and unavailable independently", () => {
  function Harness() {
    const [flags, setFlags] = useState<{
      has_hard_copy?: boolean | null;
      has_soft_copy?: boolean | null;
    }>({ has_hard_copy: null, has_soft_copy: null });
    return (
      <>
        <DocumentCopyFields
          hard={flags.has_hard_copy}
          soft={flags.has_soft_copy}
          onChange={(change) => setFlags((current) => ({ ...current, ...change }))}
        />
        <output aria-label="flags">{JSON.stringify(flags)}</output>
      </>
    );
  }
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("Soft copy"), { target: { value: "true" } });
  fireEvent.change(screen.getByLabelText("Hard copy"), { target: { value: "false" } });
  expect(JSON.parse(screen.getByLabelText("flags").textContent!)).toEqual({
    has_hard_copy: false,
    has_soft_copy: true,
  });
  fireEvent.change(screen.getByLabelText("Hard copy"), { target: { value: "" } });
  expect(JSON.parse(screen.getByLabelText("flags").textContent!)).toEqual({
    has_hard_copy: null,
    has_soft_copy: true,
  });
});

test("editing a scholar preserves hidden program and application identity and saves both copy states", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    has_hard_copy: false,
    has_soft_copy: true,
    participations: [readGrant],
  });
  api.updateFsdpRecord.mockResolvedValue(scholar);
  const router = createMemoryRouter(
    [
      { path: "/fsdp/:id/edit", element: <FsdpFormPage /> },
      { path: "/fsdp/:id", element: <h1>Saved profile</h1> },
    ],
    { initialEntries: ["/fsdp/1/edit"] },
  );
  render(<RouterProvider router={router} />);
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(3);
  await screen.findByRole("button", { name: "Edit grant MASTER OF SCIENCE" });
  scholarStep(1);
  expect((screen.getByLabelText("Hard copy") as HTMLSelectElement).value).toBe("false");
  saveScholarForm();
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  expect(api.updateFsdpRecord.mock.calls[0][1]).toMatchObject({
    has_hard_copy: false,
    has_soft_copy: true,
    participations: [
      { id: 8, source_program_id: 4, application_key: "first", program_category: "Degree" },
    ],
  });
});
