import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  applySharedWorkspace,
  checkSharedWorkspace,
  configureSharedWorkspace,
  disconnectSharedWorkspace,
  getSharedWorkspaceStatus,
  notifySharedWorkspaceChanged,
  previewSharedWorkspace,
  publishSharedWorkspaceReport,
  retrySharedWorkspace,
  type SharedChoice,
  type SharedMode,
  type SharedSummary,
  type SharedWorkspacePreview,
  type SharedWorkspaceResult,
  type SharedWorkspaceStatus,
} from "../api/sharedWorkspace";
import { UnconfirmedOperationError } from "../api/client";
import ConfirmationDialog from "./ConfirmationDialog";
import "../shared-workspace.css";

type Props = {
  disabled?: boolean;
  onPendingChange?: (pending: boolean) => void;
  onModeChange?: (configured: boolean | null) => void;
  onApplied?: () => void;
};
const pageSize = 10;
const stateLabels = {
  disconnected: "Not joined to shared storage",
  ready: "Shared copy saved",
  dirty: "Local changes are waiting to sync",
  pending: "A previous sync needs confirmation",
  rejoin_required: "This local copy needs to rejoin",
};
const previewTitles = {
  join: "Review joining shared storage",
  initialize: "Review first Office upload",
  sync: "Review shared changes",
};
const kindLabels = { program: "Program", scholar: "Scholar profile", office_log: "Office log" };
const directionLabels: Record<string, string> = {
  upload: "Send to shared storage",
  download: "Receive from shared storage",
  conflict: "Choose which version to keep",
  local: "Keep this computer's version",
  shared: "Keep shared storage's version",
  unchanged: "Already matches",
};
const dateText = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "Not synced yet";

function Summary({ value }: { value: SharedSummary }) {
  if (typeof value === "string") return <p>{value || "No record"}</p>;
  const rows = Array.isArray(value)
    ? value
    : Object.entries(value).map(
        ([key, entry]) => `${key.replace(/_/g, " ")}: ${entry == null ? "Not recorded" : entry}`,
      );
  return rows.length ? (
    <ul>
      {rows.map((row, index) => (
        <li key={index}>{row}</li>
      ))}
    </ul>
  ) : (
    <p>No record</p>
  );
}

export default function SharedWorkspacePanel({
  disabled = false,
  onPendingChange,
  onModeChange,
  onApplied,
}: Props) {
  const [status, setStatus] = useState<SharedWorkspaceStatus | null>(null);
  const [endpoint, setEndpoint] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<SharedWorkspacePreview | null>(null);
  const [choices, setChoices] = useState<Record<string, SharedChoice>>({});
  const [acknowledged, setAcknowledged] = useState(false);
  const [expired, setExpired] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [page, setPage] = useState(1);
  const [confirmation, setConfirmation] = useState<"apply" | "disconnect" | "report" | null>(null);
  const lock = useRef(false);
  const mounted = useRef(false);
  const initialSequence = useRef(0);
  const identity = useId();
  const pending = uncertain || status?.state === "pending";
  const active = busy || Boolean(preview) || Boolean(confirmation);
  const blocked = disabled || loading || busy;
  const pageCount = Math.max(1, Math.ceil((preview?.items.length || 0) / pageSize));
  const allChoices = preview?.conflicts.every((key) => choices[key]) ?? true;

  const remember = (next: SharedWorkspaceStatus) => {
    if (!mounted.current) return;
    setStatus(next);
    setEndpoint(next.endpoint || "");
    setUncertain(next.state === "pending");
    onModeChange?.(next.configured);
    notifySharedWorkspaceChanged();
  };
  const readStatus = async () => {
    const next = await getSharedWorkspaceStatus();
    remember(next);
    return next;
  };
  useEffect(() => {
    mounted.current = true;
    const sequence = ++initialSequence.current;
    const controller = new AbortController();
    const load = async () => {
      try {
        const next = await getSharedWorkspaceStatus(controller.signal);
        if (!mounted.current || sequence !== initialSequence.current) return;
        setStatus(next);
        setEndpoint(next.endpoint || "");
        onModeChange?.(next.configured);
      } catch (caught) {
        if (mounted.current && !controller.signal.aborted) {
          onModeChange?.(null);
          setError(caught instanceof Error ? caught.message : "Unable to check shared storage.");
        }
      } finally {
        if (mounted.current && !controller.signal.aborted) setLoading(false);
      }
    };
    void load();
    return () => {
      mounted.current = false;
      initialSequence.current += 1;
      controller.abort();
    };
    // Parent callbacks are state setters; avoid restarting setup while another panel refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => onPendingChange?.(active), [active, onPendingChange]);
  useEffect(() => () => onPendingChange?.(false), [onPendingChange]);
  useEffect(() => {
    if (!preview) {
      setExpired(false);
      return;
    }
    const remaining = Date.parse(preview.expires_at) - Date.now();
    setExpired(!Number.isFinite(remaining) || remaining <= 0);
    if (!Number.isFinite(remaining) || remaining <= 0) return;
    const timer = window.setTimeout(() => setExpired(true), Math.min(remaining, 2147483647));
    return () => window.clearTimeout(timer);
  }, [preview]);

  const run = async (operation: () => Promise<void>) => {
    if (disabled || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
    } catch (caught) {
      if (mounted.current)
        setError(
          caught instanceof Error ? caught.message : "The shared operation could not finish.",
        );
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  const fetchPreview = (mode: SharedMode) =>
    run(async () => {
      if (pending) return;
      const next = await previewSharedWorkspace(mode);
      if (!mounted.current) return;
      setPreview(next);
      setChoices({});
      setAcknowledged(false);
      setPage(1);
    });
  const confirmApply = () => {
    if (blocked || pending || !preview || expired) return;
    if (!allChoices) {
      setError("Choose which version to keep for every conflicting record.");
      return;
    }
    if (preview.mode !== "sync" && !acknowledged) {
      setError("Confirm the Office data or local replacement statement before continuing.");
      return;
    }
    setError("");
    setConfirmation("apply");
  };
  const finish = (result: SharedWorkspaceResult) => {
    if (!mounted.current) return;
    setPreview(null);
    setChoices({});
    setUncertain(false);
    setNotice(
      `${result.replayed ? "Earlier sync confirmed." : "Shared changes saved."} ${result.uploaded} sent · ${result.downloaded} received. ${result.message || ""}`,
    );
    notifySharedWorkspaceChanged();
    onApplied?.();
  };
  const apply = () =>
    run(async () => {
      if (!preview || pending || expired || !allChoices) return;
      setConfirmation(null);
      let result: SharedWorkspaceResult;
      try {
        result = await applySharedWorkspace(preview.preview_id, { ...choices });
      } catch (caught) {
        if (caught instanceof UnconfirmedOperationError) {
          if (mounted.current) {
            setUncertain(true);
            setPreview(null);
          }
        }
        try {
          await readStatus();
        } catch {
          /* Keep uncertain status until the service confirms it. */
        }
        throw caught;
      }
      finish(result);
      try {
        await readStatus();
      } catch {
        if (mounted.current)
          setError(
            "Changes were saved, but connection status could not refresh. Refresh shared status to check it.",
          );
      }
    });
  const retry = () =>
    run(async () => {
      let result: SharedWorkspaceResult;
      try {
        result = await retrySharedWorkspace();
      } catch (caught) {
        try {
          await readStatus();
        } catch {
          /* The pending request remains protected. */
        }
        throw caught;
      }
      finish(result);
      try {
        await readStatus();
      } catch {
        if (mounted.current)
          setError(
            "The earlier sync was confirmed. Refresh shared status when the connection is available.",
          );
      }
    });

  return (
    <article
      id="shared-workspace"
      className="maintenance-card stack-md"
      aria-labelledby={`${identity}-title`}
    >
      <div>
        <span className="eyebrow">Shared office records</span>
        <h2 id={`${identity}-title`}>Shared storage & reporting</h2>
        <p>
          Use one protected data file across computers and a separate readable report.{" "}
          <Link to="/office-guide#shared-workspace">Setup and shared-data guide</Link>
        </p>
      </div>
      {loading && <p role="status">Checking shared storage…</p>}
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {status && (
        <p role="status">
          {!status.joined && status.state === "ready"
            ? "Shared storage not joined"
            : stateLabels[status.state]}{" "}
          · Last sync: {dateText(status.last_synced_at)}
        </p>
      )}
      {status?.message && <p>{status.message}</p>}
      {busy && <p role="status">Working with shared storage…</p>}
      <div className="action-row">
        <button
          type="button"
          className="btn secondary"
          disabled={blocked || Boolean(preview)}
          onClick={() =>
            void run(async () => {
              await readStatus();
            })
          }
        >
          Refresh shared status
        </button>
        {status?.configured && (
          <button
            type="button"
            className="btn secondary"
            disabled={blocked || pending || Boolean(preview)}
            onClick={() => setConfirmation("disconnect")}
          >
            Disconnect this computer
          </button>
        )}
      </div>
      {(!status?.configured || !status.connected) && !pending && (
        <section className="stack-md" aria-label="Shared connection setup">
          <label>
            Owner's Google bridge address
            <input
              type="url"
              value={endpoint}
              disabled={blocked || Boolean(preview)}
              placeholder="https://script.google.com/macros/s/…/exec"
              onChange={(event) => setEndpoint(event.target.value)}
            />
          </label>
          <button
            type="button"
            className="btn secondary"
            disabled={blocked || !endpoint.trim() || Boolean(preview)}
            onClick={() =>
              void run(async () => {
                remember(await configureSharedWorkspace(endpoint.trim()));
                setNotice(
                  "Connection saved on this computer. Ask the owner to register the device details below, then check the connection.",
                );
              })
            }
          >
            Save shared connection
          </button>
          {status?.device_id && status.device_key_hash && (
            <div className="shared-setup-grid shared-registration">
              <label>
                Device registration ID
                <input readOnly value={status.device_id} />
              </label>
              <label>
                Device registration fingerprint
                <input readOnly value={status.device_key_hash} />
              </label>
            </div>
          )}
          {status?.configured && (
            <p>
              The owner registers this ID and fingerprint in the Google bridge. The private access
              key stays encrypted on this computer.
            </p>
          )}
        </section>
      )}
      {status?.configured && !pending && (
        <div className="action-row">
          <button
            type="button"
            className="btn secondary"
            disabled={blocked || Boolean(preview)}
            onClick={() =>
              void run(async () => {
                remember(await checkSharedWorkspace());
                setNotice(
                  "Shared connection checked. Review joining or syncing before changing records.",
                );
              })
            }
          >
            Check shared connection
          </button>
        </div>
      )}
      {status?.connected && (
        <div className="shared-external-links">
          {status.storage_url && (
            <a href={status.storage_url} target="_blank" rel="noreferrer">
              Storage file · owner access
            </a>
          )}
          {status.report_url && (
            <a href={status.report_url} target="_blank" rel="noreferrer">
              Open shared report
            </a>
          )}
        </div>
      )}
      {pending ? (
        <section className="notice" aria-label="Unconfirmed shared sync">
          <h3>Confirm the earlier sync</h3>
          <p>
            The previous save has an unconfirmed result. Record editing is protected until the same
            request is resolved. This retry will not send a different version.
          </p>
          <button
            type="button"
            className="btn primary"
            disabled={blocked}
            onClick={() => void retry()}
          >
            Retry earlier sync
          </button>
        </section>
      ) : (
        status?.connected &&
        !preview && (
          <div className="action-row">
            {status.joined && status.state !== "rejoin_required" ? (
              <>
                <button
                  type="button"
                  className="btn primary"
                  disabled={blocked}
                  onClick={() => void fetchPreview("sync")}
                >
                  Sync workspace
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={blocked}
                  onClick={() => setConfirmation("report")}
                >
                  Update shared report
                </button>
              </>
            ) : (
              <>
                {status.initialized && (
                  <button
                    type="button"
                    className="btn primary"
                    disabled={blocked}
                    onClick={() => void fetchPreview("join")}
                  >
                    Review joining shared storage
                  </button>
                )}
                {!status.initialized && status.can_initialize && (
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={blocked}
                    onClick={() => void fetchPreview("initialize")}
                  >
                    Review first Office upload
                  </button>
                )}
                {!status.initialized && !status.can_initialize && (
                  <p>The owner-authorized Office computer must initialize this workspace first.</p>
                )}
              </>
            )}
          </div>
        )
      )}
      {preview && (
        <section className="shared-preview stack-md" aria-labelledby={`${identity}-preview-title`}>
          <div className="shared-preview-heading">
            <h3 id={`${identity}-preview-title`}>{previewTitles[preview.mode]}</h3>
            <button
              type="button"
              className="btn secondary"
              disabled={blocked}
              onClick={() => {
                setPreview(null);
                setChoices({});
              }}
            >
              Close shared preview
            </button>
          </div>
          <p>Preview expires {dateText(preview.expires_at)}.</p>
          {expired && (
            <p role="alert">This preview has expired. Refresh it before applying changes.</p>
          )}
          {preview.warnings.length > 0 && (
            <ul>
              {preview.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          )}
          <div className="shared-preview-counts">
            <span>{preview.counts.upload} to send</span>
            <span>{preview.counts.download} to receive</span>
            <span>{preview.counts.conflicts} need a choice</span>
          </div>
          {!preview.items.length && (
            <p>
              The records already match. Confirm sync to refresh this computer's shared checkpoint.
            </p>
          )}
          {preview.items.slice((page - 1) * pageSize, page * pageSize).map((item) => (
            <article key={item.key} className="shared-change stack-md">
              <div>
                <h4>{item.label}</h4>
                <span className="shared-change-kind">
                  {kindLabels[item.kind]} ·{" "}
                  {directionLabels[item.direction] || item.direction.replace(/_/g, " ")}
                </span>
              </div>
              <div className="shared-comparison">
                <section>
                  <h5>This computer</h5>
                  <Summary value={item.local_summary} />
                </section>
                <section>
                  <h5>Shared storage</h5>
                  <Summary value={item.shared_summary} />
                </section>
              </div>
              {item.conflict && (
                <fieldset className="shared-conflict-choice" disabled={blocked}>
                  <legend>Which version of {item.label} should be kept?</legend>
                  <label>
                    <input
                      type="radio"
                      name={`${identity}-${item.key}`}
                      checked={choices[item.key] === "local"}
                      onChange={() => setChoices((old) => ({ ...old, [item.key]: "local" }))}
                    />
                    Keep this computer's version
                  </label>
                  <label>
                    <input
                      type="radio"
                      name={`${identity}-${item.key}`}
                      checked={choices[item.key] === "shared"}
                      onChange={() => setChoices((old) => ({ ...old, [item.key]: "shared" }))}
                    />
                    Keep shared storage's version
                  </label>
                </fieldset>
              )}
            </article>
          ))}
          {pageCount > 1 && (
            <nav className="action-row" aria-label="Shared preview pages">
              <button
                type="button"
                className="btn secondary"
                disabled={blocked || page === 1}
                onClick={() => setPage((old) => old - 1)}
              >
                Previous shared page
              </button>
              <span>
                Page {page} of {pageCount}
              </span>
              <button
                type="button"
                className="btn secondary"
                disabled={blocked || page === pageCount}
                onClick={() => setPage((old) => old + 1)}
              >
                Next shared page
              </button>
            </nav>
          )}
          {preview.mode !== "sync" && (
            <label className="shared-confirmation">
              <input
                type="checkbox"
                checked={acknowledged}
                disabled={blocked}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              {preview.mode === "initialize"
                ? "This is the authoritative Office computer, I reviewed its current records, and I have a separate backup."
                : "I reviewed this replacement. Local business records will be backed up and replaced with shared records; this computer's accounts stay local."}
            </label>
          )}
          <div className="action-row">
            <button
              type="button"
              className="btn secondary"
              disabled={blocked}
              onClick={() => void fetchPreview(preview.mode)}
            >
              Refresh shared preview
            </button>
            <button
              type="button"
              className="btn primary"
              disabled={blocked || expired}
              onClick={confirmApply}
            >
              Review shared save
            </button>
          </div>
        </section>
      )}
      <ConfirmationDialog
        open={confirmation === "apply"}
        title={
          preview?.mode === "initialize"
            ? "Initialize shared storage from this Office computer?"
            : preview?.mode === "join"
              ? "Join and replace local business records?"
              : "Apply reviewed shared changes?"
        }
        description={
          preview?.mode === "sync"
            ? "Apply the reviewed shared changes and your explicit conflict choices. The service checks for newer changes before committing."
            : preview?.mode === "initialize"
              ? "Send this Office computer's complete business records to the empty shared workspace. Only the authorized Office initializer can do this."
              : "Create a protected local recovery copy, then replace this computer's business records with the reviewed shared records. Accounts and private connections remain local."
        }
        confirmLabel="Apply reviewed shared changes"
        cancelLabel="Keep reviewing"
        confirmDisabled={blocked || expired}
        onConfirm={() => void apply()}
        onCancel={() => setConfirmation(null)}
      />
      <ConfirmationDialog
        open={confirmation === "disconnect"}
        title="Disconnect this computer?"
        description="Keep the local records and leave shared storage available to the other computers. Unsent local changes will remain on this computer."
        confirmLabel="Disconnect shared storage"
        cancelLabel="Keep connected"
        confirmDisabled={blocked || pending}
        onConfirm={() =>
          void run(async () => {
            setConfirmation(null);
            remember(await disconnectSharedWorkspace());
            setNotice("This computer is disconnected. Shared records were not deleted.");
          })
        }
        onCancel={() => setConfirmation(null)}
      />
      <ConfirmationDialog
        open={confirmation === "report"}
        title="Replace the shared reporting tab?"
        description="Generate the report from the current shared records. This replaces CATHEDRA REPORT in the separate report file; it does not upload local pending edits."
        confirmLabel="Replace shared report"
        cancelLabel="Keep report"
        confirmDisabled={blocked}
        onConfirm={() =>
          void run(async () => {
            setConfirmation(null);
            const result = await publishSharedWorkspaceReport();
            if (mounted.current)
              setNotice(
                `Shared report updated: ${result.rows} rows · ${dateText(result.synced_at)}.`,
              );
          })
        }
        onCancel={() => setConfirmation(null)}
      />
    </article>
  );
}
