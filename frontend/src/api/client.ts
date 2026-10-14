import { apiErrorMessage } from "../apiErrors";
import type { LocalUser, SessionResult } from "../types";


export const API = import.meta.env.DEV ? "http://127.0.0.1:8101/api/v1" : "/api/v1";
const sessionKey = "cathedra-fsdp-session";
export const releaseVersion = import.meta.env.VITE_CATHEDRA_VERSION;
export const getSessionToken = () => { localStorage.removeItem(sessionKey); return sessionStorage.getItem(sessionKey); };
export const sessionChangedEvent = "cathedra-session-changed";
let expiredUser: LocalUser | null = null;
let logoutWarning = "";
const logoutWarningKey = "cathedra-fsdp-logout-warning";
export const getLogoutWarning = () => logoutWarning || sessionStorage.getItem(logoutWarningKey) || "";
export const setLogoutWarning = (message: string) => {
  logoutWarning = message;
  if (message) sessionStorage.setItem(logoutWarningKey, message);
  else sessionStorage.removeItem(logoutWarningKey);
};
export const getExpiredUser = () => expiredUser;
export const saveSession = (result: SessionResult) => {
  expiredUser = null;
  setLogoutWarning("");
  sessionStorage.setItem(sessionKey, JSON.stringify(result));
  localStorage.removeItem(sessionKey);
  window.dispatchEvent(new Event(sessionChangedEvent));
};
export const clearSession = (expired = false) => {
  expiredUser = expired ? getCurrentUser() || expiredUser : null;
  localStorage.removeItem(sessionKey);
  sessionStorage.removeItem(sessionKey);
  try {
    Object.keys(sessionStorage).filter((key) => key.startsWith("cathedra-directory:")).forEach((key) => sessionStorage.removeItem(key));
  } catch {}
  window.dispatchEvent(new Event(sessionChangedEvent));
};
export const getCurrentUser = () => { try { return JSON.parse(getSessionToken() || "").user as LocalUser; } catch { return null; } };
export class UnconfirmedOperationError extends Error {}

export async function requestResponse<T>(path: string, init: RequestInit | undefined, consume: (response: Response) => Promise<T>): Promise<T> {
  let token = "";
  try { token = JSON.parse(getSessionToken() || "{}").token || ""; }
  catch { clearSession(); }
  const controller = new AbortController();
  const signal = init?.signal ? AbortSignal.any([init.signal, controller.signal]) : controller.signal;
  const timer = window.setTimeout(() => controller.abort(), path === "/maintenance/restore" ? 180000 : 30000);
  let fetched = false;
  let abort!: () => void;
  const cancelled = new Promise<never>((_resolve, reject) => {
    abort = () => reject(new DOMException("Operation aborted", "AbortError"));
    if (signal.aborted) abort();
    else signal.addEventListener("abort", abort, { once: true });
  });
  try {
    const response = await Promise.race([fetch(`${API}${path}`, {
      ...init,
      signal,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init?.headers || {}) },
    }), cancelled]);
    fetched = true;
    if (!response.ok) {
      const body = await Promise.race([response.json().catch(() => null), cancelled]);
      if (response.status === 401 && !["/auth/login", "/auth/setup"].includes(path)) clearSession(true);
      throw new Error(apiErrorMessage(body?.detail, response.status));
    }
    return await Promise.race([consume(response), cancelled]);
  } catch (caught) {
    if (!fetched || controller.signal.aborted || init?.signal?.aborted || !(caught instanceof Error) || caught instanceof TypeError) {
      throw new UnconfirmedOperationError("The local service did not confirm this operation. Check the connection and retry. Unsaved changes remain in this window.");
    }
    throw caught;
  } finally { window.clearTimeout(timer); signal.removeEventListener("abort", abort); }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return requestResponse(path, init, response => response.status === 204 ? Promise.resolve(undefined as T) : response.json() as Promise<T>);
}

export async function download(path: string, filename: string) {
  const blob = await requestResponse(path, undefined, response => response.blob());
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename; document.body.appendChild(link);
  link.click(); link.remove(); URL.revokeObjectURL(url);
}
