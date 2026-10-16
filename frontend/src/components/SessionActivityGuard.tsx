import { useEffect } from "react";
import {
  clearSession,
  getCurrentUser,
  getSessionToken,
  request,
  sessionActivityKey,
  sessionChangedEvent,
} from "../api/client";

export const sessionIdleMilliseconds = 30 * 60 * 1000;
export const activityHeartbeatMilliseconds = 60 * 1000;
const inputEvents = ["pointerdown", "keydown", "input", "wheel", "touchstart"] as const;

type SessionActivity = { token: string; lastInputAt: number; lastHeartbeatAt: number };

function readActivity(): SessionActivity | null {
  try {
    const token = JSON.parse(getSessionToken() || "{}").token;
    const activity = JSON.parse(
      sessionStorage.getItem(sessionActivityKey) || "null",
    ) as SessionActivity | null;
    if (
      token &&
      activity &&
      activity.token === token &&
      Number.isFinite(activity.lastInputAt) &&
      Number.isFinite(activity.lastHeartbeatAt)
    )
      return activity;
  } catch {}
  return null;
}

// This lives outside the protected page tree so locking keeps mounted editors and their drafts.
export default function SessionActivityGuard() {
  useEffect(() => {
    let timer: number | undefined;
    let heartbeat: AbortController | undefined;
    const cancelTimer = () => {
      window.clearTimeout(timer);
      timer = undefined;
    };
    const check = (): SessionActivity | null => {
      cancelTimer();
      if (!getCurrentUser()) return null;
      const activity = readActivity();
      const now = Date.now();
      if (
        !activity ||
        activity.lastInputAt > now ||
        now - activity.lastInputAt >= sessionIdleMilliseconds
      ) {
        clearSession(true);
        return null;
      }
      timer = window.setTimeout(check, sessionIdleMilliseconds - (now - activity.lastInputAt));
      return activity;
    };
    const onInput = (event: Event) => {
      // Check elapsed wall time first: a wake-up input cannot revive an already idle session.
      const activity = check();
      if (!activity || !event.isTrusted || document.visibilityState === "hidden") return;
      const now = Date.now();
      activity.lastInputAt = now;
      const due = !heartbeat && now - activity.lastHeartbeatAt >= activityHeartbeatMilliseconds;
      if (due) activity.lastHeartbeatAt = now;
      sessionStorage.setItem(sessionActivityKey, JSON.stringify(activity));
      check();
      if (due) {
        const controller = new AbortController();
        heartbeat = controller;
        void request<void>("/auth/activity", { method: "POST", signal: controller.signal })
          .catch(() => {
            // An unavailable service leaves drafts in place; an authentication failure locks via the client.
          })
          .finally(() => {
            if (heartbeat === controller) heartbeat = undefined;
          });
      }
    };
    const syncSession = () => {
      heartbeat?.abort();
      heartbeat = undefined;
      check();
    };
    inputEvents.forEach((name) =>
      document.addEventListener(name, onInput, { capture: true, passive: true }),
    );
    document.addEventListener("visibilitychange", check);
    window.addEventListener("focus", check);
    window.addEventListener("pageshow", check);
    window.addEventListener("storage", syncSession);
    window.addEventListener(sessionChangedEvent, syncSession);
    check();
    return () => {
      cancelTimer();
      heartbeat?.abort();
      inputEvents.forEach((name) => document.removeEventListener(name, onInput, true));
      document.removeEventListener("visibilitychange", check);
      window.removeEventListener("focus", check);
      window.removeEventListener("pageshow", check);
      window.removeEventListener("storage", syncSession);
      window.removeEventListener(sessionChangedEvent, syncSession);
    };
  }, []);
  return null;
}
