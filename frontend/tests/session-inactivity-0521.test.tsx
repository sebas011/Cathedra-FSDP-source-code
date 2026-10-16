import { useEffect, useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Outlet } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi, type MockInstance } from "vitest";
import App from "../src/App";
import SessionActivityGuard, {
  activityHeartbeatMilliseconds,
  sessionIdleMilliseconds,
} from "../src/components/SessionActivityGuard";
import {
  clearSession,
  getCurrentUser,
  getExpiredUser,
  request,
  saveSession,
  sessionActivityKey,
} from "../src/api/client";
import { administrator } from "./fixtures";

const mounts = vi.hoisted(() => ({ shell: 0, page: 0 }));
vi.mock("../src/components/AppShell", () => ({
  default: function TestShell() {
    useEffect(() => {
      mounts.shell++;
    }, []);
    return <Outlet />;
  },
}));
vi.mock("../src/pages/FsdpDashboardPage", () => ({
  default: function DraftPage() {
    const [draft, setDraft] = useState("");
    useEffect(() => {
      mounts.page++;
    }, []);
    return (
      <label>
        Unsaved draft
        <input value={draft} onChange={(event) => setDraft(event.target.value)} />
      </label>
    );
  },
}));

const start = new Date("2026-10-16T00:00:00Z");
let listeners: MockInstance<Document["addEventListener"]>;
let fetchMock: MockInstance<typeof fetch>;
const activity = () => JSON.parse(sessionStorage.getItem(sessionActivityKey) || "null");

beforeEach(() => {
  clearSession();
  vi.useFakeTimers();
  vi.setSystemTime(start);
  mounts.shell = 0;
  mounts.page = 0;
  saveSession({ token: "synthetic-session", user: administrator });
  listeners = vi.spyOn(document, "addEventListener");
  fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
});

afterEach(() => {
  vi.useRealTimers();
});

function trustedInput(type = "pointerdown") {
  // jsdom cannot dispatch trusted events. Invoke the registered browser-input listener at its trust boundary.
  const listener = listeners.mock.calls.find((call) => call[0] === type)?.[1] as
    EventListener | undefined;
  expect(listener).toBeTypeOf("function");
  act(() => listener!({ isTrusted: true } as Event));
}

async function openDraft() {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  const input = screen.getByRole("textbox", { name: "Unsaved draft" }) as HTMLInputElement;
  fireEvent.change(input, { target: { value: "Keep this local draft" } });
  return input;
}

test("saving a session initializes token-bound activity and clearing removes only session activity", () => {
  expect(activity()).toEqual({
    token: "synthetic-session",
    lastInputAt: start.getTime(),
    lastHeartbeatAt: start.getTime(),
  });
  vi.setSystemTime(new Date(start.getTime() + 1000));
  saveSession({ token: "replacement-session", user: administrator });
  expect(activity().token).toBe("replacement-session");
  expect(activity().lastInputAt).toBe(Date.now());
  sessionStorage.setItem("synthetic-draft", "Keep this draft");
  clearSession(true);
  expect(activity()).toBeNull();
  expect(getExpiredUser()?.id).toBe(administrator.id);
  expect(sessionStorage.getItem("synthetic-draft")).toBe("Keep this draft");
});

test("thirty idle minutes lock the route and same-user recovery preserves the mounted draft", async () => {
  const input = await openDraft();
  expect(mounts).toEqual({ shell: 1, page: 1 });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(sessionIdleMilliseconds - 1);
  });
  expect(getCurrentUser()?.id).toBe(administrator.id);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(getCurrentUser()).toBeNull();
  expect(screen.getByRole("dialog", { name: "Sign in again to keep editing" })).toBeTruthy();
  expect(input.value).toBe("Keep this local draft");
  expect(input.closest("[inert]")).toBeTruthy();
  expect(fetchMock).not.toHaveBeenCalled();

  fetchMock.mockResolvedValueOnce(
    new Response(JSON.stringify({ token: "recovered-session", user: administrator }), {
      status: 200,
    }),
  );
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Synthetic password" } });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Continue editing" }));
  });
  expect(getCurrentUser()?.id).toBe(administrator.id);
  expect(screen.queryByRole("dialog", { name: "Sign in again to keep editing" })).toBeNull();
  expect(screen.getByRole("textbox", { name: "Unsaved draft" })).toBe(input);
  expect(input.value).toBe("Keep this local draft");
  expect(input.closest("[inert]")).toBeNull();
  expect(mounts).toEqual({ shell: 1, page: 1 });
});

test("activity survives guard remounts and does not reset an idle page reload", async () => {
  const mounted = render(<SessionActivityGuard />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(sessionIdleMilliseconds - 1000);
  });
  const saved = activity().lastInputAt;
  mounted.unmount();
  vi.setSystemTime(new Date(start.getTime() + sessionIdleMilliseconds));
  await openDraft();
  expect(saved).toBe(start.getTime());
  expect(getCurrentUser()).toBeNull();
  expect(screen.getByRole("dialog", { name: "Sign in again to keep editing" })).toBeTruthy();
  expect(fetchMock).not.toHaveBeenCalled();
});

test.each(["focus", "pageshow", "visibilitychange"])(
  "%s checks wake-up expiry without renewing activity",
  async (eventName) => {
    render(<SessionActivityGuard />);
    vi.setSystemTime(new Date(start.getTime() + sessionIdleMilliseconds));
    act(() =>
      (eventName === "visibilitychange" ? document : window).dispatchEvent(new Event(eventName)),
    );
    expect(getCurrentUser()).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  },
);

test("focus and visibility alone neither send heartbeats nor reset the local deadline", async () => {
  render(<SessionActivityGuard />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
  });
  act(() => {
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect(activity().lastInputAt).toBe(start.getTime());
  expect(fetchMock).not.toHaveBeenCalled();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(20 * 60 * 1000);
  });
  expect(getCurrentUser()).toBeNull();
});

test("trusted input refreshes local time and sends only throttled input-driven heartbeats", async () => {
  render(<SessionActivityGuard />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(activityHeartbeatMilliseconds);
  });
  expect(fetchMock).not.toHaveBeenCalled();
  trustedInput();
  await act(async () => {});
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenLastCalledWith(
    expect.stringContaining("/auth/activity"),
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ Authorization: "Bearer synthetic-session" }),
    }),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(activityHeartbeatMilliseconds - 1);
  });
  trustedInput("keydown");
  trustedInput("input");
  trustedInput("wheel");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(activity().lastInputAt).toBe(Date.now());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  trustedInput("touchstart");
  await act(async () => {});
  expect(fetchMock).toHaveBeenCalledTimes(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(sessionIdleMilliseconds - 1);
  });
  expect(getCurrentUser()?.id).toBe(administrator.id);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(getCurrentUser()).toBeNull();
});

test("a trusted input after a suspended idle interval locks before it can send activity", () => {
  render(<SessionActivityGuard />);
  vi.setSystemTime(new Date(start.getTime() + sessionIdleMilliseconds));
  trustedInput();
  expect(getCurrentUser()).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("scripted input and input in a hidden tab cannot renew the session", async () => {
  render(<SessionActivityGuard />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(activityHeartbeatMilliseconds);
  });
  act(() => {
    document.dispatchEvent(new Event("pointerdown"));
    document.dispatchEvent(new Event("keydown"));
    document.dispatchEvent(new Event("input"));
    document.dispatchEvent(new Event("wheel"));
  });
  expect(activity().lastInputAt).toBe(start.getTime());
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  trustedInput();
  expect(activity().lastInputAt).toBe(start.getTime());
  expect(fetchMock).not.toHaveBeenCalled();
});

test.each([
  null,
  "invalid-json",
  JSON.stringify({
    token: "other-session",
    lastInputAt: start.getTime(),
    lastHeartbeatAt: start.getTime(),
  }),
])("missing or mismatched activity expires instead of starting a new clock (%s)", (stored) => {
  if (stored === null) sessionStorage.removeItem(sessionActivityKey);
  else sessionStorage.setItem(sessionActivityKey, stored);
  render(<SessionActivityGuard />);
  expect(getCurrentUser()).toBeNull();
  expect(getExpiredUser()?.id).toBe(administrator.id);
  expect(fetchMock).not.toHaveBeenCalled();
});

test("a server-expired activity response locks while an unavailable service keeps the local draft session", async () => {
  render(<SessionActivityGuard />);
  fetchMock.mockRejectedValueOnce(new Error("Synthetic unavailable service"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(activityHeartbeatMilliseconds);
  });
  trustedInput();
  await act(async () => {});
  expect(getCurrentUser()?.id).toBe(administrator.id);
  fetchMock.mockResolvedValueOnce(
    new Response(JSON.stringify({ detail: "Session expired" }), { status: 401 }),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(activityHeartbeatMilliseconds);
  });
  trustedInput();
  await act(async () => {});
  expect(getCurrentUser()).toBeNull();
  expect(getExpiredUser()?.id).toBe(administrator.id);
});

test("a late unauthorized heartbeat from the old token cannot clear a recovered session", async () => {
  let finish!: (response: Response) => void;
  fetchMock.mockImplementationOnce(
    () =>
      new Promise<Response>((resolve) => {
        finish = resolve;
      }),
  );
  const pending = request<void>("/auth/activity", { method: "POST" });
  const rejected = expect(pending).rejects.toThrow("Session expired");
  saveSession({ token: "recovered-session", user: administrator });
  finish(new Response(JSON.stringify({ detail: "Session expired" }), { status: 401 }));
  await rejected;
  expect(getCurrentUser()?.id).toBe(administrator.id);
  expect(activity().token).toBe("recovered-session");
  expect(getExpiredUser()).toBeNull();
});
