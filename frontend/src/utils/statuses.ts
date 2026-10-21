export const grantStatuses = [
  "On Going",
  "Incomplete",
  "Completed",
  "Payback",
  "Payback pending contract",
  "Transferred",
  "Withdrawn",
  "Did Not Avail",
];
export const displayGrantStatus = (status: string | null | undefined) =>
  status === "Graduated" ? "Completed" : status || "No grant record";
export const completedCount = (counts: Record<string, number>) =>
  counts.Completed ?? counts.Graduated ?? 0;
