import type { ParticipationInput } from "../types";
import { formatAcademicYear } from "./dates";
function nextYear(value: string) {
  return formatAcademicYear(value).replace(
    /^(\d{4})(\s*[-–]\s*)(\d{4})$/,
    (_, start, separator, end) => `${Number(start) + 1}${separator}${Number(end) + 1}`,
  );
}
export function copyAnnualGrant(grant: ParticipationInput): ParticipationInput {
  return {
    ...grant,
    id: undefined,
    client_key: undefined,
    start_date: null,
    end_date: null,
    contract_completed_on: null,
    graduation_date: null,
    status: "On Going",
    case_status: "Open",
    extension: "",
    start_academic_year: nextYear(grant.start_academic_year),
    end_academic_year: nextYear(grant.end_academic_year),
  };
}
