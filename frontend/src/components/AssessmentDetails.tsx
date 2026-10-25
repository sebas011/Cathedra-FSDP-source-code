import "../assessment-details.css";

export default function AssessmentDetails({
  reason,
  assessedOn,
  deadlineBasis,
}: {
  reason?: string | null;
  assessedOn?: string | null;
  deadlineBasis?: string | null;
}) {
  if (!reason) return null;
  return (
    <details className="assessment-details">
      <summary>Assessment details</summary>
      <p>{reason}</p>
      {deadlineBasis && (
        <p className="assessment-context">
          <span>Deadline based on</span>
          {deadlineBasis}
        </p>
      )}
      {assessedOn && (
        <p className="assessment-context">
          <span>Assessed on</span>
          {assessedOn}
        </p>
      )}
    </details>
  );
}
