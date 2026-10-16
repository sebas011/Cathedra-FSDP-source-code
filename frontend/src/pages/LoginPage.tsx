import BrandMark from "../components/BrandMark";
import { FormEvent, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getAccountStatus, saveSession, setupAdmin, signIn } from "../api";
import PageSkeleton from "../components/PageSkeleton";
import { productName } from "../product";
import { getLogoutWarning } from "../api/client";

export default function LoginPage() {
  const location = useLocation();
  const logoutWarning =
    (location.state as { logoutWarning?: string } | null)?.logoutWarning || getLogoutWarning();
  const navigate = useNavigate();
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [setupCode, setSetupCode] = useState(
    () => new URLSearchParams(window.location.hash.slice(1)).get("setup") || "",
  );
  useEffect(() => {
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }, []);
  useEffect(() => {
    setError("");
    void getAccountStatus()
      .then((status) => setSetupRequired(status.setup_required))
      .catch(() => setError("Cathedra could not reach the local service."));
  }, [retry]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") || "").trim();
    const password = String(data.get("password") || "");
    if (!username || !password) {
      setError("Enter your username and password.");
      return;
    }
    if (password.length < 10) {
      setError("Use a password with at least 10 characters.");
      return;
    }
    setBusy(true);
    try {
      const session = setupRequired
        ? await setupAdmin(username, password, setupCode)
        : await signIn(username, password);
      saveSession(session);
      navigate(session.user.must_change_password ? "/settings/accounts" : "/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  };
  if (setupRequired === null && !error)
    return (
      <div className="login-page">
        <PageSkeleton label="Preparing sign-in" variant="form" />
      </div>
    );
  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-brand">
          <div className="brand-mark large">
            <BrandMark />
          </div>
          <div>
            <h1>{productName}</h1>
            <p>Faculty & staff development records</p>
          </div>
        </div>
        <div className="login-copy">
          <h2>{setupRequired ? "Set up the first administrator" : "Sign in to Cathedra"}</h2>
          <p>
            {setupRequired
              ? "Create the first local administrator account for this computer. Keep these details somewhere safe."
              : "Use your local Cathedra account to access office records."}
          </p>
        </div>
        {logoutWarning && (
          <div className="notice error" role="alert">
            {logoutWarning}
          </div>
        )}
        <form onSubmit={(event) => void submit(event)} className="login-form">
          <label>
            Username
            <input name="username" autoComplete="username" placeholder="Enter username" />
          </label>
          {setupRequired && (
            <label>
              Private setup code
              <input
                value={setupCode}
                onChange={(event) => setSetupCode(event.target.value)}
                autoComplete="off"
                placeholder="From the first-time setup dialog or development console"
              />
            </label>
          )}
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={setupRequired ? "new-password" : "current-password"}
              placeholder="At least 10 characters"
            />
          </label>
          {error && (
            <div className="form-error" role="alert">
              {error}
              {setupRequired === null && (
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => setRetry((value) => value + 1)}
                >
                  Retry connection
                </button>
              )}
            </div>
          )}
          <button
            className="btn primary wide"
            type="submit"
            disabled={busy || setupRequired === null}
          >
            {busy ? "Please wait…" : setupRequired ? "Create Administrator" : "Sign In"}
          </button>
        </form>
        {setupRequired && (
          <div className="dev-note">
            <strong>First-time setup:</strong> this account can add office staff accounts and manage
            backups.
          </div>
        )}
      </div>
      <div className="login-visual">
        <div className="visual-content">
          <div className="brand-mark large">
            <BrandMark />
          </div>
          <h2>
            Scholar records,
            <br />
            clearly organized.
          </h2>
          <p>
            Manage scholar profiles, grants and follow-up in one local workspace. Keep exported
            office records private.
          </p>
          <div className="visual-modules">
            <span>{"Scholars & grants"}</span>
            <span>Reports & backups</span>
          </div>
        </div>
      </div>
    </div>
  );
}
