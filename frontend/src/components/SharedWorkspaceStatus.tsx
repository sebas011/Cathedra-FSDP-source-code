import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  getSharedWorkspaceStatus,
  sharedWorkspaceChangedEvent,
  type SharedWorkspaceStatus as WorkspaceStatus,
} from "../api/sharedWorkspace";
import "../shared-workspace.css";

const labels = {
  disconnected: "Shared storage not joined",
  ready: "Shared copy saved",
  dirty: "Changes waiting to sync",
  pending: "Sync needs confirmation",
  rejoin_required: "Shared copy needs review",
};

export default function SharedWorkspaceStatus({ admin }: { admin: boolean }) {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const location = useLocation();
  useEffect(() => {
    let active = true;
    let pending = false;
    const controller = new AbortController();
    const refresh = async () => {
      if (pending || controller.signal.aborted) return;
      pending = true;
      try {
        const next = await getSharedWorkspaceStatus(controller.signal);
        if (active) {
          setStatus(next);
          setUnavailable(false);
        }
      } catch {
        if (active && !controller.signal.aborted) setUnavailable(true);
      } finally {
        pending = false;
      }
    };
    const update = () => void refresh();
    void refresh();
    const timer = window.setInterval(update, 30000);
    window.addEventListener(sharedWorkspaceChangedEvent, update);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener(sharedWorkspaceChangedEvent, update);
    };
  }, [location.pathname]);
  if (!status?.configured && !unavailable) return null;
  const label = unavailable
    ? "Shared status unavailable"
    : status && !status.joined && status.state === "ready"
      ? "Shared storage not joined"
      : labels[status!.state];
  const title = `${label}${status?.last_synced_at ? ` · Last sync ${new Date(status.last_synced_at).toLocaleString()}` : ""}`;
  const content = (
    <>
      <span className="shared-status-dot" aria-hidden="true" />
      <span>{label}</span>
    </>
  );
  return admin ? (
    <Link
      to="/backup-export#shared-workspace"
      className={`shared-status no-print shared-status-${unavailable ? "pending" : status?.state}`}
      title={title}
    >
      {content}
    </Link>
  ) : (
    <span
      className={`shared-status no-print shared-status-${unavailable ? "pending" : status?.state}`}
      title={title}
    >
      {content}
    </span>
  );
}
