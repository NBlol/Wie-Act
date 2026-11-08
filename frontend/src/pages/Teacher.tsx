import React, { useEffect, useMemo, useState } from 'react';
import { LuGraduationCap, LuPlus, LuUsers, LuPercent, LuListChecks, LuScale, LuTriangleAlert } from 'react-icons/lu';
import { useI18n } from '../lib/i18n';
import { api, errorMessage, type ClassRoom } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, CardTitle, EmptyState, ErrorState, Field, Input, PageHeader, SkeletonList, Stat, cn } from '../components/ui';
import { DonutChart, HBarList, CHART_COLORS } from '../lib/charts';
import type { TranslationKey } from '../i18n/en';

const STYLE_COLORS = [CHART_COLORS.brand, CHART_COLORS.mint, CHART_COLORS.amber, CHART_COLORS.brandSoft, CHART_COLORS.mintSoft, CHART_COLORS.rose];

export function Teacher() {
  const { t } = useI18n();
  const classes = useQuery(() => api.classes(), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dashboard = useQuery(() => (selectedId ? api.classDashboard(selectedId) : Promise.reject(new Error('no class'))), [selectedId], !!selectedId);

  useEffect(() => {
    if (!selectedId && classes.data?.length) setSelectedId(classes.data[0].id);
  }, [classes.data, selectedId]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const c = await api.createClass(name.trim());
      classes.setData((prev) => [...(prev ?? []), { ...c, member_count: 0 }]);
      setSelectedId(c.id);
      setName('');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const d = dashboard.data;
  const styleSegments = useMemo(
    () =>
      Object.entries(d?.style_distribution ?? {})
        .filter(([, v]) => v > 0)
        .map(([k, v], i) => ({ label: t(`style.${k}` as TranslationKey), value: v, color: STYLE_COLORS[i % STYLE_COLORS.length] })),
    [d, t],
  );
  const selected: ClassRoom | undefined = classes.data?.find((c) => c.id === selectedId);

  return (
    <div className="space-y-6">
      <PageHeader title={t('tch.title')} subtitle={t('tch.sub')} />
      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <div className="space-y-4">
          <Card elevated>
            <CardTitle>{t('tch.create_class')}</CardTitle>
            <form onSubmit={create} className="space-y-3">
              <Field label={t('tch.class_name')}>
                <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} required />
              </Field>
              {error && <ErrorState message={error} />}
              <Button type="submit" loading={creating} icon={<LuPlus className="h-4 w-4" />} className="w-full">
                {t('common.create')}
              </Button>
            </form>
          </Card>
          <Card className="p-3">
            <h2 className="mb-2 px-2 text-sm font-semibold text-ink-soft">{t('tch.classes')}</h2>
            {classes.loading && <SkeletonList rows={2} />}
            {classes.error && <ErrorState message={classes.error} onRetry={() => void classes.reload()} />}
            {classes.data && classes.data.length === 0 && <p className="px-2 py-4 text-sm text-ink-muted">{t('tch.empty')}</p>}
            <ul className="space-y-1">
              {classes.data?.map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => setSelectedId(c.id)} className={cn('flex w-full items-center justify-between rounded-xl px-3 py-2 text-start text-sm', c.id === selectedId ? 'bg-brand-50 text-brand-800' : 'text-ink hover:bg-paper')}>
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{c.name}</span>
                      <span className="block text-xs text-ink-muted">{t('tch.members', { n: c.member_count ?? 0 })}</span>
                    </span>
                    <span className="rounded-lg bg-ink px-2 py-0.5 font-mono text-xs tracking-widest text-white">{c.code}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="space-y-4">
          {!selectedId && <EmptyState icon={<LuGraduationCap className="h-6 w-6" />} title={t('tch.select_class')} />}
          {selectedId && dashboard.loading && <SkeletonList rows={4} />}
          {selectedId && dashboard.error && <ErrorState message={dashboard.error} onRetry={() => void dashboard.reload()} />}
          {selected && d && (
            <>
              <Card className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{selected.name}</h2>
                  <p className="text-xs text-ink-muted">{t('tch.sub')}</p>
                </div>
                <div className="text-end">
                  <p className="text-[11px] text-ink-muted">{t('tch.code')}</p>
                  <p className="font-mono text-xl font-semibold tracking-[0.3em] text-ink">{selected.code}</p>
                </div>
              </Card>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label={t('tch.members', { n: '' }).trim()} value={d.members} icon={<LuUsers className="h-5 w-5" />} />
                <Stat label={t('tch.avg_score')} value={`${Math.round(d.avg_score_percent)}%`} icon={<LuPercent className="h-5 w-5" />} tone="mint" />
                <Stat label={t('tch.quizzes_taken')} value={d.quizzes_taken} icon={<LuListChecks className="h-5 w-5" />} />
                <Stat label={t('tch.participation')} value={`${Math.round(d.participation_balance_avg * 100)}%`} icon={<LuScale className="h-5 w-5" />} tone="amber" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardTitle>{t('tch.style_dist')}</CardTitle>
                  {styleSegments.length === 0 ? (
                    <p className="text-sm text-ink-muted">{t('tch.no_data')}</p>
                  ) : (
                    <div className="flex items-center gap-4">
                      <DonutChart title={t('tch.style_dist')} segments={styleSegments} size={130} centerLabel={`${d.members}`} />
                      <ul className="space-y-1 text-sm">
                        {styleSegments.map((s) => (
                          <li key={s.label} className="flex items-center gap-2">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
                            {s.label} <strong className="tabular-nums">{s.value}</strong>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Card>
                <Card>
                  <CardTitle>{t('tch.weak_skills')}</CardTitle>
                  {d.weak_skills.length === 0 ? <p className="text-sm text-ink-muted">{t('tch.no_data')}</p> : <HBarList items={d.weak_skills.map((s) => ({ label: s.skill, value: s.mastery_percent }))} color={CHART_COLORS.amber} />}
                </Card>
              </div>
              <Card>
                <CardTitle>{t('tch.confusion_hotspots')}</CardTitle>
                {d.confusion_hotspots.length === 0 ? (
                  <p className="text-sm text-ink-muted">{t('tch.no_data')}</p>
                ) : (
                  <ul className="flex flex-wrap gap-2">
                    {d.confusion_hotspots.map((c) => (
                      <li key={c.topic} className="inline-flex items-center gap-1.5 rounded-full border border-amber-100 bg-amber-50 px-3 py-1 text-sm text-ink">
                        <LuTriangleAlert className="h-3.5 w-3.5 text-amber-500" aria-hidden />
                        {c.topic} <strong className="tabular-nums">{c.count}</strong>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Teacher;
