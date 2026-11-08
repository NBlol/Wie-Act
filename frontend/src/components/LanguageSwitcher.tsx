import React, { useEffect, useRef, useState } from 'react';
import { LuGlobe, LuCheck } from 'react-icons/lu';
import { LANGUAGES, api, type Language } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { cn } from './ui';

const NATIVE: Record<Language, string> = { en: 'English', fr: 'Français', ar: 'العربية', tn: 'تونسي' };

export function LanguageSwitcher({ compact = false, className }: { compact?: boolean; className?: string }) {
  const { locale, setLocale, t } = useI18n();
  const { user, setUser } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const choose = async (l: Language) => {
    setLocale(l);
    setOpen(false);
    if (user && user.preferred_language !== l) {
      try {
        const updated = await api.updateMe({ preferred_language: l });
        setUser(updated);
      } catch {
        /* keep local choice even if the server is unavailable */
      }
    }
  };

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t('common.language')}
        className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-line bg-white px-2.5 text-sm font-medium text-ink hover:border-brand-300"
      >
        <LuGlobe className="h-4 w-4 text-brand-600" aria-hidden />
        {!compact && <span>{NATIVE[locale]}</span>}
      </button>
      {open && (
        <ul role="listbox" className="absolute end-0 z-50 mt-1 w-44 overflow-hidden rounded-xl border border-line bg-white p-1 shadow-lift animate-rise">
          {LANGUAGES.map((l) => (
            <li key={l}>
              <button
                type="button"
                role="option"
                aria-selected={l === locale}
                onClick={() => void choose(l)}
                className={cn('flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-brand-50', l === locale ? 'font-semibold text-brand-700' : 'text-ink')}
                dir={l === 'ar' || l === 'tn' ? 'rtl' : 'ltr'}
              >
                <span>{NATIVE[l]}</span>
                {l === locale && <LuCheck className="h-4 w-4" aria-hidden />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Horizontal chips (landing page). */
export function LanguageChips({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {LANGUAGES.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLocale(l)}
          aria-pressed={l === locale}
          dir={l === 'ar' || l === 'tn' ? 'rtl' : 'ltr'}
          className={cn(
            'rounded-full border px-4 py-1.5 text-sm font-medium transition-colors',
            l === locale ? 'border-ink bg-ink text-white' : 'border-line bg-white text-ink hover:border-brand-400',
          )}
        >
          {NATIVE[l]}
        </button>
      ))}
    </div>
  );
}

export default LanguageSwitcher;
export type LanguageSwitcherProps = React.ComponentProps<typeof LanguageSwitcher>;
