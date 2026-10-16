import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import { scholar } from "./fixtures";
import type { ParticipationRead } from "../src/types";

const api = vi.hoisted(() => ({
  getFsdpRecord: vi.fn(),
  updateFsdpRecord: vi.fn(),
  createFsdpRecord: vi.fn(),
}));
vi.mock("../src/api", () => api);

function grant(id: number): ParticipationRead {
  return {
    id,
    program_id: id,
    name: `Program ${id}`,
    delivering_hei: "University",
    start_date: null,
    end_date: null,
    start_term: null,
    start_academic_year: null,
    end_term: null,
    end_academic_year: null,
    grant_type: "Full Scholarship",
    grant_other: null,
    status: "On Going",
    extension: null,
    remarks: null,
  };
}

function openForm() {
  api.getFsdpRecord.mockResolvedValue({ ...scholar, participations: [grant(1), grant(2)] });
  const router = createMemoryRouter([{ path: "/fsdp/:id/edit", element: <FsdpFormPage /> }], {
    initialEntries: ["/fsdp/1/edit"],
  });
  render(<RouterProvider router={router} />);
}

beforeEach(() => vi.resetAllMocks());

test("removing an earlier grant preserves the active grant identity and draft", async () => {
  openForm();
  const secondRow = await screen.findByRole("row", { name: /Program 2/ });
  fireEvent.click(within(secondRow).getByRole("button", { name: /^Edit grant / }));
  const editor = await screen.findByRole("textbox", { name: "Program Applied *" });
  fireEvent.change(editor, { target: { value: "Updated second" } });
  fireEvent.click(
    within(screen.getByRole("row", { name: /Program 1/ })).getByRole("button", {
      name: /^Remove grant /,
    }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Discard changes" }));
  fireEvent.click(screen.getByRole("button", { name: "Update Grant" }));
  await screen.findByRole("row", { name: /UPDATED SECOND/ });
  expect(screen.queryByRole("row", { name: /Program 1/ })).toBeNull();
});

test("switching edited grants requires explicit discard", async () => {
  openForm();
  const firstRow = await screen.findByRole("row", { name: /Program 1/ });
  fireEvent.click(within(firstRow).getByRole("button", { name: /^Edit grant / }));
  const editor = await screen.findByRole("textbox", { name: "Program Applied *" });
  fireEvent.change(editor, { target: { value: "Unsaved first" } });
  fireEvent.click(
    within(screen.getByRole("row", { name: /Program 2/ })).getByRole("button", {
      name: /^Edit grant /,
    }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Keep editing" }));
  expect((editor as HTMLInputElement).value).toBe("UNSAVED FIRST");
});
