import { download, request } from "./client";

export type OfficeLogKind = "Note" | "Document received" | "Document transferred";
export type OfficeLogInput = {
  scholar_id?: number | null;
  occurred_on?: string | null;
  entry_type: OfficeLogKind;
  note: string;
  document_name?: string | null;
  from_department?: string | null;
  to_department?: string | null;
};
export type OfficeLogItem = OfficeLogInput & {
  id: number;
  scholar_id: number | null;
  scholar_name: string | null;
  user_id: number;
  username: string;
  occurred_on: string;
  created_at: string;
};
export type OfficeLogFilters = {
  scholar_id?: number;
  search?: string;
  entry_type?: string;
  page?: number;
};
export type OfficeLogPage = {
  items: OfficeLogItem[];
  total: number;
  page: number;
  page_size: number;
};
const query = (filters: OfficeLogFilters) => {
  const values = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") values.set(key, String(value));
  });
  return values.toString();
};
export const getOfficeLogs = (filters: OfficeLogFilters) =>
  request<OfficeLogPage>(`/office-logs?${query(filters)}`);
export const addOfficeLog = (input: OfficeLogInput, requestKey: string) =>
  request<OfficeLogItem>("/office-logs", {
    method: "POST",
    body: JSON.stringify(input),
    headers: { "Idempotency-Key": requestKey },
  });
export const exportOfficeLogs = (filters: OfficeLogFilters) => {
  const { page: _page, ...scope } = filters;
  return download(`/office-logs/export.csv?${query(scope)}`, "cathedra-office-log.csv");
};
