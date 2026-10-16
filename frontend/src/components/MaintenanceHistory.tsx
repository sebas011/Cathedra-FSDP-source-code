import { useEffect, useState } from "react";
import { request } from "../api/client";
import TableRegion from "./TableRegion";

type History = {
  items: { at: string; action: string; username: string; backup: string }[];
  total: number;
};
export default function MaintenanceHistory() {
  const [page, setPage] = useState(1),
    [data, setData] = useState<History | null>(null),
    [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    request<History>(`/maintenance/history?page=${page}&page_size=20`)
      .then((value) => {
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setError("Maintenance history could not be loaded. Retry to check it.");
      });
    return () => {
      active = false;
    };
  }, [page, revision]);
  return (
    <section className="data-card" aria-label="Maintenance history">
      <header className="section-heading">
        <div>
          <h2>Maintenance history</h2>
          <p>
            Private local records of backup and recovery actions. Actions from earlier versions may
            not be recorded.
          </p>
        </div>
        <button
          type="button"
          className="btn secondary"
          onClick={() => setRevision((value) => value + 1)}
        >
          Refresh history
        </button>
      </header>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading maintenance history…</p>}
      {data && (
        <>
          <TableRegion label="Maintenance history records">
            <table>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Action</th>
                  <th scope="col">Administrator</th>
                  <th scope="col">Backup</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length ? (
                  data.items.map((item, index) => (
                    <tr key={`${item.at}-${index}`}>
                      <td>{new Date(item.at).toLocaleString()}</td>
                      <td>{item.action}</td>
                      <td>{item.username}</td>
                      <td>{item.backup}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4}>No maintenance actions recorded on this page.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </TableRegion>
          <div className="action-group">
            <button
              type="button"
              className="btn secondary"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
            >
              Previous history
            </button>
            <span>
              Page {page} · {data.total} actions
            </span>
            <button
              type="button"
              className="btn secondary"
              disabled={page * 20 >= data.total}
              onClick={() => setPage((value) => value + 1)}
            >
              Next history
            </button>
          </div>
        </>
      )}
    </section>
  );
}
