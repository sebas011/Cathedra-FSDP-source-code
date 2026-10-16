# Current business-rule decisions

Baseline: source 0.5.21/schema 15.

15 October 2026: document-copy availability is independent Available/Not available/Not recorded for paper and electronic copies, with no inference from requirements and no document upload feature. Degree, Certification and Enhancement describe program category separately from grant funding. Annual copies remain in their application; New application separates later enrollment in the same program. Completion clearing is limited to the same scholar/program/application, while NULL-key historical grants retain their established same-program behavior until reviewed and explicitly assigned. Migration 14 does not guess application boundaries. The directory uses the full stored name for alphabetical order; no surname parser is inferred.

12 October 2026 user findings: Completed is the current outcome; Graduated remains compatible input and historical migration terminology. Open/Closed is a separate per-grant case state. Record text is uppercase for scholar/program/education/remarks/Office Log entries; account credentials remain unchanged. Graduation date is optional and clears on annual copying. Office Log records general document receipts/transfers separately from administrator change history. See [the approved implementation plan](../plans/2026-10-12-user-findings.md).

11 October 2026 review remediation: existing equivalent program identities are never automatically merged or renamed. New canonical identity keys enforce Unicode-consistent uniqueness. Explicit education-year edits and clears persist; historical rows lacking edit provenance retain established inference until edited. Prepared report printing uses an immutable scoped snapshot; native Ctrl+P describes currently loaded content. Summer remains distinct from 3rd.

| Decision | Authority / history | Implemented constraint |
|---|---|---|
| Keep Summer | 0.5.10 findings added Summer; owner explicitly reconfirmed it on 9 October 2026 | 1st, 2nd, 3rd, Summer or unrecorded; do not map Summer to 3rd. Supersedes the earlier three-term-only request. |
| Education evidence is conservative | Audit F1–F3 and approval to implement | Current-program claim only; full calendar dates validated; optional remarks remain saveable; recorded outcomes stay manual. |
| Preserve existing education | Existing manual correction/removal rules and lack of full extraction provenance | No automatic deletion/mass repair; use private candidate review and existing editor controls. |
| Assessment summaries retain scope | Existing Dashboard category-card behavior | Category summaries remain department/year-wide; attention filters select table/export rows before paging. |
| Outcome and case state are independent | Owner's 12 October answer: keep case status separate | Per-grant outcome can be Completed or Payback while its case is Open or Closed; closure does not infer graduation, repayment or a date. |
| Uppercase business record entry | Owner's 12 October answer: uppercase record text; credentials unchanged | Normalize submitted editable record text; preserve stored historical identities until explicitly edited and retain canonical system enum labels. |
| Optional graduation facts | 12 October finding 5 and lightweight validation requirement | Store an optional date per grant, separate from contract completion. Completed status can add linked education without remark parsing. |
| Annual copy clears dates | 12 October finding 9 | New annual grant identity starts On Going/Open; all actual dates and extension are cleared, while remarks are retained for review. |
| General Office Log | 12 October finding 12 | Append-only receipt/transfer register with authenticated author and optional scholar snapshot; no document-upload storage or replacement of activity auditing. |

Sources: [0.5.10 findings](../plans/2026-10-07-user-findings.md), audit review (local historical evidence; excluded from this source snapshot), [correction plan](../plans/2026-10-09-audit-corrections.md). Future changes must record which decision they supersede.

15 October 2026: the owner confirmed independent completion/payback for each repeated application to a program. This supersedes the broad same-program clearance rule for explicitly assigned applications. Annual entries within one application still share completion. Existing NULL application groups preserve their previous grouping until deliberately reviewed and reassigned; migration never invents enrollment boundaries. Education remains consolidated by qualification/program with manual decisions preserved.

The owner clarified that “for work” means the Office Log form, so no work-history module is added. Confirmed log saves close the editor; uncertain saves retain the retry draft. Independent optional hard/soft-copy availability uses Available, Not available and Not recorded. Program category is separate from grant funding. These are documented in the [15 October plan](../plans/2026-10-15-office-entry-and-applications.md).

## 16 October 2026 audit decisions

- Transferred and Withdrawn remain eligible for calculated payback review when unfinished and beyond the three-year grace period. Completed applications still clear calculated review; recorded Payback remains visible.
- Optional/custom record facts remain permitted under the essential Name/Program Applied policy.
- Idle locking after 30 minutes preserves mounted drafts for same-account reauthentication. Background polling does not count as activity.
- Automatic retention applies only to automatic unpinned copies, never manual or pinned backups. A failed pre-delete recovery copy prevents deletion.
