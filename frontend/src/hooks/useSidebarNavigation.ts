import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const preferenceKey = "cathedra-fsdp-sidebar-collapsed";
const mobileQuery = "(max-width: 760px)";

export function useSidebarNavigation() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(preferenceKey) === "true"; } catch { return false; }
  });
  const [mobile, setMobile] = useState(() => window.matchMedia(mobileQuery).matches);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const location = useLocation();

  const closeMenu = () => {
    restoreFocus.current = true;
    setOpen(false);
  };

  useEffect(() => {
    try { localStorage.setItem(preferenceKey, String(collapsed)); } catch {}
  }, [collapsed]);

  useEffect(() => {
    const query = window.matchMedia(mobileQuery);
    const update = () => {
      restoreFocus.current = false;
      setMobile(query.matches);
      setOpen(false);
    };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!open || !mobile) {
      if (restoreFocus.current) {
        menuButton.current?.focus();
        restoreFocus.current = false;
      }
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const focusable = () => Array.from(sidebar.current?.querySelectorAll<HTMLElement>("a[href], button:not(:disabled)") || [])
      .filter(element => element.getClientRects().length > 0);
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        restoreFocus.current = true;
        setOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const elements = focusable();
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, mobile]);

  useEffect(() => {
    restoreFocus.current = false;
    setOpen(false);
    document.getElementById("main-content")?.focus();
  }, [location.pathname]);

  return { open, mobile, collapsed: !mobile && collapsed, sidebar, menuButton, closeButton, closeMenu,
    openMenu: () => setOpen(true), toggleSidebar: () => setCollapsed(value => !value) };
}
