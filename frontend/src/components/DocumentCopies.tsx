export const copyAvailability = (value: boolean | null | undefined) =>
  value == null ? "Not recorded" : value ? "Available" : "Not available";

export function DocumentCopyFields({
  hard,
  soft,
  onChange,
}: {
  hard?: boolean | null;
  soft?: boolean | null;
  onChange: (change: { has_hard_copy?: boolean | null; has_soft_copy?: boolean | null }) => void;
}) {
  const field = (
    name: "has_hard_copy" | "has_soft_copy",
    label: string,
    value?: boolean | null,
  ) => (
    <label>
      {label}
      <select
        value={value == null ? "" : String(value)}
        onChange={(event) =>
          onChange({ [name]: event.target.value === "" ? null : event.target.value === "true" })
        }
      >
        <option value="">Not recorded</option>
        <option value="true">Available</option>
        <option value="false">Not available</option>
      </select>
    </label>
  );
  return (
    <fieldset className="entry-grid">
      <legend>Profile documents</legend>
      {field("has_hard_copy", "Hard copy", hard)}
      {field("has_soft_copy", "Soft copy", soft)}
    </fieldset>
  );
}
