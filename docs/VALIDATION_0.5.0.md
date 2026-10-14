# Cathedra FSDP 0.5.0 — validation

Date: 3 October 2026. Scope: isolated FSDP redesign, not Faculty or old ScholarDesk.

| Check | Executed result |
| --- | --- |
| Constrained Python build inputs | Pass |
| Ruff | Pass |
| Backend regressions | 105 passed; two existing deprecation warnings |
| Frontend regressions | 94 passed in 17 files |
| Application and test TypeScript checks | Pass |
| Vite production build | Pass; route-split output retained |
| Packaged executable workflow verification | Pass, including persisted database checks |
| Complete packaged runtime manifest | Pass, 142 files, version 0.5.0 |
| Browser review | Synthetic records only; sign-in, dashboard, directory, profile, new/edit form, monitoring, legacy review, reports, verification, backups, readiness, accounts, settings, history and guide render |
| Report interaction | Department CAS returns two synthetic scholars; view switch preserves filter and active count |
| Entry interaction | Grant editor opens and cancels; entry omits workspace tabs; existing save/draft/conflict workflows covered by regression tests |
| Mobile navigation | Open/close verified; Escape restores focus to Open menu |
| Narrow layout | Final pass measured an actual 320 CSS-pixel viewport (303 px content plus scrollbar): dashboard, directory, profile, edit form and all ten secondary workspaces have scrollWidth equal to clientWidth. Data tables scroll within their own regions. A body minimum-width overflow found during review was corrected and rebuilt |
| Wide layout | Requested 1440 px viewport; profile, form, report and dashboard visually checked |

## Measured token contrast

| Pair | Ratio |
| --- | --- |
| White on primary green | 7.31:1 |
| Main text on white | 14.00:1 |
| Secondary text on canvas | 5.47:1 |
| Warning text on warning tint | 6.03:1 |
| Error text on error tint | 6.20:1 |
| Information text on information tint | 6.15:1 |
| Field border on white | 3.18:1 |

These measurements cover the named tokens, not every rendered pixel or a formal accessibility certification. Physical printing, an actual 200% browser zoom pass on this redesign and separate-office-PC acceptance are not newly certified by this run.

## Data and installation

No database migration or office-record correction is part of this redesign. The preview uses a separate disposable data folder. Installation and independent installed-package checks are recorded after execution below; do not treat a staged build as an installed release.

Installed into `C:\Users\rodia\Desktop\Project\Cathedra-FSDP` after protected source/runtime archives and a verified SQLite snapshot. Final snapshot: `data/backups/cathedra-protected-before-0.5.0-20261003-122718.db`. The live database SHA-256 is identical before and after replacement. Only the FSDP installation was changed.

Independent installed executable verification passes. The built-in Windows PowerShell 5.1 office smoke test passes startup, authentication, record persistence, backup/restore and shutdown with Python/Node absent from PATH. This is a local rehearsal, not a claim that a separate clean office PC was tested. Final permission inspection reports 2,973 checked paths, the existing owner/SYSTEM/Administrators restriction and zero violations.

Evidence: `INSTALLATION_MANIFEST_0.5.0.json`, the installed `release-manifest.json`, and staging logs `build-050-final.log`, `installed-verification-final.log`, `office-smoke-final.log`, `permission-check-final.log`. The earlier intermediate package was replaced by the final reflow-corrected package; use the final logs for release evidence.
