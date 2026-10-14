import TableRegion from "../components/TableRegion";
import PageHeading from "../components/PageHeading";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getMaintenanceStatus } from "../api";
import PageSkeleton from "../components/PageSkeleton";

import type { MaintenanceStatus } from "../types";

const when = (value: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "No backup yet";

export default function SystemReadinessPage() {
  const [status, setStatus] = useState<MaintenanceStatus | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const sequence = useRef(0);
  const load = async () => {
    const current = ++sequence.current;
    setLoading(true); setStatus(null); setError("");
    try {
      const result = await getMaintenanceStatus();
      if (current === sequence.current) setStatus(result);
    } catch (caught) {
      if (current === sequence.current) setError(caught instanceof Error ? caught.message : "Unable to check system readiness.");
    } finally { if (current === sequence.current) setLoading(false); }
  };
  useEffect(() => { void load(); return () => { sequence.current += 1; }; }, []);
  const healthy = status?.database_status === "healthy";
  const recentBackup = status?.backup_due === false;

  return <div className="stack-md">
    <PageHeading title="Office Pre-flight Check" description="Check the local database, backup age and recovery readiness before making major changes." actions={<button className="btn secondary" disabled={loading} onClick={() => void load()}>Refresh Check</button>} />
    {error && <div className="notice error" role="alert">Readiness could not be checked: {error} Please retry before relying on this page.</div>}
    {!status ? error ? null : <PageSkeleton label="Checking the local office workspace" variant="dashboard" /> : <>
      <section className="metric-grid three" aria-label="Readiness totals">
        <div className="metric-card"><span>Database connection</span><strong className={healthy ? "green" : "amber"}>{healthy ? "Available" : "Check"}</strong><small>{status.database_file}</small></div>
        <div className="metric-card"><span>Recent local backup</span><strong className={recentBackup ? "green" : "amber"}>{recentBackup ? "Within seven days" : "Review"}</strong><small>{when(status.latest_backup_at)}</small></div>
        <div className="metric-card"><span>FSDP records</span><strong>{status.fsdp_records}</strong><small>Scholar records stored locally</small></div>
        
      </section>
      <section className="data-card"><div className="section-heading"><div><span className="eyebrow">Checklist</span><h2>Before you proceed</h2><p>These checks are local. A database connection and saved backup do not prove a successful off-device restore.</p></div></div><TableRegion label="Readiness checklist"><table><thead><tr><th>Check</th><th>Status</th><th>What to do</th><th className="right">Action</th></tr></thead><tbody>
        <tr><td><strong>Database connection</strong></td><td><span className={healthy ? "ok-chip" : "warning-chip"}>{healthy ? "Available" : "Needs attention"}</span></td><td>{healthy ? "The local database answered this check." : "Open Backup & Export and refresh the database status."}</td><td className="right"><Link className="btn secondary" to="/backup-export">Open Backups</Link></td></tr>
        <tr><td><strong>Backup age</strong></td><td><span className={recentBackup ? "ok-chip" : "warning-chip"}>{recentBackup ? "Recent" : "Review"}</span></td><td>{recentBackup ? `Latest local backup: ${when(status.latest_backup_at)}.` : "Create and download a verified backup before major changes."}</td><td className="right"><Link className="btn secondary" to="/backup-export">Create Backup</Link></td></tr>
        <tr><td><strong>Disk space</strong></td><td><span className={status.storage_warning ? "warning-chip" : "ok-chip"}>{status.storage_warning ? "Low" : "Available"}</span></td><td>{status.storage_warning ? "Move a protected copy off this PC and ask an administrator to review older backups." : "No low-storage warning was detected."}</td><td className="right"><Link className="btn secondary" to="/backup-export">Review Backups</Link></td></tr>
        <tr><td><strong>Restore rehearsal</strong></td><td><span className="warning-chip">Not recorded here</span></td><td>Confirm a recent isolated restore test separately. This page does not certify that backups were restored.</td><td className="right"><Link className="btn secondary" to="/office-guide">Open Guide</Link></td></tr>
      </tbody></table></TableRegion></section>
    </>}
  </div>;
}
