import { PrintWorkspaceProvider, usePrintWorkspace } from "./PrintWorkspace";
import BrandMark from "./BrandMark";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BackupIcon,
  CloseIcon,
  DashboardIcon,
  FsdpIcon,
  HelpIcon,
  HistoryIcon,
  LogoutIcon,
  MenuIcon,
  PrintIcon,
  SidebarCollapseIcon,
  ReadinessIcon,
  SettingsIcon,
  UserIcon,
  SearchIcon,
} from "./Icons";
import { Suspense, useEffect, useRef, useState } from "react";
import {
  clearSession,
  exitDesktop,
  getCurrentUser,
  getServiceHealth,
  releaseVersion,
  signOut,
} from "../api";
import PageSkeleton from "./PageSkeleton";
import { product, productName } from "../product";
import { useSidebarNavigation } from "../hooks/useSidebarNavigation";
import { setLogoutWarning } from "../api/client";
import ConfirmationDialog from "./ConfirmationDialog";
import SectionErrorBoundary from "./SectionErrorBoundary";
import { useDiscardConfirmation } from "../hooks/useDiscardConfirmation";

const navigation = [
  { to: "/", label: "Overview", icon: DashboardIcon },
  { to: "/fsdp", label: "Scholars", icon: FsdpIcon },
  { to: "/settings/programs", label: "Programs", icon: FsdpIcon, adminOnly: true },
  { to: "/settings/accounts", label: "Accounts", icon: UserIcon },
  { to: "/backup-export", label: "Backup & Export", icon: BackupIcon },
  { to: "/system-readiness", label: "System Readiness", icon: ReadinessIcon },
  { to: "/office-guide", label: "Office Guide", icon: HelpIcon },
  { to: "/activity", label: "Activity History", icon: HistoryIcon, adminOnly: true },
  { to: "/office-log", label: "Office log", icon: HistoryIcon },
];

const navigationGroups = [
  { label: "Workspace", paths: ["/", "/fsdp", "/office-log"] },
  {
    label: "Management",
    paths: ["/settings/programs", "/backup-export", "/activity", "/settings/accounts"],
  },
  { label: "Support", paths: ["/office-guide", "/system-readiness"] },
];

function AppShellContent() {
  const printWorkspace = usePrintWorkspace();
  const {
    open,
    mobile,
    collapsed,
    sidebar,
    menuButton,
    closeButton,
    closeMenu,
    openMenu,
    toggleSidebar,
  } = useSidebarNavigation();
  const [releaseMismatch, setReleaseMismatch] = useState(false);
  const [desktopMode, setDesktopMode] = useState(false);
  const [serviceUnavailable, setServiceUnavailable] = useState(false);
  const [recoveryRequired, setRecoveryRequired] = useState(false);
  const [healthRevision, setHealthRevision] = useState(0);
  const [exitError, setExitError] = useState("");
  const [exiting, setExiting] = useState(false);
  const [exitBusy, setExitBusy] = useState(false);
  const [exitConfirmation, setExitConfirmation] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const logoutPending = useRef(false);
  const exitPending = useRef(false);
  const exitSubmitted = useRef(false);
  const { confirmDiscard, discardDialog } = useDiscardConfirmation();
  const navigate = useNavigate();
  const location = useLocation();
  const user = getCurrentUser();
  useEffect(() => {
    const findScholar = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        !event.altKey &&
        event.key.toLowerCase() === "k" &&
        getCurrentUser() &&
        !document.querySelector("dialog[open]")
      ) {
        event.preventDefault();
        navigate("/fsdp#directory-search");
      }
    };
    window.addEventListener("keydown", findScholar);
    return () => window.removeEventListener("keydown", findScholar);
  }, [navigate]);
  useEffect(() => {
    let active = true;
    void getServiceHealth()
      .then((health) => {
        if (active) {
          setServiceUnavailable(false);
          setRecoveryRequired(health.recovery_required === true);
          setReleaseMismatch(
            health.release_version !== releaseVersion ||
              (health as typeof health & { product?: string }).product !== product,
          );
          setDesktopMode(health.desktop_mode === true);
        }
      })
      .catch(() => {
        if (active) {
          setServiceUnavailable(true);
          setReleaseMismatch(false);
        }
      });
    return () => {
      active = false;
    };
  }, [healthRevision]);
  const logout = async () => {
    if (logoutPending.current || exitPending.current) return;
    logoutPending.current = true;
    try {
      if (!window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))) {
        setExitError("Wait for the current save to finish before leaving.");
        return;
      }
      if (
        !window.dispatchEvent(new Event("cathedra-before-leave", { cancelable: true })) &&
        !(await confirmDiscard("Discard unsaved changes and log out?"))
      )
        return;
      if (!window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))) {
        setExitError("Wait for the current save to finish before leaving.");
        return;
      }
      window.dispatchEvent(new Event("cathedra-discard-before-leave"));
      setLoggingOut(true);
      let logoutWarning = "";
      try {
        await signOut();
      } catch {
        logoutWarning =
          "Signed out of this window. The local service did not confirm session revocation. " +
          (user?.role === "admin"
            ? "Sign in again and use Accounts & Access to sign out your sessions when the service is available."
            : "When the service is available, ask an administrator to sign out your sessions in Accounts & Access.");
      }
      setLogoutWarning(logoutWarning);
      clearSession();
      navigate("/login", { state: { logoutWarning } });
    } finally {
      logoutPending.current = false;
      setLoggingOut(false);
    }
  };
  const requestExit = () => {
    if (logoutPending.current || exitPending.current) return;
    if (!window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))) {
      setExitError("Wait for the current save to finish before leaving.");
      return;
    }
    exitPending.current = true;
    setExitConfirmation(true);
  };
  const exitApp = async () => {
    if (!exitPending.current || exitSubmitted.current) return;
    exitSubmitted.current = true;
    setExitConfirmation(false);
    if (!window.dispatchEvent(new Event("cathedra-can-leave", { cancelable: true }))) {
      exitPending.current = false;
      exitSubmitted.current = false;
      setExitError("Wait for the current save to finish before leaving.");
      return;
    }
    setExitBusy(true);
    setExitError("");
    try {
      await exitDesktop();
      window.dispatchEvent(new Event("cathedra-discard-before-leave"));
      clearSession();
      setExiting(true);
      window.close();
    } catch (caught) {
      setExitError(caught instanceof Error ? caught.message : "Unable to exit Cathedra.");
    } finally {
      exitPending.current = false;
      exitSubmitted.current = false;
      setExitBusy(false);
    }
  };
  if (exiting)
    return (
      <main className="page" role="status">
        <h1>Cathedra has stopped</h1>
        <p>You can close this window. Reopen Cathedra from its application icon when needed.</p>
      </main>
    );
  return (
    <div className={`app-layout ${collapsed ? "sidebar-collapsed" : ""}`}>
      {discardDialog}
      <ConfirmationDialog
        open={exitConfirmation}
        title="Exit Cathedra?"
        description="Finish and save any open changes first. Any unsaved work in this window will be discarded."
        confirmLabel="Exit Cathedra"
        cancelLabel="Keep Cathedra open"
        confirmDisabled={exitBusy}
        onConfirm={() => void exitApp()}
        onCancel={() => {
          setExitConfirmation(false);
          exitPending.current = false;
        }}
      />
      <a className="skip-link" href="#main-content">
        Skip to page content
      </a>
      <aside
        ref={sidebar}
        id="main-sidebar"
        role={mobile ? "dialog" : undefined}
        aria-modal={mobile && open ? true : undefined}
        aria-label="Navigation menu"
        inert={mobile && !open}
        aria-hidden={mobile && !open ? true : undefined}
        className={`sidebar ${open ? "sidebar-open" : ""}`}
      >
        <div className="brand">
          <button
            ref={closeButton}
            className="sidebar-collapse-toggle"
            type="button"
            onClick={mobile ? closeMenu : toggleSidebar}
            aria-label={mobile ? "Close menu" : collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={mobile ? "Close menu" : collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-controls="main-sidebar"
            aria-expanded={mobile ? open : !collapsed}
          >
            {mobile ? <CloseIcon /> : collapsed ? <MenuIcon /> : <SidebarCollapseIcon />}
          </button>
          {!collapsed && (
            <>
              <div className="brand-mark">
                <BrandMark />
              </div>
              <div className="brand-copy">
                <strong>{productName}</strong>
                <span>Scholar office</span>
              </div>
            </>
          )}
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-caption">{group.label}</div>
              {group.paths
                .flatMap((path) =>
                  navigation.filter(
                    (item) => item.to === path && (!item.adminOnly || user?.role === "admin"),
                  ),
                )
                .map(({ to, label, icon: NavIcon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    title={
                      to === "/settings/accounts" && user?.role !== "admin" ? "My account" : label
                    }
                    aria-label={
                      to === "/settings/accounts" && user?.role !== "admin" ? "My account" : label
                    }
                    end={to === "/"}
                    onClick={closeMenu}
                    className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                  >
                    <NavIcon className="nav-icon" />
                    <span>
                      {to === "/settings/accounts" && user?.role !== "admin" ? "My account" : label}
                    </span>
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span>Cathedra {releaseVersion}</span>
          <small>Local office workspace</small>
        </div>
      </aside>
      {mobile && open && <div className="sidebar-scrim" aria-hidden="true" onClick={closeMenu} />}
      <div className="workspace" inert={mobile && open}>
        <header className="topbar">
          {mobile && (
            <button
              ref={menuButton}
              className="mobile-menu"
              type="button"
              onClick={openMenu}
              aria-label="Open menu"
              aria-expanded={open}
              aria-controls="main-sidebar"
            >
              <MenuIcon />
            </button>
          )}
          <div className="topbar-title">
            <strong>Scholar office</strong>
            <span>Faculty & staff development</span>
          </div>
          <button
            className="workspace-search no-print"
            type="button"
            aria-label="Find a scholar"
            aria-keyshortcuts="Control+K Meta+K"
            onClick={() => navigate("/fsdp#directory-search")}
          >
            <SearchIcon />
            <span>Find a scholar</span>
            <kbd>Ctrl K</kbd>
          </button>
          <div className="account-box">
            {
              <button
                className="logout-button no-print"
                aria-label="Print This Page"
                title="Print This Page"
                disabled={printWorkspace?.printing}
                onClick={() => void printWorkspace?.requestPrint()}
              >
                <PrintIcon />
                <span>{printWorkspace?.printing ? "Preparing print…" : "Print This Page"}</span>
              </button>
            }
            <div className="avatar">{user?.username.slice(0, 1).toUpperCase() || "A"}</div>
            <div className="account-copy">
              <strong>{user?.username || "Administrator"}</strong>
              <span>{user?.role === "admin" ? "Administrator" : "Staff"}</span>
            </div>
            <NavLink
              className="logout-button"
              to="/settings"
              aria-label="Office settings"
              title="Office settings"
            >
              <SettingsIcon />
            </NavLink>
            <button
              className="logout-button"
              aria-label="Logout"
              title="Logout"
              disabled={loggingOut || exitBusy || exitConfirmation}
              onClick={() => void logout()}
            >
              <LogoutIcon /> <span>{loggingOut ? "Signing out…" : "Logout"}</span>
            </button>
            {desktopMode && (
              <button
                className="logout-button"
                aria-label="Exit Cathedra"
                title="Exit Cathedra"
                disabled={loggingOut || exitBusy || exitConfirmation}
                onClick={requestExit}
              >
                <CloseIcon />
                <span>{exitBusy ? "Exiting…" : "Exit Cathedra"}</span>
              </button>
            )}
          </div>
        </header>
        {releaseMismatch && (
          <div className="release-warning" role="alert">
            This Cathedra window and its local service do not match. Close Cathedra completely, then
            open the latest desktop version.
          </div>
        )}
        {recoveryRequired && (
          <div className="release-warning" role="alert">
            Database recovery is required. Exit Cathedra and restart it before working with records.
            If startup fails, keep the data folder and safety backups unchanged and contact your
            administrator.
          </div>
        )}
        {serviceUnavailable && (
          <div className="release-warning" role="alert">
            The local service could not be reached. Check that Cathedra is running.{" "}
            <button
              className="btn secondary"
              type="button"
              onClick={() => setHealthRevision((value) => value + 1)}
            >
              Retry connection
            </button>
          </div>
        )}
        {printWorkspace?.error && (
          <div className="release-warning" role="alert">
            {printWorkspace.error}
          </div>
        )}
        {exitError && (
          <div className="release-warning" role="alert">
            {exitError}
          </div>
        )}
        <main className="page" id="main-content" tabIndex={-1}>
          <div className="native-print-scope">
            Visible page content only · Generated {new Date().toLocaleString()}
          </div>
          <SectionErrorBoundary key={location.pathname}>
            <Suspense fallback={<PageSkeleton label="Loading page" variant="table" />}>
              <Outlet />
            </Suspense>
          </SectionErrorBoundary>
        </main>
      </div>
    </div>
  );
}

export default function AppShell() {
  return (
    <PrintWorkspaceProvider>
      <AppShellContent />
    </PrintWorkspaceProvider>
  );
}
