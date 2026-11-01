import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  applyGoogleSheetPull,
  previewGoogleSheetPull,
  type GooglePullApply,
  type GooglePullFields,
  type GooglePullMatch,
  type GooglePullPreview,
  type GooglePullProfile,
  type GooglePullResult,
} from "../api/googlePull";
import { UnconfirmedOperationError } from "../api/client";
import { formatRecordDateTime } from "../utils/dates";
import ConfirmationDialog from "./ConfirmationDialog";
import TableRegion from "./TableRegion";
import "../google-pull.css";

type Props = {
  disabled?: boolean;
  onPendingChange?: (pending: boolean) => void;
  onApplied?: (result: GooglePullResult) => void;
};
type GrantChoice = { selected: boolean; target: string };
type ProfileChoice = {
  selected: boolean;
  target: string;
  search: string;
  grants: Record<string, GrantChoice>;
};
type Choices = Record<string, ProfileChoice>;
type Phase = "idle" | "loading" | "review" | "applying" | "uncertain";

const pageSize = 10;
const normalize = (value: string) =>
  value.normalize("NFKC").trim().replace(/\s+/g, " ").toUpperCase().toLowerCase();
const identifier = (target: string) => (target.startsWith("id:") ? Number(target.slice(3)) : null);
const fieldLabels: Record<string, string> = {
  name: "Name",
  age: "Age",
  tenure_years: "Tenure in years",
  department: "College / Staff",
  rank: "Rank / position",
  profile_remarks: "Profile remarks",
  program_name: "Program",
  delivering_hei: "Delivering HEI",
  grant_type: "Grant type",
  grant_other: "Other grant type",
  start_date: "Start date",
  start_term: "Starting term",
  start_academic_year: "Starting year",
  end_date: "End date",
  end_term: "Ending term",
  end_academic_year: "Ending year",
  extension: "Extension",
  status: "Status",
  remarks: "Grant remarks",
};

function valueText(value: string | number | null | undefined, next = false) {
  if (value == null) return next ? "Blank" : "Not recorded";
  return value === "" ? "Empty text" : String(value);
}

function CompareFields({
  before,
  after,
  label,
}: {
  before?: GooglePullFields;
  after: GooglePullFields;
  label: string;
}) {
  const fields = Object.entries(after).filter(([field]) => field in fieldLabels);
  return (
    <TableRegion label={label}>
      <table className="google-pull-comparison">
        <thead>
          <tr>
            <th scope="col">Field</th>
            <th scope="col">Current</th>
            <th scope="col">Google Sheet</th>
          </tr>
        </thead>
        <tbody>
          {fields.map(([field, value]) => {
            const prior = before?.[field];
            const changed = (prior ?? null) !== value;
            return (
              <tr key={field} className={changed ? "google-pull-changed" : undefined}>
                <th scope="row">{fieldLabels[field]}</th>
                <td>{valueText(prior)}</td>
                <td>
                  {valueText(value, true)}
                  {changed && <small>{value == null ? "Clears this field" : "Changed"}</small>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </TableRegion>
  );
}

function initialChoices(preview: GooglePullPreview): Choices {
  const matchesById = new Map(preview.matches.map((match) => [match.id, match]));
  const existingNames = new Set(preview.matches.map((match) => normalize(match.name)));
  return Object.fromEntries(
    preview.profiles.map((profile) => {
      const suggested =
        profile.suggested_scholar_id === null
          ? undefined
          : matchesById.get(profile.suggested_scholar_id);
      const name = String(profile.fields.name || "");
      const target = suggested
        ? `id:${suggested.id}`
        : existingNames.has(normalize(name))
          ? ""
          : "new";
      return [
        profile.key,
        {
          selected: false,
          target,
          search: name,
          grants: Object.fromEntries(
            profile.grants.map((grant) => [
              grant.key,
              {
                selected: true,
                target:
                  target === "new"
                    ? "new"
                    : suggested?.grants.some((item) => item.id === grant.suggested_participation_id)
                      ? `id:${grant.suggested_participation_id}`
                      : "",
              },
            ]),
          ),
        },
      ];
    }),
  );
}

function grantLabel(grant: { id: number; fields: GooglePullFields }) {
  const period = (prefix: "start" | "end") =>
    grant.fields[`${prefix}_date`] ||
    [grant.fields[`${prefix}_term`], grant.fields[`${prefix}_academic_year`]]
      .filter(Boolean)
      .join(" ");
  const start = period("start");
  const end = period("end");
  return [
    grant.fields.program_name || "Program not recorded",
    start && `From ${start}`,
    end && `To ${end}`,
    `Grant #${grant.id}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

function buildPayload(preview: GooglePullPreview, choices: Choices): GooglePullApply {
  const scholars = new Set<number>();
  const profiles: GooglePullApply["profiles"] = [];
  for (const profile of preview.profiles) {
    const choice = choices[profile.key];
    if (!choice?.selected) continue;
    const scholarId = identifier(choice.target);
    const match = preview.matches.find((item) => item.id === scholarId);
    if (choice.target !== "new" && !match)
      throw new Error(`Choose an existing or new scholar for sheet row ${profile.row}.`);
    if (match && scholars.has(match.id))
      throw new Error(
        `Scholar #${match.id} is selected more than once. Choose each existing scholar only once.`,
      );
    if (match) scholars.add(match.id);
    const grants: GooglePullApply["profiles"][number]["grants"] = [];
    const matchedGrants = new Set<number>();
    for (const grant of profile.grants) {
      const grantChoice = choice.grants[grant.key];
      if (!grantChoice?.selected) continue;
      const participationId = identifier(grantChoice.target);
      const existing = match?.grants.find((item) => item.id === participationId);
      if (grantChoice.target !== "new" && !existing)
        throw new Error(
          `Choose an existing grant or a new independent application for sheet row ${grant.row}.`,
        );
      if (existing && matchedGrants.has(existing.id))
        throw new Error(`Grant #${existing.id} is selected more than once for this scholar.`);
      if (existing) matchedGrants.add(existing.id);
      grants.push({ key: grant.key, participation_id: existing?.id ?? null });
    }
    profiles.push({
      key: profile.key,
      scholar_id: match?.id ?? null,
      expected_revision: match?.revision ?? null,
      grants,
    });
  }
  if (!profiles.length) throw new Error("Select at least one scholar to apply.");
  if (profiles.length > 100)
    throw new Error(
      "Select at most 100 scholars for one save. Apply the remaining rows in a fresh preview.",
    );
  return { preview_id: preview.preview_id, profiles };
}

function ProfileMapping({
  profile,
  choice,
  matches,
  disabled,
  update,
}: {
  profile: GooglePullProfile;
  choice: ProfileChoice;
  matches: GooglePullMatch[];
  disabled: boolean;
  update: (value: ProfileChoice) => void;
}) {
  const selected = matches.find((match) => match.id === identifier(choice.target));
  const search = normalize(choice.search);
  const candidates = matches
    .filter(
      (match) => !search || normalize(match.name).includes(search) || String(match.id) === search,
    )
    .slice(0, 50);
  const options =
    selected && !candidates.some((item) => item.id === selected.id)
      ? [selected, ...candidates]
      : candidates;
  const exactNames = matches.filter(
    (match) => normalize(match.name) === normalize(String(profile.fields.name || "")),
  );
  const targetChanged = (target: string) => {
    const newMatch = matches.find((match) => match.id === identifier(target));
    update({
      ...choice,
      target,
      grants: Object.fromEntries(
        profile.grants.map((grant) => [
          grant.key,
          {
            selected: choice.grants[grant.key].selected,
            target:
              target === "new"
                ? "new"
                : newMatch?.grants.some((item) => item.id === grant.suggested_participation_id)
                  ? `id:${grant.suggested_participation_id}`
                  : "",
          },
        ]),
      ),
    });
  };
  return (
    <article className="google-pull-profile">
      <label className="google-pull-select-profile">
        <input
          type="checkbox"
          checked={choice.selected}
          disabled={disabled}
          onChange={(event) => update({ ...choice, selected: event.target.checked })}
        />
        <span>
          <strong>{String(profile.fields.name || "Name not recorded")}</strong>
          <small>
            Sheet row {profile.row} · {profile.grants.length} grant rows
          </small>
        </span>
      </label>
      {choice.selected && (
        <div className="google-pull-profile-body">
          <div className="google-pull-mapping">
            <label>
              Find existing scholar for row {profile.row}
              <input
                value={choice.search}
                disabled={disabled}
                onChange={(event) => update({ ...choice, search: event.target.value })}
              />
            </label>
            <label>
              Scholar for row {profile.row}
              <select
                value={choice.target}
                disabled={disabled}
                onChange={(event) => targetChanged(event.target.value)}
              >
                <option value="">Choose a scholar</option>
                <option value="new">Create new scholar</option>
                {options.map((match) => (
                  <option key={match.id} value={`id:${match.id}`}>
                    {match.name} · {String(match.fields.department || "Affiliation not recorded")} ·
                    Scholar #{match.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {!choice.target && exactNames.length > 1 && (
            <p className="notice">Several scholars have this name. Choose the intended record.</p>
          )}
          {candidates.length === 50 && (
            <p className="muted">
              Showing the first 50 matches. Narrow the name search to find another record.
            </p>
          )}
          {(selected || choice.target === "new") && (
            <>
              <p className="google-pull-target">
                {selected ? `Update scholar #${selected.id}` : "Create a new scholar"}
              </p>
              <CompareFields
                before={selected?.fields}
                after={profile.fields}
                label={`Profile comparison for sheet row ${profile.row}`}
              />
              {profile.education_text && (
                <div className="google-pull-education">
                  <strong>
                    {selected ? "Existing education is kept" : "New education text entries"}
                  </strong>
                  <p>{profile.education_text}</p>
                </div>
              )}
              {profile.grants.map((grant) => {
                const grantChoice = choice.grants[grant.key];
                const existing = selected?.grants.find(
                  (item) => item.id === identifier(grantChoice.target),
                );
                return (
                  <section
                    key={grant.key}
                    className="google-pull-grant"
                    aria-label={`Grant at sheet row ${grant.row}`}
                  >
                    <label className="google-pull-select-profile">
                      <input
                        type="checkbox"
                        checked={grantChoice.selected}
                        disabled={disabled}
                        onChange={(event) =>
                          update({
                            ...choice,
                            grants: {
                              ...choice.grants,
                              [grant.key]: { ...grantChoice, selected: event.target.checked },
                            },
                          })
                        }
                      />
                      <span>
                        <strong>
                          {String(grant.fields.program_name || "Program not recorded")}
                        </strong>
                        <small>Sheet row {grant.row}</small>
                      </span>
                    </label>
                    {grantChoice.selected && (
                      <>
                        <label>
                          Grant for sheet row {grant.row}
                          <select
                            value={grantChoice.target}
                            disabled={disabled || choice.target === "new"}
                            onChange={(event) =>
                              update({
                                ...choice,
                                grants: {
                                  ...choice.grants,
                                  [grant.key]: { ...grantChoice, target: event.target.value },
                                },
                              })
                            }
                          >
                            <option value="">
                              Choose an existing grant or add a new application
                            </option>
                            <option value="new">Add new independent application</option>
                            {selected?.grants.map((item) => (
                              <option key={item.id} value={`id:${item.id}`}>
                                {grantLabel(item)}
                              </option>
                            ))}
                          </select>
                        </label>
                        {grantChoice.target === "new" && (
                          <p className="google-pull-target">New independent application</p>
                        )}
                        <CompareFields
                          before={existing?.fields}
                          after={grant.fields}
                          label={`Grant comparison for sheet row ${grant.row}`}
                        />
                      </>
                    )}
                  </section>
                );
              })}
            </>
          )}
        </div>
      )}
    </article>
  );
}

export default function GoogleSheetPull({ disabled = false, onPendingChange, onApplied }: Props) {
  const [preview, setPreview] = useState<GooglePullPreview | null>(null);
  const [choices, setChoices] = useState<Choices>({});
  const [phase, setPhase] = useState<Phase>("idle");
  const [page, setPage] = useState(1);
  const [expired, setExpired] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GooglePullResult | null>(null);
  const [confirm, setConfirm] = useState(false);
  const lock = useRef(false);
  const mounted = useRef(false);
  const submission = useRef<GooglePullApply | null>(null);
  const identity = useId();
  const active =
    Boolean(preview) || phase === "loading" || phase === "applying" || phase === "uncertain";
  const controlsLocked =
    disabled || phase === "loading" || phase === "applying" || phase === "uncertain" || confirm;
  const selectedCount =
    preview?.profiles.filter((profile) => choices[profile.key]?.selected).length || 0;
  const pageCount = Math.max(1, Math.ceil((preview?.profiles.length || 0) / pageSize));

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    onPendingChange?.(active);
  }, [active, onPendingChange]);
  useEffect(() => () => onPendingChange?.(false), [onPendingChange]);
  useEffect(() => {
    if (!preview) {
      setExpired(false);
      return;
    }
    const remaining = Date.parse(preview.expires_at) - Date.now();
    setExpired(!Number.isFinite(remaining) || remaining <= 0);
    if (!Number.isFinite(remaining) || remaining <= 0) return;
    const timer = window.setTimeout(() => setExpired(true), Math.min(remaining, 2147483647));
    return () => window.clearTimeout(timer);
  }, [preview]);

  const fetchPreview = async () => {
    if (disabled || lock.current || phase === "uncertain") return;
    lock.current = true;
    setPhase("loading");
    setError("");
    setResult(null);
    try {
      const next = await previewGoogleSheetPull();
      if (!mounted.current) return;
      setPreview(next);
      setChoices(initialChoices(next));
      setPage(1);
      submission.current = null;
      setPhase("review");
    } catch (caught) {
      if (mounted.current) {
        setError(caught instanceof Error ? caught.message : "The sheet preview could not be read.");
        setPhase(preview ? "review" : "idle");
      }
    } finally {
      lock.current = false;
    }
  };

  const reviewApply = () => {
    if (!preview || controlsLocked || expired || lock.current) return;
    try {
      submission.current = buildPayload(preview, choices);
      setError("");
      setConfirm(true);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Review the selected records before applying.",
      );
    }
  };

  const apply = async () => {
    if (disabled || lock.current || !submission.current) return;
    lock.current = true;
    setConfirm(false);
    setPhase("applying");
    setError("");
    let applied: GooglePullResult | null = null;
    try {
      const next = await applyGoogleSheetPull(submission.current);
      if (!mounted.current) return;
      setResult(next);
      setPreview(null);
      setChoices({});
      submission.current = null;
      setPhase("idle");
      applied = next;
    } catch (caught) {
      if (mounted.current) {
        setError(
          caught instanceof Error ? caught.message : "The selected changes could not be applied.",
        );
        if (caught instanceof UnconfirmedOperationError) setPhase("uncertain");
        else {
          setPhase("review");
          submission.current = null;
        }
      }
    } finally {
      lock.current = false;
    }
    if (applied) onApplied?.(applied);
  };

  const close = () => {
    if (controlsLocked || lock.current) return;
    setPreview(null);
    setChoices({});
    setError("");
    setPhase("idle");
    submission.current = null;
  };

  return (
    <>
      <button
        type="button"
        className="btn secondary"
        disabled={disabled || active}
        onClick={() => void fetchPreview()}
        aria-controls={active || error || result ? `${identity}-preview` : undefined}
      >
        Pull from Google Sheet
      </button>
      {(active || error || result) && (
        <section
          className="google-pull-preview stack-md"
          id={`${identity}-preview`}
          aria-labelledby={`${identity}-heading`}
        >
          <div className="google-pull-heading">
            <h3 id={`${identity}-heading`}>Review Google Sheet changes</h3>
            {preview && (
              <button
                type="button"
                className="btn secondary"
                disabled={controlsLocked}
                onClick={close}
              >
                Close preview
              </button>
            )}
          </div>
          {phase === "loading" && <p role="status">Reading Google Sheet preview…</p>}
          {phase === "applying" && <p role="status">Applying selected changes…</p>}
          {error && (
            <p role="alert" className="notice error">
              {error}
            </p>
          )}
          {phase === "uncertain" && (
            <div className="notice">
              <p>
                The result is not confirmed. Your selections are locked so retry checks the same
                save.
              </p>
              <button
                type="button"
                className="btn primary"
                disabled={disabled}
                onClick={() => void apply()}
              >
                Retry same selected changes
              </button>
            </div>
          )}
          {result && (
            <div role="status" className="notice success">
              <strong>
                {result.replayed ? "Earlier save confirmed." : "Selected changes applied."}
              </strong>
              <p>
                {result.scholars_created} scholars created · {result.scholars_updated} scholars
                updated · {result.grants_created} grants created · {result.grants_updated} grants
                updated
              </p>
              <Link to="/fsdp">View scholar directory</Link>
            </div>
          )}
          {preview && (
            <>
              <p className="google-pull-timing">
                {preview.worksheet} · Read {formatRecordDateTime(preview.fetched_at)} · Expires{" "}
                {formatRecordDateTime(preview.expires_at)}
              </p>
              {preview.warnings.length > 0 && (
                <ul className="notice">
                  {preview.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              )}
              {expired && phase !== "uncertain" && (
                <p role="status">This preview has expired. Refresh it before applying changes.</p>
              )}
              <div className="google-pull-toolbar">
                <strong>
                  {selectedCount} of {preview.profiles.length} scholars selected
                </strong>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={controlsLocked}
                  onClick={() => void fetchPreview()}
                >
                  Refresh preview
                </button>
              </div>
              {!preview.profiles.length && <p>No scholar rows are available in this preview.</p>}
              {preview.profiles.slice((page - 1) * pageSize, page * pageSize).map((profile) => (
                <ProfileMapping
                  key={profile.key}
                  profile={profile}
                  choice={choices[profile.key]}
                  matches={preview.matches}
                  disabled={controlsLocked || expired}
                  update={(value) => {
                    if (controlsLocked || expired) return;
                    setError("");
                    setChoices((current) => ({ ...current, [profile.key]: value }));
                  }}
                />
              ))}
              {pageCount > 1 && (
                <nav className="google-pull-toolbar" aria-label="Google Sheet preview pages">
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={controlsLocked || page <= 1}
                    onClick={() => setPage((value) => value - 1)}
                  >
                    Previous preview page
                  </button>
                  <span>
                    Page {page} of {pageCount}
                  </span>
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={controlsLocked || page >= pageCount}
                    onClick={() => setPage((value) => value + 1)}
                  >
                    Next preview page
                  </button>
                </nav>
              )}
              <button
                type="button"
                className="btn primary"
                disabled={controlsLocked || expired || !selectedCount}
                onClick={reviewApply}
              >
                Review selected changes
              </button>
            </>
          )}
        </section>
      )}
      <ConfirmationDialog
        open={confirm}
        title="Apply selected Google Sheet changes?"
        description={`Apply the selected report values for ${selectedCount} scholars to Cathedra? Review blank cells and the chosen existing records or new applications before continuing.`}
        confirmLabel="Apply selected changes"
        cancelLabel="Keep reviewing"
        confirmDisabled={disabled || phase === "applying" || expired}
        onConfirm={() => void apply()}
        onCancel={() => {
          if (phase !== "applying") {
            setConfirm(false);
            submission.current = null;
          }
        }}
      />
    </>
  );
}
