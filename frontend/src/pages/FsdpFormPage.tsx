import { UnconfirmedOperationError, getCurrentUser } from "../api/client";
import PageHeading from "../components/PageHeading";
import ConfirmationDialog from "../components/ConfirmationDialog";
import { getScholarNameMatches, type NameMatch } from "../api/fsdp";
import TableRegion from "../components/TableRegion";
import EducationSection from "../components/EducationSection";
import { copyAnnualGrant } from "../utils/annualGrant";
import {
  applicationIdentity,
  applicationPeriod,
  inputApplicationGroups,
  newProgramApplication,
} from "../utils/grantApplications";
import { copyAvailability, DocumentCopyFields } from "../components/DocumentCopies";
import GrantEntry from "../components/GrantEntry";
import { RecordInput, RecordTextarea } from "../components/RecordTextInput";
import NumberInput from "../components/NumberInput";
import IconAction from "../components/IconAction";
import { CopyIcon, EditIcon, PlusIcon, TrashIcon } from "../components/Icons";
import { uppercaseScholar, uppercaseGrant } from "../utils/recordText";
import { formatAcademicYear } from "../utils/dates";
import { displayGrantStatus } from "../utils/statuses";
import { canonicalTerm, validateGrant } from "../utils/grantValidation";
import FormError from "../components/FormError";
import UnsavedChangesDialog from "../components/UnsavedChangesDialog";
import { useDiscardConfirmation } from "../hooks/useDiscardConfirmation";
import PageSkeleton from "../components/PageSkeleton";
import { useUnsavedChanges } from "../hooks/useUnsavedChanges";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createFsdpRecord, getFsdpRecord, updateFsdpRecord } from "../api";
import type {
  EducationInput,
  ParticipationInput,
  RequirementInput,
  ScholarPayload,
} from "../types";
import { affiliations, scholarAffiliation, personnelType } from "../utils/colleges";

const newGrant = (): ParticipationInput => ({
  application_key: null,
  program_category: null,
  program_name: "",
  delivering_hei: "",
  start_date: null,
  end_date: null,
  contract_completed_on: null,
  allowed_duration_years: null,
  completion_due_on: null,
  payback_payment_status: null,
  graduation_date: null,
  case_status: "Open",
  start_term: "",
  start_academic_year: "",
  end_term: "",
  end_academic_year: "",
  grant_type: null,
  grant_other: "",
  status: "On Going",
  extension: "",
  remarks: "",
});
const grantKey = (grant: ParticipationInput) =>
  grant.id ? `saved-${grant.id}` : grant.client_key || "";
const emptyScholar = (): ScholarPayload => ({
  personnel_type: null,
  name: "",
  age: null,
  previous_degree: "",
  missing_requirements: false,
  department: "",
  rank: "",
  tenure: "",
  tenure_years: null,
  tenure_note: "",
  profile_remarks: "",
  has_hard_copy: null,
  has_soft_copy: null,
  education: [],
  participations: [],
  requirements: [],
});

export default function FsdpFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { confirmDiscard, discardDialog } = useDiscardConfirmation();
  const [form, setForm] = useState<ScholarPayload>(emptyScholar);
  const [educationDraft, setEducationDraft] = useState<EducationInput | null>(null);
  const [draft, setDraft] = useState<ParticipationInput>(newGrant);
  const [editingGrant, setEditingGrant] = useState<string | null>(null);
  const [grantEditorOpen, setGrantEditorOpen] = useState(false);
  const [error, setError] = useState("");
  const [grantError, setGrantError] = useState("");
  const [step, setStep] = useState(1);

  const isAdmin = getCurrentUser()?.role === "admin";
  const [saving, setSaving] = useState(false);
  const creationAttempt = useRef<{ key: string; payload: ScholarPayload; userId: number } | null>(
    null,
  );
  const [uncertainSave, setUncertainSave] = useState(false);
  const [suppressedEducation, setSuppressedEducation] = useState<number[]>([]);
  const [nameMatches, setNameMatches] = useState<NameMatch[]>([]);
  const duplicateDecision = useRef<((accepted: boolean) => void) | null>(null);
  useEffect(
    () => () => {
      duplicateDecision.current?.(false);
    },
    [],
  );
  const decideDuplicate = (accepted: boolean) => {
    setNameMatches([]);
    duplicateDecision.current?.(accepted);
    duplicateDecision.current = null;
  };
  const { blocker, resetBaseline, allowLeave } = useUnsavedChanges(
    { form, draft, educationDraft, saving },
    saving,
  );
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const changeStep = (next: number) => {
    if (next === step) return;
    if (educationDraft) {
      setError("Save or cancel the open education entry before changing steps.");
      return;
    }
    if (grantEditorOpen) {
      setError("Save or cancel the open grant before changing steps.");
      return;
    }
    setError("");
    setStep(next);
  };
  useEffect(() => {
    const target = document.getElementById(`scholar-step-${step}`);
    target?.focus({ preventScroll: true });
  }, [step]);
  const [sourceRevision, setSourceRevision] = useState<number | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loadRevision, setLoadRevision] = useState(0);
  const loadForm = (value: ScholarPayload) => {
    setEducationDraft(null);
    resetBaseline({ form: value, draft: newGrant(), educationDraft: null, saving: false });
    setForm(value);
  };

  useEffect(() => {
    let active = true;
    setLoadError("");
    setError("");
    setSourceRevision(null);
    setSuppressedEducation([]);
    setGrantEditorOpen(false);
    setStep(1);
    setEditingGrant(null);
    setDraft(newGrant());
    loadForm(emptyScholar());
    if (!id) return;
    if (!/^\d+$/.test(id) || !Number.isSafeInteger(Number(id)) || Number(id) < 1) {
      setLoadError("This scholar address is invalid. Return to the directory to choose a record.");
      return;
    }
    getFsdpRecord(Number(id))
      .then((scholar) => {
        if (!active) return;
        setSourceRevision(scholar.revision);
        setSuppressedEducation(scholar.suppressed_education_program_ids || []);
        loadForm({
          personnel_type: scholar.personnel_type,
          name: scholar.name,
          age: scholar.age,
          previous_degree: scholar.previous_degree || "",
          missing_requirements:
            scholar.manual_requirements_follow_up ?? scholar.missing_requirements,
          department: scholar.department || "",
          rank: scholar.rank || "",
          tenure: scholar.tenure || "",
          tenure_years: scholar.tenure_years ?? null,
          tenure_note: scholar.tenure_note || "",
          profile_remarks: scholar.profile_remarks || "",
          has_hard_copy: scholar.has_hard_copy ?? null,
          has_soft_copy: scholar.has_soft_copy ?? null,
          education: (scholar.education || []).map((item) => ({ ...item })),
          participations: scholar.participations.map(
            ({
              id: grantId,
              program_id,
              application_key,
              program_category,
              name,
              delivering_hei,
              start_date,
              end_date,
              contract_completed_on,
              allowed_duration_years,
              completion_due_on,
              payback_payment_status,
              graduation_date,
              case_status,
              start_term,
              start_academic_year,
              end_term,
              end_academic_year,
              grant_type,
              grant_other,
              status,
              extension,
              remarks,
            }) => ({
              id: grantId,
              source_program_id: program_id,
              application_key: application_key ?? null,
              program_category: program_category ?? null,
              program_name: name,
              delivering_hei: delivering_hei || "",
              start_date,
              end_date,
              contract_completed_on: contract_completed_on ?? null,
              allowed_duration_years: allowed_duration_years ?? null,
              completion_due_on: completion_due_on ?? null,
              payback_payment_status: payback_payment_status ?? null,
              graduation_date: graduation_date ?? null,
              case_status: case_status || "Open",
              start_term: start_term || "",
              start_academic_year: start_academic_year || "",
              end_term: end_term || "",
              end_academic_year: end_academic_year || "",
              grant_type,
              grant_other: grant_other || "",
              status: displayGrantStatus(status),
              extension: extension || "",
              remarks: remarks || "",
            }),
          ),
          requirements: (scholar.requirements || []).map(
            ({ id: requirementId, requirement_name, due_date, is_complete, remarks }) => ({
              id: requirementId,
              requirement_name,
              due_date,
              is_complete,
              remarks: remarks || "",
            }),
          ),
        });
      })
      .catch((caughtError) => {
        if (active)
          setLoadError(
            caughtError instanceof Error ? caughtError.message : "Unable to load scholar.",
          );
      });
    return () => {
      active = false;
    };
  }, [id, loadRevision]);

  const updateDraft = (changes: Partial<ParticipationInput>) =>
    setDraft((current) => ({ ...current, ...changes }));
  const openNewGrant = () => {
    setDraft({ ...newGrant(), application_key: crypto.randomUUID() });
    setEditingGrant(null);
    setGrantEditorOpen(true);
    setError("");
    setGrantError("");
  };
  const openEditGrant = async (grant: ParticipationInput) => {
    if (
      grantEditorOpen &&
      !(await confirmDiscard("Discard the open grant draft before editing another grant?"))
    )
      return;
    setDraft({ ...grant });
    setEditingGrant(grantKey(grant));
    setGrantEditorOpen(true);
    setError("");
    setGrantError("");
  };
  const copyGrant = async (grant: ParticipationInput, newApplication = false) => {
    if (
      grantEditorOpen &&
      !(await confirmDiscard("Discard the open draft before copying this grant?"))
    )
      return;
    setDraft(
      newApplication
        ? newProgramApplication(
            grant,
            form.participations.filter(
              (item) => applicationIdentity(item) === applicationIdentity(grant),
            ),
          )
        : copyAnnualGrant(grant),
    );
    setEditingGrant(null);
    setGrantEditorOpen(true);
    setGrantError("");
    setError("");
  };
  const removeGrant = async (grant: ParticipationInput) => {
    if (
      !(await confirmDiscard(
        "Remove this grant from the scholar? This takes effect when you save the scholar.",
      ))
    )
      return;
    setForm((current) => ({
      ...current,
      participations: current.participations.filter((item) => grantKey(item) !== grantKey(grant)),
    }));
    if (editingGrant === grantKey(grant)) {
      setEditingGrant(null);
      setGrantEditorOpen(false);
      setDraft(newGrant());
    }
  };
  const saveGrant = () => {
    const validationError = validateGrant(draft);
    if (validationError) {
      setGrantError(validationError);
      return;
    }
    setGrantError("");
    const normalized = {
      ...(draft.id ? draft : uppercaseGrant(draft)),
      start_term: canonicalTerm(draft.start_term),
      end_term: canonicalTerm(draft.end_term),
      start_academic_year: formatAcademicYear(draft.start_academic_year).trim(),
      end_academic_year: formatAcademicYear(draft.end_academic_year).trim(),
    };
    setForm((current) => ({
      ...current,
      participations:
        editingGrant === null
          ? [...current.participations, { ...normalized, client_key: crypto.randomUUID() }]
          : current.participations.map((grant) =>
              grantKey(grant) === editingGrant ? normalized : grant,
            ),
    }));
    setGrantEditorOpen(false);
    setEditingGrant(null);
    setDraft(newGrant());
    setError("");
  };
  const saveScholar = async (event: FormEvent) => {
    event.preventDefault();
    if (saving || (id && sourceRevision === null)) return;
    if (educationDraft) {
      setError("Save or cancel the open education entry before saving the scholar.");
      setStep(2);
      return;
    }
    if (grantEditorOpen) {
      setError("Save or cancel the open grant before saving the scholar.");
      setStep(3);
      return;
    }
    if (!form.name.trim()) {
      setError("Name: enter the scholar’s name.");
      setStep(1);
      return;
    }
    if (step !== 4) {
      changeStep(4);
      return;
    }
    setSaving(true);
    try {
      const matches =
        !creationAttempt.current && form.name.trim().length >= 3 && form.name.trim().length <= 200
          ? await getScholarNameMatches(form.name.trim(), id ? Number(id) : undefined)
          : [];
      if (!mounted.current) return;
      if (matches.length) {
        setNameMatches(matches);
        const accepted = await new Promise<boolean>((resolve) => {
          duplicateDecision.current = resolve;
        });
        if (!accepted || !mounted.current) return;
      }
      if (id) await updateFsdpRecord(Number(id), form, sourceRevision ?? -1);
      else {
        const userId = getCurrentUser()?.id;
        if (!userId) throw new Error("Sign in before retrying this save.");
        if (creationAttempt.current && creationAttempt.current.userId !== userId)
          throw new Error(
            "This save belongs to another account. Return to that account and check the directory.",
          );
        creationAttempt.current ??= {
          key: crypto.randomUUID(),
          payload: structuredClone(uppercaseScholar(form)),
          userId,
        };
        await createFsdpRecord(creationAttempt.current.payload, creationAttempt.current.key);
      }
      if (mounted.current) {
        allowLeave();
        navigate(id ? `/fsdp/${id}` : "/fsdp");
      }
    } catch (caughtError) {
      if (!id) {
        if (caughtError instanceof UnconfirmedOperationError) setUncertainSave(true);
        else if (!uncertainSave) creationAttempt.current = null;
      }
      setError(caughtError instanceof Error ? caughtError.message : "Unable to save scholar.");
    } finally {
      setSaving(false);
    }
  };
  const addRequirement = () =>
    setForm((current) => ({
      ...current,
      requirements: [
        ...current.requirements,
        {
          client_key: crypto.randomUUID(),
          requirement_name: "",
          due_date: null,
          is_complete: false,
          remarks: "",
        },
      ],
    }));
  const updateRequirement = (index: number, changes: Partial<RequirementInput>) =>
    setForm((current) => ({
      ...current,
      requirements: current.requirements.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...changes } : item,
      ),
    }));

  if (loadError)
    return (
      <div className="notice error" role="alert">
        {loadError}
        <div className="action-group">
          <button
            className="btn secondary"
            type="button"
            onClick={() => setLoadRevision((value) => value + 1)}
          >
            Retry
          </button>
          <Link to="/fsdp">Back to directory</Link>
        </div>
      </div>
    );
  if (id && sourceRevision === null)
    return <PageSkeleton label="Loading scholar form" variant="form" />;
  const pendingRequirements = form.requirements.filter((item) => !item.is_complete).length;
  const cancelPath = id ? `/fsdp/${id}` : "/fsdp";
  return (
    <form onSubmit={saveScholar} noValidate className="stack-md scholar-entry scholar-office-entry">
      <UnsavedChangesDialog blocker={blocker} pending={saving} pendingTitle="Saving your changes" />
      {discardDialog}
      <ConfirmationDialog
        open={nameMatches.length > 0}
        title="Check similar scholar names"
        description={`Possible matches: ${nameMatches.map((match) => `${match.name}${match.department ? ` (${match.department})` : ""}`).join("; ")}. These may be different people. No records will be merged. Save only if this is a separate person or the intended edited record.`}
        confirmLabel="Keep separate and save"
        cancelLabel="Return to form"
        onConfirm={() => decideDuplicate(true)}
        onCancel={() => decideDuplicate(false)}
      />
      <PageHeading
        title={id ? "Edit Scholar" : "New Scholar"}
        description="One scholar. Every qualification and application, together."
        actions={
          <Link className="btn secondary" to={cancelPath}>
            Back
          </Link>
        }
      />
      <FormError message={error} />
      {uncertainSave && (
        <div className="notice" role="status">
          This save has not been confirmed. The original details are kept unchanged. Retry Save
          Scholar to check the same request safely, or check the directory before starting another
          record.
        </div>
      )}
      <div className="scholar-entry-layout">
        <aside className="entry-navigation no-print" aria-label="Scholar entry steps">
          <span className="eyebrow">Scholar record</span>
          {[
            [1, "Identity", "Personal and office details"],
            [2, "Education", `${form.education?.length || 0} qualifications`],
            [3, "Programs & grants", `${form.participations.length} annual grant records`],
            [4, "Review", "Check and save together"],
          ].map(([number, label, detail]) => (
            <button
              type="button"
              key={number}
              aria-label={`Step ${number}: ${label}`}
              aria-current={step === number ? "step" : undefined}
              disabled={saving || uncertainSave}
              onClick={() => changeStep(Number(number))}
            >
              <span className="office-step-number">{String(number).padStart(2, "0")}</span>
              <span className="office-step-copy">
                <strong>{label}</strong>
                <small>{detail}</small>
              </span>
            </button>
          ))}
          <div className="entry-save-note">
            <strong>{id ? "Editing an existing record" : "Creating a new record"}</strong>
            <p>Save Scholar stores all your changes together.</p>
          </div>
        </aside>
        <div className="entry-content">
          <fieldset className="save-fields entry-content" disabled={saving || uncertainSave}>
            <div
              className="office-step-panel"
              id="scholar-step-1"
              tabIndex={-1}
              hidden={step !== 1}
            >
              <section className="entry-section" tabIndex={-1} id="scholar-details">
                <header>
                  <span className="entry-number">01</span>
                  <div>
                    <h2>Scholar Information</h2>
                    <p>Fields marked * are required.</p>
                  </div>
                </header>
                <div className="entry-grid">
                  <label className="entry-wide">
                    Name *
                    <RecordInput
                      required
                      autoComplete="off"
                      value={form.name}
                      onValueChange={(name) => setForm({ ...form, name })}
                    />
                  </label>
                  <label>
                    College / Staff
                    <select
                      value={scholarAffiliation(form.department)}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          department: event.target.value,
                          personnel_type: personnelType(event.target.value),
                        })
                      }
                    >
                      {affiliations.map((label) => (
                        <option key={label}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Personnel type
                    <input value={personnelType(form.department)} readOnly />
                  </label>
                  <label className="entry-wide">
                    Rank / position
                    <RecordInput
                      value={form.rank}
                      onValueChange={(rank) => setForm({ ...form, rank })}
                    />
                  </label>
                  <label>
                    Age
                    <NumberInput
                      step={1}
                      value={form.age ?? ""}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          age: event.target.value ? Number(event.target.value) : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    Tenure at CHMSC (years)
                    <NumberInput
                      min="0"
                      step="any"
                      value={form.tenure_years ?? ""}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          tenure_years:
                            event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                    />
                  </label>
                  <label className="entry-wide">
                    Profile remarks
                    <RecordTextarea
                      rows={5}
                      value={form.profile_remarks || ""}
                      onValueChange={(profile_remarks) => setForm({ ...form, profile_remarks })}
                    />
                  </label>
                </div>
                <DocumentCopyFields
                  hard={form.has_hard_copy}
                  soft={form.has_soft_copy}
                  onChange={(change) => setForm((current) => ({ ...current, ...change }))}
                />
              </section>
            </div>
            <div
              className="office-step-panel"
              id="scholar-step-2"
              tabIndex={-1}
              hidden={step !== 2}
            >
              {!!suppressedEducation.length && (
                <div className="notice">
                  Automatically added education removed from this profile:
                  {suppressedEducation.map((programId) => (
                    <label key={programId}>
                      <input
                        type="checkbox"
                        checked={(form.restore_education_program_ids || []).includes(programId)}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            restore_education_program_ids: event.target.checked
                              ? [...(current.restore_education_program_ids || []), programId]
                              : (current.restore_education_program_ids || []).filter(
                                  (id) => id !== programId,
                                ),
                          }))
                        }
                      />{" "}
                      Restore{" "}
                      {form.participations.find((item) => item.source_program_id === programId)
                        ?.program_name || `program #${programId}`}{" "}
                      when saving
                    </label>
                  ))}
                </div>
              )}
              <EducationSection
                key={`${id || "new"}-${sourceRevision}`}
                entries={form.education || []}
                onChange={(education) => setForm((current) => ({ ...current, education }))}
                onDraftChange={setEducationDraft}
              />
            </div>
            <div
              className="office-step-panel"
              id="scholar-step-3"
              tabIndex={-1}
              hidden={step !== 3}
            >
              <section className="entry-section" tabIndex={-1} id="scholar-grants">
                <header>
                  <span className="entry-number">03</span>
                  <div>
                    <h2>FSDP Grants</h2>
                    <p>{form.participations.length} grant records in this form</p>
                  </div>
                </header>
                {!form.participations.length ? (
                  <p className="empty-table">No grants added yet.</p>
                ) : (
                  <div className="profile-grant-history">
                    {inputApplicationGroups(form.participations).map(([key, group]) => (
                      <details className="program-history" key={key} open>
                        <summary>
                          <span>
                            <strong className="record-value">{group[0].program_name}</strong>
                            <span className="program-history-meta">
                              {applicationPeriod(group)} · {group.length} grant{" "}
                              {group.length === 1 ? "entry" : "entries"}
                            </span>
                          </span>
                        </summary>
                        <TableRegion label={`Grants for ${group[0].program_name}`}>
                          <table className="entry-grant-table">
                            <thead>
                              <tr>
                                <th>Program / category</th>
                                <th>Grant / status</th>
                                <th>Period</th>
                                <th>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {group.map((grant) => (
                                <tr key={grantKey(grant)}>
                                  <td>
                                    <strong className="record-value">{grant.program_name}</strong>
                                    <small>
                                      {grant.program_category || "Category not recorded"}
                                    </small>
                                    <small className="record-value">
                                      {grant.delivering_hei || "HEI not recorded"}
                                    </small>
                                  </td>
                                  <td>
                                    <strong>{displayGrantStatus(grant.status)}</strong>
                                    <small>Case: {grant.case_status || "Open"}</small>
                                    <small>
                                      {grant.grant_type === "Others"
                                        ? grant.grant_other
                                        : grant.grant_type || "Grant type not recorded"}
                                    </small>
                                  </td>
                                  <td>
                                    {grant.start_term && grant.start_academic_year
                                      ? `${grant.start_term} ${grant.start_academic_year}`
                                      : "Start not recorded"}
                                    <small>
                                      to{" "}
                                      {grant.end_term && grant.end_academic_year
                                        ? `${grant.end_term} ${grant.end_academic_year}`
                                        : "End not recorded"}
                                    </small>
                                  </td>
                                  <td>
                                    <div className="action-group">
                                      <IconAction
                                        label={`Edit grant ${grant.program_name}`}
                                        onClick={() => void openEditGrant(grant)}
                                      >
                                        <EditIcon />
                                      </IconAction>
                                      {isAdmin && (
                                        <>
                                          <IconAction
                                            label={`Copy for next year ${grant.program_name}`}
                                            onClick={() => void copyGrant(grant)}
                                          >
                                            <CopyIcon />
                                          </IconAction>
                                        </>
                                      )}
                                      <IconAction
                                        label={`Remove grant ${grant.program_name}`}
                                        onClick={() => void removeGrant(grant)}
                                      >
                                        <TrashIcon />
                                      </IconAction>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </TableRegion>
                        {isAdmin && (
                          <div className="action-group">
                            <button
                              type="button"
                              className="btn secondary"
                              onClick={() => void copyGrant(group[0], true)}
                            >
                              New application
                            </button>
                          </div>
                        )}
                      </details>
                    ))}
                  </div>
                )}
                {!grantEditorOpen && (
                  <IconAction label="Add Grant" className="entry-add" onClick={openNewGrant}>
                    <PlusIcon />
                  </IconAction>
                )}
                {grantEditorOpen && (
                  <GrantEntry
                    draft={draft}
                    applications={inputApplicationGroups(
                      form.participations.filter((grant) =>
                        draft.source_program_id
                          ? grant.source_program_id === draft.source_program_id
                          : grant.program_name.trim().toUpperCase() ===
                            draft.program_name.trim().toUpperCase(),
                      ),
                    ).map(([, group]) => ({
                      key: group[0].application_key || null,
                      programId: group[0].source_program_id,
                      label: applicationPeriod(group),
                    }))}
                    update={updateDraft}
                    error={grantError}
                    editing={editingGrant !== null}
                    save={saveGrant}
                    cancel={() =>
                      void (async () => {
                        if (
                          await confirmDiscard(
                            "Discard this grant editor’s changes? Grants already added to the scholar form will stay unchanged.",
                          )
                        ) {
                          setGrantEditorOpen(false);
                          setEditingGrant(null);
                          setDraft(newGrant());
                          setGrantError("");
                        }
                      })()
                    }
                  />
                )}
              </section>
            </div>
            <div
              className="office-step-panel"
              id="scholar-step-4"
              tabIndex={-1}
              hidden={step !== 4}
            >
              <section
                className="entry-section office-review"
                aria-labelledby="scholar-review-heading"
              >
                <header>
                  <span className="entry-number">04</span>
                  <div>
                    <h2 id="scholar-review-heading">Review scholar record</h2>
                    <p>Save once to store the complete record.</p>
                  </div>
                </header>
                <div className="office-review-identity">
                  <h3 className="record-value">{form.name || "Name not recorded"}</h3>
                  <p>
                    {[form.department, form.rank].filter(Boolean).join(" · ") ||
                      "Affiliation and rank not recorded"}
                  </p>
                  <button type="button" className="btn secondary" onClick={() => changeStep(1)}>
                    Edit identity
                  </button>
                </div>
                <dl className="office-review-details">
                  <div>
                    <dt>Age</dt>
                    <dd>{form.age ?? "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt>Tenure in years</dt>
                    <dd>{form.tenure_years ?? "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt>Hard copy</dt>
                    <dd>{copyAvailability(form.has_hard_copy)}</dd>
                  </div>
                  <div>
                    <dt>Soft copy</dt>
                    <dd>{copyAvailability(form.has_soft_copy)}</dd>
                  </div>
                </dl>
                {form.profile_remarks && (
                  <div className="office-review-remarks">
                    <strong>Profile remarks</strong>
                    <p className="record-value">{form.profile_remarks}</p>
                  </div>
                )}
                <dl className="office-review-facts">
                  <div>
                    <dt>Education entries</dt>
                    <dd>{form.education?.length || 0}</dd>
                  </div>
                  <div>
                    <dt>Program applications</dt>
                    <dd>{inputApplicationGroups(form.participations).length}</dd>
                  </div>
                  <div>
                    <dt>Annual grants</dt>
                    <dd>{form.participations.length}</dd>
                  </div>
                </dl>
                <div className="office-review-sections">
                  <article>
                    <header>
                      <h3>Education</h3>
                      <button type="button" className="btn secondary" onClick={() => changeStep(2)}>
                        Edit education
                      </button>
                    </header>
                    {form.education?.length ? (
                      <ul>
                        {form.education.map((item, index) => (
                          <li key={item.id || item.client_key || index}>
                            <strong className="record-value">
                              {item.degree || "Degree not recorded"}
                            </strong>
                            <span>
                              {[item.level, item.institution, item.graduation_year]
                                .filter(Boolean)
                                .join(" · ") || "Other details not recorded"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No education entries recorded.</p>
                    )}
                  </article>
                  <article>
                    <header>
                      <h3>Programs & grants</h3>
                      <button type="button" className="btn secondary" onClick={() => changeStep(3)}>
                        Edit programs & grants
                      </button>
                    </header>
                    {form.participations.length ? (
                      <ul>
                        {inputApplicationGroups(form.participations).map(([key, group]) => (
                          <li key={key}>
                            <strong className="record-value">{group[0].program_name}</strong>
                            <span>
                              {applicationPeriod(group)} · {group.length} annual{" "}
                              {group.length === 1 ? "grant" : "grants"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No grants recorded.</p>
                    )}
                  </article>
                </div>
              </section>
              <section className="entry-section" tabIndex={-1} id="scholar-requirements">
                <header>
                  <span className="entry-number">+</span>
                  <div>
                    <h2>Requirement Register</h2>
                    <p>{pendingRequirements} pending items</p>
                  </div>
                </header>
                <label className="entry-manual">
                  <input
                    type="checkbox"
                    checked={form.missing_requirements}
                    onChange={(event) =>
                      setForm({ ...form, missing_requirements: event.target.checked })
                    }
                  />
                  <span>
                    <strong>Missing Requirements</strong>
                    <small>Additional follow-up not covered by the items below.</small>
                  </span>
                </label>
                {!form.requirements.length && (
                  <p className="entry-empty">No requirement items recorded.</p>
                )}
                <div className="requirement-entry-list">
                  {form.requirements.map((item, index) => (
                    <article
                      className="requirement-entry"
                      key={item.id ? `saved-${item.id}` : item.client_key}
                    >
                      <header>
                        <strong>Requirement {index + 1}</strong>
                        <button
                          type="button"
                          className="btn secondary"
                          onClick={() =>
                            void (async () => {
                              if (
                                await confirmDiscard(
                                  "Remove this requirement from the form? This takes effect when you save the scholar.",
                                )
                              )
                                setForm((current) => ({
                                  ...current,
                                  requirements: current.requirements.filter(
                                    (_, itemIndex) => itemIndex !== index,
                                  ),
                                }));
                            })()
                          }
                        >
                          Remove
                        </button>
                      </header>
                      <div className="entry-grid">
                        <label>
                          Requirement name
                          <RecordInput
                            aria-label={`Requirement ${index + 1} name`}
                            value={item.requirement_name}
                            onValueChange={(requirement_name) =>
                              updateRequirement(index, { requirement_name })
                            }
                          />
                        </label>
                        <label>
                          Due date
                          <input
                            type="date"
                            aria-label={`Requirement ${index + 1} due date`}
                            value={item.due_date || ""}
                            onChange={(event) =>
                              updateRequirement(index, { due_date: event.target.value || null })
                            }
                          />
                        </label>
                        <label className="entry-wide">
                          Remarks
                          <RecordTextarea
                            rows={2}
                            aria-label={`Requirement ${index + 1} remarks`}
                            value={item.remarks}
                            onValueChange={(remarks) => updateRequirement(index, { remarks })}
                          />
                        </label>
                      </div>
                      <label className="entry-check">
                        <input
                          type="checkbox"
                          aria-label={`Requirement ${index + 1} complete`}
                          checked={item.is_complete}
                          onChange={(event) =>
                            updateRequirement(index, { is_complete: event.target.checked })
                          }
                        />
                        Completed
                      </label>
                    </article>
                  ))}
                </div>
                <button type="button" className="btn secondary entry-add" onClick={addRequirement}>
                  Add Requirement
                </button>
              </section>
            </div>
          </fieldset>
          <footer className="entry-save-bar">
            <span role="status">
              {saving
                ? "Saving your record…"
                : `Step ${step} of 4 · Changes stay in this form until you save.`}
            </span>
            <div className="action-group">
              {step > 1 && (
                <button
                  type="button"
                  className="btn secondary"
                  disabled={saving || uncertainSave}
                  onClick={() => changeStep(step - 1)}
                >
                  Previous step
                </button>
              )}
              {step < 4 ? (
                <button
                  key="continue-step"
                  type="button"
                  className="btn primary"
                  disabled={saving || uncertainSave}
                  onClick={(event) => {
                    event.preventDefault();
                    changeStep(step + 1);
                  }}
                >
                  Continue
                </button>
              ) : (
                <button key="save-scholar" type="submit" className="btn primary" disabled={saving}>
                  {saving ? "Saving…" : "Save Scholar"}
                </button>
              )}
            </div>
          </footer>
        </div>
      </div>
    </form>
  );
}
