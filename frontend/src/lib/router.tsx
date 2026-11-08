import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type Params = Record<string, string>;

interface RouterState {
  path: string;
  search: string;
  navigate: (to: string, opts?: { replace?: boolean }) => void;
}

const RouterContext = createContext<RouterState | null>(null);
const ParamsContext = createContext<Params>({});

function currentPath(): string {
  return window.location.pathname || '/';
}

export function Router({ children }: { children: React.ReactNode }) {
  const [path, setPath] = useState(currentPath());
  const [search, setSearch] = useState(window.location.search);

  useEffect(() => {
    const onPop = () => {
      setPath(currentPath());
      setSearch(window.location.search);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((to: string, opts?: { replace?: boolean }) => {
    const url = new URL(to, window.location.origin);
    if (url.pathname === window.location.pathname && url.search === window.location.search) return;
    if (opts?.replace) window.history.replaceState(null, '', url.pathname + url.search);
    else window.history.pushState(null, '', url.pathname + url.search);
    setPath(url.pathname);
    setSearch(url.search);
    window.scrollTo({ top: 0 });
  }, []);

  const value = useMemo(() => ({ path, search, navigate }), [path, search, navigate]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter(): RouterState {
  const ctx = useContext(RouterContext);
  if (!ctx) throw new Error('useRouter must be used inside <Router>');
  return ctx;
}

export function useNavigate() {
  return useRouter().navigate;
}

export function useParams<T extends Params = Params>(): T {
  return useContext(ParamsContext) as T;
}

export function useSearchParams(): URLSearchParams {
  const { search } = useRouter();
  return useMemo(() => new URLSearchParams(search), [search]);
}

/** Match a pattern like `/app/tutor/:id` against a path. Returns params or null. */
export function matchPath(pattern: string, path: string): Params | null {
  const p = pattern.split('/').filter(Boolean);
  const s = path.split('/').filter(Boolean);
  if (p.length !== s.length) return null;
  const params: Params = {};
  for (let i = 0; i < p.length; i++) {
    const seg = p[i];
    if (seg.startsWith(':')) params[seg.slice(1)] = decodeURIComponent(s[i]);
    else if (seg !== s[i]) return null;
  }
  return params;
}

export interface RouteDef {
  path: string;
  element: React.ReactNode;
}

/** Renders the first matching route; `fallback` when none matches. */
export function Routes({ routes, fallback }: { routes: RouteDef[]; fallback: React.ReactNode }) {
  const { path } = useRouter();
  for (const r of routes) {
    const params = matchPath(r.path, path);
    if (params) return <ParamsContext.Provider value={params}>{r.element}</ParamsContext.Provider>;
  }
  return <>{fallback}</>;
}

export function Link({
  to,
  children,
  className,
  onClick,
  ...rest
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { to: string }) {
  const navigate = useNavigate();
  return (
    <a
      href={to}
      className={className}
      onClick={(e) => {
        onClick?.(e);
        if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        navigate(to);
      }}
      {...rest}
    >
      {children}
    </a>
  );
}

export function Redirect({ to }: { to: string }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace: true });
  }, [to, navigate]);
  return null;
}
