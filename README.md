# Cathedra FSDP 0.5.28

Windows scholar and multi-year grant administration. Database schema 19. This repository contains the backend, interface, desktop updater, tests, build tools and documentation. Working records, accounts, backups, executables, private Google files and device credentials are excluded.

## Shared storage and reporting

Optional shared mode uses two separate Google spreadsheet files: private owner-only storage with three protected tabs, and a readable reporting file. Approved computers have separate revocable credentials encrypted for their Windows user. Administrators preview incoming/outgoing changes and resolve conflicts for the whole scholar profile. Local saves remain local until synchronization is confirmed. Interrupted operations retain the exact request for safe retry.

The Office PC containing the newest records must initialize the empty workspace explicitly. Other computers review joining and replacement of their local business records. Connecting alone never uploads records. Local accounts, passwords and recovery files remain local. Simultaneous editing is supported through revision checks and reviewed conflict choices; the service does not provide live co-editing.

Follow the [owner bridge setup](google/shared-workspace/README.md), including owner authorization, two-file creation, protection review, deployment and per-computer registration. Keep an existing workspace's project and bridge address; do not create another workspace just to connect the Office PC. All other PCs should be registered with initialization disabled. Report edits do not automatically change protected storage. Storage remains a bounded service with quotas and local backups are still required.

The Google checker handles omitted false/zero protection defaults while rejecting warning-only, bounded, partly unprotected or non-owner-editable storage. Owner-approved live setup verified private protected empty storage, rejected unregistered reads, and passed an approved non-initializing device's authenticated status/read checks. The authoritative Office upload remains a separate acceptance step. No private setup addresses or credentials are published.

## Office workflow improvements included

- Existing profiles save directly from Identity, Education or Programs & grants; new profiles finish on Review.
- The sidebar has a visible independent scrollbar.
- The 16-column Google report includes separate Profile remarks and grant Remarks, with each grant on its own consecutive row.
- Local reporting mode supports a read-only pull preview, explicit record matching and selected imports. Shared mode uses its own reviewed synchronization instead.
- Existing Summer terms, optional dates and literal calendar years, education entries, independent program applications, annual grants and payback tracking remain supported.

Schema 18 adds import receipts. Schema 19 adds stable shared record identities, explicit order and local sync metadata without replacing existing business IDs or values.

## Verification and delivery

Observed local checks passed: 703 backend tests, 308 interface tests, eight offline bridge tests, formatting, static/type checks and production builds. The native package has 152 verified runtime files and an empty schema-19 seed. Both inventory verifiers and a supported fictional 0.5.27/schema-18 to 0.5.28/schema-19 Office upgrade passed while retaining records, accounts, Summer and history. The working development database and Google connection were preserved during runtime replacement. See [0.5.28 validation](docs/VALIDATION_0.5.28.md).

GitHub's exact-revision Windows workflow independently verifies the published source, including all eight offline bridge tests and native packaging. Its result and release publication are separate from those local observations. Actual Office-PC acceptance remains required.

Download the ready-to-use Windows update from [Office releases](https://github.com/sebas011/Cathedra-FSDP/releases/latest). Source archives here are for development. Use the supplied updater against the original Office installation and retain its data folder; never replace the Office database with development records or the empty seed.

## Development

Use Windows x64, PowerShell 7, Python 3.14.7 x64 and Node.js 26.8.1 with the pinned requirements and frontend lockfile. Develop with fictional records.

```powershell
pwsh -File ./desktop/build-split-release.ps1 -Python '<python-path>' -Node '<node-path>'
node --test google/shared-workspace/tests/bridge.test.cjs
```

See the [developer guide](docs/DEVELOPER_GUIDE.md), [current architecture and requirements](docs/current/README.md), [backend schema](docs/current/BACKEND_SCHEMA.md), [application flow](docs/current/APP_FLOW.md), [Office guide](docs/OFFICE_GUIDE.md), [Google OAuth reporting guide](docs/GOOGLE_SHEETS_SETUP.md) and [shared workspace protocol](docs/current/SHARED_WORKSPACE_PROTOCOL.md).
