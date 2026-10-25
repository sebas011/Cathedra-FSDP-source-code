import type { ParticipationRead } from "../types";
import { useEffect, useRef } from "react";
import { displayGrantStatus } from "../utils/statuses";
import { applicationIdentity, applicationPeriod } from "../utils/grantApplications";

const value = (text: string | null | undefined) => text || "Not recorded";
const period = (term: string | null, year: string | null) =>
  [term, year].filter(Boolean).join(" ") || "Not recorded";
const yearOrder = (grant: ParticipationRead) =>
  Number(grant.start_academic_year?.match(/^\d{4}/)?.[0] || 0);
const termOrder = (grant: ParticipationRead) =>
  ["1st", "2nd", "3rd", "Summer"].indexOf(grant.start_term || "");
const latestFirst = (a: ParticipationRead, b: ParticipationRead) =>
  yearOrder(b) - yearOrder(a) || termOrder(b) - termOrder(a) || b.id - a.id;
export function groupAnnualGrants(grants: ParticipationRead[]) {
  const groups = new Map<string, ParticipationRead[]>();
  for (const grant of grants) {
    const key = applicationIdentity(grant);
    groups.set(key, [...(groups.get(key) || []), grant]);
  }
  return [...groups.values()]
    .map((group) => group.sort(latestFirst))
    .sort((a, b) => latestFirst(a[0], b[0]));
}
export default function ProgramGrantHistory({ grants }: { grants: ParticipationRead[] }) {
  const history = useRef<HTMLDivElement>(null);
  const setExpanded = (open: boolean) => {
    for (const entry of history.current?.querySelectorAll("details") || []) entry.open = open;
  };
  useEffect(() => {
    let saved: Array<[HTMLDetailsElement, boolean]> = [];
    const expand = () => {
      if (saved.length) return;
      saved = Array.from(history.current?.querySelectorAll("details") || []).map((item) => [
        item,
        item.open,
      ]);
      for (const [item] of saved) item.open = true;
    };
    const restore = () => {
      for (const [item, open] of saved) item.open = open;
      saved = [];
    };
    window.addEventListener("beforeprint", expand);
    window.addEventListener("afterprint", restore);
    return () => {
      restore();
      window.removeEventListener("beforeprint", expand);
      window.removeEventListener("afterprint", restore);
    };
  }, []);
  return (
    <div ref={history}>
      <div className="grant-history-disclosure">
        <header className="profile-section-title grant-history-heading">
          <div className="grant-history-title">
            <h2>Grant history</h2>
            <span className="profile-record-count">
              {grants.length} {grants.length === 1 ? "record" : "records"}
            </span>
          </div>
          <div className="grant-history-controls no-print">
            <button className="btn secondary" type="button" onClick={() => setExpanded(true)}>
              Expand all grants
            </button>
            <button className="btn secondary" type="button" onClick={() => setExpanded(false)}>
              Collapse all grants
            </button>
          </div>
        </header>
        <div className="profile-grant-history">
          {groupAnnualGrants(grants).map((group, applicationIndex) => (
            <details
              className="program-history"
              key={applicationIdentity(group[0])}
              open={applicationIndex === 0}
            >
              <summary>
                <span>
                  <span className="eyebrow">
                    Application {String(applicationIndex + 1).padStart(2, "0")}
                  </span>
                  <strong className="record-value">{group[0].name}</strong>
                  <span className="program-history-meta">
                    {applicationPeriod(group)} · {group.length}{" "}
                    {group.length === 1 ? "grant record" : "annual grant records"}
                  </span>
                </span>
                <span className="status-chip">{displayGrantStatus(group[0].status)}</span>
              </summary>
              <div className="program-history-records">
                {group.map((grant, grantIndex) => (
                  <details
                    className="profile-grant annual-grant"
                    key={grant.id}
                    open={grantIndex === 0}
                  >
                    <summary>
                      <span>
                        <strong>{grant.start_academic_year || "Year not recorded"}</strong>
                        <span className="program-history-meta">
                          {grant.program_category || "Category not recorded"} ·{" "}
                          {grant.grant_type === "Others"
                            ? value(grant.grant_other)
                            : value(grant.grant_type)}{" "}
                          · <span className="record-value">{value(grant.delivering_hei)}</span>
                        </span>
                      </span>
                      <span className="status-chip">{displayGrantStatus(grant.status)}</span>
                    </summary>
                    <dl className="profile-grant-facts">
                      <div>
                        <dt>Started</dt>
                        <dd>{period(grant.start_term, grant.start_academic_year)}</dd>
                      </div>
                      <div>
                        <dt>Ending period</dt>
                        <dd>{period(grant.end_term, grant.end_academic_year)}</dd>
                      </div>
                      <div>
                        <dt>Previously recorded completion date</dt>
                        <dd>{value(grant.contract_completed_on)}</dd>
                      </div>
                      <div>
                        <dt>Program start date</dt>
                        <dd>{value(grant.start_date)}</dd>
                      </div>
                      <div>
                        <dt>Allowed duration</dt>
                        <dd>
                          {grant.allowed_duration_years
                            ? `${grant.allowed_duration_years} years`
                            : "Not recorded"}
                        </dd>
                      </div>
                      <div>
                        <dt>Completion deadline</dt>
                        <dd>
                          {grant.completion_deadline_on ||
                            grant.completion_due_on ||
                            "Not calculated"}
                        </dd>
                      </div>
                      <div>
                        <dt>Payment progress</dt>
                        <dd>{grant.payback_payment_status || "Not recorded"}</dd>
                      </div>
                      <div>
                        <dt>Graduation date</dt>
                        <dd>{value(grant.graduation_date)}</dd>
                      </div>
                      <div>
                        <dt>Case status</dt>
                        <dd>{grant.case_status || "Open"}</dd>
                      </div>
                      <div>
                        <dt>Grace period ends</dt>
                        <dd>{grant.grace_ends_on || "Not calculated"}</dd>
                      </div>
                      <div>
                        <dt>Contract assessment</dt>
                        <dd>
                          {displayGrantStatus(grant.payback_attention || "Completion date missing")}
                        </dd>
                      </div>
                      {grant.extension && (
                        <div>
                          <dt>Extension</dt>
                          <dd className="record-value">{grant.extension}</dd>
                        </div>
                      )}
                    </dl>
                    {grant.remarks && (
                      <div className="profile-remarks">
                        <strong>Grant remarks</strong>
                        <p className="record-value">{grant.remarks}</p>
                      </div>
                    )}
                  </details>
                ))}
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}
