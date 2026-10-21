import { request } from "./client";

export type GoogleSheetsStatus = {
  configured: boolean;
  connected: boolean;
  spreadsheet_id: string | null;
  worksheet: string;
  last_sync_at: string | null;
  connection_state: "idle" | "waiting" | "connected" | "error";
  message: string | null;
};

export type GoogleSheetsSyncResult = {
  rows: number;
  synced_at: string;
  spreadsheet_url: string;
};

export const getGoogleSheetsStatus = (signal?: AbortSignal) =>
  request<GoogleSheetsStatus>("/google-sheets", { signal });

export const configureGoogleSheets = (
  spreadsheet: string,
  clientConfiguration?: Record<string, unknown>,
) =>
  request<GoogleSheetsStatus>("/google-sheets/configure", {
    method: "POST",
    body: JSON.stringify({
      spreadsheet,
      ...(clientConfiguration ? { client_configuration: clientConfiguration } : {}),
    }),
  });

export const connectGoogleSheets = () =>
  request<GoogleSheetsStatus>("/google-sheets/connect", { method: "POST" });

export const disconnectGoogleSheets = () =>
  request<GoogleSheetsStatus>("/google-sheets/connection", { method: "DELETE" });

export const syncGoogleSheets = () =>
  request<GoogleSheetsSyncResult>("/google-sheets/sync", {
    method: "POST",
    body: JSON.stringify({ replace_report: true }),
  });
