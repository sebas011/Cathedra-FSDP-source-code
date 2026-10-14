import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useState } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import GrantEntry from "../src/components/GrantEntry";
import NumberInput from "../src/components/NumberInput";
import EducationSection from "../src/components/EducationSection";
import ProgramGrantHistory from "../src/components/ProgramGrantHistory";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import { copyAnnualGrant } from "../src/utils/annualGrant";
import { formatAcademicYear } from "../src/utils/dates";
import { completedCount, displayGrantStatus, grantStatuses } from "../src/utils/statuses";
import { uppercaseScholar } from "../src/utils/recordText";
import type { EducationInput, ParticipationInput, ScholarPayload } from "../src/types";
import { administrator, scholar } from "./fixtures";

const api = vi.hoisted(() => ({ getFsdpRecord: vi.fn(), updateFsdpRecord: vi.fn(), createFsdpRecord: vi.fn() }));
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => ({ getScholarNameMatches: async () => [], duplicateProgram: vi.fn() }));
vi.mock("../src/api/programs", () => ({ getPrograms: async () => [] }));
vi.mock("../src/api/client", () => ({ getCurrentUser: () => administrator }));
const grant: ParticipationInput = { id: 3, source_program_id: 7, program_name: "Master of Science", delivering_hei: "University",
  status: "Completed", case_status: "Closed", start_date: "2021-08-01", end_date: "2022-06-30", graduation_date: "2025-04-25", contract_completed_on: "2022-06-30",
  start_term: "Summer", end_term: "3rd", start_academic_year: "2021-2022", end_academic_year: "2022-2023", grant_type: "Full Scholarship", grant_other: "",
  remarks: "Documents retained", extension: "Previous extension" };
function GrantHarness() {
  const [draft, setDraft] = useState({ ...grant });
  return <><GrantEntry draft={draft} update={change => setDraft(value => ({ ...value, ...change }))} error="" editing save={() => {}} cancel={() => {}} />
    <output aria-label="Draft">{JSON.stringify(draft)}</output></>;
}
const current = () => JSON.parse(screen.getByLabelText("Draft").textContent!);
beforeEach(() => vi.resetAllMocks());

test("opening a new scholar clears previous education-restoration controls", async () => {
  api.getFsdpRecord.mockResolvedValue({ ...scholar, suppressed_education_program_ids: [7] });
  const router = createMemoryRouter([
    { path: "/fsdp/:id/edit", element: <FsdpFormPage /> },
    { path: "/fsdp/new", element: <FsdpFormPage /> },
  ], { initialEntries: ["/fsdp/1/edit"] });
  render(<RouterProvider router={router} />);
  await screen.findByRole("checkbox", { name: "Restore program #7 when saving" });
  await act(async () => { await router.navigate("/fsdp/new"); });
  await waitFor(() => expect((screen.getByRole("textbox", { name: "Name *" }) as HTMLInputElement).value).toBe(""));
  expect(screen.queryByRole("checkbox", { name: "Restore program #7 when saving" })).toBeNull();
});

test.each([
  ["20262027", false, "2026-2027"], ["2026 2027", false, "2026-2027"], ["2026–2027", false, "2026-2027"],
  ["2026", false, "2026"], ["2026", true, "2026-2027"], ["202", true, "202"], ["20272026", true, "20272026"],
  ["custom period", true, "custom period"], ["9999", true, "9999"], ["2026-2028", true, "2026-2028"],
])("academic-year entry formats recognized input %s without rejecting historical/custom values", (input, blur, expected) => {
  expect(formatAcademicYear(input, blur)).toBe(expected);
});

test("grant entry places date and remarks before independent outcome and case controls", async () => {
  render(<GrantHarness />);
  const remarks = screen.getByRole("textbox", { name: "Remarks" });
  const status = screen.getByRole("combobox", { name: "Status" });
  const caseStatus = screen.getByRole("combobox", { name: "Case status" });
  const graduation = screen.getByLabelText("Graduation date (optional)");
  expect(graduation.compareDocumentPosition(remarks) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(remarks.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.change(status, { target: { value: "Payback" } });
  expect(current()).toMatchObject({ status: "Payback", case_status: "Closed" });
  fireEvent.change(caseStatus, { target: { value: "Open" } });
  expect(current()).toMatchObject({ status: "Payback", case_status: "Open" });
  fireEvent.change(graduation, { target: { value: "2026-05-01" } });
  expect(current().graduation_date).toBe("2026-05-01");
  fireEvent.change(remarks, { target: { value: "submitted papers" } });
  expect(current().remarks).toBe("SUBMITTED PAPERS");
  expect(grantStatuses).toContain("Payback");
  expect(grantStatuses).toContain("Completed");
  expect(grantStatuses).not.toContain("Closed");
});

test("academic-year controls normalize eight digits and complete a single year on blur", () => {
  render(<GrantHarness />);
  const start = screen.getByRole("textbox", { name: "Start Academic Year" });
  fireEvent.change(start, { target: { value: "20262027" } });
  expect(current().start_academic_year).toBe("2026-2027");
  const end = screen.getByRole("textbox", { name: "Contract End Academic Year" });
  fireEvent.change(end, { target: { value: "2027" } });
  expect(current().end_academic_year).toBe("2027");
  fireEvent.blur(end);
  expect(current().end_academic_year).toBe("2027-2028");
});

test("next-year copy clears actual dates and case outcome while retaining original notes and identity", () => {
  const copied = copyAnnualGrant(grant);
  expect(copied).toMatchObject({ source_program_id: 7, program_name: "Master of Science", start_date: null, end_date: null,
    graduation_date: null, contract_completed_on: null, status: "On Going", case_status: "Open", remarks: "Documents retained",
    start_academic_year: "2022-2023", end_academic_year: "2023-2024" });
  expect(copied.id).toBeUndefined();
  expect(grant).toMatchObject({ id: 3, case_status: "Closed", graduation_date: "2025-04-25", remarks: "Documents retained" });
});

test("focused number input prevents the wheel default without losing focus or keyboard editing", () => {
  const onChange = vi.fn();
  render(<label>Tenure<NumberInput defaultValue={5.5} step="any" onChange={onChange} /></label>);
  const input = screen.getByRole("spinbutton", { name: "Tenure" }) as HTMLInputElement;
  const idle = new WheelEvent("wheel", { bubbles: true, cancelable: true });
  expect(input.dispatchEvent(idle)).toBe(true);
  input.focus();
  const wheel = new WheelEvent("wheel", { bubbles: true, cancelable: true, deltaY: 100 });
  expect(input.dispatchEvent(wheel)).toBe(false);
  expect(document.activeElement).toBe(input);
  const key = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "ArrowUp" });
  expect(input.dispatchEvent(key)).toBe(true);
  fireEvent.change(input, { target: { value: "6.5" } });
  expect(onChange).toHaveBeenCalled();
  expect(input.value).toBe("6.5");
});

test("legacy graduation outcomes display Completed and do not double-count compatibility keys", () => {
  expect(displayGrantStatus("Graduated")).toBe("Completed");
  expect(completedCount({ Completed: 3, Graduated: 3 })).toBe(3);
  expect(completedCount({ Graduated: 2 })).toBe(2);
});

test("uppercase education level has one equivalent option and an unrelated edit preserves its original value", async () => {
  function EducationHarness() {
    const [entries,setEntries]=useState<EducationInput[]>([{id:1,level:"MASTER’S",degree:"Historical degree",institution:"Historical university",graduation_year:null}]);
    return <><EducationSection entries={entries} onChange={setEntries} onDraftChange={()=>{}}/><output aria-label="Education values">{JSON.stringify(entries)}</output></>;
  }
  render(<EducationHarness/>);
  fireEvent.click(screen.getByRole("button",{name:"Edit education 1"}));
  const level=await screen.findByRole("combobox",{name:"Degree level"}) as HTMLSelectElement;
  expect(level.value).toBe("MASTER’S");
  expect(Array.from(level.options).filter(option=>option.value.toLowerCase() === "master’s")).toHaveLength(1);
  expect(Array.from(level.options).map(option=>option.value)).toEqual(["","Bachelor’s","MASTER’S","Ph.D.","Other"]);
  fireEvent.change(screen.getByLabelText("Graduation year"),{target:{value:"2026"}});
  fireEvent.click(screen.getByRole("button",{name:"Update education"}));
  expect(JSON.parse(screen.getByLabelText("Education values").textContent!)[0]).toMatchObject({id:1,level:"MASTER’S",degree:"Historical degree",institution:"Historical university",graduation_year:"2026"});
});

test("whole history collapse and nested states expand for print then restore exactly", () => {
  const { container } = render(<ProgramGrantHistory grants={[{ ...grant, id: 3, program_id: 7, name: grant.program_name,
    delivering_hei: "University", start_term: "Summer", start_academic_year: "2021-2022", end_term: "3rd", end_academic_year: "2022-2023", grant_other: null, extension: null }]} />);
  const details = [...container.querySelectorAll<HTMLDetailsElement>("details")];
  expect(details[0].open).toBe(false);
  const before = details.map(item => item.open);
  act(() => { window.dispatchEvent(new Event("beforeprint")); window.dispatchEvent(new Event("beforeprint")); });
  expect(details.every(item => item.open)).toBe(true);
  expect(screen.getByText("2025-04-25")).toBeTruthy();
  expect(screen.getByText("Closed")).toBeTruthy();
  act(() => { window.dispatchEvent(new Event("afterprint")); });
  expect(details.map(item => item.open)).toEqual(before);
});

test("scholar save uppercases edited text and preserves historical details with independent grant date/case", async () => {
  api.getFsdpRecord.mockResolvedValue({ ...scholar, profile_remarks: "profile note", education: [{ level: "Master’s", degree: "Master of Science", institution: "University", graduation_year: null }],
    participations: [{ ...grant, program_id: 7, name: grant.program_name }], requirements: [{ id: 1, requirement_name: "paper", remarks: "received", is_complete: false, due_date: null }] });
  api.updateFsdpRecord.mockResolvedValue(scholar);
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }, { path: "/fsdp/:id", element: <h1>Saved profile</h1> }], { initialEntries: ["/fsdp/1/edit"] });
  render(<RouterProvider router={router} />);
  const edit = await screen.findByRole("button", { name: "Edit grant Master of Science" });
  expect(within(edit.closest("tr")!).getByRole("button", { name: "Copy for next year Master of Science" })).toBeTruthy();
  expect(edit.textContent).toBe("");
  expect(edit.getAttribute("title")).toBe("Edit grant Master of Science");
  fireEvent.change(screen.getByRole("textbox", { name: "Profile remarks" }), { target: { value: "updated profile note" } });
  fireEvent.click(edit);
  fireEvent.change(screen.getByLabelText("Graduation date (optional)"), { target: { value: "2026-05-01" } });
  fireEvent.change(screen.getByLabelText("Case status"), { target: { value: "Open" } });
  fireEvent.click(screen.getByRole("button", { name: "Update Grant" }));
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  const payload = api.updateFsdpRecord.mock.calls[0][1] as ScholarPayload;
  expect(payload).toMatchObject({ name: "Demonstration Scholar", rank: "Instructor I", department: "CAS", profile_remarks: "UPDATED PROFILE NOTE" });
  expect(payload.participations[0]).toMatchObject({ source_program_id: 7, program_name: "Master of Science", graduation_date: "2026-05-01", status: "Completed", case_status: "Open", remarks: "Documents retained" });
  expect(payload.education?.[0]).toMatchObject({ level: "Master’s", degree: "Master of Science", institution: "University", graduation_year: null });
  expect(payload.requirements[0]).toMatchObject({ requirement_name: "paper", remarks: "received" });
  const capitalized=uppercaseScholar(payload);
  expect(capitalized).toMatchObject({name:"DEMONSTRATION SCHOLAR",rank:"INSTRUCTOR I"});
  expect(capitalized.participations[0]).toMatchObject({program_name:"MASTER OF SCIENCE",remarks:"DOCUMENTS RETAINED",grant_type:"Full Scholarship",status:"Completed",case_status:"Open"});
  expect(payload.participations[0].remarks).toBe("Documents retained");
});
