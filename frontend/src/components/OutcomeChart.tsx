import { displayGrantStatus } from "../utils/statuses";
import { useId } from "react";
import { orderRows, type ChartOrder } from "./AnalyticsChart";
import type { AnalyticsRow } from "../types";

const outcomeColors: Record<string, string> = {
  "On Going": "var(--brand)",
  Incomplete: "var(--warning)",
  Completed: "var(--success, #087365)",
  Graduated: "var(--success, #087365)",
  Payback: "var(--danger)",
  "Payback pending contract": "var(--warning)",
  Transferred: "var(--info)",
  Withdrawn: "var(--danger)",
  "Did Not Avail": "var(--muted)",
};

export default function OutcomeChart({ rows, order }: { rows: AnalyticsRow[]; order: ChartOrder }) {
  const heading = useId();
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  const sorted = orderRows(rows, order);
  const circumference = 2 * Math.PI * 86;
  let offset = 0;
  const segments = sorted.map((row) => {
    const length = total ? (row.count / total) * circumference : 0;
    const start = offset;
    offset += length;
    return { ...row, start, length, gap: Math.min(2, length * 0.08) };
  });
  return (
    <section className="analytics-card composition-card outcome-card" aria-labelledby={heading}>
      <header className="dashboard-card-heading">
        <h2 id={heading}>Current scholar status</h2>
        <span className="analytics-total">{total.toLocaleString()} total</span>
      </header>
      {!total ? (
        <p className="analytics-empty">No scholars in this selection.</p>
      ) : (
        <div className="composition-chart-body">
          <svg className="outcome-donut" viewBox="0 0 240 240" aria-hidden="true">
            <circle cx="120" cy="120" r="86" fill="none" stroke="var(--border)" strokeWidth="27" />
            {segments
              .filter((row) => row.count > 0)
              .map((row) => (
                <circle
                  key={row.label}
                  cx="120"
                  cy="120"
                  r="86"
                  fill="none"
                  stroke={outcomeColors[row.label] || "var(--muted)"}
                  strokeWidth="27"
                  strokeDasharray={`${row.length - row.gap} ${circumference - row.length + row.gap}`}
                  strokeDashoffset={-row.start}
                  transform="rotate(-90 120 120)"
                >
                  <title>
                    {displayGrantStatus(row.label)}: {row.count}
                  </title>
                </circle>
              ))}
            <text x="120" y="116" textAnchor="middle" className="donut-total">
              {total.toLocaleString()}
            </text>
            <text x="120" y="140" textAnchor="middle" className="donut-caption">
              scholars
            </text>
          </svg>
          <ul
            className="outcome-legend composition-legend"
            aria-label="Current scholar status, scholars"
          >
            {sorted.map((row) => (
              <li key={row.label}>
                <i
                  aria-hidden="true"
                  style={{ background: outcomeColors[row.label] || "var(--muted)" }}
                />
                <span>{displayGrantStatus(row.label)}</span>
                <strong>{row.count.toLocaleString()}</strong>
                <small>
                  {((row.count / total) * 100).toLocaleString(undefined, {
                    maximumFractionDigits: 1,
                  })}
                  %
                </small>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
