import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { label: string };
export default function IconAction({ label, className = "", children, ...props }: Props) {
  return <button type="button" {...props} aria-label={label} title={label} className={`btn secondary icon-action ${className}`}>{children}</button>;
}
