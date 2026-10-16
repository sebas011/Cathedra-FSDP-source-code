import { getCurrentUser } from "../api/client";
import { matchPath, NavLink, Outlet, useLocation } from "react-router-dom";

export default function WorkspaceSection({ section }: { section: "settings" | "fsdp" }) {
  const location = useLocation();
  const isScholarEntry =
    section === "fsdp" &&
    Boolean(
      matchPath("/fsdp/new", location.pathname) || matchPath("/fsdp/:id/edit", location.pathname),
    );
  const items =
    section === "settings"
      ? [
          { to: "/settings", label: "Settings home", end: true },
          { to: "/settings/accounts", label: "Accounts & security", end: false },
          ...(getCurrentUser()?.role === "admin"
            ? [{ to: "/settings/programs", label: "Program catalog", end: false }]
            : []),
        ]
      : [{ to: "/fsdp", label: "Scholars", end: true }];
  return (
    <div className="stack-md workspace-section">
      {items.length > 1 && !isScholarEntry && (
        <nav className="workspace-tabs no-print" aria-label={section + " pages"}>
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
      <Outlet />
    </div>
  );
}
