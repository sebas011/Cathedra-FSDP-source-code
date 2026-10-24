import { usePreparedPrint } from "../components/PrintWorkspace";
import { displayGrantStatus, grantStatuses } from "../utils/statuses";
import IconAction from "../components/IconAction";
import { EditIcon, TrashIcon } from "../components/Icons";
import { copyAvailability } from "../components/DocumentCopies";
import PageHeading from "../components/PageHeading";
import ConfirmationDialog from "../components/ConfirmationDialog";
import { useDirectoryValue, useDirectoryScroll } from "../hooks/useDirectoryMemory";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { SkeletonTableRows } from "../components/PageSkeleton";

import { deleteFsdpRecord, getCurrentUser, getFsdpRecords, getFsdpSummary } from "../api";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import type { FsdpSummary, Scholar } from "../types";
import "../scholar-office.css";
import { applicationIdentity } from "../utils/grantApplications";

const statuses = grantStatuses;
const scholarStatus = (scholar: Scholar) => displayGrantStatus(scholar.current_status);

export default function FsdpListPage() {
  const location = useLocation();
  const searchField = useRef<HTMLInputElement>(null);
  const canDelete = getCurrentUser()?.role === "admin";
  const [items, setItems] = useState<Scholar[]>([]);
  const [summary, setSummary] = useState<FsdpSummary | null>(null);
  const [search, setSearch] = useDirectoryValue<string>("fsdp:search", "");
  const [status, setStatus] = useDirectoryValue<string>("fsdp:status", "");
  const [missing, setMissing] = useDirectoryValue<string>("fsdp:missing", "");
  const [page, setPage] = useDirectoryValue<number>("fsdp:page", 1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (location.hash === "#directory-search") searchField.current?.focus();
  }, [location.hash, location.key]);
  useDirectoryScroll("fsdp", !loading && !error);
  const [revision, setRevision] = useState(0);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<Scholar | null>(null);
  const deletePending = useRef(false);
  const [actionError, setActionError] = useState("");
  const [summaryError, setSummaryError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void getFsdpRecords(debouncedSearch, status, page, missing)
      .then((result) => {
        if (active) {
          setItems(result.items);
          setTotal(result.total);
          const lastPage = Math.max(1, Math.ceil(result.total / 50));
          if (page > lastPage || page < 1) setPage(lastPage);
        }
      })
      .catch((caught) => {
        if (active) {
          setItems([]);
          setError(caught instanceof Error ? caught.message : "Unable to load FSDP.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [debouncedSearch, status, page, missing, revision]);

  useEffect(() => {
    let active = true;
    setSummaryError("");
    void getFsdpSummary()
      .then((result) => {
        if (active) setSummary(result);
      })
      .catch((caught) => {
        if (active) {
          setSummary(null);
          setSummaryError(caught instanceof Error ? caught.message : "Unable to load summary.");
        }
      });
    return () => {
      active = false;
    };
  }, [revision]);

  usePreparedPrint(JSON.stringify([search, status, missing, page, revision]), async () => {
    const first = await getFsdpRecords(search, status, 1, missing);
    const records = [...first.items];
    const lastPage = Math.max(1, Math.ceil(first.total / (first.page_size || 50)));
    for (let next = 2; next <= lastPage; next++) {
      const result = await getFsdpRecords(search, status, next, missing);
      if (result.total !== first.total)
        throw new Error(
          "The directory changed while preparing this print. Refresh records and print again.",
        );
      records.push(...result.items);
    }
    if (
      records.length !== first.total ||
      new Set(records.map((item) => item.id)).size !== records.length
    )
      throw new Error(
        "The directory changed while preparing this print. Refresh records and print again.",
      );
    return (
      <section>
        <h1>FSDP Scholars</h1>
        <p>
          {[
            search && `Search: ${search}`,
            status && `Status: ${status}`,
            missing && `Details: ${missing.replaceAll("_", " ")}`,
          ]
            .filter(Boolean)
            .join(" · ") || "All scholars"}{" "}
          · {records.length} scholars · Generated {new Date().toLocaleString()}
        </p>
        <table>
          <thead>
            <tr>
              <th>Scholar</th>
              <th>Department</th>
              <th>Rank / position</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {records.map((item) => (
              <tr key={item.id}>
                <td className="record-value">
                  {item.name}
                  <small>Scholar #{item.id}</small>
                </td>
                <td>{item.department || "—"}</td>
                <td className="record-value">{item.rank || "—"}</td>
                <td>{scholarStatus(item)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  });

  const removeScholar = async () => {
    const scholar = deleteCandidate;
    if (!scholar || deletePending.current) return;
    deletePending.current = true;
    setDeleteCandidate(null);
    setDeleting(scholar.id);
    setActionError("");
    try {
      await deleteFsdpRecord(scholar.id, scholar.revision);
      if (items.length === 1 && page > 1) setPage(page - 1);
      setRevision((value) => value + 1);
    } catch (caught) {
      setActionError(
        caught instanceof Error
          ? caught.message
          : "Unable to delete the scholar. The record remains in the list.",
      );
    } finally {
      deletePending.current = false;
      setDeleting(null);
    }
  };

  const pages = Math.max(1, Math.ceil(total / 50));
  return (
    <div className="stack-md office-scholar-directory">
      <ConfirmationDialog
        open={deleteCandidate !== null}
        title="Delete scholar?"
        description={
          deleteCandidate
            ? `Delete ${deleteCandidate.name} and their grant and requirement records? This cannot be undone.`
            : ""
        }
        confirmLabel="Delete scholar"
        cancelLabel="Keep scholar"
        confirmDisabled={deleting !== null}
        onConfirm={() => void removeScholar()}
        onCancel={() => setDeleteCandidate(null)}
      />
      <PageHeading
        title="Scholars"
        description="The people, qualifications and applications in your office."
        actions={
          <Link className="btn primary" to="/fsdp/new">
            Add Scholar
          </Link>
        }
      />
      {(error || actionError || summaryError) && (
        <div role="alert" className="notice error">
          {error || actionError || summaryError}
          <button
            type="button"
            className="btn secondary"
            onClick={() => {
              setActionError("");
              setRevision((value) => value + 1);
            }}
          >
            Refresh records
          </button>
        </div>
      )}
      <section className="directory-totals" aria-label="All scholar totals">
        <div className="metric-grid four">
          {[
            ["All scholars", summary?.total],
            ["On Going", summary?.ongoing],
            ["Completed", summary?.graduated],
            ["Requirements follow-up", summary?.missing_requirements],
          ].map(([label, value]) => (
            <div className="metric-card" key={String(label)}>
              <span>{label}</span>
              <strong>{value ?? "—"}</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="data-card">
        <div className="toolbar">
          <label>
            Search scholars
            <input
              id="directory-search"
              ref={searchField}
              aria-label="Search scholars"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Find a scholar by name, affiliation or program…"
            />
          </label>
          <label>
            Current grant status
            <select
              aria-label="Filter scholars by status"
              value={status ? displayGrantStatus(status) : ""}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {statuses.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Optional details to review
            <select
              aria-label="Filter missing details"
              value={missing}
              onChange={(event) => {
                setMissing(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All records</option>
              <option value="personnel_type">Personnel type not recorded</option>
              <option value="starting_year">Starting academic year not recorded</option>
              <option value="contract_date">
                Unfinished program: completion date not recorded
              </option>
            </select>
          </label>
          <button
            className="btn secondary"
            onClick={() => {
              setSearch("");
              setStatus("");
              setMissing("");
              setPage(1);
            }}
          >
            Reset
          </button>
        </div>
        <div className="table-meta" role="status">
          {loading
            ? "Loading scholar records…"
            : error
              ? "Records could not be loaded."
              : `${total} scholars · Page ${page} of ${pages}`}
        </div>
        <div className="table-scroll" role="region" aria-label="Scholar directory" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col" aria-sort="ascending">
                  Scholar
                </th>
                <th scope="col">Department</th>
                <th scope="col">Applications / grants</th>
                <th scope="col">Status</th>
                <th scope="col">Documents</th>
                <th scope="col" className="right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonTableRows columns={6} />
              ) : error ? (
                <tr>
                  <td colSpan={6} className="empty-table">
                    Unable to load records. Use Refresh records to retry.
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-table">
                    <strong>No scholar records found.</strong>
                    <span>Try changing or clearing the filters.</span>
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="identity-cell">
                        <span className="avatar" aria-hidden="true">
                          {item.name
                            .split(/\s+/)
                            .filter(Boolean)
                            .slice(0, 2)
                            .map((part) => part[0])
                            .join("")}
                        </span>
                        <div>
                          <Link to={`/fsdp/${item.id}`}>
                            <strong className="record-value">{item.name}</strong>
                          </Link>
                          <small className="record-value">
                            {item.rank ? `${item.rank} · #${item.id}` : `Scholar #${item.id}`}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <strong>{item.department || "Unknown"}</strong>
                      <small>{item.personnel_type}</small>
                    </td>
                    <td>
                      <strong>
                        {new Set(item.participations.map(applicationIdentity)).size} applications
                      </strong>
                      <small>{item.participations.length} grant records</small>
                    </td>
                    <td>
                      <span
                        className={
                          scholarStatus(item) === "On Going" ? "status-chip ongoing" : "status-chip"
                        }
                      >
                        {scholarStatus(item)}
                      </span>
                    </td>
                    <td className="office-copy-cell">
                      <span>Hard: {copyAvailability(item.has_hard_copy)}</span>
                      <span>Soft: {copyAvailability(item.has_soft_copy)}</span>
                    </td>
                    <td className="right">
                      <Link
                        className="btn secondary icon-action"
                        aria-label={`Edit scholar ${item.name}`}
                        title={`Edit scholar ${item.name}`}
                        to={`/fsdp/${item.id}/edit`}
                      >
                        <EditIcon />
                      </Link>
                      {canDelete && (
                        <IconAction
                          className="danger"
                          label={
                            deleting === item.id
                              ? `Deleting ${item.name}…`
                              : `Delete scholar ${item.name}`
                          }
                          disabled={deleting !== null}
                          onClick={() => {
                            if (!deletePending.current) setDeleteCandidate(item);
                          }}
                        >
                          <TrashIcon />
                        </IconAction>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="form-actions directory-results-footer no-print">
          <p>
            {loading || error
              ? ""
              : total
                ? `Showing ${(page - 1) * 50 + 1}–${Math.min(page * 50, total)} of ${total} scholars`
                : "0 scholars"}
          </p>
          <div className="action-group">
            <button
              className="btn secondary"
              disabled={loading || !!error || page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </button>
            <button
              className="btn secondary"
              disabled={loading || !!error || page >= pages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
