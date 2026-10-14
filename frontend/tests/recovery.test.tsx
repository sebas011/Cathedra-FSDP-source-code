import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import type { ReactElement } from "react";
import AccountSecurityPage from "../src/pages/AccountSecurityPage";
import { administrator } from "./fixtures";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(), getUsers: vi.fn(), changePassword: vi.fn(), clearSession: vi.fn(), createUser: vi.fn(),
  resetUserPassword: vi.fn(), revokeUserSessions: vi.fn(), setUserActive: vi.fn(),
}));
vi.mock("../src/api", () => api);
function openPage(element: ReactElement) {
  const router = createMemoryRouter([{ path: "*", element }], { initialEntries: ["/settings/accounts"] });
  render(<RouterProvider router={router} />);
}
beforeEach(() => { vi.resetAllMocks(); api.getCurrentUser.mockReturnValue(administrator); });
test("account retry preserves password input and does not submit credentials", async () => {
    api.getUsers.mockRejectedValueOnce(new Error("Accounts unavailable")).mockResolvedValue([administrator]);
    openPage(<AccountSecurityPage />);
    const current = screen.getByLabelText("Current password");
    fireEvent.change(current, { target: { value: "unsaved-test-input" } });
    fireEvent.click(await screen.findByRole("button", { name: "Retry accounts" }));
    await waitFor(() => expect(screen.queryByText("Accounts unavailable")).toBeNull());
    expect((current as HTMLInputElement).value).toBe("unsaved-test-input");
    expect(api.changePassword).not.toHaveBeenCalled();
    expect(api.createUser).not.toHaveBeenCalled();
  });
