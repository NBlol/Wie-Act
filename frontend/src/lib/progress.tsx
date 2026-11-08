import React, { useEffect, useMemo, useState } from 'react';
import { LuCheck, LuCpu, LuBrain, LuDatabase, LuTriangleAlert, LuWifiOff, LuZap } from 'react-icons/lu';
import type { AiMeta, Stage } from './api';
import { api } from './api';
import { useT } from './i18n';
import type { TranslationKey } from '../i18n/en';
import { useNow } from './hooks';

export const DEFAULT_STAGES: Stage[] = [
  { key: 'triage', label_key: 'stage.triage', typical_ms: 1500 },
  { key: 'retrieve', label_key: 'stage.retrieve', typical_ms: 800 },
  { key: 'reason', label_key: 'stage.reason', typical_ms: 6000 },
  { key: 'format', label_key: 'stage.format', typical_ms: 1000 },
];

export const GENERATE_STAGES: Stage[] = [
  { key: 'triage', label_key: 'stage.triage', typical_ms: 800 },
  { key: 'reason', label_key: 'stage.generate', typical_ms: 8000 },
  { key: 'format', label_key: 'stage.format', typical_ms: 1000 },
];

export const GRADE_STAGES: Stage[] = [
  { key: 'grade', label_key: 'stage.grade', typical_ms: 2500 },
  { key: 'format', label_key: 'stage.format', typical_ms: 600 },
];

let cachedStages: Stage[] | null = null;

/** Loads the tutor stage definitions once (falls back to defaults). */
export function useTutorStages(): Stage[] {
  const [stages, setStages] = useState<Stage[]>(cachedStages ?? DEFAULT_STAGES);
  useEffect(() => {
    if (cachedStages) return;
    api
      .stages()
      .then((r) => {
        if (r.stages?.length) {
          cachedStages = r.stages;
          setStages(r.stages);
        }
      })
      .catch(() => {
        /* keep defaults */
      });
  }, []);
  return stages;
}

function isKey(k: string): k is TranslationKey {
  return k.startsWith('stage.');
}

export function StagedProgress({
  stages = DEFAULT_STAGES,
  startedAt,
  note,
  compact = false,
}: {
  stages?: Stage[];
  startedAt: number;
  note?: string;
  compact?: boolean;
}) {
  const t = useT();
  const now = useNow(250);
  const elapsed = now - startedAt;

  const { current, overrun } = useMemo(() => {
    let acc = 0;
    for (let i = 0; i < stages.length; i++) {
      acc += stages[i].typical_ms;
      if (elapsed < acc) return { current: i, overrun: false };
    }
    return { current: stages.length - 1, overrun: elapsed > acc * 1.6 };
  }, [elapsed, stages]);

  const seconds = Math.floor(elapsed / 1000);

  return (
    <div className={`rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50/80 to-white ${compact ? 'p-3' : 'p-4'}`} aria-live="polite" aria-busy="true">
      <ol className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {stages.map((s, i) => {
          const state = i < current ? 'done' : i === current ? 'active' : 'todo';
          const label = isKey(s.label_key) ? t(s.label_key) : s.key;
          return (
            <li key={s.key} className="flex items-center gap-1.5 text-sm">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${
                  state === 'done'
                    ? 'bg-mint-500 text-white'
                    : state === 'active'
                      ? 'bg-brand-600 text-white animate-pulse-soft'
                      : 'border border-brand-200 bg-white text-ink-muted'
                }`}
                aria-hidden
              >
                {state === 'done' ? <LuCheck className="h-3 w-3" /> : i + 1}
              </span>
              <span className={state === 'active' ? 'font-medium text-ink thinking-dots' : state === 'done' ? 'text-ink-soft' : 'text-ink-muted'}>{label}</span>
            </li>
          );
        })}
      </ol>
      {!compact && (
        <div className="mt-3 space-y-2" aria-hidden>
          <div className="h-2.5 w-11/12 rounded-full bg-brand-100 animate-pulse-soft" />
          <div className="h-2.5 w-3/4 rounded-full bg-brand-100 animate-pulse-soft [animation-delay:200ms]" />
          <div className="h-2.5 w-1/2 rounded-full bg-brand-100 animate-pulse-soft [animation-delay:400ms]" />
        </div>
      )}
      <p className="mt-2 text-xs text-ink-muted">
        {overrun ? t('stage.still_working') : note ?? t('tutor.waiting_note')} · {seconds}s
      </p>
    </div>
  );
}

const FALLBACK_KEYS: Record<NonNullable<AiMeta['fallback_reason']>, TranslationKey> = {
  large_unavailable: 'ai.fallback_large_unavailable',
  rate_limited: 'ai.fallback_rate_limited',
  provider_error: 'ai.fallback_provider_error',
  no_api_key: 'ai.fallback_no_api_key',
};

/** Small pill describing which model produced a result. */
export function AiBadge({ ai, className = '' }: { ai: AiMeta | undefined | null; className?: string }) {
  const t = useT();
  if (!ai) return null;
  const offline = ai.provider === 'offline';
  const tierLabel = ai.tier === 'large' ? t('ai.tier_large') : ai.tier === 'compact' ? t('ai.tier_compact') : t('ai.tier_none');
  const tone = offline
    ? 'border-amber-400/60 bg-amber-50 text-amber-600'
    : ai.tier === 'large'
      ? 'border-brand-200 bg-brand-50 text-brand-700'
      : ai.tier === 'compact'
        ? 'border-mint-200 bg-mint-50 text-mint-700'
        : 'border-line bg-paper text-ink-muted';
  const Icon = offline ? LuWifiOff : ai.tier === 'large' ? LuBrain : ai.tier === 'compact' ? LuCpu : LuDatabase;
  const title = [ai.model, ai.fallback_reason ? t(FALLBACK_KEYS[ai.fallback_reason]) : null].filter(Boolean).join(' · ');
  return (
    <span className={`inline-flex flex-wrap items-center gap-1 ${className}`} title={title}>
      <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${tone}`}>
        <Icon className="h-3 w-3" aria-hidden />
        {offline ? t('ai.offline') : tierLabel}
      </span>
      {ai.cached && (
        <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5 text-[11px] text-ink-soft">
          <LuZap className="h-3 w-3 text-amber-500" aria-hidden />
          {t('ai.cached')}
        </span>
      )}
      {ai.fallback && (
        <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/50 bg-amber-50 px-2 py-0.5 text-[11px] text-amber-600">
          <LuTriangleAlert className="h-3 w-3" aria-hidden />
          {t('ai.fallback')}
        </span>
      )}
      {ai.latency_ms > 0 && !ai.cached && <span className="text-[11px] text-ink-muted">{t('ai.latency', { ms: ai.latency_ms })}</span>}
    </span>
  );
}

/** Inline notice line for `ai.notice` or fallback reasons. */
export function AiNotice({ ai }: { ai: AiMeta | undefined | null }) {
  const t = useT();
  if (!ai) return null;
  const text = ai.notice ?? (ai.fallback_reason ? t(FALLBACK_KEYS[ai.fallback_reason]) : null);
  if (!text) return null;
  return (
    <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-600">
      <LuTriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{text}</span>
    </p>
  );
}

export function TierDot({ tier }: { tier: 'compact' | 'large' }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${tier === 'large' ? 'bg-brand-600' : 'bg-mint-500'}`} aria-hidden />;
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }): React.ReactElement {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
