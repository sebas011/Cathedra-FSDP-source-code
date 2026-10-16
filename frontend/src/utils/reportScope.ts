export const reportFilters = (params: URLSearchParams) => ({
  start_academic_year: params.get("start_academic_year") || "",
  department: params.get("department") || "",
  rank: params.get("rank") || "",
  status: params.get("status") || "",
  grant_type: params.get("grant_type") || "",
  delivering_hei: params.get("delivering_hei") || "",
  missing_requirements: params.get("missing_requirements") === "true",
});
export const reportView = (params: URLSearchParams) =>
  ["overview", "actions", "directory"].includes(params.get("view") || "")
    ? params.get("view")!
    : "overview";
export const reportScopeLabel = (filters: ReturnType<typeof reportFilters>) =>
  Object.entries(filters)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value === true ? "Yes" : value}`)
    .join(" · ") || "All scholars";
