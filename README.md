# Cathedra FSDP 0.5.21

Source code for the local Windows FSDP scholar administration application. Database schema: 15.

This repository includes the backend, frontend, desktop launcher/updater, automated tests, build tools and current technical documentation. It excludes Office databases, accounts, backups, logs, packaged executables and private installation history.

## Run and build

Use Windows x64, PowerShell 7, Python 3.14.7 x64 and Node.js 26.8.1. Build with the pinned requirements and frontend lockfile:

```powershell
pwsh -File ./desktop/build-split-release.ps1 -Python '<python-path>' -Node '<node-path>'
```

The build performs regression checks, builds the frontend and packages a clean Windows application in `desktop/release/Cathedra FSDP`. See the [developer guide](docs/DEVELOPER_GUIDE.md) for verification and development details. Use synthetic data for development and testing.

## Documentation

- [Current specification and architecture](docs/current/README.md)
- [Backend schema](docs/current/BACKEND_SCHEMA.md)
- [Application flow](docs/current/APP_FLOW.md)
- [Technical requirements](docs/current/TECHNICAL_REQUIREMENTS.md)
- [Product requirements](docs/current/PRODUCT_REQUIREMENTS.md)
- [Office guide](docs/OFFICE_GUIDE.md)
- [Export schemas](docs/EXPORT_SCHEMAS.md)

## Office app downloads

Ready-to-use updates are published separately under [Cathedra FSDP Releases](https://github.com/sebas011/Cathedra-FSDP/releases/latest). Download the application ZIP under Assets. Source downloads from this repository are for development, not Office updates. Always preserve the existing Office database and use the supported updater.

## Validation

The 0.5.21 local build passed 494 unique backend cases across complete/focused runs and 220 frontend tests, static/format/type checks, packaged workflow and synthetic upgrade/recovery checks. See docs/VALIDATION_0.5.21.md for execution details. GitHub Actions is included; remote results must be checked separately. Actual Office-PC acceptance remains a separate step.
