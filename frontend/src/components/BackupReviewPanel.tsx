import { useEffect, useState } from "react";
import { recordBackupReview } from "../api/maintenance";
import type { MaintenanceStatus } from "../types";

export default function BackupReviewPanel({
  status,
  reload,
  disabled,
  onPendingChange,
}: {
  status: MaintenanceStatus;
  reload: () => Promise<void>;
  disabled: boolean;
  onPendingChange?: (pending: boolean) => void;
}) {
  const [filename, setFilename] = useState("");
  const [copied, setCopied] = useState(false);
  const [tested, setTested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      onPendingChange?.(false);
    },
    [onPendingChange],
  );
  const selectedExists = status.backups.some((backup) => backup.filename === filename);
  const save = async () => {
    if (!copied || !selectedExists || busy || disabled) return;
    onPendingChange?.(true);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await recordBackupReview(filename, tested);
      setMessage(
        "Recovery review recorded as your confirmation, not an automatic external-drive test.",
      );
      setCopied(false);
      setTested(false);
      await reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save recovery review.");
    } finally {
      setBusy(false);
      onPendingChange?.(false);
    }
  };
  return (
    <article className="maintenance-card">
      <h2>Recovery review</h2>
      <p>
        Confirm only a copy actually placed on private off-device storage. Downloading alone does
        not prove recovery.
      </p>
      <p>
        {status.recovery_review
          ? `Last administrator-reported review: ${status.recovery_review.username} · ${new Date(status.recovery_review.reviewed_at).toLocaleString()} · ${status.recovery_review.filename}. Restore test: ${status.recovery_review.restore_tested ? "reported completed" : "not reported"}. This does not certify disk encryption or newer records.`
          : "No off-device recovery review recorded in this database."}
      </p>
      <fieldset disabled={busy || disabled} className="save-fields stack-md">
        <label>
          Backup reviewed
          <select
            value={selectedExists ? filename : ""}
            onChange={(event) => {
              setFilename(event.target.value);
              setCopied(false);
              setTested(false);
            }}
          >
            <option value="">Choose a saved backup</option>
            {status.backups.map((backup) => (
              <option key={backup.filename} value={backup.filename}>
                {backup.filename}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={copied}
            onChange={(event) => setCopied(event.target.checked)}
          />{" "}
          I copied this backup to private off-device storage.
        </label>
        <label>
          <input
            type="checkbox"
            checked={tested}
            onChange={(event) => setTested(event.target.checked)}
          />{" "}
          I tested restoring this copy in a separate test data folder.
        </label>
        <button
          type="button"
          className="btn secondary"
          disabled={!copied || !selectedExists}
          onClick={() => void save()}
        >
          {busy ? "Recording…" : "Record recovery review"}
        </button>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </article>
  );
}
