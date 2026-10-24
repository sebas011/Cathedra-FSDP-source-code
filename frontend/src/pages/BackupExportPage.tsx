import MaintenanceHistory from "../components/MaintenanceHistory";
import UnsavedChangesDialog from "../components/UnsavedChangesDialog";
import { useUnsavedChanges } from "../hooks/useUnsavedChanges";
import { useNavigate } from "react-router-dom";
import PageHeading from "../components/PageHeading";
import BackupReviewPanel from "../components/BackupReviewPanel";
import GoogleSheetsPanel from "../components/GoogleSheetsPanel";
import ConfirmationDialog from "../components/ConfirmationDialog";
import { useEffect, useRef, useState } from "react";
import {
  clearSession,
  createDatabaseBackup,
  deleteDatabaseBackup,
  downloadDatabaseBackup,
  downloadExport,
  getCurrentUser,
  getMaintenanceStatus,
  restoreDatabase,
  setBackupProtection,
} from "../api";
import PageSkeleton from "../components/PageSkeleton";

import type { BackupResult, MaintenanceStatus } from "../types";

const formatBytes = (bytes: number) =>
  bytes < 1024
    ? `${bytes} B`
    : bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
const formatDate = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
      )
    : "No backup yet";
const exports = [
  {
    key: "education",
    title: "Education background",
    description: "One row per education entry. Use a database backup for complete recovery.",
    filename: "cathedra-education.csv",
  },
  {
    key: "fsdp",
    title: "FSDP directory",
    description: "Scholars and their program participation records.",
    filename: "cathedra-fsdp.csv",
  },
] as const;
type BackupConfirmation = { action: "restore" | "delete" | "unpin"; filename: string };

export default function BackupExportPage() {
  const navigate = useNavigate();
  const isAdmin = getCurrentUser()?.role === "admin";
  const [historyOpen, setHistoryOpen] = useState(false);
  const [status, setStatus] = useState<MaintenanceStatus | null>(null);
  const [error, setError] = useState("");
  const [statusError, setStatusError] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [sheetsBusy, setSheetsBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeExport, setActiveExport] = useState<string | null>(null);
  const [selectedBackup, setSelectedBackup] = useState("");
  const [confirmation, setConfirmation] = useState<BackupConfirmation | null>(null);
  const operationLock = useRef(false);
  const sequence = useRef(0);
  const [loading, setLoading] = useState(false);
  const operationPending = busy || reviewBusy || sheetsBusy || activeExport !== null;
  const { blocker, allowLeave } = useUnsavedChanges(null, operationPending);
  const selected = status?.backups.find((item) => item.filename === selectedBackup);

  const load = async () => {
    const current = ++sequence.current;
    setLoading(true);
    try {
      setStatusError("");
      const result = await getMaintenanceStatus();
      if (current !== sequence.current) return;
      setStatus(result);
      setSelectedBackup((value) =>
        value && result.backups.some((item) => item.filename === value)
          ? value
          : result.backups[0]?.filename || "",
      );
    } catch (caught) {
      if (current === sequence.current) {
        setStatus(null);
        setStatusError(
          caught instanceof Error ? caught.message : "Unable to read database status.",
        );
      }
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    return () => {
      sequence.current += 1;
    };
  }, []);

  const makeBackup = async () => {
    if (operationPending || loading || operationLock.current) return;
    operationLock.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const result: BackupResult = await createDatabaseBackup();
      setNotice(`${result.filename} created (${formatBytes(result.size_bytes)}).`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create database backup.");
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };
  const requestConfirmation = (action: BackupConfirmation["action"]) => {
    if (operationPending || loading || operationLock.current || !selected) return;
    if (action === "delete" && selected.protected !== false) return;
    if (action === "unpin" && !selected.pinned) return;
    setConfirmation({ action, filename: selected.filename });
  };
  const restore = async (filename: string) => {
    if (
      operationPending ||
      loading ||
      operationLock.current ||
      !status?.backups.some((item) => item.filename === filename)
    )
      return;
    operationLock.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      await restoreDatabase(filename);
      allowLeave();
      clearSession();
      navigate("/login", { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to restore the selected backup.");
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };
  const downloadBackup = async () => {
    if (operationPending || loading || operationLock.current) return;
    if (!selectedBackup) return;
    operationLock.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      await downloadDatabaseBackup(selectedBackup);
      setNotice(
        "Backup downloaded. Move it to a protected USB drive or another device, then keep it private.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to download the selected backup.",
      );
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };
  const deleteBackup = async (filename: string) => {
    if (operationPending || loading || operationLock.current) return;
    if (status?.backups.find((item) => item.filename === filename)?.protected !== false) return;
    operationLock.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      await deleteDatabaseBackup(filename);
      setNotice("The selected older backup was deleted. Protected backups were not changed.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete the selected backup.");
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };
  const changeProtection = async (filename: string, pinned: boolean) => {
    if (operationPending || loading || operationLock.current) return;
    const backup = status?.backups.find((item) => item.filename === filename);
    if (
      !backup ||
      backup.pinned === undefined ||
      backup.filename.startsWith("cathedra-backup-before-restore-")
    )
      return;
    operationLock.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      await setBackupProtection(filename, pinned);
      setNotice(
        !pinned
          ? "This backup is no longer manually protected. The newest backup remains protected."
          : "This backup is protected from deletion.",
      );
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to change backup protection.");
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };
  const confirmAction = () => {
    if (!confirmation || operationPending || loading || operationLock.current) return;
    const { action, filename } = confirmation;
    setConfirmation(null);
    if (action === "restore") void restore(filename);
    else if (action === "delete") void deleteBackup(filename);
    else void changeProtection(filename, false);
  };
  const exportCsv = async (key: (typeof exports)[number]["key"], filename: string) => {
    if (operationPending || loading || operationLock.current) return;
    operationLock.current = true;
    setActiveExport(key);
    setNotice("");
    setError("");
    try {
      await downloadExport(key, filename);
      setNotice(`${filename} downloaded.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to export CSV.");
    } finally {
      operationLock.current = false;
      setActiveExport(null);
    }
  };

  if (!status && !statusError)
    return <PageSkeleton label="Loading backup and export status" variant="dashboard" />;
  return (
    <div className="stack-md management-page maintenance-page">
      <ConfirmationDialog
        open={confirmation !== null}
        title={
          confirmation?.action === "restore"
            ? "Restore this backup?"
            : confirmation?.action === "delete"
              ? "Permanently delete this backup?"
              : "Remove backup protection?"
        }
        description={
          confirmation?.action === "restore"
            ? "Cathedra will first create a safety backup of the current records. All sessions will be signed out."
            : confirmation?.action === "delete"
              ? `Permanently delete ${confirmation.filename}? This cannot be undone. Keep an off-device copy before removing a local backup.`
              : "Remove this backup's manual protection? It may then be deleted by an administrator unless it is the newest backup."
        }
        confirmLabel={
          confirmation?.action === "restore"
            ? "Restore backup"
            : confirmation?.action === "delete"
              ? "Delete backup"
              : "Remove protection"
        }
        cancelLabel={
          confirmation?.action === "restore"
            ? "Keep current records"
            : confirmation?.action === "delete"
              ? "Keep backup"
              : "Keep protection"
        }
        confirmDisabled={operationPending || loading}
        onConfirm={confirmAction}
        onCancel={() => setConfirmation(null)}
      />
      <UnsavedChangesDialog
        blocker={blocker}
        pending={operationPending}
        pendingTitle="Finishing the operation"
        pendingDescription="A backup, restore, export, Google connection, or recovery review is still being processed. Wait for confirmation before leaving; leaving does not cancel the operation."
      />
      <PageHeading
        title="Backup & Export"
        eyebrow="SYSTEM MAINTENANCE"
        description="Review local data, create a safe snapshot, restore a verified backup, or download directory data."
        actions={
          <button
            className="btn secondary"
            type="button"
            disabled={operationPending || loading}
            onClick={() => void load()}
          >
            Refresh status
          </button>
        }
      />
      {statusError && (
        <div className="notice error" role="alert">
          {statusError}
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice success" role="status">
          {notice}
        </div>
      )}
      {status?.backup_due && (
        <div className="notice" role="status">
          A local backup is due: none has been saved in the last seven days.{" "}
          {isAdmin
            ? "Create a snapshot and keep a private off-device copy."
            : "Ask an administrator to create a snapshot."}
        </div>
      )}
      {status?.storage_warning && (
        <div className="notice error" role="alert">
          This PC has limited free space. Move a verified backup to protected storage, then ask an
          administrator to review older local backups.
        </div>
      )}
      <section className="maintenance-status-card">
        <div className="maintenance-status-copy">
          <span className="eyebrow">Database status</span>
          <h2>
            {!statusError && !loading && status?.database_status === "healthy"
              ? "Database connection is available"
              : statusError
                ? "Database status unavailable"
                : loading
                  ? "Checking database connection"
                  : "Database connection needs attention"}
          </h2>
          <p>
            {status
              ? `${status.database_file} · ${formatBytes(status.database_size_bytes)}`
              : "Loading current database details…"}
          </p>
        </div>
        <span
          className={`health-pill ${!loading && !statusError && status?.database_status === "healthy" ? "healthy" : "pending"}`}
        >
          <i />
          {!loading && !statusError && status?.database_status === "healthy"
            ? "Connected"
            : statusError
              ? "Unavailable"
              : loading
                ? "Checking"
                : "Needs attention"}
        </span>
      </section>
      <nav className="profile-section-nav no-print" aria-label="Backup and export sections">
        <a href="#create-backup">Create backup</a>
        {isAdmin && <a href="#restore-backup">Download &amp; restore</a>}
        <a href="#directory-exports">Directory exports</a>
        {isAdmin && <a href="#google-reporting">Google Sheets report</a>}
      </nav>
      <section className="maintenance-counts" aria-label="Record counts">
        <div>
          <span>FSDP records</span>
          <strong>{status?.fsdp_records ?? "—"}</strong>
        </div>
      </section>
      <section className="maintenance-grid">
        <article className="maintenance-card backup-card" id="create-backup">
          <div>
            <span className="eyebrow">Local database backup</span>
            <h2>Create a timestamped snapshot</h2>
            <p>
              Backups are not deleted automatically. Keep a separate protected copy before major
              changes.
            </p>
          </div>
          <dl>
            <div>
              <dt>Stored backups</dt>
              <dd>{status?.backup_count ?? "—"}</dd>
            </div>
            <div>
              <dt>Latest backup</dt>
              <dd>{formatDate(status?.latest_backup_at ?? null)}</dd>
            </div>
            <div>
              <dt>Backup storage</dt>
              <dd>
                {status?.backup_storage_bytes !== undefined
                  ? formatBytes(status.backup_storage_bytes)
                  : "—"}
              </dd>
            </div>
            <div>
              <dt>Free disk space</dt>
              <dd>
                {status?.free_storage_bytes !== undefined
                  ? formatBytes(status.free_storage_bytes)
                  : "—"}
              </dd>
            </div>
          </dl>
          <button
            className="btn primary"
            type="button"
            disabled={operationPending || loading || !status || !isAdmin}
            onClick={() => void makeBackup()}
          >
            {busy ? "Working…" : isAdmin ? "Create Backup" : "Administrator creates backups"}
          </button>
        </article>
        {isAdmin && (
          <article className="maintenance-card backup-card account-sensitive" id="restore-backup">
            <div>
              <span className="eyebrow">Backup recovery &amp; transfer</span>
              <h2>Keep a second copy</h2>
              <p>
                Choose a saved backup to download or restore. Downloads contain personnel records
                and account data; store them privately on another device. Restoring signs everyone
                out.
              </p>
            </div>
            <select
              aria-label="Backup to download or restore"
              value={selectedBackup}
              onChange={(event) => setSelectedBackup(event.target.value)}
              disabled={!status?.backups.length || operationPending || loading}
            >
              {status?.backups.map((item) => (
                <option key={item.filename} value={item.filename}>
                  {formatDate(item.created_at)} · {formatBytes(item.size_bytes)}
                  {item.protected ? " · Protected" : ""}
                </option>
              ))}
            </select>
            <p>
              {selected?.protected !== false
                ? "This safety, newest, or pinned backup cannot be deleted here."
                : "Older backups can be removed only after you confirm a protected off-device copy exists."}
            </p>
            <div className="action-row">
              <button
                className="btn secondary"
                type="button"
                disabled={!selectedBackup || !status || operationPending || loading}
                onClick={() => void downloadBackup()}
              >
                {busy ? "Working…" : "Download Selected Backup"}
              </button>
              <button
                className="btn secondary"
                type="button"
                disabled={!selectedBackup || operationPending || loading}
                onClick={() => requestConfirmation("restore")}
              >
                {busy ? "Working…" : "Restore Selected Backup"}
              </button>
              <button
                className="btn secondary"
                type="button"
                disabled={
                  !selected ||
                  selected.pinned === undefined ||
                  selected.filename.startsWith("cathedra-backup-before-restore-") ||
                  operationPending ||
                  loading
                }
                onClick={() => {
                  if (selected?.pinned) requestConfirmation("unpin");
                  else if (selected) void changeProtection(selected.filename, true);
                }}
              >
                {selected?.pinned ? "Unpin Backup" : "Pin Backup"}
              </button>
              <button
                className="btn secondary danger"
                type="button"
                disabled={!selected || selected.protected !== false || operationPending || loading}
                onClick={() => requestConfirmation("delete")}
              >
                Delete Older Backup
              </button>
            </div>
          </article>
        )}
        <article className="maintenance-card export-card" id="directory-exports">
          <div>
            <span className="eyebrow">Csv exports</span>
            <h2>Download directory data</h2>
            <p>Exports use a simple, portable CSV format for review, reporting, or archival.</p>
          </div>
          <div className="export-list">
            {exports.map((item) => (
              <div className="export-row" key={item.key}>
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.description}</span>
                </div>
                <button
                  className="btn secondary"
                  type="button"
                  disabled={operationPending || loading}
                  onClick={() => void exportCsv(item.key, item.filename)}
                >
                  {activeExport === item.key ? "Preparing…" : "Download CSV"}
                </button>
              </div>
            ))}
          </div>
        </article>
        {isAdmin && status && (
          <BackupReviewPanel
            status={status}
            reload={load}
            onPendingChange={setReviewBusy}
            disabled={operationPending || loading}
          />
        )}
        {isAdmin && (
          <GoogleSheetsPanel
            disabled={busy || reviewBusy || activeExport !== null || loading}
            onPendingChange={setSheetsBusy}
          />
        )}
      </section>
      {isAdmin && (
        <details open={historyOpen} onToggle={(event) => setHistoryOpen(event.currentTarget.open)}>
          <summary>Maintenance history</summary>
          {historyOpen && <MaintenanceHistory />}
        </details>
      )}
    </div>
  );
}
