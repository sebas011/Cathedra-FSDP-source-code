import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { clearSession, saveSession, signIn } from "../api";
import type { LocalUser } from "../types";
import { getExpiredUser } from "../api/client";
import ConfirmationDialog from "./ConfirmationDialog";

export default function SessionRecovery({ user }: { user: LocalUser }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [discardOpen, setDiscardOpen] = useState(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const password = String(new FormData(event.currentTarget).get("password") || "");
    setBusy(true);
    setError("");
    try {
      const session = await signIn(user.username, password);
      if (!active.current || getExpiredUser()?.id !== user.id) return;
      if (session.user.id !== user.id || session.user.must_change_password) {
        setError("This account requires a new sign-in. Discard this draft to continue securely.");
        return;
      }
      saveSession(session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <dialog
        ref={dialog}
        className="unsaved-dialog"
        aria-labelledby="session-recovery-title"
        onCancel={(event) => event.preventDefault()}
      >
        <h2 id="session-recovery-title">Sign in again to keep editing</h2>
        <p>
          Your session ended. Your unsaved work remains only in this window. Sign in as{" "}
          {user.username} to continue; no save will be retried automatically.
        </p>
        <form onSubmit={(event) => void submit(event)}>
          <fieldset className="save-fields stack-md" disabled={busy}>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                autoFocus
              />
            </label>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <div className="action-group">
              <button className="btn primary" type="submit">
                {busy ? "Signing in…" : "Continue editing"}
              </button>
              <button
                className="btn secondary danger"
                type="button"
                onClick={() => {
                  if (!busy) setDiscardOpen(true);
                }}
              >
                Discard and sign in
              </button>
            </div>
          </fieldset>
        </form>
      </dialog>
      <ConfirmationDialog
        open={discardOpen}
        title="Discard unsaved work?"
        description="Discard unsaved work and return to sign-in? This window's unsaved changes cannot be recovered."
        confirmLabel="Discard and sign in"
        cancelLabel="Keep editing"
        confirmDisabled={busy}
        onConfirm={() => {
          if (!busy) {
            setDiscardOpen(false);
            clearSession();
          }
        }}
        onCancel={() => setDiscardOpen(false)}
      />
    </>
  );
}
