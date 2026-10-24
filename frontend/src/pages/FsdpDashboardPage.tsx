import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { usePreparedPrint } from "../components/PrintWorkspace";
import { ReportPrintResults, PaybackPrintResults } from "../components/ReportPrintResults";
import { reportFilters, reportView, reportScopeLabel } from "../utils/reportScope";
import { getPayback } from "../api/payback";
import { getFsdpReport, getFsdpAnalytics } from "../api";
import type { FsdpAnalytics } from "../types";
import { formatRegistrationDate, registrationTimestamp } from "../utils/dates";
import AnalyticsChart, { type ChartOrder } from "../components/AnalyticsChart";
import RegistrationChart from "../components/RegistrationChart";
import OutcomeChart from "../components/OutcomeChart";
import GrantTypeChart from "../components/GrantTypeChart";
import PaybackFollowUp from "../components/PaybackFollowUp";
import DashboardReports from "../components/DashboardReports";
import TableRegion from "../components/TableRegion";
import PageSkeleton from "../components/PageSkeleton";
import PageHeading from "../components/PageHeading";
import { ArrowIcon, FsdpIcon, ReportsIcon, AttentionIcon, HistoryIcon } from "../components/Icons";
import "../dashboard.css";

export default function FsdpDashboardPage() {
  const location = useLocation();
  const [contractsOpen, setContractsOpen] = useState(location.hash === "#contract-assessment");
  const [reportsOpen, setReportsOpen] = useState(location.hash === "#dashboard-reports");
  useEffect(() => {
    const openHash = () => {
      if (window.location.hash === "#contract-assessment") setContractsOpen(true);
      if (window.location.hash === "#dashboard-reports") setReportsOpen(true);
    };
    openHash();
    window.addEventListener("hashchange", openHash);
    return () => window.removeEventListener("hashchange", openHash);
  }, []);
  useEffect(() => {
    if (location.hash === "#contract-assessment") setContractsOpen(true);
    if (location.hash === "#dashboard-reports") setReportsOpen(true);
  }, [location.hash]);
  const [analytics, setAnalytics] = useState<FsdpAnalytics | null>(null);
  const [params, setParams] = useSearchParams();
  const department = params.get("department") || "";
  const year = params.get("start_academic_year") || "";
  const setScope = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const [order, setOrder] = useState<ChartOrder>("largest");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void getFsdpAnalytics(department, year)
      .then((value) => {
        if (active) {
          setAnalytics(value);
          setLoading(false);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Unable to load FSDP statistics.");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [department, year, revision]);

  const printScope = JSON.stringify([params.toString(), order, revision]);
  usePreparedPrint(printScope, async () => {
    const filters = reportFilters(params),
      view = reportView(params),
      group = params.get("contract_attention") ?? "Payback action";
    const [overview, report, contracts] = await Promise.all([
      getFsdpAnalytics(department, year),
      getFsdpReport(filters),
      getPayback(department, year, group),
    ]);
    return (
      <div className="fsdp-dashboard dashboard-page">
        <h1>Scholar development overview</h1>
        <p>
          {department || "All colleges and Staff"} · {year || "All academic years"} · Generated{" "}
          {new Date().toLocaleString()}
        </p>
        <section className="dashboard-metrics">
          <article>
            <span>Scholars</span>
            <strong>{overview.scholars}</strong>
          </article>
          <article>
            <span>Grant records</span>
            <strong>{overview.grants}</strong>
          </article>
          <article>
            <span>Scholars on going</span>
            <strong>{overview.ongoing_scholars}</strong>
          </article>
          <article>
            <span>Requirements follow-up</span>
            <strong>{overview.requirements_follow_up}</strong>
          </article>
        </section>
        {overview.registration_series && (
          <RegistrationChart series={overview.registration_series} total={overview.scholars} />
        )}
        <AnalyticsChart
          title="Scholars by college / Staff"
          unit="Scholars"
          rows={overview.departments}
          order={order}
        />
        <div className="dashboard-chart-row">
          <OutcomeChart rows={overview.statuses} order={order} />
          <GrantTypeChart rows={overview.grant_types} order={order} />
        </div>
        <section>
          <h2>10 most recently added scholars</h2>
          <table>
            <thead>
              <tr>
                <th>Scholar</th>
                <th>College / Staff</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {(overview.recent_scholars || []).map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.department || "Not recorded"}</td>
                  <td>{formatRegistrationDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <p>
          Contract scope: {department || "All departments"} · {year || "All academic years"}
        </p>
        <PaybackPrintResults data={contracts} group={group} />
        <p>Report scope: {reportScopeLabel(filters)}</p>
        <ReportPrintResults report={report} view={view} />
      </div>
    );
  });

  const resetScope = () => {
    const next = new URLSearchParams(params);
    next.delete("department");
    next.delete("start_academic_year");
    setParams(next, { replace: true });
    setOrder("largest");
  };
  const metrics = analytics
    ? [
        { label: "Scholars", count: analytics.scholars, icon: <FsdpIcon /> },
        { label: "Grant records", count: analytics.grants, icon: <HistoryIcon /> },
        { label: "Scholars on going", count: analytics.ongoing_scholars, icon: <ReportsIcon /> },
        {
          label: "Requirements follow-up",
          count: analytics.requirements_follow_up,
          icon: <AttentionIcon />,
        },
      ]
    : [];

  return (
    <div className="fsdp-dashboard dashboard-page">
      <div className="dashboard-overview" id="dashboard-overview">
        <div className="dashboard-heading">
          <PageHeading
            title="Scholar overview"
            actions={
              <>
                <Link className="text-button" to="/office-guide">
                  Office Guide
                </Link>
                <a className="btn secondary" href="#dashboard-reports">
                  View reports
                </a>
                <Link className="btn primary" to="/fsdp/new">
                  Add scholar
                </Link>
              </>
            }
          />
        </div>
        <nav className="dashboard-section-nav" aria-label="Dashboard sections">
          <a href="#dashboard-overview">Overview</a>
          <a href="#dashboard-reports">Reports &amp; exports</a>
          <a href="#contract-assessment">Contract follow-up</a>
        </nav>
        <section className="dashboard-scope" aria-label="Dashboard filters">
          <div className="dashboard-scope-label">
            <strong>Dashboard scope</strong>
          </div>
          <label>
            College / Staff
            <select
              aria-label="Dashboard department"
              value={department}
              onChange={(event) => setScope("department", event.target.value)}
            >
              <option value="">All colleges and Staff</option>
              {analytics?.options.departments.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Academic year
            <select
              aria-label="Grant start academic year"
              value={year}
              onChange={(event) => setScope("start_academic_year", event.target.value)}
            >
              <option value="">All years, including unrecorded</option>
              {analytics?.options.start_academic_years.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Chart order
            <select
              aria-label="Chart order"
              value={order}
              onChange={(event) => setOrder(event.target.value as ChartOrder)}
            >
              <option value="largest">Largest first</option>
              <option value="smallest">Smallest first</option>
              <option value="name">Alphabetical</option>
            </select>
          </label>
          <button className="text-button" onClick={resetScope}>
            Reset
          </button>
        </section>
        {error && (
          <div className="notice error" role="alert">
            {error}{" "}
            <button className="btn secondary" onClick={() => setRevision((value) => value + 1)}>
              Retry
            </button>
          </div>
        )}
        {loading && <PageSkeleton label="Loading FSDP analytics" variant="dashboard" />}
        {!loading && !error && analytics && (
          <>
            <section className="dashboard-metrics" aria-label="Selected scope totals">
              {metrics.map((metric) => (
                <article
                  className={
                    "dashboard-metric" +
                    (metric.label === "Requirements follow-up" && metric.count > 0
                      ? " metric-attention"
                      : "")
                  }
                  key={metric.label}
                >
                  <div className="dashboard-metric-top">
                    <span>{metric.label}</span>
                    <span className="dashboard-metric-icon" aria-hidden="true">
                      {metric.icon}
                    </span>
                  </div>
                  <strong>{metric.count.toLocaleString()}</strong>
                </article>
              ))}
            </section>
            <div className="dashboard-primary-row">
              {analytics.registration_series ? (
                <RegistrationChart
                  series={analytics.registration_series}
                  total={analytics.scholars}
                />
              ) : (
                <section className="analytics-card registration-card">
                  <header className="dashboard-card-heading">
                    <h2>Scholar registrations</h2>
                  </header>
                  <p className="analytics-empty">
                    Registration history is unavailable. Try refreshing the dashboard.
                  </p>
                </section>
              )}
              <section className="analytics-card attention-card" aria-label="Attention queue">
                <header className="dashboard-card-heading">
                  <div>
                    <span className="dashboard-kicker">Office priorities</span>
                    <h2>Requires attention</h2>
                  </div>
                  <AttentionIcon />
                </header>
                <div className="attention-list">
                  {[
                    { label: "Recorded Payback", tone: "critical" },
                    { label: "Payback review", tone: "warning" },
                    { label: "Payback pending contract", tone: "warning" },
                    { label: "In grace period", tone: "neutral" },
                    { label: "Completion date missing", tone: "neutral" },
                  ].map(({ label, tone }) => (
                    <Link
                      className={"attention-item attention-" + tone}
                      key={label}
                      to={`/?${new URLSearchParams({ ...Object.fromEntries(params), contract_attention: label })}#contract-assessment`}
                    >
                      <span className="attention-dot" aria-hidden="true" />
                      <span>{label}</span>
                      <strong>{(analytics.payback_summary?.[label] || 0).toLocaleString()}</strong>
                      <ArrowIcon />
                    </Link>
                  ))}
                  <Link
                    className="attention-item attention-neutral"
                    to={`/?${new URLSearchParams({ ...Object.fromEntries(params), missing_requirements: "true" })}#dashboard-reports`}
                  >
                    <span className="attention-dot" aria-hidden="true" />
                    <span>Requirements follow-up</span>
                    <strong>{analytics.requirements_follow_up.toLocaleString()}</strong>
                    <ArrowIcon />
                  </Link>
                </div>
                <Link className="dashboard-queue-footer" to="/office-guide#contract-payback">
                  Assessment guide <ArrowIcon />
                </Link>
              </section>
            </div>
            <div className="dashboard-secondary-row">
              <AnalyticsChart
                title="Scholars by college / Staff"
                unit="Scholars"
                rows={analytics.departments}
                order={order}
              />
              <OutcomeChart rows={analytics.statuses} order={order} />
            </div>
            <section className="data-card dashboard-recent">
              <header className="dashboard-card-heading">
                <div>
                  <span className="dashboard-kicker">Recently registered</span>
                  <h2>10 most recently added scholars</h2>
                </div>
                <Link className="text-button" to="/fsdp">
                  View directory <ArrowIcon />
                </Link>
              </header>
              <TableRegion label="Recently added scholars">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Scholar</th>
                      <th scope="col">College / Staff</th>
                      <th scope="col">Current status</th>
                      <th scope="col">Added</th>
                      <th scope="col">
                        <span className="chart-text-values">Profile</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {!(analytics.recent_scholars || []).length ? (
                      <tr>
                        <td colSpan={5} className="dashboard-empty">
                          <strong>No scholars in this scope.</strong>
                          <span>Choose another department or add a scholar.</span>
                        </td>
                      </tr>
                    ) : (
                      analytics.recent_scholars?.map((scholar) => (
                        <tr key={scholar.id}>
                          <td>
                            <div className="dashboard-scholar">
                              <span className="scholar-initials" aria-hidden="true">
                                {scholar.name
                                  .split(/\s+/)
                                  .filter(Boolean)
                                  .slice(0, 2)
                                  .map((word) => word[0])
                                  .join("")
                                  .toUpperCase()}
                              </span>
                              <span>
                                <Link className="record-value" to={"/fsdp/" + scholar.id}>
                                  {scholar.name}
                                </Link>
                                <small>Scholar #{scholar.id}</small>
                              </span>
                            </div>
                          </td>
                          <td>{scholar.department || "Unknown"}</td>
                          <td>
                            <span className="dashboard-status">
                              {scholar.current_status || "No grants"}
                            </span>
                          </td>
                          <td>
                            <time dateTime={registrationTimestamp(scholar.created_at) || undefined}>
                              {formatRegistrationDate(scholar.created_at)}
                            </time>
                          </td>
                          <td>
                            <Link
                              className="dashboard-profile-link"
                              aria-label={"View profile for " + scholar.name}
                              to={"/fsdp/" + scholar.id}
                            >
                              View profile <ArrowIcon />
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </TableRegion>
            </section>
            <details className="dashboard-grant-composition data-card">
              <summary>Grant type composition</summary>
              <GrantTypeChart rows={analytics.grant_types} order={order} />
            </details>
          </>
        )}
      </div>
      <details
        id="contract-assessment"
        className="data-card"
        open={contractsOpen}
        onToggle={(event) => setContractsOpen(event.currentTarget.open)}
      >
        <summary>Contract and payback details</summary>
        {contractsOpen && <PaybackFollowUp />}
      </details>
      <details
        id="dashboard-reports"
        className="dashboard-report-section data-card"
        open={reportsOpen}
        onToggle={(event) => setReportsOpen(event.currentTarget.open)}
      >
        <summary>Dashboard reports and exports</summary>
        {reportsOpen && <DashboardReports compactFilters />}
      </details>
    </div>
  );
}
