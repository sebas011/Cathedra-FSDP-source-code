import type { ActivityChange } from "../types";
import "../history.css";

const fieldNames: Record<string, string> = {
  name: "Name",
  age: "Age",
  previous_degree: "Previous degree",
  department: "College / Staff",
  personnel_type: "Personnel type",
  rank: "Rank / position",
  tenure: "Recorded tenure",
  tenure_years: "Tenure in years",
  tenure_note: "Tenure note",
  profile_remarks: "Profile remarks",
  missing_requirements: "Requirements follow-up",
  has_hard_copy: "Hard copy",
  has_soft_copy: "Soft copy",
  program_category: "Program category",
  delivering_hei: "Delivering HEI",
  start_date: "Program start date",
  end_date: "End date",
  start_term: "Starting term",
  start_academic_year: "Starting year",
  end_term: "Ending term",
  end_academic_year: "Ending year",
  contract_completed_on: "Previously recorded completion date",
  allowed_duration_years: "Allowed duration in years",
  completion_due_on: "Completion deadline",
  graduation_date: "Graduation date",
  grant_type: "Grant type",
  grant_other: "Other grant type",
  extension: "Extension",
  status: "Status",
  case_status: "Case status",
  payback_payment_status: "Payback payment progress",
  remarks: "Remarks",
  degree: "Degree",
  level: "Degree level",
  institution: "Institution",
  graduation_year: "Graduation year",
  requirement_name: "Requirement",
  due_date: "Due date",
  is_complete: "Complete",
  completed_at: "Completed at",
  description: "Description",
};

function fieldLabel(field: string) {
  return (
    fieldNames[field] || field.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())
  );
}

function valueLabel(value: ActivityChange["before"]) {
  if (value === null) return "Not recorded";
  if (value === "") return "Empty text";
  if (value === true) return "Yes";
  if (value === false) return "No";
  return String(value);
}

const isValue = (value: unknown) =>
  value === null ||
  typeof value === "string" ||
  typeof value === "boolean" ||
  (typeof value === "number" && Number.isFinite(value));

export default function ChangeDetails({ changes }: { changes?: ActivityChange[] }) {
  const rows = Array.isArray(changes)
    ? changes.filter(
        (change) =>
          change &&
          typeof change.field === "string" &&
          isValue(change.before) &&
          isValue(change.after),
      )
    : [];
  if (!rows.length) return null;
  return (
    <details className="change-comparison">
      <summary>View previous and new values</summary>
      <dl className="change-value-list">
        {rows.map((change, index) => (
          <div className="change-value-group" key={`${change.field}-${index}`}>
            <dt>{fieldLabel(change.field)}</dt>
            <dd>
              <span className="change-value-label">Previous</span>
              <span className="change-value-text">{valueLabel(change.before)}</span>
              {change.before_truncated && <small>Preview truncated</small>}
            </dd>
            <dd>
              <span className="change-value-label">New</span>
              <span className="change-value-text">{valueLabel(change.after)}</span>
              {change.after_truncated && <small>Preview truncated</small>}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
