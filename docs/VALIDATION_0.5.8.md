# Cathedra FSDP 0.5.8 — First-launch connection fix

## Diagnosis

The supplied Edge screenshot shows ERR_CONNECTION_REFUSED. During inspection, the Cathedra Edge window was still running under its dedicated browser profile with `--edge-skip-compat-layer-relaunch`, its original parent process had ended, and port 8101 had no listener. The launcher waited for the original Edge process and incorrectly shut down the healthy local service when Edge relaunched through its Windows compatibility layer. Refresh could not restart the terminated service.

## Change

On Windows, follow the launched Edge process and its descendants and inspect their visible top-level windows. The initial process exiting no longer stops the service. Wait for the actual app window to appear, and stop after its windows disappear for two seconds. A temporary inspection failure does not count as window closure. Explicit application Exit remains supported. No browser security flags, permissions, database rules or UI features are changed.

## Validation

- 143 backend and launcher tests passed; 121 frontend tests passed.
- Regression tests cover initial Edge handoff, temporary relaunch after window creation, inspection errors, matching service identity, exclusive database ownership and shutdown resource ordering.
- Native Windows ownership inspection detected the surviving Cathedra window and its process family.
- Production build, packaged feature tests, persisted database integrity and 138 runtime inventory checks passed.
- Two fresh packaged browser launches use isolated databases and browser profiles; structured results are in WINDOW_STARTUP_0.5.8.json.

Guarded installation preserves the live schema-6 database without migration. A protected snapshot and source/runtime rollback archives are retained; installation hashes are in INSTALLATION_MANIFEST_0.5.8.json. The Office distribution remains unchanged.
