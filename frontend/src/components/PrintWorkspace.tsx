import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal, flushSync } from "react-dom";
import { useLocation } from "react-router-dom";

type Preparation = { prepare: () => Promise<ReactNode>; current: () => boolean; priority: number };
type PrintWorkspace = {
  register: (preparation: Preparation) => () => void;
  requestPrint: () => Promise<void>;
  printing: boolean;
  error: string;
};
const Context = createContext<PrintWorkspace | null>(null);

export function PrintWorkspaceProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const locationKey = useRef(location.key);
  locationKey.current = location.key;
  const preparations = useRef(new Map<symbol, Preparation>());
  const busy = useRef(false);
  const mounted = useRef(true);
  const [printing, setPrinting] = useState(false);
  const [error, setError] = useState("");
  const [document, setDocument] = useState<ReactNode>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      window.document.body.classList.remove("prepared-print");
    };
  }, []);
  useEffect(() => {
    setError("");
  }, [location.key]);
  const register = useCallback((preparation: Preparation) => {
    const token = Symbol();
    preparations.current.set(token, preparation);
    return () => {
      preparations.current.delete(token);
    };
  }, []);
  const requestPrint = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    setPrinting(true);
    setError("");
    const startedAtLocation = locationKey.current;
    const entry = [...preparations.current.entries()].sort(
      (a, b) => b[1].priority - a[1].priority,
    )[0];
    try {
      if (!entry) {
        window.print();
        return;
      }
      const [token, preparation] = entry;
      const snapshot = await preparation.prepare();
      if (
        !mounted.current ||
        locationKey.current !== startedAtLocation ||
        preparations.current.get(token) !== preparation ||
        !preparation.current()
      ) {
        if (mounted.current)
          setError(
            "Print cancelled because the page or selected filters changed. Start printing again from the current view.",
          );
        return;
      }
      flushSync(() => setDocument(snapshot));
      window.document.body.classList.add("prepared-print");
      window.print();
    } catch (caught) {
      if (mounted.current)
        setError(
          caught instanceof Error ? caught.message : "Unable to prepare this print. Try again.",
        );
    } finally {
      window.document.body.classList.remove("prepared-print");
      if (mounted.current) {
        flushSync(() => setDocument(null));
        setPrinting(false);
      }
      busy.current = false;
    }
  }, []);
  return (
    <Context.Provider value={{ register, requestPrint, printing, error }}>
      {children}
      {document &&
        createPortal(<div id="prepared-print-document">{document}</div>, window.document.body)}
    </Context.Provider>
  );
}

export function usePrintWorkspace() {
  return useContext(Context);
}

export function usePreparedPrint(scope: string, prepare: () => Promise<ReactNode>, priority = 10) {
  const workspace = usePrintWorkspace();
  const scopeRef = useRef(scope);
  scopeRef.current = scope;
  const prepareRef = useRef(prepare);
  prepareRef.current = prepare;
  const register = workspace?.register;
  useEffect(() => {
    if (!register) return;
    return register({
      prepare: () => prepareRef.current(),
      current: () => scopeRef.current === scope,
      priority,
    });
  }, [register, scope, priority]);
  return workspace;
}
