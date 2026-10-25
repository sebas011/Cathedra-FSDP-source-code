import { Link, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { useRecord } from "../hooks/useRecord";
import { localToday } from "../utils/dates";
import { getFsdpRecord } from "../api";
import { getCurrentUser } from "../api/client";
import { applicationIdentity } from "../utils/grantApplications";
import { copyAvailability } from "../components/DocumentCopies";
import ProgramGrantHistory from "../components/ProgramGrantHistory";
import OfficeLogPanel from "../components/OfficeLogPanel";
import { displayGrantStatus } from "../utils/statuses";
import ScholarHistory from "../components/ScholarHistory";
import PageSkeleton from "../components/PageSkeleton";
import { EditIcon, FsdpIcon } from "../components/Icons";

const value = (item: string | null | undefined) => item || "Not recorded";

export default function FsdpDetailPage() {
  const { id } = useParams();
  const [profileTab, setProfileTab] = useState("overview");
  const { record: scholar, error, retry } = useRecord(id, getFsdpRecord, "Unable to load scholar.");
  const educationHistory = useRef<HTMLUListElement>(null);
  useEffect(() => {
    let saved: Array<[HTMLDetailsElement, boolean]> = [];
    const expand = () => {
      if (saved.length) return;
      saved = Array.from(educationHistory.current?.querySelectorAll("details") || []).map(
        (entry) => [entry, entry.open],
      );
      for (const [entry] of saved) entry.open = true;
    };
    const restore = () => {
      for (const [entry, open] of saved) entry.open = open;
      saved = [];
    };
    window.addEventListener("beforeprint", expand);
    window.addEventListener("afterprint", restore);
    return () => {
      restore();
      window.removeEventListener("beforeprint", expand);
      window.removeEventListener("afterprint", restore);
    };
  }, [id]);
  if (error)
    return (
      <div className="notice error" role="alert">
        {error}
        <div className="action-group">
          <button className="btn secondary" type="button" onClick={retry}>
            Retry
          </button>
          <Link to="/fsdp">Back to directory</Link>
        </div>
      </div>
    );
  if (!scholar) return <PageSkeleton label="Loading scholar profile" />;
  const requirements = scholar.requirements || [];
  const complete = requirements.filter((item) => item.is_complete).length;
  const today = localToday();
  const initials = scholar.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
  const ongoing = scholar.participations.filter((item) => item.status === "On Going").length;
  const applications = new Set(scholar.participations.map(applicationIdentity)).size;
  const tabs = [
    { value: "overview", label: "Overview" },
    { value: "education", label: "Education" },
    { value: "grants", label: "Programs & grants" },
  ];
  const manual =
    scholar.manual_requirements_follow_up ??
    (scholar.missing_requirements && complete === requirements.length);

  return (
    <div className="stack-md fsdp-person-profile">
      <div className="office-profile-return no-print">
        <Link to="/fsdp">← Scholar directory</Link>
        <span>Scholar profile</span>
      </div>
      <section className="profile-identity" aria-label="Scholar identity">
        <div className="profile-avatar" aria-hidden="true">
          {initials}
        </div>
        <div className="profile-identity-copy">
          <span className="eyebrow">Scholar #{scholar.id}</span>
          <h1 className="record-value">{scholar.name}</h1>
          <p className="record-value">{value(scholar.rank)}</p>
          <div className="profile-tags">
            <span>{scholar.personnel_type || "Not recorded"}</span>
            {scholar.department !== scholar.personnel_type && (
              <span>{value(scholar.department)}</span>
            )}
            <span className="profile-current-status">
              {scholar.current_status ? displayGrantStatus(scholar.current_status) : "No grants"}
            </span>
          </div>
        </div>
        <Link
          className="btn primary no-print"
          aria-label="Edit profile"
          title="Edit profile"
          to={`/fsdp/${scholar.id}/edit`}
        >
          <EditIcon />
          Edit profile
        </Link>
      </section>
      <dl className="office-profile-metrics">
        <div>
          <dt>Age</dt>
          <dd>{scholar.age ?? "—"}</dd>
        </div>
        <div>
          <dt>Tenure in years</dt>
          <dd>
            {scholar.tenure_years == null
              ? "—"
              : scholar.tenure_years.toLocaleString(undefined, { maximumFractionDigits: 6 })}
          </dd>
        </div>
        <div>
          <dt>Applications</dt>
          <dd>{applications}</dd>
        </div>
        <div>
          <dt>Annual grants</dt>
          <dd>{scholar.participations.length}</dd>
        </div>
      </dl>
      <nav
        className="profile-section-nav office-profile-tabs no-print"
        role="tablist"
        aria-label="Scholar sections"
      >
        {tabs.map((tab, index) => (
          <button
            type="button"
            key={tab.value}
            id={`profile-tab-${tab.value}`}
            role="tab"
            aria-controls={`profile-panel-${tab.value}`}
            aria-selected={profileTab === tab.value}
            tabIndex={profileTab === tab.value ? 0 : -1}
            onClick={() => setProfileTab(tab.value)}
            onKeyDown={(event) => {
              const next =
                event.key === "ArrowRight"
                  ? (index + 1) % tabs.length
                  : event.key === "ArrowLeft"
                    ? (index + tabs.length - 1) % tabs.length
                    : event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? tabs.length - 1
                        : null;
              if (next !== null) {
                event.preventDefault();
                setProfileTab(tabs[next].value);
                document.getElementById(`profile-tab-${tabs[next].value}`)?.focus();
              }
            }}
          >
            {tab.label}
            {tab.value === "education" && <span>{scholar.education?.length || 0}</span>}
            {tab.value === "grants" && <span>{applications}</span>}
          </button>
        ))}
      </nav>
      <div
        className={`profile-layout${profileTab !== "overview" ? " profile-layout-records" : ""}`}
      >
        <aside className="profile-sidebar">
          <section className="profile-panel">
            <h2>Scholar information</h2>
            <dl className="profile-facts">
              <div>
                <dt>Age</dt>
                <dd>{scholar.age ?? "Not recorded"}</dd>
              </div>
              <div>
                <dt>Tenure at CHMSC</dt>
                <dd>
                  {scholar.tenure_years == null
                    ? "Not recorded"
                    : `${scholar.tenure_years.toLocaleString(undefined, { maximumFractionDigits: 6 })} ${scholar.tenure_years === 1 ? "year" : "years"}`}
                </dd>
              </div>
            </dl>
          </section>
          <section className="profile-panel">
            <h2>Profile documents</h2>
            <dl className="profile-facts">
              <div>
                <dt>Hard copy</dt>
                <dd>{copyAvailability(scholar.has_hard_copy)}</dd>
              </div>
              <div>
                <dt>Soft copy</dt>
                <dd>{copyAvailability(scholar.has_soft_copy)}</dd>
              </div>
            </dl>
          </section>
          <section className="profile-panel profile-notes-panel" id="scholar-remarks">
            <header className="profile-section-title">
              <h2>Profile remarks</h2>
              <Link
                className="btn secondary icon-action no-print"
                aria-label={scholar.profile_remarks ? "Edit remarks" : "Add remarks"}
                title={scholar.profile_remarks ? "Edit remarks" : "Add remarks"}
                to={`/fsdp/${scholar.id}/edit`}
              >
                <EditIcon />
              </Link>
            </header>
            <p
              className={
                scholar.profile_remarks ? "profile-note-text record-value" : "profile-empty-copy"
              }
            >
              {scholar.profile_remarks || "No profile remarks recorded."}
            </p>
          </section>
          <section className="profile-panel">
            <h2>At a glance</h2>
            <dl className="profile-counts">
              <div>
                <dt>Grant records</dt>
                <dd>{scholar.participations.length}</dd>
              </div>
              <div>
                <dt>On going</dt>
                <dd>{ongoing}</dd>
              </div>
              <div>
                <dt>Completed requirements</dt>
                <dd>
                  {complete} / {requirements.length}
                </dd>
              </div>
            </dl>
            <span
              className={`profile-follow-up ${scholar.missing_requirements ? "needs-attention" : ""}`}
            >
              {scholar.missing_requirements
                ? "Requirements need follow-up"
                : requirements.length
                  ? "Recorded requirements complete"
                  : "No requirements recorded"}
            </span>
          </section>
        </aside>
        <div className="profile-main">
          <div
            className="office-profile-tabpanel"
            id="profile-panel-education"
            role="tabpanel"
            aria-labelledby="profile-tab-education"
            tabIndex={0}
            hidden={profileTab !== "education"}
          >
            <section className="profile-panel" id="scholar-education">
              <header className="profile-section-title">
                <h2>Education background</h2>
                <span className="profile-record-count">
                  {(scholar.education || []).length} entries
                </span>
              </header>
              {!scholar.education?.length ? (
                <p>No education entries recorded.</p>
              ) : (
                <ul ref={educationHistory} className="profile-requirements office-education-list">
                  {scholar.education.map((item) => (
                    <li key={item.id || item.client_key}>
                      <details open>
                        <summary>
                          <span className="office-education-heading">
                            <span className="office-education-level">
                              {item.level || "Level not recorded"}
                            </span>
                            <strong className="record-value">
                              {item.degree || "Degree not recorded"}
                            </strong>
                          </span>
                        </summary>
                        <dl className="office-education-facts">
                          <div>
                            <dt>Institution</dt>
                            <dd className="record-value">{value(item.institution)}</dd>
                          </div>
                          <div>
                            <dt>Graduation year</dt>
                            <dd>{value(item.graduation_year)}</dd>
                          </div>
                        </dl>
                      </details>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
          <div
            className="office-profile-tabpanel"
            id="profile-panel-grants"
            role="tabpanel"
            aria-labelledby="profile-tab-grants"
            tabIndex={0}
            hidden={profileTab !== "grants"}
          >
            <section className="profile-panel" id="scholar-grants">
              {!scholar.participations.length ? (
                <div className="profile-empty">
                  <h2>Grant history</h2>
                  <FsdpIcon />
                  <h3>No grants yet</h3>
                  <Link className="btn secondary no-print" to={`/fsdp/${scholar.id}/edit`}>
                    Add the first grant
                  </Link>
                </div>
              ) : (
                <ProgramGrantHistory grants={scholar.participations} />
              )}
            </section>
          </div>
          <div
            className="office-profile-tabpanel"
            id="profile-panel-overview"
            role="tabpanel"
            aria-labelledby="profile-tab-overview"
            tabIndex={0}
            hidden={profileTab !== "overview"}
          >
            <section className="profile-panel office-profile-overview">
              <header className="profile-section-title">
                <div>
                  <span className="eyebrow">Academic record</span>
                  <h2>Qualifications & applications</h2>
                </div>
              </header>
              <div className="office-profile-overview-grid">
                <div>
                  <strong>{scholar.education?.length || 0}</strong>
                  <span>Education entries</span>
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => {
                      setProfileTab("education");
                      document.getElementById("profile-tab-education")?.focus();
                    }}
                  >
                    View education
                  </button>
                </div>
                <div>
                  <strong>{applications}</strong>
                  <span>Program applications</span>
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => {
                      setProfileTab("grants");
                      document.getElementById("profile-tab-grants")?.focus();
                    }}
                  >
                    View programs & grants
                  </button>
                </div>
              </div>
            </section>
            <section className="profile-panel" id="scholar-requirements">
              <header className="profile-section-title">
                <div>
                  <h2>Requirements</h2>
                </div>
                <span className="profile-record-count">{requirements.length} items</span>
              </header>
              {manual && (
                <p className="profile-manual-note">
                  Additional missing requirements are marked for follow-up.
                </p>
              )}
              {!requirements.length ? (
                <p className="profile-empty-copy">No requirement items recorded.</p>
              ) : (
                <ul className="profile-requirements">
                  {requirements.map((item) => {
                    const overdue = !item.is_complete && !!item.due_date && item.due_date < today;
                    return (
                      <li key={item.id}>
                        <div>
                          <strong className="record-value">{item.requirement_name}</strong>
                          <span>{item.due_date ? `Due ${item.due_date}` : "No due date"}</span>
                          {item.remarks && <p className="record-value">{item.remarks}</p>}
                        </div>
                        <span
                          className={`profile-outcome ${overdue ? "overdue" : item.is_complete ? "ongoing" : ""}`}
                        >
                          {item.is_complete ? "Complete" : overdue ? "Overdue" : "Pending"}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
            <OfficeLogPanel scholarId={scholar.id} />
            {getCurrentUser()?.role === "admin" && <ScholarHistory scholarId={scholar.id} />}
          </div>
        </div>
      </div>
    </div>
  );
}
