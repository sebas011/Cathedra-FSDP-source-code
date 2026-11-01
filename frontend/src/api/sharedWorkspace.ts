import { request } from "./client";

export const sharedWorkspaceChangedEvent = "cathedra-shared-workspace-changed";
export type SharedState = "disconnected" | "ready" | "dirty" | "pending" | "rejoin_required";
export type SharedMode = "join" | "initialize" | "sync";
export type SharedChoice = "local" | "shared";
export type SharedWorkspaceStatus = {
  configured: boolean;
  connected: boolean;
  initialized: boolean;
  joined: boolean;
  state: SharedState;
  device_id: string | null;
  device_label: string | null;
  device_key_hash: string | null;
  endpoint: string | null;
  workspace_id: string | null;
  revision: number | null;
  last_synced_at: string | null;
  storage_url: string | null;
  report_url: string | null;
  can_initialize: boolean;
  message: string | null;
};
export type SharedSummary = string | string[] | Record<string, string | number | null>;
export type SharedPreviewItem = {
  key: string;
  kind: "program" | "scholar" | "office_log";
  label: string;
  direction: string;
  conflict: boolean;
  local_summary: SharedSummary;
  shared_summary: SharedSummary;
};
export type SharedWorkspacePreview = {
  preview_id: string;
  mode: SharedMode;
  expires_at: string;
  items: SharedPreviewItem[];
  conflicts: string[];
  counts: { local: number; shared: number; upload: number; download: number; conflicts: number };
  warnings: string[];
};
export type SharedWorkspaceResult = {
  state: SharedState;
  revision: number;
  uploaded: number;
  downloaded: number;
  conflicts: number;
  replayed: boolean;
  message: string;
};
export type SharedReportResult = {
  rows: number;
  synced_at: string;
  spreadsheet_url: string;
  revision: number;
};

export const getSharedWorkspaceStatus = async (signal?: AbortSignal) =>
  request<SharedWorkspaceStatus>("/shared-workspace", { signal });
export const configureSharedWorkspace = async (endpoint: string) =>
  request<SharedWorkspaceStatus>("/shared-workspace/configure", {
    method: "POST",
    body: JSON.stringify({ endpoint }),
  });
export const checkSharedWorkspace = async () =>
  request<SharedWorkspaceStatus>("/shared-workspace/check", { method: "POST" });
export const disconnectSharedWorkspace = async () =>
  request<SharedWorkspaceStatus>("/shared-workspace/connection", { method: "DELETE" });
export const previewSharedWorkspace = async (mode: SharedMode) =>
  request<SharedWorkspacePreview>("/shared-workspace/preview", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
export const applySharedWorkspace = async (
  preview_id: string,
  choices: Record<string, SharedChoice>,
) =>
  request<SharedWorkspaceResult>("/shared-workspace/apply", {
    method: "POST",
    body: JSON.stringify({ preview_id, choices, confirm: true }),
  });
export const retrySharedWorkspace = async () =>
  request<SharedWorkspaceResult>("/shared-workspace/retry", { method: "POST" });
export const publishSharedWorkspaceReport = async () =>
  request<SharedReportResult>("/shared-workspace/report", { method: "POST" });

export const notifySharedWorkspaceChanged = () =>
  window.dispatchEvent(new Event(sharedWorkspaceChangedEvent));
