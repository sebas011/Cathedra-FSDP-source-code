import { getCurrentUser } from "../api/client";
import PageHeading from "../components/PageHeading";
import { SettingsIcon, BackupIcon } from "../components/Icons";
import { Link } from "react-router-dom";

export default function SettingsPage() {
  return (
    <div className="stack-md">
      <PageHeading
        title="Office settings"
        eyebrow="SETTINGS"
        description="Manage office access and keep your local workspace protected."
      />
      <div className="workspace-card-grid">
        {getCurrentUser()?.role === "admin" && (
          <section className="data-card workspace-card">
            <h2>Program catalog</h2>
            <Link className="btn secondary" to="/settings/programs">
              Manage programs
            </Link>
          </section>
        )}
        <section className="data-card workspace-card">
          <div className="workspace-card-icon" aria-hidden="true">
            <SettingsIcon />
          </div>
          <h2>Accounts & security</h2>
          <p>Change your password. Administrators can also manage office accounts.</p>
          <Link className="btn secondary" to="/settings/accounts">
            Open account settings
          </Link>
        </section>
        <section className="data-card workspace-card">
          <div className="workspace-card-icon" aria-hidden="true">
            <BackupIcon />
          </div>
          <h2>Backup & system health</h2>
          <p>
            Backups, restore, and readiness checks stay in dedicated pages, separate from everyday
            settings.
          </p>
          <div className="action-group">
            <Link className="btn secondary" to="/backup-export">
              Backup & Export
            </Link>
            <Link className="btn secondary" to="/system-readiness">
              System Readiness
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
