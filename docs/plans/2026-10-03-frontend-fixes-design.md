# Frontend reliability fixes — 0.5.3

Skills: brainstorming, senior-frontend and code-reviewer from the requested .claude folder. User authorization covers implementation. Use isolated source staging; no project-local Git repository is available.

Reuse the shared pending guard rather than introduce another router blocker or broad application state manager. The backup page owns the pending state, including its child recovery-review save. Block route navigation, unload and AppShell leave events through completion/status refresh. Release the guard explicitly for the successful restore sign-out. Freeze conflicting controls. Keep operation feedback separate from status-load failure and derive the heading/badge consistently.

Use a request sequence and unmount cleanup for readiness; disable refresh while pending. A sequence remains necessary for StrictMode and delayed responses. Accept only the current success/error. A broad query-library dependency is unnecessary.

Validate canonical grant terms before closing the editor. Compare against an immutable server baseline to preserve only unchanged imported terms belonging to the same saved grant. Constrained dropdowns would also prevent invalid new values, but complicate preserving existing imported values; keep the current editor and add precise validation feedback.

Verify route/unload/logout/exit guards, child review propagation, successful restore redirect, failed-operation recovery, request ordering/unmount, independent health feedback, and new/legacy grant validation. Run all frontend/backend tests, TypeScript/static checks and the desktop release build. Preserve source/runtime/database rollback backups, install while stopped, verify installed hashes and unchanged office data, then run synthetic installed checks and audit access restrictions. No new database migration.
