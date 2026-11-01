import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import { saveSession } from "../src/api/client";
import type { Scholar } from "../src/types";
import { administrator, scholar } from "./fixtures";
import { scholarStep } from "./scholarSteps";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
}));
const names = vi.hoisted(() => ({ getScholarNameMatches: vi.fn() }));
vi.mock("../src/api", () => api);
vi.mock("../src/api/fsdp", () => names);

const savedScholar: Scholar = {
  ...scholar,
  revision: 7,
  has_hard_copy: true,
  has_soft_copy: false,
  education: [
    {
      id: 2,
      degree: "BACHELOR OF SCIENCE",
      level: "Bachelor’s",
      institution: "EXAMPLE COLLEGE",
      graduation_year: "2014",
    },
  ],
  participations: [
    {
      id: 3,
      program_id: 4,
      name: "EXISTING PROGRAM",
      delivering_hei: "EXAMPLE UNIVERSITY",
      start_date: null,
      end_date: null,
      start_term: "Summer",
      start_academic_year: "2021",
      end_term: "2nd",
      end_academic_year: "2021",
      status: "On Going",
      grant_type: "Thesis Aid",
      grant_other: null,
      extension: null,
      remarks: "RETAIN THIS GRANT",
      application_key: "existing-application",
      program_category: "Certification",
    },
  ],
  requirements: [
    {
      id: 5,
      requirement_name: "EXISTING REQUIREMENT",
      due_date: null,
      is_complete: false,
      remarks: "RETAIN THIS REQUIREMENT",
      completed_at: null,
    },
  ],
};

function openEditor() {
  const router = createMemoryRouter(
    [
      { path: "/fsdp/:id/edit", element: <FsdpFormPage /> },
      { path: "/fsdp/:id", element: <h1>Saved scholar profile</h1> },
    ],
    { initialEntries: ["/fsdp/1/edit"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => {
  vi.resetAllMocks();
  saveSession({ token: "synthetic-step-save", user: administrator });
  api.getFsdpRecord.mockResolvedValue(savedScholar);
  api.updateFsdpRecord.mockResolvedValue(savedScholar);
  names.getScholarNameMatches.mockResolvedValue([]);
});

test.each([1, 2, 3])("an existing scholar saves the full record from step %s", async (step) => {
  const router = openEditor();
  fireEvent.change(await screen.findByRole("textbox", { name: "Name *" }), {
    target: { value: "Changed identity" },
  });
  scholarStep(step);
  expect(screen.queryByRole("heading", { name: "Review scholar record" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByRole("heading", { name: "Saved scholar profile" });
  expect(router.state.location.pathname).toBe("/fsdp/1");
  expect(api.updateFsdpRecord).toHaveBeenCalledTimes(1);
  expect(api.updateFsdpRecord).toHaveBeenCalledWith(
    1,
    expect.objectContaining({
      name: "CHANGED IDENTITY",
      has_hard_copy: true,
      has_soft_copy: false,
      education: [expect.objectContaining({ id: 2, degree: "BACHELOR OF SCIENCE" })],
      participations: [
        expect.objectContaining({
          id: 3,
          source_program_id: 4,
          application_key: "existing-application",
          start_term: "Summer",
          start_academic_year: "2021",
          remarks: "RETAIN THIS GRANT",
        }),
      ],
      requirements: [expect.objectContaining({ id: 5, remarks: "RETAIN THIS REQUIREMENT" })],
    }),
    7,
  );
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});

test("staged education saves from Education without visiting Review", async () => {
  openEditor();
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(2);
  fireEvent.click(screen.getByRole("button", { name: "Add education" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Degree" }), {
    target: { value: "Master of Education" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save education" }));
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalledTimes(1));
  expect(api.updateFsdpRecord.mock.calls[0][1].education).toEqual([
    expect.objectContaining({ id: 2, degree: "BACHELOR OF SCIENCE" }),
    expect.objectContaining({ degree: "MASTER OF EDUCATION" }),
  ]);
});

test("staged grants save from Programs and grants without visiting Review", async () => {
  openEditor();
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(3);
  fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Program Applied *" }), {
    target: { value: "New certification" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalledTimes(1));
  expect(api.updateFsdpRecord.mock.calls[0][1].participations).toEqual([
    expect.objectContaining({ id: 3, program_name: "EXISTING PROGRAM" }),
    expect.objectContaining({ program_name: "NEW CERTIFICATION" }),
  ]);
});

test.each([
  { step: 2, add: "Add education", field: "Degree", editor: "education entry" },
  { step: 3, add: "Add Grant", field: "Program Applied *", editor: "grant" },
])("quick save cannot discard an open $editor", async ({ step, add, field, editor }) => {
  openEditor();
  await screen.findByRole("textbox", { name: "Name *" });
  scholarStep(step);
  fireEvent.click(screen.getByRole("button", { name: add }));
  const input = screen.getByRole("textbox", { name: field });
  fireEvent.change(input, { target: { value: "Retained nested draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(screen.getByRole("alert").textContent).toContain(`open ${editor}`);
  expect(screen.getByRole("textbox", { name: field })).toBe(input);
  expect((input as HTMLInputElement).value).toBe("RETAINED NESTED DRAFT");
  expect(api.updateFsdpRecord).not.toHaveBeenCalled();
});

test("quick save with a missing name returns to Identity with all entries retained", async () => {
  openEditor();
  fireEvent.change(await screen.findByRole("textbox", { name: "Name *" }), {
    target: { value: "" },
  });
  scholarStep(2);
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(screen.getByRole("heading", { name: "Scholar Information" })).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain("enter the scholar’s name");
  scholarStep(2);
  expect(
    within(document.getElementById("scholar-step-2")!).getByText("BACHELOR OF SCIENCE"),
  ).toBeTruthy();
  expect(api.updateFsdpRecord).not.toHaveBeenCalled();
});

test("pending quick saves block repeated submissions and keep controls disabled", async () => {
  let finish!: (value: Scholar) => void;
  api.updateFsdpRecord.mockReturnValue(new Promise<Scholar>((resolve) => (finish = resolve)));
  openEditor();
  const input = await screen.findByRole("textbox", { name: "Name *" });
  const form = input.closest("form")!;
  act(() => {
    fireEvent.submit(form);
    fireEvent.submit(form);
  });
  await waitFor(() => expect(api.updateFsdpRecord).toHaveBeenCalledTimes(1));
  expect(names.getScholarNameMatches).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Saving…" }).hasAttribute("disabled")).toBe(true);
  expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(true);
  expect(screen.getByRole("button", { name: "Step 2: Education" }).hasAttribute("disabled")).toBe(
    true,
  );
  expect(input.closest("fieldset")?.disabled).toBe(true);
  await act(async () => finish(savedScholar));
  await screen.findByRole("heading", { name: "Saved scholar profile" });
});

test("a rejected grant field opens Programs and grants after saving Identity", async () => {
  api.updateFsdpRecord.mockRejectedValue(new Error("Grant · 1 · Program applied: Required."));
  openEditor();
  await screen.findByRole("textbox", { name: "Name *" });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("heading", { name: "FSDP Grants" })).toBeTruthy();
  expect(
    within(screen.getByRole("region", { name: "Grants for EXISTING PROGRAM" })).getByText(
      "EXISTING PROGRAM",
    ),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: "Save changes" }).hasAttribute("disabled")).toBe(false);
});

test("new scholars retain the explicit Review step before their first save", () => {
  const router = createMemoryRouter([{ path: "/fsdp/new", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/new"],
  });
  render(<RouterProvider router={router} />);
  const name = screen.getByRole("textbox", { name: "Name *" });
  fireEvent.change(name, { target: { value: "New scholar" } });
  expect(screen.queryByRole("button", { name: "Save changes" })).toBeNull();
  fireEvent.submit(name.closest("form")!);
  expect(screen.getByRole("heading", { name: "Review scholar record" })).toBeTruthy();
  expect(api.createFsdpRecord).not.toHaveBeenCalled();
});
