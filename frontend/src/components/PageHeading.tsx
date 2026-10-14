import type { ReactNode } from "react";

export default function PageHeading({ title, description, actions }: { title:string; eyebrow?:string; description?:string; actions?:ReactNode }) {
  return <header className="workspace-heading">
    <div><h1>{title}</h1>{description && <p>{description}</p>}</div>
    {actions && <div className="action-group">{actions}</div>}
  </header>;
}
