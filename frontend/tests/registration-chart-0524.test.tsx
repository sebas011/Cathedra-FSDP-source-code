import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RegistrationChart from "../src/components/RegistrationChart";
import { formatRegistrationDate, registrationTimestamp } from "../src/utils/dates";

const series = {
  timezone: "Asia/Manila",
  starts_on: "2025-11-01",
  ends_on: "2026-10-24",
  before_period: 50,
  plotted: 53,
  rows: [
    { month: "2025-11", count: 1, cumulative: 51 },
    { month: "2025-12", count: 0, cumulative: 51 },
    { month: "2026-01", count: 2, cumulative: 53 },
  ],
};

describe("actual registration history", () => {
  it("shows the cumulative baseline, zero months, and accessible exact counts", () => {
    const { container } = render(<RegistrationChart series={series} total={53} />);
    expect(screen.getByRole("region", { name: "Scholar registrations" })).toBeTruthy();
    expect(container.querySelector(".registration-summary strong")?.textContent).toBe("53");
    fireEvent.click(screen.getByText("View registration data"));
    expect(screen.getByRole("region", { name: "Scholar registration data" }).tabIndex).toBe(0);
    const table = screen.getByRole("table");
    expect(within(table).getByText("2025-12").closest("tr")?.textContent).toBe("2025-12051");
    expect(within(table).getByText("2026-01").closest("tr")?.textContent).toBe("2026-01253");
    const points = [...container.querySelectorAll("circle.registration-point")];
    expect(points[0].getAttribute("cy")).toBe(points[1].getAttribute("cy"));
    expect(Number(points[2].getAttribute("cy"))).toBeLessThan(Number(points[1].getAttribute("cy")));
    expect(screen.queryByText(/unavailable or future/)).toBeNull();
  });
  it("aligns recent-record dates with the Manila registration month", () => {
    expect(formatRegistrationDate("2026-09-30T16:00:00", "en-GB")).toBe("01 Oct 2026");
    expect(formatRegistrationDate("2026-09-30 15:59:59", "en-GB")).toBe("30 Sept 2026");
    expect(formatRegistrationDate("2026-10-01T00:00:00+08:00", "en-GB")).toBe("01 Oct 2026");
    expect(registrationTimestamp("2026-09-30T16:00:00")).toBe("2026-09-30T16:00:00.000Z");
    expect(formatRegistrationDate("invalid")).toBe("Not recorded");
    expect(formatRegistrationDate(null)).toBe("Not recorded");
  });
  it("reports timestamps omitted from the plot without reducing the scope total", () => {
    render(<RegistrationChart series={series} total={55} />);
    expect(
      screen.getByText("2 profiles have an unavailable or future registration timestamp."),
    ).toBeTruthy();
  });
  it("draws a truthful zero series without invalid coordinates", () => {
    const empty = {
      ...series,
      before_period: 0,
      plotted: 0,
      rows: series.rows.map((row) => ({ ...row, count: 0, cumulative: 0 })),
    };
    const { container } = render(<RegistrationChart series={empty} total={0} />);
    expect(container.querySelector("polyline")?.getAttribute("points")).not.toMatch(/NaN|Infinity/);
    expect(
      [...container.querySelectorAll("circle")].every(
        (point) => point.getAttribute("cy") === "184",
      ),
    ).toBe(true);
  });
});
