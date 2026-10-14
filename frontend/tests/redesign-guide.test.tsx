import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ProductGuidePage from "../src/pages/ProductGuidePage";

describe("offline guide search", () => {
  const open = () => render(<MemoryRouter><ProductGuidePage /></MemoryRouter>);
  it("searches article body text and opens the matching answer", () => {
    open();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "BitLocker" } });
    expect(screen.getByRole("heading", { name: "Check protection of the working computer" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Add and update a scholar" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Check protection of the working computer" }).closest("details")?.open).toBe(true);
  });
  it("combines topic and search and lets staff recover from no matches", () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "Reports" }));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "BitLocker" } });
    expect(screen.getByRole("heading", { name: "No guidance matches your search" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear search and topic" }));
    expect(screen.queryByRole("heading", { name: "No guidance matches your search" })).toBeNull();
    expect(screen.getByRole("button", { name: "All topics" }).getAttribute("aria-pressed")).toBe("true");
  });
  it("keeps recovery guidance and links accessible even with no search results", () => {
    open();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "nonexistent phrase" } });
    expect(screen.getByRole("heading", { name: "Before restoring office records" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open backups" }).getAttribute("href")).toBe("/backup-export");
    expect(screen.getByText(/keep the data folder and safety backups unchanged/)).toBeTruthy();
  });
});
