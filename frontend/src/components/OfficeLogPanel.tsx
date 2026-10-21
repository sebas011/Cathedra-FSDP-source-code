import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { getCurrentUser, getExpiredUser, UnconfirmedOperationError } from "../api/client";
import {
  addOfficeLog,
  exportOfficeLogs,
  getOfficeLogs,
  type OfficeLogInput,
  type OfficeLogKind,
  type OfficeLogPage,
} from "../api/officeLog";
import { useDiscardConfirmation } from "../hooks/useDiscardConfirmation";
import { useUnsavedChanges } from "../hooks/useUnsavedChanges";
import UnsavedChangesDialog from "./UnsavedChangesDialog";
import { RecordInput, RecordTextarea } from "./RecordTextInput";
import "../office-log.css";

const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};
const newDraft = () => ({
  occurred_on: today(),
  entry_type: "Note" as OfficeLogKind,
  note: "",
  document_name: "",
  from_department: "",
  to_department: "",
});
const displayDate = (value: string) =>
  new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { dateStyle: "medium" });
const displayTime = (value: string) =>
  new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`).toLocaleString();

function OfficeLogEditor({
  scholarId,
  onSaved,
  onClose,
}: {
  scholarId?: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState(newDraft);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [uncertainPayload, setUncertainPayload] = useState<OfficeLogInput | null>(null);
  const submitting = useRef(false);
  const requestKey = useRef(crypto.randomUUID());
  const mounted = useRef(true);
  const guard = useUnsavedChanges(draft, saving);
  const { confirmDiscard, discardDialog } = useDiscardConfirmation();
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const resetEditor = () => {
    const next = newDraft();
    setDraft(next);
    guard.resetBaseline(next);
    requestKey.current = crypto.randomUUID();
    setError("");
    setUncertainPayload(null);
  };
  const discard = async (close: boolean) => {
    if (
      saving ||
      (guard.dirty &&
        !(await confirmDiscard(
          "Discard this office-log draft? Any entry already saved will remain in the log.",
        )))
    )
      return;
    resetEditor();
    if (close) onClose();
  };
  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting.current) return;
    if (!draft.note.trim()) {
      setError("Enter a note before saving the log entry.");
      return;
    }
    const payload = uncertainPayload ?? {
      ...draft,
      scholar_id: scholarId ?? null,
      occurred_on: draft.occurred_on || null,
      note: draft.note.trim().toUpperCase(),
      document_name: draft.document_name.trim().toUpperCase() || null,
      from_department: draft.from_department.trim().toUpperCase() || null,
      to_department: draft.to_department.trim().toUpperCase() || null,
    };
    submitting.current = true;
    setSaving(true);
    setError("");
    try {
      await addOfficeLog(payload, requestKey.current);
      if (mounted.current) {
        resetEditor();
        onSaved();
      }
    } catch (caught) {
      if (mounted.current) {
        if (caught instanceof UnconfirmedOperationError) setUncertainPayload(payload);
        setError(
          caught instanceof Error
            ? caught.message
            : "The log entry was not confirmed. Check the log and retry this same entry.",
        );
      }
    } finally {
      submitting.current = false;
      if (mounted.current) setSaving(false);
    }
  };
  const textField = (
    field: "document_name" | "from_department" | "to_department",
    label: string,
  ) => (
    <label>
      {label}
      <RecordInput
        value={draft[field]}
        disabled={saving || !!uncertainPayload}
        onValueChange={(text) => setDraft((value) => ({ ...value, [field]: text }))}
      />
    </label>
  );
  return (
    <div className="no-print">
      <form
        className="stack-md"
        onSubmit={(event) => void save(event)}
        aria-label={scholarId ? "Scholar office-log entry" : "General office-log entry"}
      >
        <div className="form-grid">
          <label>
            Entry date
            <input
              type="date"
              value={draft.occurred_on}
              disabled={saving || !!uncertainPayload}
              onChange={(event) =>
                setDraft((value) => ({ ...value, occurred_on: event.target.value }))
              }
            />
          </label>
          <label>
            Entry type
            <select
              value={draft.entry_type}
              disabled={saving || !!uncertainPayload}
              onChange={(event) =>
                setDraft((value) => ({ ...value, entry_type: event.target.value as OfficeLogKind }))
              }
            >
              <option>Note</option>
              <option>Document received</option>
              <option>Document transferred</option>
            </select>
          </label>
          {textField("document_name", "Document (optional)")}
          {textField("from_department", "From department (optional)")}
          {textField("to_department", "To department (optional)")}
        </div>
        <label>
          Log note
          <RecordTextarea
            rows={3}
            value={draft.note}
            disabled={saving || !!uncertainPayload}
            onValueChange={(text) => setDraft((value) => ({ ...value, note: text }))}
          />
        </label>
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        {uncertainPayload && (
          <p role="status">
            This entry is held for confirmation. Check the log, then retry the same entry or clear
            the editor.
          </p>
        )}
        <div className="action-group">
          <button type="submit" className="btn primary" disabled={saving}>
            {saving ? "Saving entry…" : uncertainPayload ? "Retry same entry" : "Save log entry"}
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={saving}
            onClick={() => void discard(false)}
          >
            Clear log editor
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={saving}
            onClick={() => void discard(true)}
          >
            Close log editor
          </button>
        </div>
      </form>
      <UnsavedChangesDialog
        blocker={guard.blocker}
        pending={saving}
        pendingTitle="Saving the log entry"
      />
      {discardDialog}
    </div>
  );
}

export default function OfficeLogPanel({ scholarId }: { scholarId?: number }) {
  const identity = useId();
  const [editorOpen, setEditorOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<OfficeLogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [exporting, setExporting] = useState(false);
  const mounted = useRef(true);
  const logHistory = useRef<HTMLDivElement>(null);
  const addEntryButton = useRef<HTMLButtonElement>(null);
  const editorWasOpen = useRef(false);
  const user = getCurrentUser() || getExpiredUser();
  const canWrite = user?.role === "admin" || user?.role === "staff";
  const filters = { scholar_id: scholarId, search, entry_type: kind, page };
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (editorWasOpen.current && !editorOpen) addEntryButton.current?.focus();
    editorWasOpen.current = editorOpen;
  }, [editorOpen]);
  useEffect(() => {
    let previous: Array<[HTMLDetailsElement, boolean]> = [];
    const expand = () => {
      if (previous.length) return;
      previous = Array.from(logHistory.current?.querySelectorAll("details") || []).map((item) => [
        item,
        item.open,
      ]);
      for (const [item] of previous) item.open = true;
    };
    const restore = () => {
      for (const [item, open] of previous) item.open = open;
      previous = [];
    };
    window.addEventListener("beforeprint", expand);
    window.addEventListener("afterprint", restore);
    return () => {
      restore();
      window.removeEventListener("beforeprint", expand);
      window.removeEventListener("afterprint", restore);
    };
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getOfficeLogs({ scholar_id: scholarId, search, entry_type: kind, page })
      .then((value) => {
        if (!active) return;
        const lastPage = Math.max(1, Math.ceil(value.total / value.page_size));
        if (page > lastPage) {
          setPage(lastPage);
          return;
        }
        setResult(value);
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "Unable to load office log.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [scholarId, search, kind, page, attempt]);
  const exportEntries = async () => {
    if (exporting) return;
    setExporting(true);
    setError("");
    try {
      await exportOfficeLogs(filters);
    } catch (caught) {
      if (mounted.current)
        setError(caught instanceof Error ? caught.message : "Unable to export the office log.");
    } finally {
      if (mounted.current) setExporting(false);
    }
  };
  return (
    <section
      className="profile-panel stack-md"
      id="scholar-office-log"
      aria-labelledby={`${identity}-title`}
    >
      <div className="action-group">
        <h2 id={`${identity}-title`}>{scholarId ? "Office log" : "Office entries"}</h2>
        <Link className="btn secondary no-print" to="/office-guide">
          Office Guide
        </Link>
        {canWrite && !editorOpen && (
          <button
            ref={addEntryButton}
            type="button"
            className="btn primary no-print"
            onClick={() => {
              setSaved("");
              setEditorOpen(true);
            }}
          >
            Add log entry
          </button>
        )}
      </div>
      {canWrite && editorOpen && (
        <OfficeLogEditor
          key={scholarId ?? "general"}
          scholarId={scholarId}
          onSaved={() => {
            setSaved("Log entry saved.");
            setEditorOpen(false);
            setPage(1);
            setSearch("");
            setKind("");
            setAttempt((value) => value + 1);
          }}
          onClose={() => setEditorOpen(false)}
        />
      )}
      {saved && (
        <p className="notice success" role="status">
          {saved}
        </p>
      )}
      <div className="form-grid no-print">
        <label>
          Search office log
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setPage(1);
              setSearch(event.target.value);
            }}
          />
        </label>
        <label>
          Filter log entry type
          <select
            value={kind}
            onChange={(event) => {
              setPage(1);
              setKind(event.target.value);
            }}
          >
            <option value="">All entries</option>
            <option>Note</option>
            <option>Document received</option>
            <option>Document transferred</option>
          </select>
        </label>
        <div className="action-group">
          <button
            type="button"
            className="btn secondary"
            disabled={loading}
            onClick={() => setAttempt((value) => value + 1)}
          >
            Refresh log
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={exporting}
            onClick={() => void exportEntries()}
          >
            {exporting ? "Exporting…" : "Export log CSV"}
          </button>
        </div>
      </div>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button
            type="button"
            className="btn secondary"
            onClick={() => setAttempt((value) => value + 1)}
          >
            Retry log
          </button>
        </div>
      )}
      <div ref={logHistory} aria-busy={loading}>
        {loading ? (
          <p role="status">Loading office log…</p>
        ) : error ? null : (
          result && (
            <>
              <p>
                {result.total} log {result.total === 1 ? "entry" : "entries"}
              </p>
              {!result.items.length ? (
                <p>No log entries recorded.</p>
              ) : (
                <ol className="office-log-list">
                  {result.items.map((item) => (
                    <li key={item.id}>
                      <details className="office-log-entry">
                        <summary>
                          <span className="office-log-summary">
                            <strong>{item.entry_type}</strong>
                            {(item.document_name || item.scholar_name) && (
                              <span className="office-log-summary-context">
                                {[item.document_name, item.scholar_name]
                                  .filter(Boolean)
                                  .join(" · ")}
                              </span>
                            )}
                          </span>
                          <time dateTime={item.occurred_on}>{displayDate(item.occurred_on)}</time>
                        </summary>
                        <div className="office-log-details">
                          {item.scholar_name && (
                            <p>
                              {item.scholar_id ? (
                                <Link to={`/fsdp/${item.scholar_id}`}>{item.scholar_name}</Link>
                              ) : (
                                item.scholar_name
                              )}
                            </p>
                          )}
                          {item.document_name && (
                            <p>
                              <strong>Document:</strong> {item.document_name}
                            </p>
                          )}
                          {(item.from_department || item.to_department) && (
                            <p>
                              {item.from_department || "Not recorded"} →{" "}
                              {item.to_department || "Not recorded"}
                            </p>
                          )}
                          <p className="office-log-note">{item.note}</p>
                          <p>
                            <small>
                              Recorded by {item.username} · {displayTime(item.created_at)}
                            </small>
                          </p>
                        </div>
                      </details>
                    </li>
                  ))}
                </ol>
              )}
              <nav aria-label="Office log pages" className="action-group no-print">
                <button
                  type="button"
                  className="btn secondary"
                  disabled={page <= 1}
                  onClick={() => setPage((value) => value - 1)}
                >
                  Previous log entries
                </button>
                <span>
                  Page {page} of {Math.max(1, Math.ceil(result.total / result.page_size))}
                </span>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={page * result.page_size >= result.total}
                  onClick={() => setPage((value) => value + 1)}
                >
                  Next log entries
                </button>
              </nav>
            </>
          )
        )}
      </div>
    </section>
  );
}
