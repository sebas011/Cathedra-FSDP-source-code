import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import AnalyticsChart, { countAxis, orderRows } from "../src/components/AnalyticsChart";

describe("dashboard charts", () => {
  const rows = [
    { label: "CAS", count: 3 },
    { label: "CCS", count: 7 },
    { label: "CBMA", count: 3 },
  ];
  it("sorts without changing API data and breaks ties consistently", () => {
    expect(orderRows(rows, "largest").map((row) => row.label)).toEqual(["CCS", "CAS", "CBMA"]);
    expect(orderRows(rows, "smallest").map((row) => row.label)).toEqual(["CAS", "CBMA", "CCS"]);
    expect(orderRows(rows, "name").map((row) => row.label)).toEqual(["CAS", "CBMA", "CCS"]);
    expect(rows[0].label).toBe("CAS");
  });
  it("exposes values as text, not only colored bars", () => {
    render(<AnalyticsChart title="Departments" unit="Scholars" rows={rows} order="largest" />);
    expect(screen.getByRole("region", { name: "Departments chart" })).toBeTruthy();
    expect(screen.getAllByRole("listitem")[0].textContent).toBe("CCS7");
    expect(screen.getByText("13 scholars")).toBeTruthy();
  });
  it("provides a truthful empty state", () => {
    render(<AnalyticsChart title="Outcomes" unit="Grant records" rows={[]} order="name" />);
    expect(screen.getByText("No grant records in this selection.")).toBeTruthy();
  });
  it("draws vertical bars from zero with visible counts and full text alternatives", () => {
    const { container } = render(
      <AnalyticsChart title="Colleges" unit="Scholars" rows={rows} order="largest" />,
    );
    const bars = Array.from(container.querySelectorAll("rect.chart-bar"));
    expect(bars).toHaveLength(3);
    expect(new Set(bars.map((bar) => bar.getAttribute("width"))).size).toBe(1);
    expect(Number(bars[0].getAttribute("height"))).toBeGreaterThan(
      Number(bars[1].getAttribute("height")),
    );
    expect(
      bars.map((bar) => Number(bar.getAttribute("y")) + Number(bar.getAttribute("height"))),
    ).toEqual([268, 268, 268]);
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "CCS7",
      "CAS3",
      "CBMA3",
    ]);
  });
  it.each([0, 1, 4, 19, 126, 1300])(
    "uses a zero baseline and whole-number count ticks for %s",
    (maximum) => {
      const axis = countAxis(maximum);
      expect(axis.ticks[0]).toBe(0);
      expect(axis.limit).toBeGreaterThanOrEqual(maximum);
      expect(axis.ticks.at(-1)).toBe(axis.limit);
      expect(axis.ticks.every(Number.isInteger)).toBe(true);
      expect(axis.ticks.length).toBeLessThanOrEqual(6);
    },
  );
  it("does not draw zero records as a nonzero bar", () => {
    render(
      <AnalyticsChart
        title="Empty department"
        unit="Scholars"
        rows={[{ label: "CAS", count: 0 }]}
        order="name"
      />,
    );
    expect(screen.getByText("No scholars in this selection.")).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
