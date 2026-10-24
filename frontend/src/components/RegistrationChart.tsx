import { useId } from "react";
import type { FsdpAnalytics } from "../types";
import { countAxis } from "./AnalyticsChart";
import TableRegion from "./TableRegion";

export default function RegistrationChart({
  series,
  total,
}: {
  series: NonNullable<FsdpAnalytics["registration_series"]>;
  total: number;
}) {
  const heading = useId();
  const rows = series.rows;
  const axis = countAxis(Math.max(0, ...rows.map((row) => row.cumulative)));
  const left = 46,
    top = 20,
    height = 164,
    width = 620,
    plotWidth = 548;
  const x = (index: number) => left + (index * plotWidth) / Math.max(1, rows.length - 1);
  const y = (count: number) => top + height - (count / axis.limit) * height;
  const points = rows.map((row, index) => `${x(index)},${y(row.cumulative)}`).join(" ");
  const monthLabel = (month: string) =>
    new Date(month + "-01T00:00:00Z").toLocaleDateString(undefined, {
      month: "short",
      timeZone: "UTC",
    });
  const periodLabel = (date: string) =>
    new Date(date + "T00:00:00Z").toLocaleDateString(undefined, {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  const unplotted = Math.max(0, total - series.plotted);
  return (
    <section className="analytics-card registration-card" aria-labelledby={heading}>
      <header className="dashboard-card-heading">
        <div>
          <span className="dashboard-kicker">Registration history</span>
          <h2 id={heading}>Scholar registrations</h2>
        </div>
        <span className="analytics-total">
          {periodLabel(series.starts_on)} – {periodLabel(series.ends_on)}
        </span>
      </header>
      <div className="registration-summary">
        <strong>{series.plotted.toLocaleString()}</strong>
        <span>profiles registered · cumulative</span>
      </div>
      <div
        className="registration-plot"
        role="region"
        aria-label="Cumulative scholar registrations chart"
        tabIndex={0}
      >
        <svg viewBox={`0 0 ${width} ${top + height + 42}`} aria-hidden="true">
          {axis.ticks.map((tick) => (
            <g key={tick}>
              <line
                x1={left}
                x2={left + plotWidth}
                y1={y(tick)}
                y2={y(tick)}
                className={tick ? "chart-gridline" : "chart-baseline"}
              />
              <text x={left - 12} y={y(tick) + 4} textAnchor="end" className="chart-tick">
                {tick.toLocaleString()}
              </text>
            </g>
          ))}
          {rows.length > 0 && <polyline points={points} className="registration-line" />}
          {rows.map((row, index) => (
            <g key={row.month}>
              <circle cx={x(index)} cy={y(row.cumulative)} r="3" className="registration-point">
                <title>
                  {row.month}: {row.count} added, {row.cumulative} cumulative
                </title>
              </circle>
              <text x={x(index)} y={top + height + 26} textAnchor="middle" className="chart-tick">
                {monthLabel(row.month)}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <details className="chart-data-disclosure">
        <summary>View registration data</summary>
        <TableRegion label="Scholar registration data">
          <table>
            <caption>
              Registrations by month · {series.timezone} · through {series.ends_on}
            </caption>
            <thead>
              <tr>
                <th scope="col">Month</th>
                <th scope="col">Added</th>
                <th scope="col">Cumulative</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.month}>
                  <th scope="row">{row.month}</th>
                  <td>{row.count.toLocaleString()}</td>
                  <td>{row.cumulative.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      </details>
      {unplotted > 0 && (
        <p className="registration-unplotted">
          {unplotted.toLocaleString()} {unplotted === 1 ? "profile has" : "profiles have"} an
          unavailable or future registration timestamp.
        </p>
      )}
    </section>
  );
}
