import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageHeading from "../src/components/PageHeading";


describe("shared page heading", () => {
  it("exposes one page title and preserves its action", () => {
    render(<PageHeading title="Scholars" eyebrow="FSDP" actions={<button type="button">Add scholar</button>} />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "Scholars" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Add scholar" })).toBeTruthy();
  });
  it("does not render empty descriptions or action containers", () => {
    const { container } = render(<PageHeading title="Reports" />);
    expect(container.querySelector("p")).toBeNull();
    expect(container.querySelector(".action-group")).toBeNull();
  });
});
