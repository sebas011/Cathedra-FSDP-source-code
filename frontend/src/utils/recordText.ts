import type { EducationInput, ParticipationInput, ScholarPayload } from "../types";

/** New or edited record text is uppercase; credentials and controlled values are separate. */
export const recordText = (value: string) => value.toUpperCase();

export function uppercaseEducation(entry: EducationInput): EducationInput {
  return { ...entry, degree: recordText(entry.degree), institution: recordText(entry.institution) };
}

export function uppercaseGrant(grant: ParticipationInput): ParticipationInput {
  return { ...grant, program_name: recordText(grant.program_name), delivering_hei: recordText(grant.delivering_hei),
    grant_other: recordText(grant.grant_other), extension: recordText(grant.extension), remarks: recordText(grant.remarks) };
}

export function uppercaseScholar(form: ScholarPayload): ScholarPayload {
  return { ...form, name: recordText(form.name), previous_degree: recordText(form.previous_degree),
    rank: recordText(form.rank), tenure: recordText(form.tenure), tenure_note: form.tenure_note == null ? form.tenure_note : recordText(form.tenure_note),
    profile_remarks: form.profile_remarks == null ? form.profile_remarks : recordText(form.profile_remarks),
    education: form.education?.map(uppercaseEducation), participations: form.participations.map(uppercaseGrant),
    requirements: form.requirements.map(entry => ({ ...entry, requirement_name: recordText(entry.requirement_name), remarks: recordText(entry.remarks) })) };
}
