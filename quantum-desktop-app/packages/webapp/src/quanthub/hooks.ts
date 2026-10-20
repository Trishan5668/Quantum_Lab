import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./client";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | Error | null;
  reload: () => void;
}

/** Small fetch-on-deps hook with an explicit reload trigger and abort support. */
export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [token, setToken] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    setLoading(true);
    loaderRef
      .current(controller.signal)
      .then((value) => {
        if (!alive) return;
        setData(value);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!alive || controller.signal.aborted) return;
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, token]);

  const reload = useCallback(() => setToken((value) => value + 1), []);
  return { data, loading, error, reload };
}

/** Poll an async loader until it reports a terminal condition. */
export function usePolling(active: boolean, intervalMs: number, run: () => void): void {
  const runRef = useRef(run);
  runRef.current = run;
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => runRef.current(), intervalMs);
    return () => window.clearInterval(timer);
  }, [active, intervalMs]);
}

export function useDocumentTitle(title: string | null | undefined): void {
  useEffect(() => {
    if (!title) return;
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);
}
