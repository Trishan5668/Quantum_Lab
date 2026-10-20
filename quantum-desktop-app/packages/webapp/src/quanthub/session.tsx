import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "../auth/AuthProvider";
import { api, loadIdentity, saveIdentity, type LocalIdentity } from "./client";
import type { Viewer } from "./types";

interface SessionValue {
  viewer: Viewer | null;
  loading: boolean;
  error: string | null;
  identity: LocalIdentity;
  updateIdentity: (next: Partial<Pick<LocalIdentity, "handle" | "display_name" | "email">>) => void;
  refresh: () => void;
  usingFirebase: boolean;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }): JSX.Element {
  const auth = useAuth();
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [identity, setIdentity] = useState<LocalIdentity>(() => loadIdentity());
  const [reloadToken, setReloadToken] = useState(0);

  const usingFirebase = Boolean(auth.firebaseReady && auth.user);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api<Viewer>("/me")
      .then((next) => {
        if (!alive) return;
        setViewer(next);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!alive) return;
        setViewer(null);
        setError(cause instanceof Error ? cause.message : "Unable to load your session.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [reloadToken, auth.user?.uid, identity.handle]);

  const updateIdentity = useCallback(
    (next: Partial<Pick<LocalIdentity, "handle" | "display_name" | "email">>) => {
      setIdentity((current) => {
        const merged: LocalIdentity = {
          ...current,
          ...next,
          handle: (next.handle ?? current.handle).trim().toLowerCase() || current.handle,
          display_name: (next.display_name ?? current.display_name).trim() || current.handle,
        };
        saveIdentity(merged);
        return merged;
      });
      setReloadToken((token) => token + 1);
    },
    [],
  );

  const value = useMemo<SessionValue>(
    () => ({
      viewer,
      loading,
      error,
      identity,
      updateIdentity,
      refresh: () => setReloadToken((token) => token + 1),
      usingFirebase,
    }),
    [viewer, loading, error, identity, updateIdentity, usingFirebase],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return value;
}
