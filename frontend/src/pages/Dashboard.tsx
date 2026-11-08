import { LuMessageSquare, LuListChecks, LuUsers, LuFileText, LuFlame, LuSparkles, LuBrain, LuRoute, LuZap } from 'react-icons/lu';
import { Link, useNavigate } from '../lib/router';
import { useI18n, formatDate } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, type AnalyticsOverview } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, CardTitle, ErrorState, Skeleton, EmptyState, Badge } from '../components/ui';
import { DonutChart, ProgressRing, CHART_COLORS } from '../lib/charts';
import type { TranslationKey } from '../i18n/en';

const ACTION_ROUTE: Record<AnalyticsOverview['next_step']['action'], string> = {
  tutor: '/app/tutor',
  quiz: '/app/quizzes',
  roadmap: '/app/roadmap',
  room: '/app/rooms',
  document: '/app/documents',
  onboarding: '/onboarding',
};

export function Dashboard() {
  const { t, locale } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();
  const analytics = useQuery(() => api.analytics(), []);
  const convs = useQuery(() => api.conversations(), []);
  const quizzes = useQuery(() => api.quizzes(), []);

  const a = analytics.data;
  const styleKey = user?.learning_style ? (`style.${user.learning_style}` as TranslationKey) : null;
  const styleDescKey = user?.learning_style ? (`style.${user.learning_style}_desc` as TranslationKey) : null;

  const quick = [
    { to: '/app/tutor', label: t('dash.qa_tutor'), icon: <LuMessageSquare className="h-5 w-5" />, tone: 'bg-brand-50 text-brand-700' },
    { to: '/app/quizzes', label: t('dash.qa_quiz'), icon: <LuListChecks className="h-5 w-5" />, tone: 'bg-mint-50 text-mint-700' },
    { to: '/app/rooms', label: t('dash.qa_room'), icon: <LuUsers className="h-5 w-5" />, tone: 'bg-amber-50 text-amber-600' },
    { to: '/app/documents', label: t('dash.qa_document'), icon: <LuFileText className="h-5 w-5" />, tone: 'bg-brand-50 text-brand-700' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-2xl text-ink sm:text-3xl">{t('dash.greeting', { name: user?.display_name ?? '' })}</h1>
        <p className="mt-1 text-sm text-ink-soft">{t('dash.sub')}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardTitle>{t('dash.style_card')}</CardTitle>
          {styleKey ? (
            <div className="flex items-start gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-brand-600 text-white">
                <LuBrain className="h-6 w-6" />
              </span>
              <div>
                <p className="text-lg font-semibold text-ink">{t(styleKey)}</p>
                {styleDescKey && <p className="mt-1 text-sm text-ink-soft">{t(styleDescKey)}</p>}
                {user?.level && (
                  <Badge className="mt-2" tone="mint">
                    {t(`level.${user.level}` as TranslationKey)}
                  </Badge>
                )}
              </div>
            </div>
          ) : (
            <EmptyState title={t('dash.style_none')} action={<Button size="sm" onClick={() => navigate('/onboarding')}>{t('dash.style_cta')}</Button>} className="py-6" />
          )}
        </Card>

        <Card className="flex items-center gap-5">
          <ProgressRing percent={a?.level_progress_percent ?? 0} label={`${user?.level_number ?? 1}`} sub={t('nav.level', { n: '' }).trim()} color={CHART_COLORS.amber} size={104} />
          <div className="space-y-2">
            <p className="text-sm text-ink-muted">{t('dash.progress')}</p>
            <p className="flex items-center gap-1.5 text-2xl font-semibold text-ink tabular-nums">
              <LuZap className="h-5 w-5 text-amber-500" aria-hidden />
              {a?.xp ?? user?.xp ?? 0} <span className="text-sm font-medium text-ink-muted">{t('nav.xp')}</span>
            </p>
            <p className="flex items-center gap-1.5 text-sm text-ink-soft">
              <LuFlame className="h-4 w-4 text-amber-500" aria-hidden />
              {t('dash.streak', { n: a?.streak_days ?? user?.streak_days ?? 0 })}
            </p>
          </div>
        </Card>

        <Card className="surface-brand text-white">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-white/80">
            <LuSparkles className="h-4 w-4" aria-hidden />
            {t('dash.next_step')}
          </div>
          {analytics.loading && <Skeleton className="h-16 w-full bg-white/20" />}
          {a && (
            <>
              <p className="text-base font-semibold leading-snug">{a.next_step.text}</p>
              <Button
                variant="mint"
                size="sm"
                className="mt-4"
                onClick={() => navigate(a.next_step.target_id ? `${ACTION_ROUTE[a.next_step.action]}/${a.next_step.target_id}` : ACTION_ROUTE[a.next_step.action])}
              >
                {t('dash.go')}
              </Button>
            </>
          )}
          {analytics.error && <p className="text-sm text-white/80">{analytics.error}</p>}
        </Card>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-ink-soft">{t('dash.quick_actions')}</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {quick.map((q) => (
            <Link key={q.to} to={q.to} className="panel flex items-center gap-3 p-4 transition-colors hover:border-brand-300">
              <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${q.tone}`}>{q.icon}</span>
              <span className="text-sm font-medium text-ink">{q.label}</span>
            </Link>
          ))}
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardTitle action={<Link to="/app/tutor" className="text-xs font-medium text-brand-700 hover:underline">{t('common.view_all')}</Link>}>{t('dash.recent_conversations')}</CardTitle>
          {convs.loading && <Skeleton className="h-24 w-full" />}
          {convs.error && <ErrorState message={convs.error} onRetry={() => void convs.reload()} />}
          {convs.data && convs.data.length === 0 && <p className="text-sm text-ink-muted">{t('dash.no_activity')}</p>}
          <ul className="divide-y divide-line">
            {convs.data?.slice(0, 5).map((c) => (
              <li key={c.id}>
                <Link to={`/app/tutor/${c.id}`} className="flex items-center justify-between gap-3 py-2.5 text-sm hover:text-brand-700">
                  <span className="truncate font-medium">{c.title || t('tutor.untitled')}</span>
                  <span className="shrink-0 text-xs text-ink-muted">{formatDate(c.updated_at, locale)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle action={<Link to="/app/quizzes" className="text-xs font-medium text-brand-700 hover:underline">{t('common.view_all')}</Link>}>{t('dash.recent_quizzes')}</CardTitle>
          {quizzes.loading && <Skeleton className="h-24 w-full" />}
          {quizzes.error && <ErrorState message={quizzes.error} onRetry={() => void quizzes.reload()} />}
          {quizzes.data && quizzes.data.length === 0 && <p className="text-sm text-ink-muted">{t('quiz.empty_sub')}</p>}
          <ul className="divide-y divide-line">
            {quizzes.data?.slice(0, 5).map((q) => (
              <li key={q.id}>
                <Link to={`/app/quizzes/${q.id}`} className="flex items-center justify-between gap-3 py-2.5 text-sm hover:text-brand-700">
                  <span className="truncate font-medium">{q.topic}</span>
                  <span className="shrink-0 text-xs text-ink-muted">{q.best_score !== null ? t('quiz.best', { n: Math.round(q.best_score) }) : t('quiz.questions', { n: q.num_questions })}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>{t('dash.ai_efficiency')}</CardTitle>
          {analytics.loading && <Skeleton className="h-28 w-full" />}
          {a && (
            <div className="flex items-center gap-4">
              <DonutChart
                title={t('dash.ai_efficiency')}
                size={110}
                centerLabel={`${a.ai_efficiency.large_share_percent}%`}
                centerSub={t('an.large_share')}
                segments={[
                  { label: t('dash.compact_calls'), value: a.ai_efficiency.calls_compact, color: CHART_COLORS.mint },
                  { label: t('dash.large_calls'), value: a.ai_efficiency.calls_large, color: CHART_COLORS.brand },
                ]}
              />
              <ul className="space-y-1.5 text-sm">
                <li className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-mint-500" aria-hidden />
                  {t('dash.compact_calls')}: <strong className="tabular-nums">{a.ai_efficiency.calls_compact}</strong>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-brand-600" aria-hidden />
                  {t('dash.large_calls')}: <strong className="tabular-nums">{a.ai_efficiency.calls_large}</strong>
                </li>
                <li className="flex items-center gap-2 text-ink-soft">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-400" aria-hidden />
                  {t('dash.cache_hits')}: <strong className="tabular-nums">{a.ai_efficiency.cache_hits}</strong>
                </li>
                <li className="flex items-center gap-2 text-ink-soft">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500" aria-hidden />
                  {t('dash.fallbacks')}: <strong className="tabular-nums">{a.ai_efficiency.fallbacks}</strong>
                </li>
                {a.ai_efficiency.calls_offline > 0 && (
                  <li className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-400" aria-hidden />
                    {t('dash.offline_calls')}: <strong className="tabular-nums">{a.ai_efficiency.calls_offline}</strong>
                  </li>
                )}
              </ul>
            </div>
          )}
          <p className="mt-3 text-xs leading-relaxed text-ink-muted">{t('dash.ai_efficiency_desc')}</p>
        </Card>
      </div>

      {a && a.skills.length > 0 && (
        <Card>
          <CardTitle action={<Link to="/app/analytics" className="text-xs font-medium text-brand-700 hover:underline">{t('common.view_all')}</Link>}>{t('an.skills')}</CardTitle>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {a.skills.slice(0, 6).map((s) => (
              <div key={s.skill} className="flex items-center gap-3 rounded-xl border border-line p-3">
                <LuRoute className="h-4 w-4 shrink-0 text-brand-600" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{s.skill}</p>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-brand-50">
                    <div className="h-full rounded-full bg-brand-600" style={{ width: `${s.mastery_percent}%` }} />
                  </div>
                </div>
                <span className="text-sm font-semibold tabular-nums text-ink">{Math.round(s.mastery_percent)}%</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default Dashboard;
