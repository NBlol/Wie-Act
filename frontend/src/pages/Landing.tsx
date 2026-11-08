import {
  LuLightbulb,
  LuBrain,
  LuCpu,
  LuListChecks,
  LuUsers,
  LuFileText,
  LuChartBar,
  LuShieldCheck,
  LuSparkles,
  LuCheck,
  LuDatabase,
  LuRefreshCw,
} from 'react-icons/lu';
import { Link } from '../lib/router';
import { useT } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { LanguageChips, LanguageSwitcher } from '../components/LanguageSwitcher';
import { Logo } from '../components/Logo';
import { Button } from '../components/ui';

function HeroDemo() {
  const t = useT();
  return (
    <div className="panel-elevated relative mx-auto w-full max-w-md overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          <LuSparkles className="h-4 w-4 text-brand-600" aria-hidden />
          {t('nav.tutor')}
        </span>
        <span className="rounded-full bg-mint-50 px-2 py-0.5 text-[11px] font-medium text-mint-700">{t('landing.demo_label')}</span>
      </div>
      <div className="space-y-3 bg-gradient-to-b from-white to-brand-50/40 p-4">
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-2xl rounded-ee-md bg-brand-600 px-4 py-2.5 text-sm text-white">{t('landing.demo_user')}</p>
        </div>
        <ol className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-ink-muted" aria-hidden>
          <li className="flex items-center gap-1">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-mint-500 text-white">
              <LuCheck className="h-2.5 w-2.5" />
            </span>
            {t('stage.triage')}
          </li>
          <li className="flex items-center gap-1">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-mint-500 text-white">
              <LuCheck className="h-2.5 w-2.5" />
            </span>
            {t('stage.reason')}
          </li>
          <li className="flex items-center gap-1">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-mint-500 text-white">
              <LuCheck className="h-2.5 w-2.5" />
            </span>
            {t('stage.format')}
          </li>
        </ol>
        <div className="max-w-[92%] rounded-2xl rounded-ss-md border border-line bg-white px-4 py-3 text-sm text-ink shadow-soft">
          <p>{t('landing.demo_hint')}</p>
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-ink-soft">
            <LuLightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden />
            {t('landing.demo_guiding')}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-mint-200 bg-mint-50 px-2 py-0.5 text-[11px] font-medium text-mint-700">
              <LuCpu className="h-3 w-3" aria-hidden />
              {t('ai.tier_compact')}
            </span>
            <span className="rounded-lg border border-brand-200 px-2.5 py-1 text-xs font-medium text-brand-700">{t('landing.demo_reveal')}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Landing() {
  const t = useT();
  const { user } = useAuth();

  const features = [
    { icon: <LuLightbulb className="h-5 w-5" />, title: t('landing.f1_title'), desc: t('landing.f1_desc') },
    { icon: <LuBrain className="h-5 w-5" />, title: t('landing.f2_title'), desc: t('landing.f2_desc') },
    { icon: <LuListChecks className="h-5 w-5" />, title: t('landing.f3_title'), desc: t('landing.f3_desc') },
    { icon: <LuUsers className="h-5 w-5" />, title: t('landing.f4_title'), desc: t('landing.f4_desc') },
    { icon: <LuFileText className="h-5 w-5" />, title: t('landing.f5_title'), desc: t('landing.f5_desc') },
    { icon: <LuChartBar className="h-5 w-5" />, title: t('landing.f6_title'), desc: t('landing.f6_desc') },
  ];

  return (
    <div className="surface-glow min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" aria-label="EdNova AI">
          <Logo />
        </Link>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          {user ? (
            <Link to="/app">
              <Button size="sm">{t('nav.dashboard')}</Button>
            </Link>
          ) : (
            <>
              <Link to="/login" className="hidden sm:block">
                <Button variant="ghost" size="sm">
                  {t('nav.login')}
                </Button>
              </Link>
              <Link to="/register">
                <Button size="sm">{t('nav.register')}</Button>
              </Link>
            </>
          )}
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:pt-14">
        <div className="animate-rise">
          <p className="mb-4 text-sm font-medium text-brand-700">{t('app.tagline')}</p>
          <h1 className="display max-w-xl text-4xl text-ink sm:text-5xl lg:text-6xl">{t('landing.hero_title')}</h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-ink-soft sm:text-lg">{t('landing.hero_sub')}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={user ? '/app' : '/register'}>
              <Button size="lg">{t('landing.cta_start')}</Button>
            </Link>
            {!user && (
              <Link to="/login">
                <Button size="lg" variant="secondary">
                  {t('landing.cta_login')}
                </Button>
              </Link>
            )}
          </div>
          <div className="mt-10">
            <p className="mb-2 text-sm text-ink-muted">{t('landing.languages_title')}</p>
            <LanguageChips />
          </div>
        </div>
        <div className="animate-rise [animation-delay:120ms]">
          <HeroDemo />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="max-w-2xl">
          <h2 className="display text-3xl text-ink">{t('landing.features_title')}</h2>
          <p className="mt-3 text-ink-soft">{t('landing.features_sub')}</p>
        </div>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <li key={i} className="panel p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">{f.icon}</div>
              <h3 className="text-base font-semibold text-ink">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{f.desc}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="panel-elevated overflow-hidden p-0">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
            <div className="surface-brand p-8 text-white sm:p-10">
              <h2 className="display text-3xl">{t('landing.routing_title')}</h2>
              <p className="mt-4 text-white/85">{t('landing.routing_sub')}</p>
              <div className="mt-8 space-y-3">
                <div className="flex items-start gap-3 rounded-2xl bg-white/10 p-3">
                  <LuDatabase className="mt-0.5 h-5 w-5 shrink-0 text-mint-300" aria-hidden />
                  <div>
                    <p className="font-semibold">{t('landing.cache_title')}</p>
                    <p className="mt-1 text-sm text-white/80">{t('landing.cache_desc')}</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-8 sm:p-10">
              <div className="relative grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-mint-200 bg-mint-50/60 p-5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mint-500 text-ink">
                      <LuCpu className="h-5 w-5" />
                    </span>
                    <h3 className="font-semibold text-ink">{t('landing.compact_title')}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-ink-soft">{t('landing.compact_desc')}</p>
                  <div className="mt-4 h-1.5 w-full rounded-full bg-mint-200">
                    <div className="h-full w-[78%] rounded-full bg-mint-500" />
                  </div>
                </div>
                <div className="rounded-2xl border border-brand-200 bg-brand-50/60 p-5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
                      <LuBrain className="h-5 w-5" />
                    </span>
                    <h3 className="font-semibold text-ink">{t('landing.large_title')}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-ink-soft">{t('landing.large_desc')}</p>
                  <div className="mt-4 h-1.5 w-full rounded-full bg-brand-200">
                    <div className="h-full w-[22%] rounded-full bg-brand-600" />
                  </div>
                </div>
              </div>
              <div className="mt-6 flex items-start gap-3 rounded-2xl border border-line p-4 text-sm text-ink-soft">
                <LuRefreshCw className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" aria-hidden />
                <p>{t('banner.large_unavailable')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-6 lg:grid-cols-[0.6fr_1fr] lg:items-start">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-mint-100 text-mint-700">
              <LuShieldCheck className="h-6 w-6" />
            </span>
            <h2 className="display text-3xl text-ink">{t('landing.privacy_title')}</h2>
          </div>
          <ul className="grid gap-3 sm:grid-cols-3">
            {[t('landing.privacy_p1'), t('landing.privacy_p2'), t('landing.privacy_p3')].map((p, i) => (
              <li key={i} className="panel flex items-start gap-2 p-4 text-sm text-ink-soft">
                <LuCheck className="mt-0.5 h-4 w-4 shrink-0 text-mint-600" aria-hidden />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-4 py-10 text-sm text-ink-muted sm:flex-row sm:items-center sm:px-6">
        <Logo size="sm" />
        <p>{t('landing.footer')}</p>
      </footer>
    </div>
  );
}

export default Landing;
