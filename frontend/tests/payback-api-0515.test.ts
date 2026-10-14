import { beforeEach, expect, test, vi } from "vitest";
import { getPayback } from "../src/api/payback";

const client = vi.hoisted(() => ({ request: vi.fn(), download: vi.fn() }));
vi.mock("../src/api/client", () => client);
beforeEach(() => client.request.mockReset());

test("unpaged assessment keeps explicit filters", async () => {
  client.request.mockResolvedValue({ items: [] });
  await getPayback("CAS", "2025-2026", "Payback action");
  const url = new URL(client.request.mock.calls[0][0], "http://localhost");
  expect(url.searchParams.get("attention")).toBe("Payback action");
  expect(url.searchParams.get("department")).toBe("CAS");
  expect(url.searchParams.has("page")).toBe(false);
});

test("paged assessment keeps the same category and bounded page size", async () => {
  client.request.mockResolvedValue({ items: [] });
  await getPayback("CAS", "2025-2026", "Payback pending contract", 2);
  const url = new URL(client.request.mock.calls[0][0], "http://localhost");
  expect(url.searchParams.get("attention")).toBe("Payback pending contract");
  expect(url.searchParams.get("page")).toBe("2");
  expect(url.searchParams.get("page_size")).toBe("50");
});
