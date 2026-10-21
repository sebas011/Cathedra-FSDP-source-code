import { afterEach, expect, test, vi } from "vitest";
import {
  configureGoogleSheets,
  connectGoogleSheets,
  disconnectGoogleSheets,
  getGoogleSheetsStatus,
  syncGoogleSheets,
} from "../src/api/googleSheets";

afterEach(() => vi.useRealTimers());

test("Google API calls keep the chosen target in configure and require report replacement for sync", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 204 }));
  const configuration = { installed: { client_id: "synthetic", client_secret: "synthetic-only" } };
  await getGoogleSheetsStatus();
  await configureGoogleSheets("synthetic-sheet-id", configuration);
  await configureGoogleSheets("another-sheet-id");
  await connectGoogleSheets();
  await syncGoogleSheets();
  await disconnectGoogleSheets();
  expect(fetcher.mock.calls.map(([url]) => String(url).split("/api/v1")[1])).toEqual([
    "/google-sheets",
    "/google-sheets/configure",
    "/google-sheets/configure",
    "/google-sheets/connect",
    "/google-sheets/sync",
    "/google-sheets/connection",
  ]);
  expect(JSON.parse(String(fetcher.mock.calls[1][1]?.body))).toEqual({
    spreadsheet: "synthetic-sheet-id",
    client_configuration: configuration,
  });
  expect(JSON.parse(String(fetcher.mock.calls[2][1]?.body))).toEqual({
    spreadsheet: "another-sheet-id",
  });
  expect(JSON.parse(String(fetcher.mock.calls[4][1]?.body))).toEqual({ replace_report: true });
  expect(fetcher.mock.calls[5][1]?.method).toBe("DELETE");
  expect(Object.values(localStorage)).toEqual([]);
  expect(Object.values(sessionStorage)).toEqual([]);
});

test("a Google sync has enough time for the bounded Google requests and still times out", async () => {
  vi.useFakeTimers();
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(
    (_url, init) =>
      new Promise((_resolve, reject) => {
        init!.signal!.addEventListener("abort", () => reject(new Error("Aborted")), { once: true });
      }),
  );
  const operation = syncGoogleSheets();
  const rejected = expect(operation).rejects.toThrow("did not confirm");
  await vi.advanceTimersByTimeAsync(119999);
  expect(fetcher.mock.calls[0][1]?.signal?.aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(1);
  await rejected;
  expect(fetcher.mock.calls[0][1]?.signal?.aborted).toBe(true);
});
