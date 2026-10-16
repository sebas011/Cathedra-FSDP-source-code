import { lazy, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import WorkspaceSection from "./components/WorkspaceSection";
import AppShell from "./components/AppShell";
import LoginPage from "./pages/LoginPage";
import { getCurrentUser } from "./api";
import { getExpiredUser, sessionChangedEvent } from "./api/client";
import SessionRecovery from "./components/SessionRecovery";
import SessionActivityGuard from "./components/SessionActivityGuard";
const FsdpDashboardPage = lazy(() => import("./pages/FsdpDashboardPage"));
const ProductGuidePage = lazy(() => import("./pages/ProductGuidePage"));
const ProgramCatalogPage = lazy(() => import("./pages/ProgramCatalogPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const FsdpFormPage = lazy(() => import("./pages/FsdpFormPage"));
const FsdpListPage = lazy(() => import("./pages/FsdpListPage"));
const FsdpDetailPage = lazy(() => import("./pages/FsdpDetailPage"));
const BackupExportPage = lazy(() => import("./pages/BackupExportPage"));
const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const OfficeLogPage = lazy(() => import("./pages/OfficeLogPage"));
const AccountSecurityPage = lazy(() => import("./pages/AccountSecurityPage"));
const SystemReadinessPage = lazy(() => import("./pages/SystemReadinessPage"));

function ProtectedShell() {
  const [user, setUser] = useState(getCurrentUser);
  const [expired, setExpired] = useState(getExpiredUser);
  const location = useLocation();
  useEffect(() => {
    const syncSession = () => {
      setUser(getCurrentUser());
      setExpired(getExpiredUser());
    };
    window.addEventListener(sessionChangedEvent, syncSession);
    window.addEventListener("storage", syncSession);
    return () => {
      window.removeEventListener(sessionChangedEvent, syncSession);
      window.removeEventListener("storage", syncSession);
    };
  }, []);
  const identity = user || expired;
  if (!identity) return <Navigate to="/login" replace />;
  if (user?.must_change_password && location.pathname !== "/settings/accounts")
    return <Navigate to="/settings/accounts" replace />;
  return (
    <>
      <div inert={!user}>
        <AppShell key={identity.id} />
      </div>
      {!user && expired && <SessionRecovery user={expired} />}
    </>
  );
}
function LegacyPage({ to }: { to: string }) {
  const { search, hash } = useLocation();
  return <Navigate to={`${to}${search}${hash}`} replace />;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedShell />}>
          <Route path="/" element={<FsdpDashboardPage />} />
          <Route path="/fsdp" element={<WorkspaceSection section="fsdp" />}>
            <Route index element={<FsdpListPage />} />
            <Route path="new" element={<FsdpFormPage />} />
            <Route path=":id" element={<FsdpDetailPage />} />
            <Route path=":id/edit" element={<FsdpFormPage />} />
          </Route>
          <Route path="/settings" element={<WorkspaceSection section="settings" />}>
            <Route index element={<SettingsPage />} />
            <Route path="accounts" element={<AccountSecurityPage />} />
            <Route path="programs" element={<ProgramCatalogPage />} />
          </Route>
          <Route path="/backup-export" element={<BackupExportPage />} />
          <Route path="/system-readiness" element={<SystemReadinessPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/office-log" element={<OfficeLogPage />} />
          <Route path="/account-security" element={<LegacyPage to="/settings/accounts" />} />
          <Route path="/office-guide" element={<ProductGuidePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <SessionActivityGuard />
    </>
  );
}
