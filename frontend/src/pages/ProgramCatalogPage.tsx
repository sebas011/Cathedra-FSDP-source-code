import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { getCurrentUser } from "../api/client";
import {
  createProgram,
  deleteProgram,
  duplicateCatalogProgram,
  getPrograms,
  updateProgram,
  type Program,
  type ProgramInput,
} from "../api/programs";
import { recordText } from "../utils/recordText";
import { RecordInput, RecordTextarea } from "../components/RecordTextInput";
import PageHeading from "../components/PageHeading";
import TableRegion from "../components/TableRegion";
import FormError from "../components/FormError";
import ConfirmationDialog from "../components/ConfirmationDialog";
import UnsavedChangesDialog from "../components/UnsavedChangesDialog";
import { useUnsavedChanges } from "../hooks/useUnsavedChanges";
import { useDiscardConfirmation } from "../hooks/useDiscardConfirmation";
const blank = (): ProgramInput => ({ name: "", delivering_hei: "", description: "" });

export default function ProgramCatalogPage() {
  const isAdmin = getCurrentUser()?.role === "admin";
  const [programs, setPrograms] = useState<Program[]>([]);
  const [editing, setEditing] = useState<Program | null>(null);
  const [draft, setDraft] = useState<ProgramInput>(blank);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<Program | null>(null);
  const [revision, setRevision] = useState(0);
  const mounted = useRef(true);
  const { confirmDiscard, discardDialog } = useDiscardConfirmation();
  const { blocker, dirty, resetBaseline } = useUnsavedChanges(draft, pending);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!isAdmin) return;
    let active = true;
    setLoading(true);
    setError("");
    void getPrograms()
      .then((value) => {
        if (active) setPrograms(value);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "Unable to load programs.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAdmin, revision]);
  const changeEditor = async (program: Program | null) => {
    if (pending || (dirty && !(await confirmDiscard("Discard this program editor’s changes?"))))
      return;
    const next = program
      ? {
          name: program.name,
          delivering_hei: program.delivering_hei || "",
          description: program.description || "",
        }
      : blank();
    resetBaseline(next);
    setDraft(next);
    setEditing(program);
    setError("");
  };
  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    if (!draft.name.trim()) {
      setError("Program name is required.");
      return;
    }
    setPending(true);
    setError("");
    try {
      const input = editing
        ? { ...draft, name: draft.name.trim() }
        : {
            ...draft,
            name: recordText(draft.name.trim()),
            delivering_hei: recordText(draft.delivering_hei || ""),
            description: recordText(draft.description || ""),
          };
      const saved = editing
        ? await updateProgram(editing.id, input, editing.revision)
        : await createProgram(input);
      if (!mounted.current) return;
      setPrograms((current) =>
        [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      const next = blank();
      resetBaseline(next);
      setDraft(next);
      setEditing(null);
    } catch (caught) {
      if (mounted.current)
        setError(caught instanceof Error ? caught.message : "Unable to save the program.");
    } finally {
      if (mounted.current) setPending(false);
    }
  };
  const duplicate = async (program: Program) => {
    if (pending) return;
    setPending(true);
    setError("");
    try {
      const copy = await duplicateCatalogProgram(program.id);
      if (mounted.current)
        setPrograms((current) => [...current, copy].sort((a, b) => a.name.localeCompare(b.name)));
    } catch (caught) {
      if (mounted.current)
        setError(caught instanceof Error ? caught.message : "Unable to duplicate the program.");
    } finally {
      if (mounted.current) setPending(false);
    }
  };
  const remove = async (program: Program) => {
    if (pending) return;
    setDeleteCandidate(null);
    setPending(true);
    setError("");
    try {
      await deleteProgram(program.id);
      if (!mounted.current) return;
      setPrograms((current) => current.filter((item) => item.id !== program.id));
      if (editing?.id === program.id) {
        const next = blank();
        resetBaseline(next);
        setDraft(next);
        setEditing(null);
      }
    } catch (caught) {
      if (mounted.current)
        setError(caught instanceof Error ? caught.message : "Unable to delete the program.");
    } finally {
      if (mounted.current) setPending(false);
    }
  };
  if (!isAdmin)
    return (
      <div className="notice" role="status">
        Program catalog management is available to administrators.
        <Link to="/settings">Back to Settings</Link>
      </div>
    );
  return (
    <div className="stack-md">
      <UnsavedChangesDialog
        blocker={blocker}
        pending={pending}
        pendingTitle="Updating the program catalog"
        pendingDescription="A catalog operation is still being processed. Wait for confirmation before leaving."
      />
      {discardDialog}
      <ConfirmationDialog
        open={deleteCandidate !== null}
        title="Delete program?"
        description={
          deleteCandidate
            ? `Delete ${deleteCandidate.name} (#${deleteCandidate.id})? Programs with scholar history cannot be deleted.`
            : ""
        }
        confirmLabel="Delete program"
        cancelLabel="Keep program"
        onConfirm={() => {
          if (deleteCandidate) void remove(deleteCandidate);
        }}
        onCancel={() => setDeleteCandidate(null)}
      />
      <PageHeading
        title="Program catalog"
        actions={
          <Link className="text-button" to="/office-guide">
            Office Guide
          </Link>
        }
      />
      <FormError message={error} />
      {loading && <p role="status">Loading programs…</p>}
      <form
        className="data-card stack-md no-print record-editor"
        onSubmit={(event) => void save(event)}
      >
        <h2>{editing ? `Edit program #${editing.id}` : "Add program"}</h2>
        <fieldset className="entry-grid" disabled={pending}>
          <label className="entry-wide">
            Program name *
            <RecordInput
              required
              value={draft.name}
              onValueChange={(value) => setDraft((current) => ({ ...current, name: value }))}
            />
          </label>
          <label className="entry-wide">
            Default delivering HEI
            <RecordInput
              value={draft.delivering_hei || ""}
              onValueChange={(value) =>
                setDraft((current) => ({
                  ...current,
                  delivering_hei: value,
                }))
              }
            />
          </label>
          <label className="entry-wide">
            Description
            <RecordTextarea
              value={draft.description || ""}
              onValueChange={(value) => setDraft((current) => ({ ...current, description: value }))}
            />
          </label>
        </fieldset>
        <div className="action-group">
          <button type="submit" className="btn primary" disabled={pending}>
            {pending ? "Processing…" : editing ? "Save program" : "Add program"}
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={pending}
            onClick={() => void changeEditor(null)}
          >
            Clear editor
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={pending}
            onClick={() => setRevision((value) => value + 1)}
          >
            Refresh catalog
          </button>
        </div>
      </form>
      <section className="data-card">
        <h2>Existing programs</h2>
        <p>{programs.length} programs</p>
        <TableRegion label="Program catalog">
          <table>
            <thead>
              <tr>
                <th>Program</th>
                <th>Default HEI</th>
                <th>Description</th>
                <th className="no-print">Actions</th>
              </tr>
            </thead>
            <tbody>
              {programs.map((program) => (
                <tr key={program.id}>
                  <td>
                    <strong className="record-value">{program.name}</strong>
                    <small>Program #{program.id}</small>
                    {program.identity_conflict && (
                      <span className="warning-chip">Identity review</span>
                    )}
                  </td>
                  <td className="record-value">{program.delivering_hei || "—"}</td>
                  <td className="record-value">{program.description || "—"}</td>
                  <td className="no-print">
                    <div className="action-group">
                      <button
                        type="button"
                        className="btn secondary"
                        disabled={pending}
                        onClick={() => void changeEditor(program)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="btn secondary"
                        disabled={pending}
                        onClick={() => void duplicate(program)}
                      >
                        Duplicate
                      </button>
                      <button
                        type="button"
                        className="btn secondary danger"
                        disabled={pending}
                        onClick={() => setDeleteCandidate(program)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      </section>
    </div>
  );
}
