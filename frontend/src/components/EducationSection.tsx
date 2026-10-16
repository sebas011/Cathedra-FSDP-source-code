import { useState } from "react";
import type { EducationInput } from "../types";
import TableRegion from "./TableRegion";
import { useDiscardConfirmation } from "../hooks/useDiscardConfirmation";
import { recordText, uppercaseEducation } from "../utils/recordText";
import IconAction from "./IconAction";
import { EditIcon, PlusIcon, TrashIcon } from "./Icons";

const blank = (): EducationInput => ({
  level: "",
  degree: "",
  institution: "",
  graduation_year: null,
});
const levels = ["Bachelor’s", "Master’s", "Ph.D.", "Other"];
const equivalentLevel = (value: string, standard: string) =>
  value.trim().toLowerCase() === standard.toLowerCase();
export default function EducationSection({
  entries,
  onChange,
  onDraftChange,
}: {
  entries: EducationInput[];
  onChange: (entries: EducationInput[]) => void;
  onDraftChange: (draft: EducationInput | null) => void;
}) {
  const [draft, setDraft] = useState<EducationInput | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const { confirmDiscard, discardDialog } = useDiscardConfirmation();
  const change = (value: EducationInput | null) => {
    setDraft(value);
    onDraftChange(value);
  };
  const open = async (index: number | null) => {
    if (
      draft &&
      !(await confirmDiscard(
        "Discard this education editor’s changes? Saved entries in this form will stay unchanged.",
      ))
    )
      return;
    setEditing(index);
    change(index === null ? blank() : { ...entries[index] });
  };
  const save = () => {
    if (!draft) return;
    const saved = editing === null ? uppercaseEducation(draft) : draft;
    onChange(
      editing === null
        ? [...entries, { ...saved, client_key: crypto.randomUUID() }]
        : entries.map((item, index) => (index === editing ? saved : item)),
    );
    change(null);
    setEditing(null);
  };
  return (
    <section className="entry-section" tabIndex={-1} id="scholar-education">
      {discardDialog}
      <header>
        <div>
          <h2>Education background</h2>
        </div>
      </header>
      <TableRegion label="Scholar education">
        <table className="entry-grant-table">
          <thead>
            <tr>
              <th scope="col">Degree / level</th>
              <th scope="col">Institution</th>
              <th scope="col">Graduation year</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {!entries.length ? (
              <tr>
                <td colSpan={4} className="empty-table">
                  No education entries recorded.
                </td>
              </tr>
            ) : (
              entries.map((item, index) => (
                <tr key={item.id || item.client_key || index}>
                  <td>
                    <strong className="record-value">{item.degree || "Degree not recorded"}</strong>
                    <small>{item.level || "Level not recorded"}</small>
                    {item.source_program_id && <small>Added from completed program</small>}
                  </td>
                  <td className="record-value">{item.institution || "Not recorded"}</td>
                  <td>{item.graduation_year || "Not recorded"}</td>
                  <td>
                    <div className="action-group">
                      <IconAction
                        label={`Edit education ${index + 1}`}
                        onClick={() => void open(index)}
                      >
                        <EditIcon />
                      </IconAction>
                      <IconAction
                        label={`Remove education ${index + 1}`}
                        onClick={() =>
                          void (async () => {
                            if (
                              !(await confirmDiscard(
                                "Remove this education entry? This is stored when you save the scholar.",
                              ))
                            )
                              return;
                            onChange(entries.filter((_, i) => i !== index));
                            if (editing === index) {
                              change(null);
                              setEditing(null);
                            } else if (editing !== null && editing > index) setEditing(editing - 1);
                          })()
                        }
                      >
                        <TrashIcon />
                      </IconAction>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </TableRegion>
      {!draft ? (
        <IconAction label="Add education" className="entry-add" onClick={() => void open(null)}>
          <PlusIcon />
        </IconAction>
      ) : (
        <section className="grant-entry" aria-label="Education editor">
          <header>
            <div>
              <span className="eyebrow">Education entry</span>
              <h3>{editing === null ? "New education details" : "Edit education details"}</h3>
            </div>
            <span className="entry-stage">Draft</span>
          </header>
          <div className="entry-grid">
            <label>
              Degree level
              <select
                value={draft.level}
                onChange={(event) => change({ ...draft, level: event.target.value })}
              >
                <option value="">Not recorded</option>
                {levels.map((level) => (
                  <option
                    key={level}
                    value={equivalentLevel(draft.level, level) ? draft.level : level}
                  >
                    {level}
                  </option>
                ))}
                {draft.level && !levels.some((level) => equivalentLevel(draft.level, level)) && (
                  <option>{draft.level}</option>
                )}
              </select>
            </label>
            <label>
              Degree
              <input
                value={draft.degree}
                onChange={(event) => change({ ...draft, degree: recordText(event.target.value) })}
              />
            </label>
            <label>
              Institution
              <input
                value={draft.institution}
                onChange={(event) =>
                  change({ ...draft, institution: recordText(event.target.value) })
                }
              />
            </label>
            <label>
              Graduation year
              <input
                value={draft.graduation_year || ""}
                onChange={(event) =>
                  change({ ...draft, graduation_year: event.target.value || null })
                }
              />
            </label>
          </div>
          <footer>
            <div className="action-group">
              <button
                type="button"
                className="btn secondary"
                onClick={() =>
                  void (async () => {
                    if (await confirmDiscard("Discard this education editor’s changes?")) {
                      change(null);
                      setEditing(null);
                    }
                  })()
                }
              >
                Cancel education
              </button>
              <button type="button" className="btn primary" onClick={save}>
                {editing === null ? "Save education" : "Update education"}
              </button>
            </div>
          </footer>
        </section>
      )}
    </section>
  );
}
