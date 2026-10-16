import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { useDirectoryValue, useDirectoryScroll } from "../src/hooks/useDirectoryMemory";

const account = vi.hoisted(() => ({ getCurrentUser: vi.fn(() => ({ id: 1 })) }));
vi.mock("../src/api", () => account);

function Directory() {
  const [search, setSearch] = useDirectoryValue<string>("fsdp:search", "");
  const [page, setPage] = useDirectoryValue<number>("fsdp:page", 1);
  return (
    <>
      <input
        aria-label="Search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <button onClick={() => setPage((value) => value + 1)}>Next</button>
      <span>Page {page}</span>
    </>
  );
}

test("directory search and page survive a profile round trip but stay account scoped", () => {
  account.getCurrentUser.mockReturnValue({ id: 1 });
  const first = render(<Directory />);
  fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Maria" } });
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  first.unmount();
  const returned = render(<Directory />);
  expect((screen.getByLabelText("Search") as HTMLInputElement).value).toBe("Maria");
  expect(screen.getByText("Page 2")).toBeTruthy();
  returned.unmount();
  account.getCurrentUser.mockReturnValue({ id: 2 });
  render(<Directory />);
  expect((screen.getByLabelText("Search") as HTMLInputElement).value).toBe("");
  expect(screen.getByText("Page 1")).toBeTruthy();
});

test("malformed directory state falls back safely", () => {
  account.getCurrentUser.mockReturnValue({ id: 1 });
  sessionStorage.setItem("cathedra-directory:1:fsdp:page", "-5");
  sessionStorage.setItem("cathedra-directory:1:fsdp:search", "not json");
  render(<Directory />);
  expect(screen.getByText("Page 1")).toBeTruthy();
  expect((screen.getByLabelText("Search") as HTMLInputElement).value).toBe("");
});

test("scroll position is restored only after the directory is ready", () => {
  account.getCurrentUser.mockReturnValue({ id: 1 });
  sessionStorage.setItem("cathedra-directory:1:fsdp:scroll", "320");
  const frame = vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
    callback(0);
    return 1;
  });
  const scroll = vi.spyOn(window, "scrollTo");
  function Position({ ready }: { ready: boolean }) {
    useDirectoryScroll("fsdp", ready);
    return null;
  }
  const view = render(<Position ready={false} />);
  expect(scroll).not.toHaveBeenCalled();
  view.rerender(<Position ready={true} />);
  expect(scroll).toHaveBeenCalledWith({ top: 320, behavior: "instant" });
  view.unmount();
  frame.mockRestore();
  scroll.mockRestore();
});
