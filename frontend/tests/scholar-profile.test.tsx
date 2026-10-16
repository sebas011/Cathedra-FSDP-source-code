import { expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import FsdpDetailPage from "../src/pages/FsdpDetailPage";
import { scholar } from "./fixtures";
import type { Scholar } from "../src/types";

const api = vi.hoisted(() => ({ getFsdpRecord: vi.fn() }));
vi.mock("../src/api/officeLog", () => ({
  getOfficeLogs: async () => ({ items: [], total: 0, page: 1, page_size: 50 }),
}));
vi.mock("../src/api", () => api);

function openProfile(record: Scholar) {
  api.getFsdpRecord.mockResolvedValue(record);
  const router = createMemoryRouter([{ path: "/fsdp/:id", element: <FsdpDetailPage /> }], {
    initialEntries: ["/fsdp/1"],
  });
  render(<RouterProvider router={router} />);
}

test("empty register does not claim requirements are complete", async () => {
  openProfile(scholar);
  await screen.findByRole("heading", { name: scholar.name });
  expect(screen.getByText("No requirements recorded")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Edit profile" }).getAttribute("href")).toBe(
    "/fsdp/1/edit",
  );
});

test("manual follow-up remains visible when the register is empty", async () => {
  openProfile({ ...scholar, missing_requirements: true, manual_requirements_follow_up: true });
  await screen.findByRole("heading", { name: scholar.name });
  expect(
    screen.getByText("Additional missing requirements are marked for follow-up."),
  ).toBeTruthy();
  expect(screen.getByText("Requirements need follow-up")).toBeTruthy();
});
