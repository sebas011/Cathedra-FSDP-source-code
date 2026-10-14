import { request, download } from "./client";
import type { ActivityEvent } from "../types";

export type NameMatch = { id: number; name: string; department: string | null; reason: string; score: number };
export const getScholarNameMatches = (name: string, excludeId?: number) => request<NameMatch[]>(`/fsdp/name-matches?${new URLSearchParams({name, ...(excludeId ? {exclude_id: String(excludeId)} : {})})}`);
export const getScholarHistory = (id: number, page = 1) => request<import("../types").PagedResult<ActivityEvent>>(`/activity/scholars/${id}?page=${page}&page_size=20`);
import type { FsdpAnalytics, FsdpReport, FsdpSummary, PagedResult, Scholar, ScholarPayload } from "../types";

export const getFsdpRecords = (search = "", status = "", page = 1, missing = "") => request<PagedResult<Scholar>>(`/fsdp/page?${new URLSearchParams({ search, status, missing, page: String(page), page_size: "50" })}`)
export const getFsdpSummary = () => request<FsdpSummary>("/fsdp/summary")
export const getFsdpAnalytics = (department = "", startAcademicYear = "") => request<FsdpAnalytics>(`/fsdp/analytics?${new URLSearchParams({department,start_academic_year:startAcademicYear})}`);
export const getFsdpRecord = (id: number) => request<Scholar>(`/fsdp/${id}`)
export const createFsdpRecord = (payload: ScholarPayload, requestKey?:string) => request<Scholar>("/fsdp", { method: "POST", headers: requestKey ? {"Idempotency-Key":requestKey} : {}, body: JSON.stringify(payload) })
export const updateFsdpRecord = (id: number, payload: ScholarPayload, revision: number) => request<Scholar>(`/fsdp/${id}`, { method: "PUT", headers: { "If-Match": String(revision) }, body: JSON.stringify(payload) })
export const deleteFsdpRecord = (id: number, revision:number) => request<void>(`/fsdp/${id}`, { method: "DELETE", headers:{"If-Match":String(revision)} });
export const getFsdpReport = (filters:Record<string,string|boolean>) => request<FsdpReport>(`/fsdp/report?${new URLSearchParams(Object.entries(filters).map(([key,value])=>[key,String(value)]))}`);
export const downloadFsdpReport = (filters:Record<string,string|boolean>) => download(`/fsdp/report.csv?${new URLSearchParams(Object.entries(filters).map(([key,value])=>[key,String(value)]))}`, "cathedra-fsdp-report.csv");
export const getFsdpReportOptions = () => request<{departments:string[];ranks:string[];delivering_heis:string[];statuses?:string[];grant_types?:string[]}>("/fsdp/report-options");

export const duplicateProgram = (id:number) => request<{id:number;name:string;delivering_hei:string|null;description:string|null}>(`/fsdp/programs/${id}/duplicate`, {method:"POST"});
export const duplicateGrant = (scholarId:number, grantId:number, revision:number) => request<Scholar>(`/fsdp/${scholarId}/grants/${grantId}/duplicate`, {method:"POST",headers:{"If-Match":String(revision)}});
