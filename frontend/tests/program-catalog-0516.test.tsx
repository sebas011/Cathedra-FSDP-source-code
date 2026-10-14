import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useState } from "react";
import { createMemoryRouter, Link, RouterProvider } from "react-router-dom";
import GrantEntry from "../src/components/GrantEntry";
import ProgramCatalogPage from "../src/pages/ProgramCatalogPage";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import { saveSession } from "../src/api/client";
import type { ParticipationInput } from "../src/types";
import { administrator, scholar } from "./fixtures";

const programs = vi.hoisted(() => ({ getPrograms: vi.fn(), createProgram: vi.fn(), updateProgram: vi.fn(), deleteProgram: vi.fn(), duplicateCatalogProgram: vi.fn() }));
const api = vi.hoisted(() => ({ getFsdpRecord: vi.fn(), updateFsdpRecord: vi.fn(), createFsdpRecord: vi.fn() }));
const grants = vi.hoisted(() => ({ getScholarNameMatches: vi.fn(), duplicateProgram: vi.fn() }));
vi.mock("../src/api/programs", () => programs);
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => grants);
const program = { id: 7, revision: 3, name: "Master of Éducation", delivering_hei: "Default university", description: "", identity_conflict: false };
const draft: ParticipationInput = { source_program_id: 7, program_name: program.name, delivering_hei: "Recorded university", status: "On Going", grant_type: null, grant_other: "", start_date: null, end_date: null, contract_completed_on: null, start_term: "Summer", start_academic_year: "2026-2027", end_term: "", end_academic_year: "", remarks: "", extension: "" };
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(yes => { resolve = yes; });
  return { promise, resolve };
}
function Catalog() { return <><Link to="/away">Leave catalog</Link><ProgramCatalogPage /></>; }
function mountCatalog() {
  const router = createMemoryRouter([{ path: "/", element: <Catalog /> }, { path: "/away", element: <h1>Another page</h1> }]);
  render(<RouterProvider router={router} />);
  return router;
}
function GrantHarness() {
  const [value, setValue] = useState(draft);
  return <><GrantEntry draft={value} update={change => setValue(current => ({ ...current, ...change }))} error="" editing={false} save={() => {}} cancel={() => {}} /><output aria-label="Grant draft">{JSON.stringify(value)}</output></>;
}
beforeEach(() => {
  vi.resetAllMocks();
  saveSession({ token: "synthetic-catalog-test", user: administrator });
  programs.getPrograms.mockResolvedValue([program]);
  grants.getScholarNameMatches.mockResolvedValue([]);
});

test("selecting an existing program preserves its exact identity and recorded HEI, while typing clears the identity", async () => {
  programs.getPrograms.mockResolvedValue([program, { ...program, id: 8, name: "Master of éducation", identity_conflict: true }]);
  render(<GrantHarness />);
  await screen.findByRole("option", { name: "Master of éducation (#8) — identity review" });
  fireEvent.change(screen.getByLabelText("Existing program"), { target: { value: "8" } });
  const selected = JSON.parse(screen.getByLabelText("Grant draft").textContent!);
  expect(selected.source_program_id).toBe(8);
  expect(selected.program_name).toBe("Master of éducation");
  expect(selected.delivering_hei).toBe("Recorded university");
  expect(selected.start_term).toBe("Summer");
  fireEvent.change(screen.getByRole("textbox", { name: "Program Applied *" }), { target: { value: "A different program" } });
  const typed = JSON.parse(screen.getByLabelText("Grant draft").textContent!);
  expect(typed.source_program_id).toBeUndefined();
  expect(typed.program_name).toBe("A DIFFERENT PROGRAM");
});

test("catalog saves an existing program with its revision and keeps the catalog on a conflict", async () => {
  programs.updateProgram.mockRejectedValue(new Error("A program with that name already exists. Select its existing catalog entry."));
  mountCatalog();
  const row = (await screen.findByText("Program #7")).closest("tr")!;
  fireEvent.click(within(row).getByRole("button", { name: "Edit" }));
  await screen.findByRole("heading", { name: "Edit program #7" });
  fireEvent.change(screen.getByRole("textbox", { name: "Program name *" }), { target: { value: "Another program" } });
  fireEvent.click(screen.getByRole("button", { name: "Save program" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("already exists"));
  expect(programs.updateProgram).toHaveBeenCalledWith(7, expect.objectContaining({ name: "ANOTHER PROGRAM" }), 3);
  expect(screen.getByText("Program #7")).toBeTruthy();
  expect((screen.getByRole("textbox", { name: "Program name *" }) as HTMLInputElement).value).toBe("ANOTHER PROGRAM");
});

test("a new catalog program needs only its name and retains the returned identity", async () => {
  programs.createProgram.mockResolvedValue({ ...program, id: 9, name: "Annual program" });
  mountCatalog();
  await screen.findByText("Program #7");
  fireEvent.change(screen.getByRole("textbox", { name: "Program name *" }), { target: { value: "Annual program" } });
  fireEvent.click(screen.getByRole("button", { name: "Add program" }));
  await screen.findByText("Program #9");
  expect(programs.createProgram).toHaveBeenCalledWith({ name: "ANNUAL PROGRAM", delivering_hei: "", description: "" });
});

test("in-flight catalog duplication blocks leaving and preserves the new program identity", async () => {
  const pending = deferred<typeof program>();
  programs.duplicateCatalogProgram.mockReturnValue(pending.promise);
  const router = mountCatalog();
  const row = (await screen.findByText("Program #7")).closest("tr")!;
  fireEvent.click(within(row).getByRole("button", { name: "Duplicate" }));
  fireEvent.click(screen.getByRole("link", { name: "Leave catalog" }));
  await screen.findByRole("heading", { name: "Updating the program catalog" });
  expect(screen.getByRole("button", { name: "Leave without saving" }).hasAttribute("disabled")).toBe(true);
  expect(router.state.location.pathname).toBe("/");
  fireEvent.click(screen.getByRole("button", { name: "Stay here" }));
  await act(async () => { pending.resolve({ ...program, id: 10, name: `${program.name} (Copy)` }); await pending.promise; });
  expect(screen.getByText("Program #10")).toBeTruthy();
  expect(programs.duplicateCatalogProgram).toHaveBeenCalledWith(7);
});

test("deleting a catalog program requires confirmation and retains protected history after failure", async () => {
  programs.deleteProgram.mockRejectedValue(new Error("This program has scholar history and cannot be deleted."));
  mountCatalog();
  const row = (await screen.findByText("Program #7")).closest("tr")!;
  fireEvent.click(within(row).getByRole("button", { name: "Delete" }));
  await screen.findByRole("heading", { name: "Delete program?" });
  expect(programs.deleteProgram).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Delete program" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("scholar history"));
  expect(screen.getByText("Program #7")).toBeTruthy();
});

test("staff cannot open catalog management or request catalog records", () => {
  saveSession({ token: "synthetic-staff-test", user: { ...administrator, id: 2, role: "staff" } });
  mountCatalog();
  expect(screen.getByRole("status").textContent).toContain("available to administrators");
  expect(programs.getPrograms).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Add program" })).toBeNull();
});

test("in-flight program copy blocks scholar navigation until completion", async () => {
  const pending = deferred<typeof program>();
  grants.duplicateProgram.mockReturnValue(pending.promise);
  api.getFsdpRecord.mockResolvedValue({ ...scholar, participations: [{ ...draft, id: 1, program_id: 7, name: program.name }] });
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }, { path: "/fsdp/:id", element: <h1>Scholar profile</h1> }], { initialEntries: ["/fsdp/1/edit"] });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("button", { name: /^Edit grant / }));
  fireEvent.click(screen.getByRole("button", { name: "Duplicate program" }));
  fireEvent.click(screen.getByRole("link", { name: "Back" }));
  await screen.findByRole("heading", { name: "Copying the program" });
  expect(screen.getByRole("button", { name: "Leave without saving" }).hasAttribute("disabled")).toBe(true);
  expect(router.state.location.pathname).toBe("/fsdp/1/edit");
  const leave = new Event("cathedra-can-leave", { cancelable: true });
  expect(window.dispatchEvent(leave)).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Stay here" }));
  await act(async () => { pending.resolve({ ...program, id: 11, name: `${program.name} (Copy)` }); await pending.promise; });
  await waitFor(() => expect((screen.getByRole("textbox", { name: "Program Applied *" }) as HTMLInputElement).value).toBe(`${program.name} (Copy)`));
  expect((screen.getByLabelText("Existing program") as HTMLSelectElement).value).toBe("11");
  expect(api.updateFsdpRecord).not.toHaveBeenCalled();
});
