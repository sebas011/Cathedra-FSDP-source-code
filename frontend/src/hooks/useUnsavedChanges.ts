import { useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";

export function useUnsavedChanges(value: unknown, pending = false) {
  const serialized = JSON.stringify(value);
  const baseline = useRef(serialized);
  const bypass = useRef(false);
  const dirty = serialized !== baseline.current;
  const blocker = useBlocker(() => (dirty || pending) && !bypass.current);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if ((!dirty && !pending) || bypass.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    const checkLeave = (event: Event) => {
      if (dirty && !bypass.current) event.preventDefault();
    };
    const checkPending = (event: Event) => {
      if (pending) event.preventDefault();
    };
    const discard = () => {
      bypass.current = true;
    };
    window.addEventListener("cathedra-discard-before-leave", discard);
    window.addEventListener("cathedra-can-leave", checkPending);
    window.addEventListener("cathedra-before-leave", checkLeave);
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("cathedra-discard-before-leave", discard);
      window.removeEventListener("cathedra-can-leave", checkPending);
      window.removeEventListener("beforeunload", warn);
      window.removeEventListener("cathedra-before-leave", checkLeave);
    };
  }, [dirty, pending]);

  return {
    blocker,
    dirty,
    resetBaseline: (next: unknown) => {
      baseline.current = JSON.stringify(next);
    },
    allowLeave: () => {
      bypass.current = true;
    },
  };
}
