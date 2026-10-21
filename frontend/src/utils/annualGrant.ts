import type { ParticipationInput } from "../types";
import { formatAcademicYear } from "./dates";
function nextYear(value: string) {
  const singleYear = value.trim();
  if (/^\d{4}$/.test(singleYear) && Number(singleYear) < 9999) {
    return String(Number(singleYear) + 1).padStart(4, "0");
  }
  return formatAcademicYear(value).replace(
    /^(\d{4})(\s*[-–]\s*)(\d{4})$/,
    (_, start, separator, end) => `${Number(start) + 1}${separator}${Number(end) + 1}`,
  );
}
export function copyAnnualGrant(grant: ParticipationInput): ParticipationInput {
  const hasCompletionRule = grant.allowed_duration_years != null || !!grant.completion_due_on;
  return {
    ...grant,
    id: undefined,
    client_key: undefined,
    start_date: hasCompletionRule ? grant.start_date : null,
    end_date: null,
    contract_completed_on: null,
    completion_due_on: grant.completion_due_on ?? null,
    payback_payment_status: null,
    graduation_date: null,
    status: "On Going",
    case_status: "Open",
    extension: "",
    start_academic_year: nextYear(grant.start_academic_year),
    end_academic_year: nextYear(grant.end_academic_year),
  };
}
