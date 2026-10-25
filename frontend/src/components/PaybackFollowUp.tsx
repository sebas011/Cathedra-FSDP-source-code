import { displayGrantStatus } from "../utils/statuses";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { downloadPayback, getPayback, type PaybackData } from "../api/payback";
import TableRegion from "./TableRegion";
import AssessmentDetails from "./AssessmentDetails";

const groups = [
  "Recorded Payback",
  "Payback review",
  "Payback pending contract",
  "In grace period",
  "Completion date missing",
  "Contract not completed",
  "Completed",
  "Did Not Avail",
];

export default function PaybackFollowUp() {
  const [params, setParams] = useSearchParams();
  const department = params.get("department") || "",
    year = params.get("start_academic_year") || "";
  const [data, setData] = useState<PaybackData | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const group = displayGrantStatus(params.get("contract_attention") ?? "Payback action");
  const setGroup = (value: string) => {
    const next = new URLSearchParams(params);
    if (value === "Payback action") next.delete("contract_attention");
    else next.set("contract_attention", value);
    setParams(next, { replace: true });
  };
  const [page, setPage] = useState(1);
  const scopeKey = JSON.stringify([department, year, group]);
  const previousScope = useRef(scopeKey);
  const effectivePage = previousScope.current === scopeKey ? page : 1;
  useEffect(() => {
    previousScope.current = scopeKey;
    setPage(1);
  }, [scopeKey]);
  const [exporting, setExporting] = useState(false);
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    void getPayback(department, year, group, effectivePage)
      .then((value) => {
        if (active) {
          const lastPage = Math.max(1, Math.ceil((value.total ?? value.items.length) / 50));
          if (effectivePage > lastPage) {
            setPage(lastPage);
            return;
          }
          setData(value);
        }
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "Unable to load contract follow-up.");
      });
    return () => {
      active = false;
    };
  }, [department, year, group, effectivePage, revision]);
  const rows = (data?.items || []).filter(
    (item) =>
      !group ||
      (group === "Payback action"
        ? ["Recorded Payback", "Payback review", "Payback pending contract"].includes(
            item.attention,
          )
        : displayGrantStatus(item.attention) === group),
  );
  const exportRows = async () => {
    setExporting(true);
    setError("");
    try {
      await downloadPayback(department, year, group);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to export follow-up.");
    } finally {
      setExporting(false);
    }
  };
  return (
    <section className="data-card" aria-label="Contract and payback assessment">
      <header className="section-heading">
        <div>
          <h2>Contract and payback assessment</h2>
          <p>
            {department || "All departments"} · {year || "All academic years"}
            {data && ` · As of ${data.as_of}`}
          </p>
        </div>
        <button
          type="button"
          className="btn secondary no-print"
          disabled={!data || exporting}
          onClick={() => void exportRows()}
        >
          {exporting ? "Preparing…" : "Export follow-up CSV"}
        </button>
      </header>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button
            className="btn secondary"
            type="button"
            onClick={() => setRevision((value) => value + 1)}
          >
            Retry contract assessment
          </button>
        </div>
      )}
      {!data && !error && <p role="status">Loading contract follow-up…</p>}
      {data && (
        <>
          <div className="filter-chips no-print" aria-label="Contract follow-up counts">
            {groups.slice(0, 5).map((value) => (
              <button
                type="button"
                className="filter-chip"
                key={value}
                onClick={() => {
                  setGroup(value);
                  setPage(1);
                }}
              >
                {value}: {data.scholar_counts[value] || 0} scholars
              </button>
            ))}
          </div>
          <label className="no-print">
            Contract assessment category
            <select
              value={group}
              onChange={(event) => {
                setGroup(event.target.value);
                setPage(1);
              }}
            >
              <option>Payback action</option>
              <option value="">All records</option>
              {groups.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <p>{data.total ?? rows.length} grant records</p>
          <TableRegion label="Contract assessment records">
            <table>
              <thead>
                <tr>
                  <th scope="col">Scholar</th>
                  <th scope="col">Program / year</th>
                  <th scope="col">Recorded status</th>
                  <th scope="col">Completion deadline</th>
                  <th scope="col">Grace ends</th>
                  <th scope="col">Payment progress</th>
                  <th scope="col">Follow-up</th>
                  <th scope="col" className="no-print">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {!rows.length ? (
                  <tr>
                    <td colSpan={8} className="empty-table">
                      No records in this category. Check “Completion date missing” for records that
                      cannot yet be assessed.
                    </td>
                  </tr>
                ) : (
                  rows.map((item) => (
                    <tr key={item.participation_id}>
                      <td>
                        <Link className="record-value" to={`/fsdp/${item.scholar_id}`}>
                          {item.scholar_name}
                        </Link>
                        <small>{item.department || "Not recorded"}</small>
                      </td>
                      <td className="record-value">
                        {item.program_name}
                        <small>{item.academic_year || "Year not recorded"}</small>
                      </td>
                      <td>{displayGrantStatus(item.recorded_status)}</td>
                      <td>
                        {item.completion_deadline_on ||
                          item.contract_completed_on ||
                          "Not recorded"}
                      </td>
                      <td>{item.grace_ends_on || "Not calculated"}</td>
                      <td>{item.payback_payment_status || "Not recorded"}</td>
                      <td className="assessment-cell">
                        <span
                          className={
                            [
                              "Recorded Payback",
                              "Payback review",
                              "Payback pending contract",
                            ].includes(item.attention)
                              ? "warning-chip"
                              : "status-chip"
                          }
                        >
                          {displayGrantStatus(item.attention)}
                        </span>
                        {item.days_remaining != null && (
                          <small>{item.days_remaining} days remaining</small>
                        )}
                        <AssessmentDetails
                          reason={item.assessment_reason}
                          assessedOn={item.assessment_as_of || data.as_of}
                          deadlineBasis={item.completion_deadline_source}
                        />
                      </td>
                      <td className="no-print">
                        <Link className="btn secondary" to={`/fsdp/${item.scholar_id}/edit`}>
                          Update contract
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </TableRegion>
          <div className="action-group no-print">
            <button
              type="button"
              className="btn secondary"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
            >
              Previous assessment
            </button>
            <span>Page {page}</span>
            <button
              type="button"
              className="btn secondary"
              disabled={page * 50 >= (data.total ?? rows.length)}
              onClick={() => setPage((value) => value + 1)}
            >
              Next assessment
            </button>
          </div>
        </>
      )}
    </section>
  );
}
