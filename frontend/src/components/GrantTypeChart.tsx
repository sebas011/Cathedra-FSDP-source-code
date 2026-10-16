import { useId } from "react";
import type { AnalyticsRow } from "../types";
import { orderRows, type ChartOrder } from "./AnalyticsChart";

const colors = ["var(--brand)", "#428c79", "#b48435", "#597f94", "#758178", "#816b91"];

export default function GrantTypeChart({
  rows,
  order,
}: {
  rows: AnalyticsRow[];
  order: ChartOrder;
}) {
  const heading = useId();
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  const sorted = orderRows(rows, order);
  const labels = [...rows].map((row) => row.label).sort((a, b) => a.localeCompare(b));
  const color = (label: string) => colors[labels.indexOf(label) % colors.length];
  let angle = -Math.PI / 2;
  const slices = sorted
    .filter((row) => row.count > 0)
    .map((row) => {
      const start = angle;
      angle += (row.count / total) * Math.PI * 2;
      const point = (value: number) =>
        `${120 + 92 * Math.cos(value)} ${120 + 92 * Math.sin(value)}`;
      return {
        ...row,
        path: `M 120 120 L ${point(start)} A 92 92 0 ${row.count / total > 0.5 ? 1 : 0} 1 ${point(angle)} Z`,
      };
    });
  return (
    <section className="analytics-card composition-card grant-type-card" aria-labelledby={heading}>
      <header className="dashboard-card-heading">
        <h2 id={heading}>Types of grant</h2>
        <span className="analytics-total">{total.toLocaleString()} grant records</span>
      </header>
      {!total ? (
        <p className="analytics-empty">No grant records in this selection.</p>
      ) : (
        <div className="composition-chart-body">
          <svg className="composition-pie" viewBox="0 0 240 240" aria-hidden="true">
            {slices.length === 1 ? (
              <circle cx="120" cy="120" r="92" fill={color(slices[0].label)}>
                <title>
                  {slices[0].label}: {slices[0].count}
                </title>
              </circle>
            ) : (
              slices.map((slice) => (
                <path key={slice.label} d={slice.path} fill={color(slice.label)}>
                  <title>
                    {slice.label}: {slice.count}
                  </title>
                </path>
              ))
            )}
          </svg>
          <ul
            className="outcome-legend composition-legend"
            aria-label="Types of grant, grant records"
          >
            {sorted.map((row) => (
              <li key={row.label}>
                <i aria-hidden="true" style={{ background: color(row.label) }} />
                <span>{row.label}</span>
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
