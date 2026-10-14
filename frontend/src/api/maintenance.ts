import { request, download } from "./client";
import type { BackupResult, MaintenanceStatus } from "../types";
export const recordBackupReview = (filename:string, restoreTested:boolean) => request<{recorded:boolean}>(`/maintenance/backups/${encodeURIComponent(filename)}/review`, {method:"POST",body:JSON.stringify({copied_off_device:true,restore_tested:restoreTested})});

export const getMaintenanceStatus = () => request<MaintenanceStatus>("/maintenance/status")
export const createDatabaseBackup = () => request<BackupResult>("/maintenance/backups", { method: "POST" })
export const restoreDatabase = (filename:string) => request<{restored_from:string;safety_backup:string}>("/maintenance/restore", {method:"POST",body:JSON.stringify({filename})});
export const deleteDatabaseBackup = (filename:string) => request<void>(`/maintenance/backups/${encodeURIComponent(filename)}`, {method:"DELETE"});
export const setBackupProtection = (filename:string, protect:boolean) => request<void>(`/maintenance/backups/${encodeURIComponent(filename)}/protection`, {method:protect?"POST":"DELETE"});
export const downloadDatabaseBackup = (filename:string) => download(`/maintenance/backups/${encodeURIComponent(filename)}/download`, filename);
export const downloadExport = (kind:"fsdp"|"education", filename:string) => download(`/maintenance/exports/${kind}.csv`, filename);
