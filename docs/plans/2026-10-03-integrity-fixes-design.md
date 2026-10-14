# Integrity fixes for Cathedra FSDP

Date: 3 October 2026. Scope: the three reproduced review findings.

## Decision and alternatives

Use an additive SQLite identity counter, atomic SQL revision increments, and a database-backed username uniqueness rule. This preserves scholar IDs, relationships, API payloads, passwords, and existing history.

Rebuilding scholars with AUTOINCREMENT would also prevent ID reuse, but requires rebuilding a parent table with active foreign keys. UUIDs would introduce new identity fields across the frontend and API. The counter is the smaller change: allocate scholar IDs using UPDATE ... RETURNING in the same transaction as the record insert. Seed its high-water mark from live scholars and historical scholar references, and track explicit inserts with a trigger so imports cannot lower the next ID.

## Migration and data flow

Migration 4 adds the counter and a unique index on SQLite lower(username). Detect pre-existing case-equivalent accounts first and refuse startup with an actionable error rather than rename, merge, disable, or discard accounts. New schemas carry the same index. API account creation hashes the password before obtaining BEGIN IMMEDIATE, checks availability inside the write transaction, and maps uniqueness failures to HTTP 409 with rollback. Login uses the same SQLite normalization on both sides of the comparison.

Program changes increment affected scholars' revisions with one SQL UPDATE using a participation subquery. Each affected scholar advances once, regardless of grant count. The increment and program mutation commit together. Failed program changes roll back both.

Counter increments roll back with failed scholar creation. Rolled-back IDs may be allocated again because no successful scholar or corresponding audit event was committed. Deleted committed scholars do not return IDs to the counter.

Backup/restore retains the counter in new snapshots. Old snapshots acquire it during staged migration before replacement. The legacy converter reseeds after copying preserved records. No existing ambiguous audit history is reassigned.

## Implementation plan

1. Add migration 4, schema index, and transactional ID allocator.
2. Use the allocator for new scholars; atomically advance revisions for program updates.
3. Serialize username checks/insertion and handle conflicts.
4. Add behavioral regressions for deletion/history/stale writes, historical high-water seeding, restart and backup/restore, interleaved program saves, multiple grants, username races, duplicate-account migration refusal, and rollback.
5. Run constrained backend regressions, Ruff, frontend regressions/type checks, and package verification in an isolated workspace.
6. Produce a tested 0.5.1 package, then install it into the authorized project folder with source/runtime archives and a verified database snapshot. Confirm that office data is unchanged during installation.

## Acceptance criteria

- Replacement scholars have new IDs; old updates/deletes cannot target them and history remains separate.
- Program edits always invalidate older scholar forms, including concurrent saves.
- Case-equivalent usernames cannot coexist after migration or concurrent API writes.
- Existing record/account/audit rows are preserved by migration.
- New and older supported backups remain verifiable and recoverable.
- All existing regressions and new integrity regressions pass.
- A staged executable contains the fixes; changing source alone does not change the installed executable.

No project-local Git repository exists, so no commit or Git worktree is created in the unrelated parent repository. The source workspace is isolated on disk.
