import { Link, useParams } from "react-router-dom";
import { useRecord } from "../hooks/useRecord";
import { localToday } from "../utils/dates";
import { getFsdpRecord } from "../api";
import { getCurrentUser } from "../api/client";
import "../profile.css";
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
  const { record: scholar, error, retry } = useRecord(id, getFsdpRecord, "Unable to load scholar.");
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
  const manual =
    scholar.manual_requirements_follow_up ??
    (scholar.missing_requirements && complete === requirements.length);

  return (
    <div className="stack-md fsdp-person-profile">
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
          className="btn primary icon-action no-print"
          aria-label="Edit profile"
          title="Edit profile"
          to={`/fsdp/${scholar.id}/edit`}
        >
          <EditIcon />
        </Link>
      </section>
      <nav className="profile-section-nav no-print" aria-label="Scholar sections">
        <a href="#scholar-remarks">Profile remarks</a>
        <a href="#scholar-education">Education background</a>
        <a href="#scholar-grants">Grant history</a>
        <a href="#scholar-requirements">Requirements</a>
        <a href="#scholar-office-log">Office log</a>
      </nav>
      <div className="profile-layout">
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
              <ul className="profile-requirements">
                {scholar.education.map((item) => (
                  <li key={item.id || item.client_key}>
                    <div>
                      <strong className="record-value">
                        {item.degree || "Degree not recorded"}
                      </strong>
                      <span className="record-value">
                        {[item.level, item.institution, item.graduation_year]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
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
  );
}
