import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  configureGoogleSheets,
  connectGoogleSheets,
  disconnectGoogleSheets,
  getGoogleSheetsStatus,
  syncGoogleSheets,
  type GoogleSheetsStatus,
} from "../api/googleSheets";
import ConfirmationDialog from "./ConfirmationDialog";

type Props = {
  disabled?: boolean;
  onPendingChange?: (pending: boolean) => void;
};

const reportingAddress = (id: string) =>
  `https://docs.google.com/spreadsheets/d/${encodeURIComponent(id)}/edit`;

export default function GoogleSheetsPanel({ disabled = false, onPendingChange }: Props) {
  const [status, setStatus] = useState<GoogleSheetsStatus | null>(null);
  const [spreadsheet, setSpreadsheet] = useState("");
  const [credentialName, setCredentialName] = useState("");
  const [loading, setLoading] = useState(true);
  const [readingCredentials, setReadingCredentials] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmSync, setConfirmSync] = useState(false);
  const [editDetails, setEditDetails] = useState(false);
  const clientConfiguration = useRef<Record<string, unknown> | undefined>(undefined);
  const fileInput = useRef<HTMLInputElement>(null);
  const fileSequence = useRef(0);
  const operationLock = useRef(false);
  const mounted = useRef(false);
  const waiting = status?.connection_state === "waiting";
  const pending = busy || readingCredentials || waiting;
  const blocked = disabled || loading || pending;
  const targetChanged = Boolean(
    status?.configured && spreadsheet.trim() !== reportingAddress(status.spreadsheet_id || ""),
  );
  const unsavedDetails = targetChanged || Boolean(credentialName);

  useEffect(() => {
    onPendingChange?.(pending);
  }, [pending, onPendingChange]);
  useEffect(
    () => () => {
      onPendingChange?.(false);
    },
    [onPendingChange],
  );
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void getGoogleSheetsStatus(controller.signal)
      .then((result) => {
        if (!mounted.current || controller.signal.aborted) return;
        setStatus(result);
        setSpreadsheet(result.spreadsheet_id ? reportingAddress(result.spreadsheet_id) : "");
        setEditDetails(!result.configured);
      })
      .catch((caught) => {
        if (mounted.current && !controller.signal.aborted) {
          setEditDetails(true);
          setError(
            caught instanceof Error ? caught.message : "Unable to read the Google connection.",
          );
        }
      })
      .finally(() => {
        if (mounted.current && !controller.signal.aborted) setLoading(false);
      });
    return () => {
      mounted.current = false;
      controller.abort();
      fileSequence.current += 1;
      clientConfiguration.current = undefined;
    };
  }, []);

  useEffect(() => {
    if (!waiting) return;
    const controller = new AbortController();
    let timer: number | undefined;
    let active = true;
    const deadline = window.setTimeout(() => {
      if (!active) return;
      setStatus((current) => (current ? { ...current, connection_state: "error" } : current));
      setError(
        "Google sign-in status was not confirmed. Refresh the connection before trying again.",
      );
    }, 240000);
    const poll = async () => {
      try {
        const next = await getGoogleSheetsStatus(controller.signal);
        if (!active) return;
        setStatus(next);
        setError("");
        if (next.connection_state === "waiting") timer = window.setTimeout(poll, 2000);
        else if (next.connected)
          setNotice("Google account connected. The report is ready to update.");
      } catch (caught) {
        if (!active) return;
        setError(caught instanceof Error ? caught.message : "Unable to check Google sign-in.");
        timer = window.setTimeout(poll, 5000);
      }
    };
    timer = window.setTimeout(poll, 2000);
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timer);
      window.clearTimeout(deadline);
    };
  }, [waiting]);

  const run = async (operation: () => Promise<void>) => {
    if (blocked || operationLock.current) return;
    operationLock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
    } catch (caught) {
      if (mounted.current)
        setError(
          caught instanceof Error ? caught.message : "The Google operation could not finish.",
        );
    } finally {
      operationLock.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  const readCredentials = async (file?: File) => {
    const sequence = ++fileSequence.current;
    clientConfiguration.current = undefined;
    setCredentialName("");
    setError("");
    if (!file) {
      setReadingCredentials(false);
      return;
    }
    setReadingCredentials(true);
    try {
      if (file.size > 20000)
        throw new Error("Choose the small Desktop OAuth credentials JSON file.");
      const parsed: unknown = JSON.parse(await file.text());
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
        throw new Error("Choose a valid Google Desktop OAuth credentials JSON file.");
      if (!mounted.current || sequence !== fileSequence.current) return;
      clientConfiguration.current = parsed as Record<string, unknown>;
      setCredentialName(file.name);
    } catch {
      if (mounted.current && sequence === fileSequence.current) {
        if (fileInput.current) fileInput.current.value = "";
        setError("Choose a valid Google Desktop OAuth credentials JSON file under 20 KB.");
      }
    } finally {
      if (mounted.current && sequence === fileSequence.current) setReadingCredentials(false);
    }
  };
  const refreshConnection = () =>
    run(async () => {
      const result = await getGoogleSheetsStatus();
      if (!mounted.current) return;
      setStatus(result);
      if (!spreadsheet)
        setSpreadsheet(result.spreadsheet_id ? reportingAddress(result.spreadsheet_id) : "");
      setEditDetails(!result.configured);
    });
  const saveDetails = () =>
    run(async () => {
      const result = await configureGoogleSheets(spreadsheet.trim(), clientConfiguration.current);
      if (!mounted.current) return;
      setStatus(result);
      setSpreadsheet(result.spreadsheet_id ? reportingAddress(result.spreadsheet_id) : "");
      clientConfiguration.current = undefined;
      setCredentialName("");
      if (fileInput.current) fileInput.current.value = "";
      setEditDetails(false);
      setNotice("Connection details saved.");
    });
  const connect = () =>
    run(async () => {
      const result = await connectGoogleSheets();
      if (mounted.current) setStatus(result);
    });
  const disconnect = () =>
    run(async () => {
      const result = await disconnectGoogleSheets();
      if (!mounted.current) return;
      setStatus(result);
      if (!result.configured) setEditDetails(true);
      setNotice("Google account disconnected from this app.");
    });
  const updateSheet = () => {
    if (blocked || !status?.connected || unsavedDetails || operationLock.current) return;
    setConfirmSync(false);
    void run(async () => {
      const result = await syncGoogleSheets();
      if (!mounted.current) return;
      setStatus((current) =>
        current ? { ...current, last_sync_at: result.synced_at, message: null } : current,
      );
      setNotice(`Google report updated: ${result.rows} grant and scholar rows.`);
    });
  };

  return (
    <article className="maintenance-card stack-md" id="google-reporting">
      <div>
        <span className="eyebrow">Cloud reporting</span>
        <h2>Google Sheets report</h2>
        <p>
          Update your dedicated reporting tab from the current Cathedra records.{" "}
          <Link to="/office-guide#cloud-reporting">Connection setup and guide</Link>
        </p>
      </div>
      {loading ? (
        <p role="status">Checking the Google connection…</p>
      ) : (
        <>
          <p>
            {waiting
              ? "Complete Google sign-in in the browser that opened, then return here."
              : status?.connected
                ? "Google account connected."
                : status?.configured
                  ? "Connection details saved. Connect your Google account to update the report."
                  : "Save your reporting spreadsheet and Desktop credentials, then connect Google."}
          </p>
          {status?.spreadsheet_id && (
            <a href={reportingAddress(status.spreadsheet_id)} target="_blank" rel="noreferrer">
              Open reporting spreadsheet
            </a>
          )}
          <p>
            Last successful update:{" "}
            {status?.last_sync_at
              ? new Date(status.last_sync_at).toLocaleString()
              : "Not updated yet"}
          </p>
          <details
            open={editDetails}
            onToggle={(event) => setEditDetails(event.currentTarget.open)}
          >
            <summary>Connection details</summary>
            <fieldset className="save-fields stack-md" disabled={blocked}>
              <label>
                Reporting spreadsheet URL or ID
                <input
                  value={spreadsheet}
                  onChange={(event) => setSpreadsheet(event.target.value)}
                />
              </label>
              <label>
                Google Desktop credentials JSON
                <input
                  ref={fileInput}
                  type="file"
                  accept=".json,application/json"
                  onChange={(event) => void readCredentials(event.target.files?.[0])}
                />
              </label>
              {credentialName && <span>Credentials selected: {credentialName}</span>}
              <button
                type="button"
                className="btn secondary"
                disabled={!spreadsheet.trim() || (!status?.configured && !credentialName)}
                onClick={() => void saveDetails()}
              >
                Save connection details
              </button>
            </fieldset>
          </details>
          <div className="action-row">
            <button
              type="button"
              className="btn secondary"
              disabled={blocked}
              onClick={() => void refreshConnection()}
            >
              Refresh Google connection
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={blocked || !status?.configured || unsavedDetails}
              onClick={() => void connect()}
            >
              {waiting
                ? "Waiting for Google sign-in…"
                : status?.connected
                  ? "Reconnect Google"
                  : "Connect Google"}
            </button>
            <button
              type="button"
              className="btn primary"
              disabled={blocked || !status?.connected || unsavedDetails}
              onClick={() => setConfirmSync(true)}
            >
              {busy ? "Working…" : "Update Google Sheet"}
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={blocked}
              onClick={() => void disconnect()}
            >
              {status?.connected ? "Disconnect Google" : "Forget Google connection"}
            </button>
          </div>
        </>
      )}
      {(error || status?.message) && <p role="alert">{error || status?.message}</p>}
      {notice && <p role="status">{notice}</p>}
      <ConfirmationDialog
        open={confirmSync}
        title="Replace the Google report?"
        description="This sends the current scholar and grant records to the saved Google spreadsheet and replaces all report values in its CATHEDRA REPORT tab. Other tabs are unchanged."
        confirmLabel="Replace reporting tab"
        cancelLabel="Keep existing report"
        confirmDisabled={blocked || !status?.connected || unsavedDetails}
        onConfirm={updateSheet}
        onCancel={() => setConfirmSync(false)}
      />
    </article>
  );
}
