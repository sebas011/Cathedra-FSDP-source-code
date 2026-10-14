import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import GrantTypeChart from "../src/components/GrantTypeChart";

describe("grant type composition", () => {
  it("exposes the actual counts and proportions beside pie slices", () => {
    const { container } = render(<GrantTypeChart rows={[{label:"Scholarship",count:6},{label:"Study Leave",count:3},{label:"Other",count:1}]} order="largest" />);
    expect(screen.getByRole("region", {name:"Types of grant"})).toBeTruthy();
    expect(screen.getByText("10 grant records")).toBeTruthy();
    expect(screen.getAllByRole("listitem").map(item=>item.textContent)).toEqual(["Scholarship660%","Study Leave330%","Other110%"]);
    const paths = [...container.querySelectorAll("svg path")];
    expect(paths).toHaveLength(3);
    expect(paths[0].getAttribute("d")).toContain("A 92 92 0 1 1");
    expect(paths[1].getAttribute("d")).toContain("A 92 92 0 0 1");
    expect(paths.every(path=>!path.getAttribute("d")?.includes("NaN"))).toBe(true);
  });
  it("renders a complete circle when only one category has records", () => {
    const {container} = render(<GrantTypeChart rows={[{label:"Scholarship",count:5},{label:"Other",count:0}]} order="largest" />);
    expect(container.querySelectorAll("svg circle")).toHaveLength(1);
    expect(container.querySelectorAll("svg path")).toHaveLength(0);
    expect(screen.getAllByRole("listitem").map(item=>item.textContent)).toEqual(["Scholarship5100%","Other00%"]);
  });
  it("keeps each category color when the sort order changes", () => {
    const rows = [{label:"Scholarship",count:8},{label:"Other",count:2}];
    const {container, rerender} = render(<GrantTypeChart rows={rows} order="largest" />);
    const colors = () => Object.fromEntries([...container.querySelectorAll("svg path")].map(path=>[path.querySelector("title")?.textContent,path.getAttribute("fill")]));
    const before = colors();
    rerender(<GrantTypeChart rows={rows} order="name" />);
    expect(colors()).toEqual(before);
    expect(screen.getAllByRole("listitem")[0].textContent).toBe("Other220%");
  });
  it("handles an empty filtered selection without drawing invalid proportions", () => {
    const {container} = render(<GrantTypeChart rows={[{label:"Scholarship",count:0}]} order="name" />);
    expect(screen.getByText("No grant records in this selection.")).toBeTruthy();
    expect(container.querySelector("svg")).toBeNull();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
