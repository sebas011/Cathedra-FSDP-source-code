# Cathedra FSDP 0.5.24

Source code for the local Windows FSDP scholar administration application. Database schema: 16.

This repository contains backend, frontend, desktop launcher/updater, tests, build tools and technical documentation. Working scholar records, accounts, backups, OAuth credentials, Google connection tokens, executables and private installation history are excluded.

## Paper & Ink Scholar Office

The working React application now uses ink navigation, a warm canvas and cobalt controls; redesigned profiles, a four-step atomic editor and real registration analytics retain the existing business rules and recovery behavior. The database remains schema16. See the [implementation plan](docs/plans/2026-10-24-paper-office.md).

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
- [0.5.24 validation](docs/VALIDATION_0.5.24.md)

## Office application downloads

Download the ready-to-use ZIP from [Cathedra FSDP Releases](https://github.com/sebas011/Cathedra-FSDP/releases/latest). Source downloads here are for development. Use the supported updater and preserve the existing Office database. Local validation and GitHub Actions are separate evidence; intended Office-PC acceptance remains a separate check.
