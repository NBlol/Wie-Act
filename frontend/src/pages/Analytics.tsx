import { useMemo } from "react";
import { LuMessageSquare, LuListChecks, LuPercent, LuClock, LuFileText, LuUsers, LuNotebookPen, LuTrendingUp, LuTrendingDown, LuMinus, LuLock, LuAward, LuTriangleAlert } from 'react-icons/lu';
import { useI18n, formatDate } from '../lib/i18n';
import { api } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Card, CardTitle, ErrorState, PageHeader, SkeletonList, Stat, cn } from '../components/ui';
import { BarChart, DonutChart, HBarList, StyleRadar, CHART_COLORS } from '../lib/charts';
import type { TranslationKey } from '../i18n/en';

const STYLE_KEYS = ['visual', 'analogy', 'step_by_step', 'examples', 'repetition', 'problem_solving'] as const;

export function Analytics() {
  const { t, locale } = useI18n();
  const q = useQuery(() => api.analytics(), []);
  const a = q.data;
  const styleLabels = useMemo(() => Object.fromEntries(STYLE_KEYS.map((k) => [k, t(`style.${k}` as TranslationKey)])), [t]);

  if (q.loading) return <SkeletonList rows={5} />;
  if (q.error || !a) return <ErrorState message={q.error ?? t('common.error')} onRetry={() => void q.reload()} />;

  const activity = a.activity_last_14_days.map((d) => ({ label: d.date.slice(8, 10), value: d.questions + d.quiz_points }));
  const hasStyle = Object.values(a.style_scores ?? {}).some((v) => v > 0);
  const trendIcon = (tr: 'up' | 'flat' | 'down') => (tr === 'up' ? <LuTrendingUp className="h-3.5 w-3.5 text-mint-600" aria-label={tr} /> : tr === 'down' ? <LuTrendingDown className="h-3.5 w-3.5 text-rose-500" aria-label={tr} /> : <LuMinus className="h-3.5 w-3.5 text-ink-muted" aria-label={tr} />);
  const totalCalls = a.ai_efficiency.calls_compact + a.ai_efficiency.calls_large;

  return (
    <div className="space-y-6">
      <PageHeader title={t('an.title')} subtitle={t('an.sub')} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={t('an.questions')} value={a.totals.questions_asked} icon={<LuMessageSquare className="h-5 w-5" />} />
        <Stat label={t('an.quizzes')} value={a.totals.quizzes_taken} icon={<LuListChecks className="h-5 w-5" />} tone="mint" />
        <Stat label={t('an.avg_score')} value={`${Math.round(a.totals.avg_score_percent)}%`} icon={<LuPercent className="h-5 w-5" />} tone="amber" />
        <Stat label={t('an.study_minutes')} value={a.totals.study_minutes} icon={<LuClock className="h-5 w-5" />} />
        <Stat label={t('an.documents')} value={a.totals.documents} icon={<LuFileText className="h-5 w-5" />} />
        <Stat label={t('an.rooms')} value={a.totals.rooms} icon={<LuUsers className="h-5 w-5" />} tone="mint" />
        <Stat label={t('an.notes')} value={a.totals.notes} icon={<LuNotebookPen className="h-5 w-5" />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardTitle>{t('an.activity_14')}</CardTitle>
          <BarChart data={activity} title={t('an.activity_14')} height={170} />
          <p className="mt-1 text-xs text-ink-muted">
            {t('an.questions')} + {t('an.quiz_points')}
          </p>
        </Card>
        <Card>
          <CardTitle>{t('an.ai_title')}</CardTitle>
          <div className="flex items-center gap-4">
            <DonutChart
              title={t('an.ai_title')}
              size={120}
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
                {t('dash.compact_calls')} <strong className="tabular-nums">{a.ai_efficiency.calls_compact}</strong>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-brand-600" aria-hidden />
                {t('dash.large_calls')} <strong className="tabular-nums">{a.ai_efficiency.calls_large}</strong>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" aria-hidden />
                {t('dash.cache_hits')} <strong className="tabular-nums">{a.ai_efficiency.cache_hits}</strong>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-500" aria-hidden />
                {t('dash.fallbacks')} <strong className="tabular-nums">{a.ai_efficiency.fallbacks}</strong>
              </li>
              {a.ai_efficiency.calls_offline > 0 && (
                <li className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-400" aria-hidden />
                  {t('dash.offline_calls')} <strong className="tabular-nums">{a.ai_efficiency.calls_offline}</strong>
                </li>
              )}
            </ul>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-ink-muted">{totalCalls === 0 && a.ai_efficiency.calls_offline === 0 ? t('dash.no_activity') : t('an.ai_desc')}</p>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardTitle>{t('an.skills')}</CardTitle>
          {a.skills.length === 0 ? (
            <p className="text-sm text-ink-muted">{t('an.skills_empty')}</p>
          ) : (
            <HBarList items={a.skills.map((s) => ({ label: `${s.skill} (${s.attempts})`, value: s.mastery_percent, extra: trendIcon(s.trend) }))} />
          )}
        </Card>
        <Card>
          <CardTitle>{t('an.style_title')}</CardTitle>
          {hasStyle ? <StyleRadar scores={a.style_scores} labels={styleLabels} size={220} /> : <p className="text-sm text-ink-muted">{t('an.style_empty')}</p>}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardTitle>{t('an.confusion')}</CardTitle>
          {a.confusion_events.length === 0 ? (
            <p className="text-sm text-ink-muted">{t('an.confusion_empty')}</p>
          ) : (
            <ul className="space-y-2">
              {a.confusion_events.slice(0, 8).map((c, i) => (
                <li key={i} className="flex items-center justify-between gap-2 rounded-xl border border-line px-3 py-2 text-sm">
                  <span className="flex items-center gap-2 truncate">
                    <LuTriangleAlert className={cn('h-4 w-4 shrink-0', c.level === 'high' ? 'text-rose-500' : 'text-amber-500')} aria-hidden />
                    <span className="truncate">{c.topic}</span>
                  </span>
                  <span className="shrink-0 text-xs text-ink-muted">{formatDate(c.date, locale)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card className="lg:col-span-2">
          <CardTitle>{t('an.badges')}</CardTitle>
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {a.badges.map((b) => {
              const unlocked = !!b.unlocked_at;
              const key = `badge.${b.id}` as TranslationKey;
              const name = (t(key) === key ? b.id : t(key));
              return (
                <li key={b.id} className={cn('flex flex-col items-center rounded-2xl border p-3 text-center', unlocked ? 'border-amber-100 bg-amber-50' : 'border-line bg-paper opacity-70')} title={unlocked ? `${t('an.unlocked')} · ${formatDate(b.unlocked_at!, locale)}` : t('an.locked')}>
                  <span className={cn('flex h-10 w-10 items-center justify-center rounded-full', unlocked ? 'bg-amber-400 text-white' : 'bg-white text-ink-muted')}>{unlocked ? <LuAward className="h-5 w-5" aria-hidden /> : <LuLock className="h-4 w-4" aria-hidden />}</span>
                  <span className="mt-2 text-xs font-medium text-ink">{name}</span>
                  <span className="text-[10px] text-ink-muted">{unlocked ? t('an.unlocked') : t('an.locked')}</span>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}

export default Analytics;
