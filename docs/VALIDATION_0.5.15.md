# Validation: 0.5.15

Completed on the development PC, 9 October 2026, Asia/Manila. Schema remains 11; no destructive correction migration was introduced.

- Backend: **255 tests passed**. Ruff and pinned dependency checks passed. New coverage includes previous/other-degree and third-party claims, qualification identity, Ph.D./Ed.D., valid/invalid/future dates, ambiguous numeric dates, conflicting statements, optional remark saves and authoritative recorded graduation.
- Frontend: **131 tests passed** across 27 files. Application/test TypeScript checks and production build passed. API adapter tests preserve category filters with and without pagination. Existing UI regression coverage passed; this release changes Guide copy and API behavior, without a visual redesign.
- Payback: paged/unpaged JSON and complete CSV agree on selected records. Scope-wide category summaries remain intact. Recorded pending-contract precedence and Summer preservation are covered.
- Exports/documentation: actual CSV writer headers match the new machine-readable contracts, including current outcome columns. Formula-leading and multiline profile/grant remarks remain distinct. Current version identities, migration ceiling, local links and export prose/header agreement passed the new build gate.
- Preservation rehearsal: upgraded a private copy through schema 11 twice safely; **126 scholars, 126 grants and 215 education entries** retained. Grant data, requirements, accounts, IDs, existing manual education/years and exact stored edit timestamps remained intact under the documented migration allowances. The original database was unchanged.
- Read-only education review: hash-preservation test passed. On the upgraded private copy, 95 linked entries were checked and zero lacked accepted current evidence. This is not proof of every achievement's factual accuracy. No automatic deletion/correction occurred.
- Package: clean installer seed, production frontend, Windows version resource, executable startup/authenticated persistence and **140 runtime files** verified. Additional synthetic packaged checks reproduced the repaired cases: unrelated degree and future date skipped; dotted abbreviation year retained; Summer kept; pending precedence and JSON/CSV filtering correct; normal exit succeeded.
- Office updater: disposable 0.5.14-to-0.5.15 update verified with `database_replaced=false`, protected snapshot and retained old runtime. Source database hash preserved. This does not certify the actual Office PC.

Full test output contained two existing test-runtime deprecation warnings; locked frontend installation also reported dependency/install-script warnings. They did not fail these checks. No claim of a new dependency-advisory scan is made.

Private build/rehearsal/install receipts and recoverable source/runtime archives remain outside the release payload. The current update includes application files and an empty new-install seed, never a working Office/development database. Existing manual achievements are preserved; the new read-only candidate tool supports individual review.

Actual Office cold launch, clean-PC operation, keyboard/zoom/assistive-technology acceptance, device encryption, signing and remote CI evidence remain open in [Office acceptance](current/OFFICE_ACCEPTANCE.md).

See [implementation plan](plans/2026-10-09-audit-corrections.md), [current decisions](current/DECISIONS.md), [export reference](EXPORT_SCHEMAS.md) and [current documentation](current/README.md).
