import type { SharedWorkspacePreview, SharedWorkspaceStatus } from "../src/api/sharedWorkspace";

export const disconnectedSharedWorkspace = (): SharedWorkspaceStatus => ({
  configured: false,
  connected: false,
  initialized: false,
  joined: false,
  state: "disconnected",
  device_id: null,
  device_label: null,
  device_key_hash: null,
  endpoint: null,
  workspace_id: null,
  revision: null,
  last_synced_at: null,
  storage_url: null,
  report_url: null,
  can_initialize: false,
  message: null,
});

export const joinedSharedWorkspace = (): SharedWorkspaceStatus => ({
  ...disconnectedSharedWorkspace(),
  configured: true,
  connected: true,
  initialized: true,
  joined: true,
  state: "dirty",
  device_id: "11111111-1111-4111-8111-111111111111",
  device_label: "FICTIONAL OFFICE PC",
  device_key_hash: "a".repeat(64),
  endpoint: "https://script.google.com/macros/s/fictional-bridge/exec",
  workspace_id: "22222222-2222-4222-8222-222222222222",
  revision: 3,
  storage_url: "https://docs.google.com/spreadsheets/d/fictional-data/edit",
  report_url: "https://docs.google.com/spreadsheets/d/fictional-report/edit",
});

export const sharedPreview = (): SharedWorkspacePreview => ({
  preview_id: "33333333-3333-4333-8333-333333333333",
  mode: "sync",
  expires_at: "2099-01-01T00:00:00Z",
  items: [
    {
      key: "44444444-4444-4444-8444-444444444444",
      kind: "scholar",
      label: "FICTIONAL SCHOLAR",
      direction: "upload",
      conflict: false,
      local_summary: [
        "Profile remarks: NEW LOCAL NOTE",
        "Education entries: 2",
        "Grant records: 3",
      ],
      shared_summary: [
        "Profile remarks: OLD SHARED NOTE",
        "Education entries: 2",
        "Grant records: 3",
      ],
    },
  ],
  conflicts: [],
  counts: { local: 12, shared: 12, upload: 1, download: 0, conflicts: 0 },
  warnings: ["The complete scholar record is kept together."],
});
