import type { ParticipationInput, ParticipationRead } from "../types";
import { copyAnnualGrant } from "./annualGrant";

type Grant = ParticipationInput | ParticipationRead;
export const applicationIdentity = (grant: Grant) =>
  `${"program_id" in grant ? grant.program_id : (grant.source_program_id ?? grant.program_name.trim().toLocaleUpperCase())}::${grant.application_key || "legacy"}`;
export const grantPeriod = (term: string | null | undefined, year: string | null | undefined) =>
  [term, year].filter(Boolean).join(" ") || "Period not recorded";
const periodOrder = (term: string | null, year: string | null) =>
  Number(year?.match(/^\d{4}/)?.[0] || 0) * 10 +
  Math.max(0, ["1st", "2nd", "3rd", "Summer"].indexOf(term || ""));
export function applicationPeriod(grants: Grant[]) {
  const starts = grants
    .filter((grant) => grant.start_academic_year)
    .sort(
      (a, b) =>
        periodOrder(a.start_term, a.start_academic_year) -
        periodOrder(b.start_term, b.start_academic_year),
    );
  const ends = grants
    .filter((grant) => grant.end_academic_year)
    .sort(
      (a, b) =>
        periodOrder(b.end_term, b.end_academic_year) - periodOrder(a.end_term, a.end_academic_year),
    );
  return `${grantPeriod(starts[0]?.start_term, starts[0]?.start_academic_year)} — ${grantPeriod(ends[0]?.end_term, ends[0]?.end_academic_year)}`;
}
export function newProgramApplication(
  grant: ParticipationInput,
  application: ParticipationInput[] = [grant],
): ParticipationInput {
  const first =
    [...application]
      .filter((item) => item.start_academic_year)
      .sort(
        (a, b) =>
          periodOrder(a.start_term, a.start_academic_year) -
          periodOrder(b.start_term, b.start_academic_year),
      )[0] || grant;
  const last =
    [...application]
      .filter((item) => item.end_academic_year)
      .sort(
        (a, b) =>
          periodOrder(b.end_term, b.end_academic_year) -
          periodOrder(a.end_term, a.end_academic_year),
      )[0] ||
    [...application].sort(
      (a, b) =>
        periodOrder(b.start_term, b.start_academic_year) -
        periodOrder(a.start_term, a.start_academic_year),
    )[0] ||
    grant;
  const copy = copyAnnualGrant(grant);
  const start = Number(first.start_academic_year.match(/^\d{4}/)?.[0] || 0);
  const end = Number(
    (last.end_academic_year || last.start_academic_year).match(/^\d{4}/)?.[0] || 0,
  );
  const next = end ? end + 1 : start ? start + 1 : 0;
  const duration = start && end >= start ? end - start : 0;
  const year = (value: number) => (value > 0 && value < 9999 ? `${value}-${value + 1}` : "");
  return {
    ...copy,
    application_key: crypto.randomUUID(),
    start_term: first.start_term,
    end_term: last.end_term,
    start_academic_year: year(next),
    end_academic_year: year(next ? next + duration : 0),
    remarks: "",
  };
}

export function inputApplicationGroups(grants: ParticipationInput[]) {
  const groups = new Map<string, ParticipationInput[]>();
  for (const grant of grants) {
    const key = applicationIdentity(grant);
    groups.set(key, [...(groups.get(key) || []), grant]);
  }
  return [...groups.entries()];
}
