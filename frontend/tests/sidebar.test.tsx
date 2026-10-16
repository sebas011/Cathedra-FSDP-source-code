import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import axe from "axe-core";
import AppShell from "../src/components/AppShell";
import { administrator } from "./fixtures";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getServiceHealth: vi.fn(),
  clearSession: vi.fn(),
  signOut: vi.fn(),
  exitDesktop: vi.fn(),
  releaseVersion: "test",
}));
vi.mock("../src/api", () => api);
let mobile = false;
let changeListeners: Array<() => void> = [];

function openShell() {
  const router = createMemoryRouter(
    [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <h1>Dashboard test</h1> },
          { path: "/fsdp", element: <h1>Scholars test</h1> },
        ],
      },
    ],
    { initialEntries: ["/"] },
  );
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  mobile = false;
  changeListeners = [];
  api.getCurrentUser.mockReturnValue(administrator);
  api.getServiceHealth.mockResolvedValue({
    status: "ok",
    product: "fsdp",
    release_version: "test",
    desktop_mode: false,
  });
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      get matches() {
        return mobile;
      },
      addEventListener: (_event: string, listener: () => void) => changeListeners.push(listener),
      removeEventListener: (_event: string, listener: () => void) => {
        changeListeners = changeListeners.filter((item) => item !== listener);
      },
    })),
  );
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockReturnValue([
    { width: 44, height: 44 },
  ] as unknown as DOMRectList);
});

test("desktop has one sidebar toggle and no calendar destination", async () => {
  openShell();
  expect(screen.getAllByRole("button", { name: "Collapse sidebar" })).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Open menu" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Academic Calendar" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
  expect(screen.getByRole("button", { name: "Expand sidebar" }).getAttribute("aria-expanded")).toBe(
    "false",
  );
  expect(document.querySelector(".app-layout")?.classList.contains("sidebar-collapsed")).toBe(true);
  expect(screen.queryByText("Cathedra FSDP")).toBeNull();
  expect(localStorage.getItem("cathedra-fsdp-sidebar-collapsed")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "Expand sidebar" }));
  expect(screen.getByText("Cathedra FSDP")).toBeTruthy();
  await waitFor(() => expect(api.getServiceHealth).toHaveBeenCalled());
});

test("desktop remembers the last sidebar choice", () => {
  localStorage.setItem("cathedra-fsdp-sidebar-collapsed", "true");
  openShell();
  expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeTruthy();
});

test("removed workspace breadcrumbs stay absent during navigation", async () => {
  openShell();
  expect(screen.queryByLabelText("Current workspace")).toBeNull();
  fireEvent.click(screen.getByRole("link", { name: "FSDP" }));
  await waitFor(() => expect(screen.queryByLabelText("Current workspace")).toBeNull());
});

test("mobile drawer opens with labels and closes with Escape and restored focus", async () => {
  mobile = true;
  localStorage.setItem("cathedra-fsdp-sidebar-collapsed", "true");
  document.body.style.overflow = "auto";
  openShell();
  const opener = screen.getByRole("button", { name: "Open menu" });
  fireEvent.click(opener);
  const closer = screen.getByRole("button", { name: "Close menu" });
  expect(document.activeElement).toBe(closer);
  expect(screen.getByRole("dialog", { name: "Navigation menu" }).getAttribute("aria-modal")).toBe(
    "true",
  );
  expect(document.querySelector(".workspace")?.hasAttribute("inert")).toBe(true);
  expect(document.body.style.overflow).toBe("hidden");
  expect(document.querySelector(".app-layout")?.classList.contains("sidebar-collapsed")).toBe(
    false,
  );
  expect(screen.getByText("Cathedra FSDP")).toBeTruthy();
  fireEvent.keyDown(document, { key: "Escape" });
  await waitFor(() => expect(document.activeElement).toBe(opener));
  expect(document.querySelector(".workspace")?.hasAttribute("inert")).toBe(false);
  expect(document.body.style.overflow).toBe("auto");
});

test("mobile keyboard navigation stays in the drawer and close button works", () => {
  mobile = true;
  openShell();
  fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
  const closer = screen.getByRole("button", { name: "Close menu" });
  const guide = screen.getByRole("link", { name: "Office Guide" });
  guide.focus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(document.activeElement).toBe(closer);
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(guide);
  fireEvent.click(closer);
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("backdrop closes the drawer and navigation opens the selected page", async () => {
  mobile = true;
  openShell();
  fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
  fireEvent.click(document.querySelector(".sidebar-scrim")!);
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
  fireEvent.click(screen.getByRole("link", { name: "FSDP" }));
  expect(await screen.findByRole("heading", { name: "Scholars test" })).toBeTruthy();
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement?.id).toBe("main-content");
});

test("resizing closes the drawer without losing the desktop preference", () => {
  localStorage.setItem("cathedra-fsdp-sidebar-collapsed", "true");
  openShell();
  act(() => {
    mobile = true;
    changeListeners.forEach((listener) => listener());
  });
  fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
  act(() => {
    mobile = false;
    changeListeners.forEach((listener) => listener());
  });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeTruthy();
  expect(document.body.style.overflow).not.toBe("hidden");
});

test("drawer controls have valid accessible names and modal structure", async () => {
  mobile = true;
  openShell();
  fireEvent.click(screen.getByRole("button", { name: "Open menu" }));
  const result = await axe.run(document.body, {
    runOnly: {
      type: "rule",
      values: [
        "button-name",
        "link-name",
        "aria-valid-attr",
        "aria-valid-attr-value",
        "aria-required-attr",
        "aria-roles",
        "aria-dialog-name",
      ],
    },
  });
  expect(result.violations.map((item) => item.id)).toEqual([]);
});
