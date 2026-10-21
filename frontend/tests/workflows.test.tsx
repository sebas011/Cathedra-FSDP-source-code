import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import type { ReactElement } from "react";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import { scholar, administrator } from "./fixtures";
import { saveSession } from "../src/api/client";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
}));
vi.mock("../src/api", () => api);
const names = vi.hoisted(() => ({ getScholarNameMatches: vi.fn() }));
vi.mock("../src/api/fsdp", () => names);

function openPage(element: ReactElement, path = "/") {
  const router = createMemoryRouter([{ path: "*", element }], { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => {
  vi.resetAllMocks();
  saveSession({ token: "synthetic-test", user: administrator });
  names.getScholarNameMatches.mockResolvedValue([]);
});

test("edited scholars return to their own profile after successful save", async () => {
  api.getFsdpRecord.mockResolvedValue(scholar);
  api.updateFsdpRecord.mockResolvedValue(scholar);
  const router = createMemoryRouter(
    [
      { path: "/fsdp/:id/edit", element: <FsdpFormPage /> },
      { path: "/fsdp/:id", element: <h1>Saved scholar profile</h1> },
    ],
    { initialEntries: ["/fsdp/1/edit"] },
  );
  render(<RouterProvider router={router} />);
  const name = await screen.findByRole("textbox", { name: "Name *" });
  fireEvent.change(name, { target: { value: "Updated Demonstration Scholar" } });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await screen.findByRole("heading", { name: "Saved scholar profile" });
  expect(router.state.location.pathname).toBe("/fsdp/1");
  expect(api.updateFsdpRecord).toHaveBeenCalledWith(
    1,
    expect.objectContaining({ name: "UPDATED DEMONSTRATION SCHOLAR" }),
    1,
  );
});

test("failed scholar load cannot submit a blank edit", async () => {
  api.getFsdpRecord.mockRejectedValue(new Error("Scholar unavailable"));
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/1/edit"],
  });
  render(<RouterProvider router={router} />);
  await screen.findByRole("button", { name: "Retry" });
  expect(screen.queryByRole("button", { name: "Save Scholar" })).toBeNull();
  expect(api.updateFsdpRecord).not.toHaveBeenCalled();
});

test("grant cancellation preserves input until discard is confirmed", async () => {
  openPage(<FsdpFormPage />, "/fsdp/new");
  fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));
  const program = screen.getByRole("textbox", { name: "Program Applied *" });
  fireEvent.change(program, { target: { value: "Demonstration program" } });
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  fireEvent.click(await screen.findByRole("button", { name: "Keep editing" }));
  expect((program as HTMLInputElement).value).toBe("DEMONSTRATION PROGRAM");
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  fireEvent.click(await screen.findByRole("button", { name: "Discard changes" }));
  await screen.findByRole("button", { name: "Add Grant" });
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});

test("invalid scholar address never fetches or exposes an editable form", async () => {
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/invalid/edit"],
  });
  render(<RouterProvider router={router} />);
  await screen.findByRole("alert");
  expect(api.getFsdpRecord).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Save Scholar" })).toBeNull();
});

test("requirement removal is confirmed and preserves the remaining entry", async () => {
  openPage(<FsdpFormPage />, "/fsdp/new");
  fireEvent.click(screen.getByRole("button", { name: "Add Requirement" }));
  fireEvent.click(screen.getByRole("button", { name: "Add Requirement" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Requirement 2 name" }), {
    target: { value: "Keep this item" },
  });
  fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);
  expect(screen.getByRole("textbox", { name: "Requirement 1 name" })).toBeTruthy();
  fireEvent.click(await screen.findByRole("button", { name: "Discard changes" }));
  await waitFor(() =>
    expect(
      (screen.getByRole("textbox", { name: "Requirement 1 name" }) as HTMLInputElement).value,
    ).toBe("KEEP THIS ITEM"),
  );
});

test("saving an unchanged record still protects pending work from navigation", async () => {
  api.getFsdpRecord.mockResolvedValue(scholar);
  api.updateFsdpRecord.mockReturnValue(new Promise(() => {}));
  const router = createMemoryRouter(
    [
      { path: "/fsdp/:id/edit", element: <FsdpFormPage /> },
      { path: "/fsdp/:id", element: <h1>Profile</h1> },
    ],
    { initialEntries: ["/fsdp/1/edit"] },
  );
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("button", { name: "Save Scholar" }));
  fireEvent.click(screen.getByRole("link", { name: "Back" }));
  await screen.findByRole("button", { name: "Stay here" });
  expect(
    screen.getByRole("button", { name: "Leave without saving" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(router.state.location.pathname).toBe("/fsdp/1/edit");
});

test("section navigation scrolls without adding unmanaged browser history", () => {
  const router = openPage(<FsdpFormPage />, "/fsdp/new");
  const section = document.getElementById("scholar-grants")!;
  section.scrollIntoView = vi.fn();
  fireEvent.click(screen.getByRole("button", { name: "02 FSDP grants 0" }));
  expect(section.scrollIntoView).toHaveBeenCalledWith({ block: "start" });
  expect(router.state.location.hash).toBe("");
});

test("identical-name warnings require an explicit separate-person decision", async () => {
  names.getScholarNameMatches.mockResolvedValue([
    { id: 7, name: "Maria Santos", department: "CAS", reason: "Exact name", score: 0.95 },
  ]);
  api.createFsdpRecord.mockResolvedValue(scholar);
  openPage(<FsdpFormPage />, "/fsdp/new");
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), {
    target: { value: "Maria Santos" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await screen.findByRole("dialog", { name: "Check similar scholar names" });
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Return to form" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Save Scholar" }).hasAttribute("disabled")).toBe(
      false,
    ),
  );
  expect((screen.getByRole("textbox", { name: "Name *" }) as HTMLInputElement).value).toBe(
    "MARIA SANTOS",
  );
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await screen.findByRole("dialog", { name: "Check similar scholar names" });
  fireEvent.click(screen.getByRole("button", { name: "Keep separate and save" }));
  await waitFor(() => expect(api.createFsdpRecord).toHaveBeenCalledTimes(1));
});

test("failed name check retains the scholar draft and performs no write", async () => {
  names.getScholarNameMatches.mockRejectedValue(new Error("Name check unavailable"));
  openPage(<FsdpFormPage />, "/fsdp/new");
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), {
    target: { value: "Retain this draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await screen.findByText("Name check unavailable");
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
  expect((screen.getByRole("textbox", { name: "Name *" }) as HTMLInputElement).value).toBe(
    "RETAIN THIS DRAFT",
  );
});

test("custom new term is accepted and saved with the scholar", async () => {
  openPage(<FsdpFormPage />, "/fsdp/new");
  fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Program Applied *" }), {
    target: { value: "Example" },
  });
  fireEvent.change(screen.getByLabelText("Start Term"), { target: { value: "3rd" } });
  fireEvent.change(screen.getByRole("textbox", { name: "Start year / academic year" }), {
    target: { value: "2026-2027" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));
  await screen.findByRole("button", { name: "Add Grant" });
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), {
    target: { value: "Custom term scholar" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.createFsdpRecord).toHaveBeenCalled());
  expect(api.createFsdpRecord.mock.calls[0][0].participations[0].start_term).toBe("3rd");
});

test("grant editor preserves and updates custom imported terms", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    participations: [
      {
        id: 7,
        program_id: 1,
        name: "Legacy",
        delivering_hei: null,
        description: null,
        start_date: null,
        end_date: null,
        start_term: "3rd",
        start_academic_year: "2026-2027",
        end_term: null,
        end_academic_year: null,
        grant_type: null,
        grant_other: null,
        status: "On Going",
        extension: null,
        remarks: null,
      },
    ],
  });
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/1/edit"],
  });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("button", { name: /^Edit grant / }));
  fireEvent.click(screen.getByRole("button", { name: "Update Grant" }));
  await screen.findByRole("button", { name: "Add Grant" });
  fireEvent.click(screen.getByRole("button", { name: /^Edit grant / }));
  fireEvent.change(screen.getByLabelText("Start Term"), { target: { value: "2nd" } });
  fireEvent.click(screen.getByRole("button", { name: "Update Grant" }));
  await screen.findByRole("button", { name: "Add Grant" });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  expect(api.updateFsdpRecord.mock.calls[0][1].participations[0].start_term).toBe("2nd");
});

test("long names and unnamed optional requirements save without hidden lookup constraints", async () => {
  openPage(<FsdpFormPage />, "/fsdp/new");
  const name = "N".repeat(250);
  fireEvent.change(screen.getByRole("textbox", { name: "Name *" }), { target: { value: name } });
  fireEvent.change(screen.getByLabelText("Age"), { target: { value: "17" } });
  fireEvent.click(screen.getByRole("button", { name: "Add Requirement" }));
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.createFsdpRecord).toHaveBeenCalled());
  expect(names.getScholarNameMatches).not.toHaveBeenCalled();
  expect(api.createFsdpRecord.mock.calls[0][0]).toMatchObject({
    name,
    age: 17,
    requirements: [{ requirement_name: "" }],
  });
});

test("editing displays recorded custom grant types and statuses without changing them", async () => {
  api.getFsdpRecord.mockResolvedValue({
    ...scholar,
    participations: [
      {
        id: 7,
        program_id: 1,
        name: "Custom grant",
        delivering_hei: null,
        description: null,
        start_date: null,
        end_date: null,
        start_term: null,
        start_academic_year: null,
        end_term: null,
        end_academic_year: null,
        grant_type: "Historical grant",
        grant_other: null,
        status: "Historical status",
        extension: null,
        remarks: null,
      },
    ],
  });
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/1/edit"],
  });
  render(<RouterProvider router={router} />);
  fireEvent.click(await screen.findByRole("button", { name: /^Edit grant / }));
  expect((screen.getByLabelText("Type of Grant") as HTMLSelectElement).value).toBe(
    "Historical grant",
  );
  expect((screen.getByLabelText("Status") as HTMLSelectElement).value).toBe("Historical status");
  fireEvent.click(screen.getByRole("button", { name: "Update Grant" }));
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalled());
  expect(api.updateFsdpRecord.mock.calls[0][1].participations[0]).toMatchObject({
    grant_type: "Historical grant",
    status: "Historical status",
  });
});

test("uncertain creation retry uses the original request and freezes edits", async () => {
  const { UnconfirmedOperationError } = await import("../src/api/client");
  api.createFsdpRecord
    .mockRejectedValueOnce(new UnconfirmedOperationError("Not confirmed"))
    .mockResolvedValueOnce(scholar);
  openPage(<FsdpFormPage />, "/fsdp/new");
  const name = screen.getByRole("textbox", { name: "Name *" });
  fireEvent.change(name, { target: { value: "Original draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await screen.findByText(/This save has not been confirmed/);
  expect((name.closest("fieldset") as HTMLFieldSetElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
  await waitFor(() => expect(api.createFsdpRecord).toHaveBeenCalledTimes(2));
  expect(api.createFsdpRecord.mock.calls[1]).toEqual(api.createFsdpRecord.mock.calls[0]);
  expect(api.createFsdpRecord.mock.calls[0][1]).toMatch(/^[a-f0-9-]{36}$/);
});
