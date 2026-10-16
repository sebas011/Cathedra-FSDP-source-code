import { useId } from "react";
import type { AnalyticsRow } from "../types";

export type ChartOrder = "largest" | "smallest" | "name";

export function orderRows(rows: AnalyticsRow[], order: ChartOrder) {
  return [...rows].sort((first, second) => {
    const difference =
      order === "name"
        ? 0
        : order === "largest"
          ? second.count - first.count
          : first.count - second.count;
    return difference || first.label.localeCompare(second.label);
  });
}

export function countAxis(maximum: number) {
  const target = Math.max(1, maximum) / 4;
  const magnitude = 10 ** Math.floor(Math.log10(target));
  const step = Math.max(
    1,
    ([1, 2, 5, 10].find((value) => value * magnitude >= target) || 10) * magnitude,
  );
  const limit = Math.max(step, Math.ceil(maximum / step) * step);
  return {
    limit,
    ticks: Array.from({ length: Math.round(limit / step) + 1 }, (_, index) => index * step),
  };
}

function labelLines(label: string) {
  return label
    .split(/\s+/)
    .flatMap((word) => word.match(/.{1,13}/g) || [])
    .reduce<string[]>((lines, word) => {
      const last = lines.length - 1;
      if (last >= 0 && (lines[last] + " " + word).length <= 13) lines[last] += " " + word;
      else lines.push(word);
      return lines;
    }, []);
}

export default function AnalyticsChart({
  title,
  unit,
  rows,
  order,
}: {
  title: string;
  unit: string;
  rows: AnalyticsRow[];
  order: ChartOrder;
}) {
  const headingId = useId();
  const sorted = orderRows(rows, order);
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  const axis = countAxis(Math.max(0, ...rows.map((row) => row.count)));
  const plotLeft = 48,
    plotTop = 28,
    plotHeight = 240;
  const slotWidth = 94,
    plotWidth = Math.max(376, sorted.length * slotWidth);
  const width = plotLeft + plotWidth + 20;
  const slot = plotWidth / Math.max(1, sorted.length);
  const barWidth = Math.min(46, slot * 0.55);
  const labelHeight = Math.max(3, ...sorted.map((row) => labelLines(row.label).length)) * 16 + 30;
  return (
    <section className="analytics-card comparison-card" aria-labelledby={headingId}>
      <header className="dashboard-card-heading">
        <h2 id={headingId}>{title}</h2>
        <span className="analytics-total">
          {total.toLocaleString()} {unit.toLowerCase()}
        </span>
      </header>
      {!total ? (
        <div className="analytics-empty">No {unit.toLowerCase()} in this selection.</div>
      ) : (
        <>
          <div className="comparison-plot" role="region" aria-label={`${title} chart`} tabIndex={0}>
            <svg
              className="count-chart vertical-count-chart"
              style={{ minWidth: width }}
              viewBox={`0 0 ${width} ${plotTop + plotHeight + labelHeight}`}
              aria-hidden="true"
            >
              {axis.ticks.map((tick) => (
                <g key={tick}>
                  <line
                    x1={plotLeft}
                    x2={plotLeft + plotWidth}
                    y1={plotTop + plotHeight - (tick / axis.limit) * plotHeight}
                    y2={plotTop + plotHeight - (tick / axis.limit) * plotHeight}
                    className={tick === 0 ? "chart-baseline" : "chart-gridline"}
                  />
                  <text
                    x={plotLeft - 12}
                    y={plotTop + plotHeight - (tick / axis.limit) * plotHeight + 4}
                    textAnchor="end"
                    className="chart-tick"
                  >
                    {tick.toLocaleString()}
                  </text>
                </g>
              ))}
              {sorted.map((row, index) => (
                <g key={row.label}>
                  <title>
                    {row.label}: {row.count.toLocaleString()} {unit.toLowerCase()}
                  </title>
                  <text
                    x={plotLeft + (index + 0.5) * slot}
                    y={plotTop + plotHeight + 24}
                    textAnchor="middle"
                    className="chart-label"
                  >
                    {labelLines(row.label).map((line, lineIndex) => (
                      <tspan
                        key={lineIndex}
                        x={plotLeft + (index + 0.5) * slot}
                        dy={lineIndex ? 16 : 0}
                      >
                        {line}
                      </tspan>
                    ))}
                  </text>
                  <rect
                    x={plotLeft + (index + 0.5) * slot - barWidth / 2}
                    y={plotTop + plotHeight - (row.count / axis.limit) * plotHeight}
                    width={barWidth}
                    height={(row.count / axis.limit) * plotHeight}
                    rx={4}
                    className="chart-bar"
                  />
                  <text
                    x={plotLeft + (index + 0.5) * slot}
                    y={plotTop + plotHeight - (row.count / axis.limit) * plotHeight - 10}
                    textAnchor="middle"
                    className="chart-value"
                  >
                    {row.count.toLocaleString()}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <ul className="chart-text-values" aria-label={`${title}, ${unit.toLowerCase()}`}>
            {sorted.map((row) => (
              <li key={row.label}>
                <span>{row.label}</span>
                <strong>{row.count.toLocaleString()}</strong>
              </li>
            ))}
          </ul>
          <p className="chart-axis-caption">Number of {unit.toLowerCase()}</p>
        </>
      )}
    </section>
  );
}
