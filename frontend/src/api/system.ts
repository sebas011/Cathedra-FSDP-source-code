import { request } from "./client";
import type { ActivityEvent, ServiceHealth } from "../types";

export const getServiceHealth = () => request<ServiceHealth>("/health");
export const exitDesktop = () => request<{status:"closing"}>("/desktop/exit", {method:"POST"});
export const getActivity = () => request<ActivityEvent[]>("/activity");
