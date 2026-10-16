import TableRegion from "../components/TableRegion";
import PageHeading from "../components/PageHeading";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  changePassword,
  clearSession,
  createUser,
  getCurrentUser,
  getUsers,
  resetUserPassword,
  revokeUserSessions,
  setUserActive,
} from "../api";
import PageSkeleton from "../components/PageSkeleton";
import UnsavedChangesDialog from "../components/UnsavedChangesDialog";
import { useUnsavedChanges } from "../hooks/useUnsavedChanges";
import { getExpiredUser } from "../api/client";
import type { LocalUser } from "../types";

export default function AccountSecurityPage() {
  const navigate = useNavigate();
  const currentUser = getCurrentUser() || getExpiredUser();
  const admin = currentUser?.role === "admin" && !currentUser.must_change_password;
  const [users, setUsers] = useState<LocalUser[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(admin);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState({ change: false, create: false, reset: false });
  const { blocker, allowLeave } = useUnsavedChanges(drafts, busy);
  const leave = () => {
    allowLeave();
    clearSession();
    navigate("/login", { replace: true });
  };
  const [loadError, setLoadError] = useState("");
  const [loadRevision, setLoadRevision] = useState(0);

  useEffect(() => {
    if (!admin) return;
    let active = true;
    setLoadError("");
    setAccountsLoading(true);
    void getUsers()
      .then((value) => {
        if (active) setUsers(value);
      })
      .catch((caught) => {
        if (active)
          setLoadError(caught instanceof Error ? caught.message : "Unable to load accounts.");
      })
      .finally(() => {
        if (active) setAccountsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [admin, loadRevision]);

  const submit = async (
    event: FormEvent<HTMLFormElement>,
    action: "change" | "reset" | "create",
  ) => {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const password = String(values.get("password") || "");
      if (action === "change") {
        await changePassword(String(values.get("current") || ""), password);
        leave();
        return;
      } else if (action === "reset") {
        const userId = Number(values.get("user"));
        await resetUserPassword(userId, password);
        if (userId === getCurrentUser()?.id) {
          leave();
          return;
        }
        setNotice("Temporary password saved. Give it to the person securely.");
      } else {
        const created = await createUser(
          String(values.get("username") || "").trim(),
          password,
          values.get("role") === "admin" ? "admin" : "staff",
        );
        setUsers((current) =>
          [...current, created].sort((left, right) => left.username.localeCompare(right.username)),
        );
        setNotice(`${created.username} can now sign in.`);
      }
      form.reset();
      setDrafts((current) => ({ ...current, [action]: false }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update the account.");
    } finally {
      setBusy(false);
    }
  };

  const updateAccount = async (user: LocalUser, action: "status" | "sessions") => {
    if (busy || accountsLoading || loadError) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (action === "status") {
        const saved = await setUserActive(user.id, !user.is_active);
        setUsers((current) => current.map((item) => (item.id === saved.id ? saved : item)));
        setNotice(`${saved.username} is now ${saved.is_active ? "active" : "disabled"}.`);
        if (saved.id === currentUser?.id && !saved.is_active) {
          leave();
        }
      } else {
        await revokeUserSessions(user.id);
        setNotice(`${user.username} must sign in again.`);
        if (user.id === currentUser?.id) {
          leave();
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update the account.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack-md">
      <UnsavedChangesDialog blocker={blocker} pending={busy} />
      <PageHeading
        title="Accounts & Access"
        eyebrow="ACCOUNT SECURITY"
        description="Manage your password and local office accounts in one place."
      />
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {loadError && (
        <div className="notice error" role="alert">
          {loadError}{" "}
          <button
            className="btn secondary"
            type="button"
            onClick={() => setLoadRevision((value) => value + 1)}
          >
            Retry accounts
          </button>
        </div>
      )}
      {currentUser?.must_change_password && (
        <div className="notice" role="status">
          Change your temporary password before accessing office records.
        </div>
      )}
      {notice && (
        <div className="notice success" role="status">
          {notice}
        </div>
      )}
      <section className="maintenance-card">
        <div className="account-identity">
          <span className="avatar" aria-hidden="true">
            {currentUser?.username.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <h2>Change your sign-in password</h2>
            <p>Use at least 10 characters. Cathedra never displays stored passwords.</p>
          </div>
        </div>
        <form
          onChange={() => setDrafts((current) => ({ ...current, change: true }))}
          onSubmit={(event) => void submit(event, "change")}
        >
          <fieldset className="account-form save-fields" disabled={busy}>
            <label>
              Current password
              <input name="current" type="password" autoComplete="current-password" required />
            </label>
            <label>
              New password
              <input
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
              />
            </label>
            <div>
              <button className="btn primary" disabled={busy}>
                Change Password
              </button>
            </div>
          </fieldset>
        </form>
      </section>
      {admin && (
        <>
          <section className="maintenance-card">
            <div>
              <h2>People who can use this computer</h2>
              <p>
                Administrators manage accounts and restores. Staff work with records and exports.
              </p>
            </div>
            {accountsLoading ? (
              <PageSkeleton label="Loading office accounts" variant="table" />
            ) : (
              <TableRegion label="Office accounts">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Account</th>
                      <th scope="col">Access level</th>
                      <th scope="col">Status</th>
                      <th scope="col">Account actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <strong>{user.username}</strong>
                          {user.must_change_password && <small>Password change required</small>}
                        </td>
                        <td>
                          <span className="status-chip">
                            {user.role === "admin" ? "Administrator" : "Staff"}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`status-chip ${user.is_active ? "ongoing" : "warning-chip"}`}
                          >
                            {user.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td>
                          <div className="action-group">
                            <button
                              className="btn secondary"
                              type="button"
                              disabled={busy || accountsLoading || !!loadError}
                              onClick={() => void updateAccount(user, "status")}
                            >
                              {user.is_active ? "Disable" : "Reactivate"}
                            </button>
                            <button
                              className="btn secondary"
                              type="button"
                              disabled={busy || accountsLoading || !!loadError}
                              onClick={() => void updateAccount(user, "sessions")}
                            >
                              Sign out sessions
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableRegion>
            )}
            <details className="disclosure">
              <summary>Add an office account</summary>
              <form
                onChange={() => setDrafts((current) => ({ ...current, create: true }))}
                onSubmit={(event) => void submit(event, "create")}
              >
                <fieldset className="account-form save-fields" disabled={busy}>
                  <label>
                    Username
                    <input name="username" autoComplete="off" required minLength={3} />
                  </label>
                  <label>
                    Temporary password
                    <input
                      name="password"
                      type="password"
                      autoComplete="new-password"
                      required
                      minLength={10}
                    />
                  </label>
                  <label>
                    Access level
                    <select name="role" defaultValue="staff">
                      <option value="staff">Staff</option>
                      <option value="admin">Administrator</option>
                    </select>
                  </label>
                  <div>
                    <button className="btn primary" disabled={busy}>
                      Add User
                    </button>
                  </div>
                </fieldset>
              </form>
            </details>
          </section>
          <section className="maintenance-card account-sensitive">
            <div>
              <h2>Account recovery</h2>
              <p>
                Reset a password only when the account owner needs help signing in. A temporary
                password requires a change at the next sign-in.
              </p>
            </div>
            <details className="disclosure">
              <summary>Reset an account password</summary>
              <p>The person should sign in and change the temporary password immediately.</p>
              <form
                onChange={() => setDrafts((current) => ({ ...current, reset: true }))}
                onSubmit={(event) => void submit(event, "reset")}
              >
                <fieldset className="account-form save-fields" disabled={busy}>
                  <label>
                    Account
                    <select name="user" required>
                      {users.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.username} · {user.role}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Temporary password
                    <input
                      name="password"
                      type="password"
                      autoComplete="new-password"
                      required
                      minLength={10}
                    />
                  </label>
                  <div>
                    <button
                      className="btn primary"
                      disabled={busy || accountsLoading || !!loadError || !users.length}
                    >
                      Save Temporary Password
                    </button>
                  </div>
                </fieldset>
              </form>
            </details>
          </section>
        </>
      )}
    </div>
  );
}
