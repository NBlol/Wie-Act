import { useMemo, useState } from "react";
import { LuCheck, LuChevronLeft, LuChevronRight, LuSparkles } from 'react-icons/lu';
import { Link, useNavigate } from '../lib/router';
import { useI18n } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, LEVELS, type DiagnosticQuestion, type DiagnosticResult, type Level } from '../lib/api';
import { useQuery, useAction } from '../lib/hooks';
import { Logo } from '../components/Logo';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { Button, Field, Input, Select, ErrorState, Skeleton, Badge, cn } from '../components/ui';
import { StyleRadar } from '../lib/charts';
import { AiBadge, AiNotice, StagedProgress, GRADE_STAGES } from '../lib/progress';
import type { TranslationKey } from '../i18n/en';

const STYLE_KEYS = ['visual', 'analogy', 'step_by_step', 'examples', 'repetition', 'problem_solving'] as const;

export function Onboarding() {
  const { t, locale } = useI18n();
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const questions = useQuery(() => api.diagnosticQuestions(locale), [locale]);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [level, setLevel] = useState<Level | ''>('');
  const [goal, setGoal] = useState('');
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [startedAt, setStartedAt] = useState(0);

  const qs: DiagnosticQuestion[] = questions.data?.questions ?? [];
  const total = qs.length + 1; // + level/goal step
  const isFinal = step === qs.length;
  const current = qs[step];

  const submit = useAction(async () => {
    setStartedAt(Date.now());
    const res = await api.diagnosticSubmit({
      answers: Object.entries(answers).map(([question_id, option_id]) => ({ question_id, option_id })),
      self_reported_level: level || null,
      goal: goal.trim(),
    });
    setResult(res);
    setUser(res.user);
    return res;
  });

  const styleLabels = useMemo(() => Object.fromEntries(STYLE_KEYS.map((k) => [k, t(`style.${k}` as TranslationKey)])), [t]);

  const header = (
    <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-4 py-4">
      <Link to="/" aria-label="EdNova AI">
        <Logo />
      </Link>
      <div className="flex items-center gap-2">
        <LanguageSwitcher />
        {!result && (
          <Link to="/app">
            <Button variant="ghost" size="sm">
              {t('common.skip')}
            </Button>
          </Link>
        )}
      </div>
    </header>
  );

  if (result) {
    const p = result.profile;
    return (
      <div className="surface-glow min-h-screen">
        {header}
        <main className="mx-auto max-w-3xl px-4 pb-16">
          <div className="panel-elevated animate-rise p-6 sm:p-8">
            <div className="flex items-center gap-2 text-sm font-medium text-brand-700">
              <LuSparkles className="h-4 w-4" aria-hidden />
              {t('onb.result_title')}
            </div>
            <h1 className="display mt-2 text-3xl text-ink">{t('onb.result_style', { style: styleLabels[p.learning_style] ?? p.learning_style })}</h1>
            <p className="mt-2 text-ink-soft">{t(`style.${p.learning_style}_desc` as TranslationKey)}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {p.secondary_style && <Badge tone="mint">{t('onb.secondary', { style: styleLabels[p.secondary_style] ?? p.secondary_style })}</Badge>}
              <Badge>{t('onb.level_detected', { level: t(`level.${p.level}` as TranslationKey) })}</Badge>
              <Badge tone="amber">{t('onb.exercise_score', { score: p.exercise_score, total: p.exercise_total })}</Badge>
            </div>
            <div className="mt-6 grid gap-6 md:grid-cols-[260px_1fr] md:items-start">
              <div className="rounded-2xl border border-line bg-white p-3">
                <p className="mb-1 text-center text-xs font-medium text-ink-muted">{t('onb.scores_title')}</p>
                <StyleRadar scores={p.style_scores} labels={styleLabels} size={230} />
              </div>
              <div>
                {result.explanation && <p className="prose-md rounded-2xl bg-brand-50/60 p-4 text-sm">{result.explanation}</p>}
                <h2 className="mt-4 text-sm font-semibold text-ink">{t('onb.recommendations')}</h2>
                <ul className="mt-2 space-y-2">
                  {result.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                      <LuCheck className="mt-0.5 h-4 w-4 shrink-0 text-mint-600" aria-hidden />
                      {r}
                    </li>
                  ))}
                </ul>
                <div className="mt-3">
                  <AiBadge ai={result.ai} />
                  <AiNotice ai={result.ai} />
                </div>
              </div>
            </div>
            <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-ink-muted">{t('onb.redirect_note')}</p>
              <Button size="lg" onClick={() => navigate('/app')}>
                {t('onb.go_dashboard')}
              </Button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="surface-glow min-h-screen">
      {header}
      <main className="mx-auto max-w-3xl px-4 pb-16">
        <div className="mb-6">
          <h1 className="display text-3xl text-ink sm:text-4xl">{t('onb.title')}</h1>
          <p className="mt-2 text-ink-soft">{t('onb.sub')}</p>
        </div>

        {questions.loading && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </div>
        )}
        {questions.error && <ErrorState message={questions.error} onRetry={() => void questions.reload()} />}

        {!questions.loading && !questions.error && qs.length > 0 && (
          <div className="panel-elevated animate-rise p-6 sm:p-8" key={step}>
            <div className="mb-5">
              <div className="mb-2 flex items-center justify-between text-xs text-ink-muted">
                <span>{t('onb.step_of', { n: step + 1, total })}</span>
                {current && <span>{current.kind === 'exercise' ? t('onb.kind_exercise') : t('onb.kind_preference')}</span>}
              </div>
              <div className="h-1.5 w-full rounded-full bg-brand-100" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={total}>
                <div className="h-full rounded-full bg-brand-600 transition-[width] duration-300" style={{ width: `${((step + 1) / total) * 100}%` }} />
              </div>
            </div>

            {!isFinal && current && (
              <>
                <h2 className="text-lg font-semibold text-ink">{current.text}</h2>
                <div className="mt-4 grid gap-2">
                  {current.options.map((o) => {
                    const selected = answers[current.id] === o.id;
                    return (
                      <button
                        key={o.id}
                        type="button"
                        onClick={() => {
                          setAnswers((a) => ({ ...a, [current.id]: o.id }));
                          window.setTimeout(() => setStep((s) => Math.min(s + 1, qs.length)), 180);
                        }}
                        aria-pressed={selected}
                        className={cn(
                          'flex items-start gap-3 rounded-2xl border p-4 text-start text-sm transition-colors',
                          selected ? 'border-brand-600 bg-brand-50 text-ink' : 'border-line bg-white text-ink hover:border-brand-300 hover:bg-brand-50/40',
                        )}
                      >
                        <span className={cn('mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold', selected ? 'border-brand-600 bg-brand-600 text-white' : 'border-line text-ink-muted')}>
                          {selected ? <LuCheck className="h-3 w-3" /> : o.id.toUpperCase().slice(0, 1)}
                        </span>
                        {o.text}
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            {isFinal && (
              <div className="space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{t('onb.level_title')}</h2>
                  <p className="text-sm text-ink-soft">{t('onb.level_sub')}</p>
                </div>
                <Field label={t('onb.level_label')}>
                  <Select value={level} onChange={(e) => setLevel(e.target.value as Level | '')}>
                    <option value="">{t('onb.level_unknown')}</option>
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>
                        {t(`level.${l}` as TranslationKey)}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label={t('onb.goal_label')} hint={t('common.optional')}>
                  <Input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder={t('onb.goal_placeholder')} maxLength={200} />
                </Field>
                {submit.pending && <StagedProgress stages={GRADE_STAGES} startedAt={startedAt} compact />}
                {submit.error && <ErrorState message={submit.error} />}
              </div>
            )}

            <div className="mt-6 flex items-center justify-between">
              <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} icon={<LuChevronLeft className="h-4 w-4 rtl:rotate-180" />}>
                {t('common.previous')}
              </Button>
              {isFinal ? (
                <Button size="lg" loading={submit.pending} onClick={() => void submit.run()}>
                  {t('onb.submit')}
                </Button>
              ) : (
                <Button variant="secondary" onClick={() => setStep((s) => s + 1)} disabled={!current || !answers[current.id]} icon={<LuChevronRight className="h-4 w-4 rtl:rotate-180" />}>
                  {t('common.next')}
                </Button>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default Onboarding;
