import { displayGrantStatus, grantStatuses } from "../utils/statuses";
import { recordText } from "../utils/recordText";
import AcademicYearInput from "./AcademicYearInput";
import type { ParticipationInput } from "../types";
import FormError from "./FormError";

const statuses = grantStatuses;
const grantTypes = [
  "Full Scholarship",
  "Partial Scholarship",
  "Dissertation Aid",
  "Thesis Aid",
  "Others",
] as const;

export default function GrantEntry({
  draft,
  update,
  error,
  editing,
  save,
  cancel,
  applications = [],
}: {
  applications?: { key: string | null; programId?: number; label: string }[];
  draft: ParticipationInput;
  update: (changes: Partial<ParticipationInput>) => void;
  error: string;
  editing: boolean;
  save: () => void;
  cancel: () => void;
}) {
  const applicationIndex = applications.findIndex(
    (item) =>
      item.key === (draft.application_key || null) &&
      (!draft.source_program_id || item.programId === draft.source_program_id),
  );
  return (
    <section className="grant-entry" aria-label="Grant editor">
      <header>
        <div>
          <span className="eyebrow">Grant entry</span>
          <h3>{editing ? "Edit grant details" : "New grant details"}</h3>
        </div>
        <span className="entry-stage">Draft</span>
      </header>
      <FormError message={error} />
      <div className="entry-grid">
        <label className="entry-wide">
          Program Applied *
          <input
            value={draft.program_name}
            onChange={(event) =>
              update({ program_name: recordText(event.target.value), source_program_id: undefined })
            }
          />
        </label>
        <label>
          Program category
          <select
            value={draft.program_category || ""}
            onChange={(event) => update({ program_category: event.target.value || null })}
          >
            <option value="">Not recorded</option>
            {["Degree", "Certification", "Enhancement"].map((category) => (
              <option key={category}>{category}</option>
            ))}
            {draft.program_category &&
              !["Degree", "Certification", "Enhancement"].includes(draft.program_category) && (
                <option>{draft.program_category}</option>
              )}
          </select>
        </label>
        {!!applications.length && (
          <label>
            Application
            <select
              value={applicationIndex < 0 ? "new" : String(applicationIndex)}
              onChange={(event) => {
                const selected = applications[Number(event.target.value)];
                update(
                  event.target.value === "new"
                    ? { application_key: crypto.randomUUID() }
                    : { application_key: selected.key, source_program_id: selected.programId },
                );
              }}
            >
              <option value="new">New application</option>
              {applications.map((item, index) => (
                <option key={`${item.programId}-${item.key || "legacy"}`} value={String(index)}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Delivering HEI
          <input
            value={draft.delivering_hei}
            onChange={(event) => update({ delivering_hei: recordText(event.target.value) })}
          />
        </label>
        <label>
          Type of Grant
          <select
            value={draft.grant_type || ""}
            onChange={(event) =>
              update({
                grant_type: (event.target.value || null) as ParticipationInput["grant_type"],
              })
            }
          >
            <option value="">Not recorded</option>
            {draft.grant_type && !grantTypes.some((item) => item === draft.grant_type) && (
              <option>{draft.grant_type}</option>
            )}
            {grantTypes.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        {draft.grant_type === "Others" && (
          <label className="entry-wide">
            Other Grant
            <input
              value={draft.grant_other}
              onChange={(event) => update({ grant_other: recordText(event.target.value) })}
            />
          </label>
        )}
        <label className="entry-wide">
          Extension
          <input
            value={draft.extension}
            onChange={(event) => update({ extension: recordText(event.target.value) })}
          />
        </label>
      </div>
      <div className="entry-periods">
        <fieldset>
          <legend>Starting period</legend>
          <label>
            Start Term
            <select
              value={draft.start_term}
              onChange={(event) => update({ start_term: event.target.value })}
            >
              <option value="">Not recorded</option>
              {["1st", "2nd", "3rd", "Summer"].map((term) => (
                <option key={term}>{term}</option>
              ))}
            </select>
          </label>
          <label>
            Start Academic Year
            <AcademicYearInput
              placeholder="2026-2027"
              value={draft.start_academic_year}
              onValueChange={(start_academic_year) => update({ start_academic_year })}
            />
          </label>
        </fieldset>
        <fieldset>
          <legend>Contract end period</legend>
          <label>
            Contract End Term
            <select
              value={draft.end_term}
              onChange={(event) => update({ end_term: event.target.value })}
            >
              <option value="">Not recorded</option>
              {["1st", "2nd", "3rd", "Summer"].map((term) => (
                <option key={term}>{term}</option>
              ))}
            </select>
          </label>
          <label>
            Contract End Academic Year
            <AcademicYearInput
              placeholder="2026-2027"
              value={draft.end_academic_year}
              onValueChange={(end_academic_year) => update({ end_academic_year })}
            />
          </label>
        </fieldset>
      </div>
      <div className="entry-grid">
        <label>
          Contract completion date (optional)
          <input
            type="date"
            aria-label="Contract completion date (optional)"
            value={draft.contract_completed_on || ""}
            onChange={(event) => update({ contract_completed_on: event.target.value || null })}
          />
        </label>
        <label>
          Graduation date (optional)
          <input
            type="date"
            value={draft.graduation_date || ""}
            onChange={(event) => update({ graduation_date: event.target.value || null })}
          />
        </label>
      </div>
      <label>
        Remarks
        <textarea
          rows={3}
          value={draft.remarks}
          onChange={(event) => update({ remarks: recordText(event.target.value) })}
        />
      </label>
      <div className="entry-grid">
        <label>
          Status
          <select
            value={displayGrantStatus(draft.status)}
            onChange={(event) => update({ status: event.target.value })}
          >
            {!statuses.includes(displayGrantStatus(draft.status)) && (
              <option>{displayGrantStatus(draft.status)}</option>
            )}
            {statuses.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Case status
          <select
            value={draft.case_status || "Open"}
            onChange={(event) => update({ case_status: event.target.value as "Open" | "Closed" })}
          >
            <option>Open</option>
            <option>Closed</option>
          </select>
        </label>
      </div>
      <footer>
        <div className="action-group">
          <button type="button" className="btn secondary" onClick={cancel}>
            Cancel
          </button>
          <button type="button" className="btn primary" onClick={save}>
            {editing ? "Update Grant" : "Save Grant"}
          </button>
        </div>
      </footer>
    </section>
  );
}
