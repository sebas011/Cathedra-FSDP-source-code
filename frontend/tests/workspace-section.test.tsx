import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, it } from "vitest";
import WorkspaceSection from "../src/components/WorkspaceSection";

function openWorkspace(path: string, section: "fsdp" | "settings" = "fsdp") {
  render(<MemoryRouter initialEntries={[path]}><Routes><Route element={<WorkspaceSection section={section} />}><Route path="*" element={<h1>Workspace content</h1>} /></Route></Routes></MemoryRouter>);
}

it.each(["/fsdp/new", "/fsdp/new/", "/fsdp/12/edit", "/fsdp/12/edit/?from=directory"])("hides FSDP tabs on %s without hiding entry content", path => {
  openWorkspace(path);
  expect(screen.queryByRole("navigation", { name: "fsdp pages" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Scholars" })).toBeNull();
  expect(screen.getByRole("heading", { name: "Workspace content" })).toBeTruthy();
});

it.each(["/fsdp", "/fsdp/12"])("removes redundant FSDP tabs on %s", path => {
  openWorkspace(path);
  expect(screen.queryByRole("navigation", { name: "fsdp pages" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Scholars" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Monitoring & follow-up" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Legacy grant review" })).toBeNull();
});

it("preserves account-settings navigation", () => {
  openWorkspace("/settings/accounts", "settings");
  expect(screen.getByRole("navigation", { name: "settings pages" })).toBeTruthy();
});

it("does not restore redundant single-tab report navigation", () => {
  render(<MemoryRouter><h1>Dashboard</h1></MemoryRouter>);
  expect(screen.queryByRole("navigation")).toBeNull();
});
