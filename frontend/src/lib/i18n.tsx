import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { Language } from './api';
import { en, type Dictionary, type TranslationKey } from '../i18n/en';
import { fr } from '../i18n/fr';
import { ar } from '../i18n/ar';
import { tn } from '../i18n/tn';

export const DICTIONARIES: Record<Language, Dictionary> = { en, fr, ar, tn };
export const RTL_LANGUAGES: Language[] = ['ar', 'tn'];
const LOCALE_KEY = 'ednova_locale';

export type Vars = Record<string, string | number>;
export type TFunction = (key: TranslationKey, vars?: Vars) => string;

interface I18nState {
  locale: Language;
  setLocale: (l: Language) => void;
  t: TFunction;
  dir: 'ltr' | 'rtl';
}

const I18nContext = createContext<I18nState | null>(null);

function detectInitial(): Language {
  try {
    const stored = localStorage.getItem(LOCALE_KEY);
    if (stored && (['en', 'fr', 'ar', 'tn'] as string[]).includes(stored)) return stored as Language;
  } catch {
    /* ignore */
  }
  const nav = (navigator.language || 'en').toLowerCase();
  if (nav.startsWith('fr')) return 'fr';
  if (nav.startsWith('ar')) return 'ar';
  return 'en';
}

export function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k: string) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Language>(detectInitial);

  const setLocale = useCallback((l: Language) => {
    setLocaleState(l);
    try {
      localStorage.setItem(LOCALE_KEY, l);
    } catch {
      /* ignore */
    }
  }, []);

  const dir: 'ltr' | 'rtl' = RTL_LANGUAGES.includes(locale) ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = locale === 'tn' ? 'aeb' : locale;
  }, [dir, locale]);

  const t = useCallback<TFunction>(
    (key, vars) => {
      const dict = DICTIONARIES[locale];
      const raw = dict[key] ?? en[key] ?? key;
      return interpolate(raw, vars);
    },
    [locale],
  );

  const value = useMemo(() => ({ locale, setLocale, t, dir }), [locale, setLocale, t, dir]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nState {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>');
  return ctx;
}

export function useT(): TFunction {
  return useI18n().t;
}

/** Format a date in the active locale with Latin digits. */
export function formatDate(iso: string, locale: Language, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' }): string {
  const tag = locale === 'ar' || locale === 'tn' ? 'ar-TN-u-nu-latn' : locale === 'fr' ? 'fr-FR' : 'en-GB';
  try {
    return new Intl.DateTimeFormat(tag, opts).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

export function formatTime(iso: string, locale: Language): string {
  return formatDate(iso, locale, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
}
