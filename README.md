# Cathedra FSDP 0.5.26

Source code for the local Windows FSDP scholar administration application. Database schema: 17.

This repository contains backend, frontend, desktop launcher/updater, tests, build tools and technical documentation. Working scholar records, accounts, backups, OAuth credentials, Google connection tokens, executables and private installation history are excluded.

## Selected blueprint improvements

- Administrators can inspect bounded previous/new business values in scholar change history. Capture and the record change share a transaction. An explicit allowlist excludes credential and internal identifier values, and long text previews are marked when truncated. Old events remain readable without fabricated prior values; general activity responses remain metadata-only.
- Grant profiles and dashboard contract follow-up can expand assessment details for the factual reason, deadline basis where available and assessed-on date. Recorded outcomes, application-specific completion, repayment progress, case status, deadline precedence and the three-calendar-year grace boundary are retained.
- A shared Philippine business date keeps contract/report calculations, registration analytics and default Office Log dates consistent. Authentication and expiry keep UTC semantics; existing backup/recovery timestamp handling is retained.

Migration 17 adds only nullable `activity_events.change_details`. Existing IDs, records, optional dates, Name and Program Applied essential fields, Summer, Staff/Unknown, certification/enhancement programs, repeated applications and annual grant records remain supported. No degree-only model, mandatory appointment history or approval workflow is introduced. See the [selected implementation plan](docs/plans/2026-10-25-selective-blueprint-improvements.md).

## Observed local verification

All 628 backend tests and 270 frontend tests passed. Backend combined statement/branch coverage was 92.35%; frontend coverage met its configured thresholds. Static checks, formatting, production/test types and production builds passed.

The clean Windows package has 151 verified runtime files and an empty schema-17 seed. Both inventory verifiers, PowerShell 5.1/7 workflows and a packaged schema-16-to-17 upgrade rehearsal passed. Existing business rows, IDs, historical events and encrypted dummy Google connection bytes were retained in the synthetic rehearsal. Guarded local runtime replacement preserved the working database and Google connection bytes. See [0.5.26 validation](docs/VALIDATION_0.5.26.md).

These are observed local results. The newly published source revision's GitHub Actions result is separate and must be checked before Office publication. Actual Office-PC acceptance, physical printing, full assistive-technology checks and live Google transmission were not performed by these local gates.

## Scholar Office interface

Ink navigation, a warm workspace, cobalt controls, readable profiles and a four-step atomic editor retain the existing business rules and recovery workflow. The dashboard combines real registration history, affiliation columns, outcomes and embedded reports. The 0.5.25 status-chart/profile-readability improvements remain included. See the [interface implementation plan](docs/plans/2026-10-24-paper-office.md) and [readability plan](docs/plans/2026-10-25-profile-readability.md).

## Google Sheets reporting

Follow the [detailed Google Sheets setup guide](docs/GOOGLE_SHEETS_SETUP.md), including API activation, Desktop OAuth credentials, test-user approval, spreadsheet editing permission, connection and troubleshooting. Configure and sign in separately on each PC/Windows account. The app works locally without hosting.

The reporting tab has only these columns: No., Name, Age, Tenure, Department, Rank/position, Previous degree, Program, Delivering HEI, Grant type, Date started, Date ended, Extension, Status and Remarks. Each grant has its own row; profile information appears on the scholar's first row. CSV exports retain their separate full-detail format.

## Run and build

Use Windows x64, PowerShell 7, Python 3.14.7 x64 and Node.js 26.8.1 with the pinned requirements and frontend lockfile:

```powershell
pwsh -File ./desktop/build-split-release.ps1 -Python '<python-path>' -Node '<node-path>'
```

The build checks regressions and packages a clean Windows app in `desktop/release/Cathedra FSDP`. Use synthetic data for development and testing. See the [developer guide](docs/DEVELOPER_GUIDE.md).

## Documentation

- [Current specification and architecture](docs/current/README.md)
- [Backend schema](docs/current/BACKEND_SCHEMA.md)
- [Application flow](docs/current/APP_FLOW.md)
- [Technical requirements](docs/current/TECHNICAL_REQUIREMENTS.md)
- [Product requirements](docs/current/PRODUCT_REQUIREMENTS.md)
- [Office guide](docs/OFFICE_GUIDE.md)
- [Export schemas](docs/EXPORT_SCHEMAS.md)
- [0.5.26 validation](docs/VALIDATION_0.5.26.md)

## Office application downloads

Download the ready-to-use ZIP from [Cathedra FSDP Releases](https://github.com/sebas011/Cathedra-FSDP/releases/latest) after the current version's publication gates pass. Source downloads here are for development. Use the supported updater and preserve the existing Office database. Intended Office-PC acceptance remains a separate check.
