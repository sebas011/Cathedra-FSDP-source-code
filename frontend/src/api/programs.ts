import { request } from "./client";
export interface Program { id: number; revision: number; name: string; delivering_hei: string | null; description: string | null; identity_conflict?: boolean; }
export type ProgramInput = Pick<Program, "name" | "delivering_hei" | "description">;
export const getPrograms = () => request<Program[]>("/fsdp/programs");
export const createProgram = (payload: ProgramInput) => request<Program>("/fsdp/programs", { method: "POST", body: JSON.stringify(payload) });
export const updateProgram = (id: number, payload: ProgramInput, revision: number) => request<Program>(`/fsdp/programs/${id}`, { method: "PUT", headers: { "If-Match": String(revision) }, body: JSON.stringify(payload) });
export const deleteProgram = (id: number) => request<void>(`/fsdp/programs/${id}`, { method: "DELETE" });
export const duplicateCatalogProgram = (id: number) => request<Program>(`/fsdp/programs/${id}/duplicate`, { method: "POST" });
