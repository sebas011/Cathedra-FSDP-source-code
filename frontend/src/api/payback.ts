import { request, download } from "./client";

export interface ContractFollowUp {
  scholar_id:number; scholar_name:string; department:string|null;
  participation_id:number; program_name:string; academic_year:string|null;
  recorded_status:string; contract_completed_on:string|null; grace_ends_on:string|null;
  attention:string; days_remaining:number|null;
}
export interface PaybackData { total?:number; page?:number; page_size?:number; as_of:string; items:ContractFollowUp[]; scholar_counts:Record<string,number>; grant_counts:Record<string,number>; }
export async function getPayback(department:string, year:string, attention="", page?:number):Promise<PaybackData> {
  return request<PaybackData>(`/fsdp/payback?${new URLSearchParams({department,start_academic_year:year,attention,...(page ? {page:String(page),page_size:"50"} : {})})}`);
}
export async function downloadPayback(department:string, year:string, attention:string) {
  return download(`/fsdp/payback.csv?${new URLSearchParams({department,start_academic_year:year,attention})}`,"cathedra-payback-follow-up.csv");
}
