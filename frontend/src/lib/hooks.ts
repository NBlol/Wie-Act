import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react';
import { errorMessage } from './api';

export interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setData: (updater: T | ((prev: T | null) => T | null)) => void;
}

/** Load data on mount / when deps change, with loading and error states. */
export function useQuery<T>(fn: () => Promise<T>, deps: DependencyList, enabled = true): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const alive = useRef(true);

  const reload = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fnRef.current();
      if (alive.current) setData(result);
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    } finally {
      if (alive.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  useEffect(() => {
    alive.current = true;
    void reload();
    return () => {
      alive.current = false;
    };
  }, [reload]);

  const setDataSafe = useCallback((updater: T | ((prev: T | null) => T | null)) => {
    setData((prev) => (typeof updater === 'function' ? (updater as (p: T | null) => T | null)(prev) : updater));
  }, []);

  return { data, loading, error, reload, setData: setDataSafe };
}

/** Run an async action with pending / error tracking. */
export function useAction<A extends unknown[], R>(fn: (...args: A) => Promise<R>) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(
    async (...args: A): Promise<R | undefined> => {
      setPending(true);
      setError(null);
      try {
        return await fn(...args);
      } catch (e) {
        setError(errorMessage(e));
        return undefined;
      } finally {
        setPending(false);
      }
    },
    [fn],
  );
  return { run, pending, error, clearError: () => setError(null) };
}

export function useInterval(callback: () => void, ms: number | null) {
  const saved = useRef(callback);
  saved.current = callback;
  useEffect(() => {
    if (ms === null) return;
    const id = window.setInterval(() => saved.current(), ms);
    return () => window.clearInterval(id);
  }, [ms]);
}

export function useNow(tickMs = 1000, active = true): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setNow(Date.now()), tickMs);
    return () => window.clearInterval(id);
  }, [tickMs, active]);
  return now;
}

export function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  const set = useCallback(
    (v: T) => {
      setValue(v);
      try {
        localStorage.setItem(key, JSON.stringify(v));
      } catch {
        /* ignore */
      }
    },
    [key],
  );
  return [value, set];
}
