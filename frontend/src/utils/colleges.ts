export const colleges = ["CIT", "CAS", "COED", "COE", "CCJ", "COF", "CBMA", "CCS"] as const;
export const affiliations = [...colleges, "Staff", "Unknown"];
export function scholarAffiliation(value: string | null | undefined) {
  const label = (value || "").trim().toUpperCase();
  if (!label || ["UNKNOWN", "NOT RECORDED"].includes(label)) return "Unknown";
  return colleges.some((college) => college === label) ? label : "Staff";
}

export function personnelType(value: string | null | undefined): "Faculty" | "Staff" | "Unknown" {
  const label = scholarAffiliation(value);
  return label === "Unknown" ? "Unknown" : label === "Staff" ? "Staff" : "Faculty";
}
