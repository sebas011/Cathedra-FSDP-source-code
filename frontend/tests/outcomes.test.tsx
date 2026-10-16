import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import OutcomeChart from "../src/components/OutcomeChart";

describe("grant outcome visualization", () => {
  it("provides a named region and sorted text values without relying on color", () => {
    render(
      <OutcomeChart
        rows={[
          { label: "Graduated", count: 2 },
          { label: "On Going", count: 6 },
        ]}
        order="largest"
      />,
    );
    expect(screen.getByRole("region", { name: "Current scholar status" })).toBeTruthy();
    expect(screen.getByText("8 total")).toBeTruthy();
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "On Going675%",
      "Completed225%",
    ]);
  });
  it("handles a selection with zero grant records", () => {
    render(<OutcomeChart rows={[{ label: "Graduated", count: 0 }]} order="name" />);
    expect(screen.getByText("No scholars in this selection.")).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
  });
  it("preserves unknown recorded outcomes and exposes small shares as text", () => {
    render(
      <OutcomeChart
        rows={[
          { label: "On Going", count: 99 },
          { label: "Recorded status", count: 1 },
        ]}
        order="largest"
      />,
    );
    const values = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(values).toEqual(["On Going9999%", "Recorded status11%"]);
  });
});
