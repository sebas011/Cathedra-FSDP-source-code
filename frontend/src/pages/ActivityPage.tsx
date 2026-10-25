import TableRegion from "../components/TableRegion";
import PageHeading from "../components/PageHeading";
import { useEffect, useState } from "react";
import { getActivity } from "../api";
import { SkeletonTableRows } from "../components/PageSkeleton";
import type { ActivityEvent } from "../types";
import { formatRecordDateTime } from "../utils/dates";

export default function ActivityPage() {
  const [items, setItems] = useState<ActivityEvent[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try {
      setError("");
      setItems(await getActivity());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load activity history.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  return (
    <div className="stack-md management-page activity-page">
      <PageHeading
        title="Activity History"
        eyebrow="ADMINISTRATION"
        description="Review saved record and account changes. Backup and restore operations are not included."
        actions={
          <button className="btn secondary" disabled={loading} onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button
            className="btn secondary"
            type="button"
            disabled={loading}
            onClick={() => void load()}
          >
            Retry
          </button>
        </div>
      )}
      <section className="data-card">
        <div className="table-meta">Latest {items.length} recorded actions</div>
        <TableRegion label="Office activity history">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Person</th>
                <th>Area</th>
                <th>Action</th>
                <th>Changed fields</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonTableRows columns={5} />
              ) : error ? (
                <tr>
                  <td colSpan={5} className="empty-table">
                    Unable to load activity history.
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-table">
                    <strong>No activity recorded yet.</strong>
                    <span>New changes will appear here.</span>
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatRecordDateTime(item.created_at)}</td>
                    <td>{item.username || "System"}</td>
                    <td>{item.area}</td>
                    <td>
                      <strong>{item.action}</strong>
                    </td>
                    <td>{item.changed_fields.join(", ") || "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </TableRegion>
      </section>
    </div>
  );
}
