import type { ParticipationInput } from "../types";

export function canonicalTerm(term:string) {
  const key = term.trim().toLowerCase().split(/\s+/)[0];
  return ({"1st":"1st","1":"1st",first:"1st","2nd":"2nd","2":"2nd",second:"2nd","3rd":"3rd","3":"3rd",third:"3rd",summer:"Summer"} as Record<string,string>)[key] || term.trim();
}

export function validateGrant(draft:ParticipationInput):string {
  if (!draft.program_name.trim()) return "Program Applied is required.";
  for (const term of [draft.start_term,draft.end_term]) {
    if (term.trim() && !["1st","2nd","3rd","Summer"].includes(canonicalTerm(term))) return "Choose 1st, 2nd, 3rd or Summer.";
  }
  return "";
}
