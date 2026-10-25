import { useEffect, useState } from "react";
import { getScholarHistory } from "../api/fsdp";
import type { ActivityEvent, PagedResult } from "../types";
import { formatRecordDateTime } from "../utils/dates";
import ChangeDetails from "./ChangeDetails";

export default function ScholarHistory({ scholarId }: { scholarId: number }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<PagedResult<ActivityEvent> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!open) return;
    let active = true;
    setResult(null);
    setError("");
    getScholarHistory(scholarId, page)
      .then((value) => {
        if (active) setResult(value);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "Unable to load history.");
      });
    return () => {
      active = false;
    };
  }, [scholarId, page, open, attempt]);
  return (
    <section className="profile-panel no-print">
      <button
        className="btn secondary"
        type="button"
        aria-expanded={open}
        aria-controls="scholar-change-history"
        onClick={() => setOpen((value) => !value)}
      >
        Change history
      </button>
      {open && (
        <div id="scholar-change-history" className="stack-md">
          {error ? (
            <div role="alert">
              {error}
              <button
                className="btn secondary"
                type="button"
                onClick={() => setAttempt((value) => value + 1)}
              >
                Retry
              </button>
            </div>
          ) : !result ? (
            <p role="status">Loading change history…</p>
          ) : (
            <>
              {!result.total ? (
                <p>No attributable changes recorded.</p>
              ) : (
                <ol>
                  {result.items.map((item) => (
                    <li key={item.id}>
                      <strong>
                        {item.operation} · {item.area}
                      </strong>
                      <p>
                        {item.username || "Unknown editor"} ·{" "}
                        {formatRecordDateTime(item.created_at)}
                      </p>
                      <p>
                        {item.changed_fields
                          .map((field) => field.replaceAll("_", " "))
                          .join(", ") || "No field details"}
                      </p>
                      <ChangeDetails changes={item.change_details} />
                    </li>
                  ))}
                </ol>
              )}
              {result.total > 20 && (
                <nav aria-label="Change history pages" className="action-group">
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={page === 1}
                    onClick={() => setPage((value) => value - 1)}
                  >
                    Previous
                  </button>
                  <span>
                    Page {page} of {Math.ceil(result.total / 20)}
                  </span>
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={page * 20 >= result.total}
                    onClick={() => setPage((value) => value + 1)}
                  >
                    Next
                  </button>
                </nav>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
