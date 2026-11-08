import React, { useEffect, useState } from 'react';
import { LuRoute, LuPlus, LuBookOpen, LuPencilLine, LuListChecks, LuMessagesSquare, LuVideo, LuRepeat, LuFlag, LuCheck } from 'react-icons/lu';
import { useI18n, formatDate } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, type Activity, type Roadmap as RoadmapT } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, CardTitle, EmptyState, ErrorState, Field, Input, PageHeader, Select, SkeletonList, Textarea, cn } from '../components/ui';
import { ProgressRing } from '../lib/charts';
import { AiBadge, AiNotice, StagedProgress, GENERATE_STAGES } from '../lib/progress';
import type { TranslationKey } from '../i18n/en';

const KIND_ICON: Record<Activity['kind'], React.ReactNode> = {
  read: <LuBookOpen className="h-4 w-4" />,
  practice: <LuPencilLine className="h-4 w-4" />,
  quiz: <LuListChecks className="h-4 w-4" />,
  discuss: <LuMessagesSquare className="h-4 w-4" />,
  watch: <LuVideo className="h-4 w-4" />,
  recall: <LuRepeat className="h-4 w-4" />,
};

export function Roadmap() {
  const { t, locale } = useI18n();
  const { refresh } = useAuth();
  const roadmaps = useQuery(() => api.roadmaps(), []);
  const docs = useQuery(() => api.documents(), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [goal, setGoal] = useState('');
  const [weeks, setWeeks] = useState(4);
  const [hours, setHours] = useState(5);
  const [documentId, setDocumentId] = useState('');
  const [pending, setPending] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && roadmaps.data?.length) setSelectedId(roadmaps.data[0].id);
    if (roadmaps.data && roadmaps.data.length === 0) setShowForm(true);
  }, [roadmaps.data, selectedId]);

  const selected: RoadmapT | undefined = roadmaps.data?.find((r) => r.id === selectedId);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    setPending(true);
    setError(null);
    setStartedAt(Date.now());
    try {
      const r = await api.createRoadmap({ goal: goal.trim(), weeks, hours_per_week: hours, language: locale, document_id: documentId || null });
      roadmaps.setData((prev) => [r, ...(prev ?? [])]);
      setSelectedId(r.id);
      setShowForm(false);
      setGoal('');
      void refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  const toggle = async (activity: Activity) => {
    if (!selected) return;
    setToggling(activity.id);
    try {
      const updated = await api.toggleActivity(selected.id, activity.id, !activity.done);
      roadmaps.setData((prev) => (prev ?? []).map((r) => (r.id === updated.id ? updated : r)));
      void refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('rm.title')}
        subtitle={t('rm.empty_sub')}
        action={
          <Button icon={<LuPlus className="h-4 w-4" />} onClick={() => setShowForm((s) => !s)}>
            {t('rm.create_title')}
          </Button>
        }
      />

      {showForm && (
        <Card elevated>
          <CardTitle>{t('rm.create_title')}</CardTitle>
          <form onSubmit={create} className="space-y-4">
            <Field label={t('rm.goal')}>
              <Textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder={t('rm.goal_placeholder')} required maxLength={300} rows={2} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label={t('rm.weeks')}>
                <Input type="number" min={1} max={12} value={weeks} onChange={(e) => setWeeks(Math.max(1, Math.min(12, Number(e.target.value) || 4)))} />
              </Field>
              <Field label={t('rm.hours')}>
                <Input type="number" min={1} max={40} value={hours} onChange={(e) => setHours(Math.max(1, Math.min(40, Number(e.target.value) || 5)))} />
              </Field>
              <Field label={t('rm.document')} hint={t('common.optional')}>
                <Select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
                  <option value="">{t('tutor.no_document')}</option>
                  {docs.data?.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            {pending && <StagedProgress stages={GENERATE_STAGES} startedAt={startedAt} note={t('rm.generating')} compact />}
            {error && <ErrorState message={error} />}
            <Button type="submit" loading={pending} disabled={!goal.trim()}>
              {t('common.generate')}
            </Button>
          </form>
        </Card>
      )}

      {roadmaps.loading && <SkeletonList rows={3} />}
      {roadmaps.error && <ErrorState message={roadmaps.error} onRetry={() => void roadmaps.reload()} />}
      {roadmaps.data && roadmaps.data.length === 0 && !showForm && <EmptyState icon={<LuRoute className="h-6 w-6" />} title={t('rm.empty')} description={t('rm.empty_sub')} />}

      {roadmaps.data && roadmaps.data.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <Card className="p-3">
            <h2 className="mb-2 px-2 text-sm font-semibold text-ink-soft">{t('rm.your_roadmaps')}</h2>
            <ul className="space-y-1">
              {roadmaps.data.map((r) => (
                <li key={r.id}>
                  <button type="button" onClick={() => setSelectedId(r.id)} className={cn('flex w-full items-center gap-3 rounded-xl px-3 py-2 text-start text-sm', r.id === selectedId ? 'bg-brand-50 text-brand-800' : 'text-ink hover:bg-paper')}>
                    <ProgressRing percent={r.progress_percent} size={36} stroke={12} label="" />
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{r.goal}</span>
                      <span className="block text-xs text-ink-muted">
                        {t('rm.week', { n: r.weeks })} · {formatDate(r.created_at, locale)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          {selected && (
            <div className="space-y-4">
              <Card elevated className="flex flex-wrap items-center gap-5">
                <ProgressRing percent={selected.progress_percent} size={92} sub={t('rm.progress')} />
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-semibold text-ink">{selected.goal}</h2>
                  <p className="text-sm text-ink-muted">
                    {selected.weeks} {t('rm.weeks').toLowerCase()} · {t(`lang.${selected.language}` as TranslationKey)}
                  </p>
                  <div className="mt-2">
                    <AiBadge ai={selected.ai} />
                    <AiNotice ai={selected.ai} />
                  </div>
                </div>
              </Card>

              <ol className="relative space-y-4 border-s-2 border-brand-100 ps-6">
                {selected.milestones.map((m) => {
                  const done = m.activities.filter((a) => a.done).length;
                  const complete = done === m.activities.length && m.activities.length > 0;
                  return (
                    <li key={m.id} className="relative">
                      <span className={cn('absolute -start-[31px] top-4 flex h-6 w-6 items-center justify-center rounded-full border-2 text-[11px] font-semibold', complete ? 'border-mint-500 bg-mint-500 text-white' : 'border-brand-300 bg-white text-brand-700')} aria-hidden>
                        {complete ? <LuCheck className="h-3.5 w-3.5" /> : m.week}
                      </span>
                      <Card>
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="text-xs font-medium text-brand-700">{t('rm.week', { n: m.week })}</p>
                            <h3 className="text-base font-semibold text-ink">{m.title}</h3>
                          </div>
                          <span className="text-xs tabular-nums text-ink-muted">
                            {done}/{m.activities.length}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-ink-soft">
                          <span className="font-medium text-ink">{t('rm.objective')}: </span>
                          {m.objective}
                        </p>
                        <ul className="mt-3 space-y-1.5">
                          {m.activities.map((a) => (
                            <li key={a.id}>
                              <label className={cn('flex cursor-pointer items-start gap-3 rounded-xl border p-2.5 text-sm transition-colors', a.done ? 'border-mint-200 bg-mint-50/60' : 'border-line hover:border-brand-300')}>
                                <input type="checkbox" className="mt-0.5 h-4 w-4 accent-brand-600" checked={a.done} disabled={toggling === a.id} onChange={() => void toggle(a)} />
                                <span className={cn('flex h-6 w-6 shrink-0 items-center justify-center rounded-lg', a.done ? 'bg-mint-100 text-mint-700' : 'bg-brand-50 text-brand-700')} title={t(`rm.kind_${a.kind}` as TranslationKey)}>
                                  {KIND_ICON[a.kind] ?? <LuBookOpen className="h-4 w-4" />}
                                </span>
                                <span className={cn('flex-1', a.done && 'text-ink-muted line-through')}>{a.text}</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                        {m.checkpoint && (
                          <p className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-ink">
                            <LuFlag className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
                            <span>
                              <span className="font-medium">{t('rm.checkpoint')}: </span>
                              {m.checkpoint}
                            </span>
                          </p>
                        )}
                      </Card>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Roadmap;
