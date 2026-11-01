import { request } from "./client";

export type GooglePullFields = Record<string, string | number | null>;

export type GooglePullGrant = {
  key: string;
  row: number;
  fields: GooglePullFields;
  suggested_participation_id: number | null;
};

export type GooglePullProfile = {
  key: string;
  row: number;
  fields: GooglePullFields;
  education_text: string | null;
  suggested_scholar_id: number | null;
  grants: GooglePullGrant[];
};

export type GooglePullMatch = {
  id: number;
  name: string;
  revision: number;
  fields: GooglePullFields;
  grants: { id: number; fields: GooglePullFields }[];
};

export type GooglePullPreview = {
  preview_id: string;
  fetched_at: string;
  expires_at: string;
  worksheet: string;
  warnings: string[];
  profiles: GooglePullProfile[];
  matches: GooglePullMatch[];
};

export type GooglePullApply = {
  preview_id: string;
  profiles: {
    key: string;
    scholar_id: number | null;
    expected_revision: number | null;
    grants: { key: string; participation_id: number | null }[];
  }[];
};

export type GooglePullResult = {
  scholars_created: number;
  scholars_updated: number;
  grants_created: number;
  grants_updated: number;
  scholar_ids: number[];
  replayed: boolean;
};

export const previewGoogleSheetPull = () =>
  request<GooglePullPreview>("/google-sheets/pull/preview", { method: "POST" });

export const applyGoogleSheetPull = (payload: GooglePullApply) =>
  request<GooglePullResult>("/google-sheets/pull/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
