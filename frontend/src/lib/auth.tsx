import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getToken, setToken, LOGOUT_EVENT, type Language, type Role, type User } from './api';
import { useI18n } from './i18n';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (body: { email: string; password: string; display_name: string; preferred_language: Language; role: Role }) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<User | null>;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(!!getToken());
  const { setLocale } = useI18n();

  const applyUser = useCallback(
    (u: User) => {
      setUser(u);
      if (u.preferred_language) setLocale(u.preferred_language);
    },
    [setLocale],
  );

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const me = await api.me();
      applyUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [applyUser]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const onLogout = () => {
      setTokenState(null);
      setUser(null);
    };
    window.addEventListener(LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login({ email, password });
      setToken(res.access_token);
      setTokenState(res.access_token);
      applyUser(res.user);
      return res.user;
    },
    [applyUser],
  );

  const register = useCallback<AuthState['register']>(
    async (body) => {
      const res = await api.register(body);
      setToken(res.access_token);
      setTokenState(res.access_token);
      applyUser(res.user);
      return res.user;
    },
    [applyUser],
  );

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, loading, login, register, logout, refresh, setUser: applyUser }),
    [user, token, loading, login, register, logout, refresh, applyUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
