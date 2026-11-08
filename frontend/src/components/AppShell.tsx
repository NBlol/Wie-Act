import React, { useEffect, useState } from 'react';
import {
  LuLayoutDashboard,
  LuMessageSquare,
  LuListChecks,
  LuUsers,
  LuFileText,
  LuRoute,
  LuNotebookPen,
  LuChartBar,
  LuSettings,
  LuGraduationCap,
  LuLogOut,
  LuMenu,
  LuX,
  LuFlame,
  LuZap,
} from 'react-icons/lu';
import { Link, useNavigate, useRouter } from '../lib/router';
import { useT } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { ServiceBanner } from '../lib/status';
import { LanguageSwitcher } from './LanguageSwitcher';
import { Logo, LogoMark } from './Logo';
import { cn } from './ui';
import type { TranslationKey } from '../i18n/en';

interface NavItem {
  to: string;
  key: TranslationKey;
  icon: React.ReactNode;
  exact?: boolean;
  teacherOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: '/app', key: 'nav.dashboard', icon: <LuLayoutDashboard className="h-5 w-5" />, exact: true },
  { to: '/app/tutor', key: 'nav.tutor', icon: <LuMessageSquare className="h-5 w-5" /> },
  { to: '/app/quizzes', key: 'nav.quizzes', icon: <LuListChecks className="h-5 w-5" /> },
  { to: '/app/rooms', key: 'nav.rooms', icon: <LuUsers className="h-5 w-5" /> },
  { to: '/app/documents', key: 'nav.documents', icon: <LuFileText className="h-5 w-5" /> },
  { to: '/app/roadmap', key: 'nav.roadmap', icon: <LuRoute className="h-5 w-5" /> },
  { to: '/app/notes', key: 'nav.notes', icon: <LuNotebookPen className="h-5 w-5" /> },
  { to: '/app/analytics', key: 'nav.analytics', icon: <LuChartBar className="h-5 w-5" /> },
  { to: '/app/teacher', key: 'nav.teacher', icon: <LuGraduationCap className="h-5 w-5" />, teacherOnly: true },
  { to: '/app/settings', key: 'nav.settings', icon: <LuSettings className="h-5 w-5" /> },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useT();
  const { user, logout } = useAuth();
  const { path } = useRouter();
  const navigate = useNavigate();
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    setDrawer(false);
  }, [path]);

  const items = NAV.filter((n) => !n.teacherOnly || user?.role === 'teacher');
  const isActive = (n: NavItem) => (n.exact ? path === n.to : path === n.to || path.startsWith(n.to + '/'));

  const navList = (
    <nav aria-label={t('nav.menu')} className="flex flex-1 flex-col gap-1">
      {items.map((n) => (
        <Link
          key={n.to}
          to={n.to}
          aria-current={isActive(n) ? 'page' : undefined}
          className={cn(
            'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
            isActive(n) ? 'bg-brand-600 text-white shadow-soft' : 'text-ink-soft hover:bg-brand-50 hover:text-ink',
          )}
        >
          <span className={cn(isActive(n) ? 'text-white' : 'text-brand-600')}>{n.icon}</span>
          {t(n.key)}
        </Link>
      ))}
    </nav>
  );

  const userBlock = user && (
    <div className="mt-auto rounded-2xl border border-line bg-paper p-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-semibold text-white" aria-hidden>
          {user.display_name.slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink">{user.display_name}</p>
          <p className="truncate text-xs text-ink-muted">{t('nav.level', { n: user.level_number })}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate('/');
          }}
          className="rounded-lg p-2 text-ink-muted hover:bg-white hover:text-rose-600"
          aria-label={t('nav.logout')}
          title={t('nav.logout')}
        >
          <LuLogOut className="h-4 w-4" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-paper">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 start-0 z-30 hidden w-[248px] flex-col gap-4 border-e border-line bg-white p-4 lg:flex">
        <Link to="/app" className="px-2 py-1">
          <Logo />
        </Link>
        {navList}
        {userBlock}
      </aside>

      {/* mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label={t('nav.menu')}>
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 start-0 flex w-[280px] max-w-[85vw] flex-col gap-4 bg-white p-4 shadow-lift animate-rise">
            <div className="flex items-center justify-between">
              <Logo />
              <button type="button" onClick={() => setDrawer(false)} className="rounded-lg p-2 text-ink-muted hover:bg-brand-50" aria-label={t('common.close')}>
                <LuX className="h-5 w-5" />
              </button>
            </div>
            {navList}
            {userBlock}
          </div>
        </div>
      )}

      <div className="lg:ps-[248px]">
        <header className="sticky top-0 z-20 border-b border-line bg-white/85 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6">
            <button type="button" onClick={() => setDrawer(true)} className="rounded-lg p-2 text-ink-soft hover:bg-brand-50 lg:hidden" aria-label={t('nav.menu')}>
              <LuMenu className="h-5 w-5" />
            </button>
            <Link to="/app" className="lg:hidden">
              <LogoMark className="h-7 w-7" />
            </Link>
            <div className="ms-auto flex items-center gap-2">
              {user && (
                <>
                  <span className="hidden items-center gap-1 rounded-full border border-amber-100 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-600 sm:inline-flex" title={t('nav.xp')}>
                    <LuZap className="h-3.5 w-3.5" aria-hidden />
                    {user.xp} {t('nav.xp')}
                  </span>
                  {user.streak_days > 0 && (
                    <span className="hidden items-center gap-1 rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-ink-soft sm:inline-flex" title={t('dash.streak', { n: user.streak_days })}>
                      <LuFlame className="h-3.5 w-3.5 text-amber-500" aria-hidden />
                      {user.streak_days}
                    </span>
                  )}
                </>
              )}
              <LanguageSwitcher compact />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
          <div className="mb-4 empty:hidden">
            <ServiceBanner />
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}

export default AppShell;
