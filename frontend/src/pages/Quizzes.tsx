import React, { useEffect, useMemo, useState } from 'react';
import { LuListChecks, LuPlus, LuCheck, LuX, LuTimer, LuRotateCcw, LuSparkles, LuTrophy, LuChevronLeft, LuChevronRight } from 'react-icons/lu';
import { Link, useNavigate, useParams, useSearchParams } from '../lib/router';
import { useI18n, formatDate } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, LEVELS, type Level, type Quiz, type QuizAnswer, type QuizSubmitResponse } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { useToast } from '../lib/toast';
import { Button, Card, CardTitle, Chip, EmptyState, ErrorState, Field, Input, PageHeader, Select, SkeletonList, Badge, cn } from '../components/ui';
import { AiBadge, AiNotice, StagedProgress, GENERATE_STAGES, GRADE_STAGES } from '../lib/progress';
import { Markdown } from '../lib/markdown';
import type { TranslationKey } from '../i18n/en';

export function QuizGenerateForm({ onCreated, defaultDocumentId, defaultTopic, compact = false }: { onCreated: (q: Quiz) => void; defaultDocumentId?: string | null; defaultTopic?: string; compact?: boolean }) {
  const { t, locale } = useI18n();
  const docs = useQuery(() => api.documents(), []);
  const [topic, setTopic] = useState(defaultTopic ?? '');
  const [documentId, setDocumentId] = useState<string>(defaultDocumentId ?? '');
  const [num, setNum] = useState(5);
  const [difficulty, setDifficulty] = useState<Level | 'auto'>('auto');
  const [types, setTypes] = useState<('mcq' | 'short')[]>(['mcq', 'short']);
  const [pending, setPending] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const toggleType = (tp: 'mcq' | 'short') => setTypes((prev) => (prev.includes(tp) ? (prev.length > 1 ? prev.filter((x) => x !== tp) : prev) : [...prev, tp]));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() && !documentId) {
      setError(t('quiz.needs_topic_or_doc'));
      return;
    }
    setPending(true);
    setError(null);
    setStartedAt(Date.now());
    try {
      const q = await api.generateQuiz({
        topic: topic.trim() || (docs.data?.find((d) => d.id === documentId)?.title ?? ''),
        document_id: documentId || null,
        num_questions: num,
        difficulty,
        language: locale,
        question_types: types,
        room_id: null,
      });
      onCreated(q);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label={t('quiz.topic')}>
        <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t('quiz.topic_placeholder')} maxLength={120} />
      </Field>
      <Field label={t('quiz.from_document')} hint={t('common.optional')}>
        <Select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
          <option value="">{t('tutor.no_document')}</option>
          {docs.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </Select>
      </Field>
      <div className={cn('grid gap-4', compact ? 'grid-cols-2' : 'sm:grid-cols-2')}>
        <Field label={t('quiz.num_questions')}>
          <Input type="number" min={3} max={10} value={num} onChange={(e) => setNum(Math.max(3, Math.min(10, Number(e.target.value) || 5)))} />
        </Field>
        <Field label={t('quiz.difficulty')}>
          <Select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Level | 'auto')}>
            <option value="auto">{t('quiz.difficulty_auto')}</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {t(`level.${l}` as TranslationKey)}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div>
        <p className="mb-1.5 text-sm font-medium text-ink">{t('quiz.types')}</p>
        <div className="flex gap-2">
          <Chip active={types.includes('mcq')} onClick={() => toggleType('mcq')}>
            {t('quiz.type_mcq')}
          </Chip>
          <Chip active={types.includes('short')} onClick={() => toggleType('short')}>
            {t('quiz.type_short')}
          </Chip>
        </div>
      </div>
      {pending && <StagedProgress stages={GENERATE_STAGES} startedAt={startedAt} note={t('quiz.generating')} compact />}
      {error && <ErrorState message={error} />}
      <Button type="submit" loading={pending} icon={<LuSparkles className="h-4 w-4" />} className="w-full sm:w-auto">
        {t('common.generate')}
      </Button>
    </form>
  );
}

export function Quizzes() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const search = useSearchParams();
  const quizzes = useQuery(() => api.quizzes(), []);
  const [showForm, setShowForm] = useState(!!search.get('document') || !!search.get('topic'));

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('quiz.title')}
        subtitle={t('landing.f3_desc')}
        action={
          <Button icon={<LuPlus className="h-4 w-4" />} onClick={() => setShowForm((s) => !s)}>
            {t('quiz.generate_title')}
          </Button>
        }
      />
      {showForm && (
        <Card elevated>
          <CardTitle>{t('quiz.generate_title')}</CardTitle>
          <QuizGenerateForm defaultDocumentId={search.get('document')} defaultTopic={search.get('topic') ?? ''} onCreated={(q) => navigate(`/app/quizzes/${q.id}`)} />
        </Card>
      )}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-ink-soft">{t('quiz.list_title')}</h2>
        {quizzes.loading && <SkeletonList rows={3} />}
        {quizzes.error && <ErrorState message={quizzes.error} onRetry={() => void quizzes.reload()} />}
        {quizzes.data && quizzes.data.length === 0 && (
          <EmptyState icon={<LuListChecks className="h-6 w-6" />} title={t('quiz.empty')} description={t('quiz.empty_sub')} action={<Button onClick={() => setShowForm(true)}>{t('quiz.generate_title')}</Button>} />
        )}
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quizzes.data?.map((q) => (
            <li key={q.id}>
              <Link to={`/app/quizzes/${q.id}`} className="panel flex h-full flex-col p-4 transition-colors hover:border-brand-300">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-ink">{q.topic}</h3>
                  <Badge tone="neutral">{t(`lang.${q.language}` as TranslationKey)}</Badge>
                </div>
                <p className="mt-1 text-xs text-ink-muted">
                  {t('quiz.questions', { n: q.num_questions })} · {q.difficulty === 'auto' ? t('quiz.difficulty_auto') : t(`level.${q.difficulty}` as TranslationKey)} · {formatDate(q.created_at, locale)}
                </p>
                <div className="mt-auto flex items-center justify-between pt-3 text-sm">
                  {q.best_score !== null ? <Badge tone="mint">{t('quiz.best', { n: Math.round(q.best_score) })}</Badge> : <span className="text-ink-muted">{t('quiz.attempts', { n: 0 })}</span>}
                  <span className="text-xs text-ink-muted">{t('quiz.attempts', { n: q.attempts })}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function useElapsed(active: boolean) {
  const [start] = useState(() => Date.now());
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [active]);
  return Math.floor((now - start) / 1000);
}

export function QuizTake() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const { refresh } = useAuth();
  const quiz = useQuery(() => api.quiz(id), [id]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showSimilar, setShowSimilar] = useState(false);
  const elapsed = useElapsed(!result && !submitting);

  const questions = quiz.data?.questions ?? [];
  const q = questions[index];
  const unanswered = useMemo(() => questions.filter((x) => !answers[x.id]?.trim()).length, [questions, answers]);

  const submit = async () => {
    if (!quiz.data) return;
    setSubmitting(true);
    setError(null);
    setStartedAt(Date.now());
    try {
      const payload: QuizAnswer[] = questions.map((x) => (x.type === 'mcq' ? { question_id: x.id, option_id: answers[x.id] ?? '' } : { question_id: x.id, text: answers[x.id] ?? '' }));
      const res = await api.submitQuiz(quiz.data.id, { answers: payload, time_spent_s: elapsed });
      setResult(res);
      void refresh();
      for (const b of res.badges_unlocked) toast('badge', t('quiz.badges_unlocked'), t(`badge.${b}` as TranslationKey));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const retake = () => {
    setResult(null);
    setAnswers({});
    setIndex(0);
  };

  if (quiz.loading) return <SkeletonList rows={4} />;
  if (quiz.error || !quiz.data) return <ErrorState message={quiz.error ?? t('common.error')} onRetry={() => void quiz.reload()} />;

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  if (result) {
    const byId = Object.fromEntries(result.results.map((r) => [r.question_id, r]));
    return (
      <div className="space-y-6">
        <PageHeader title={t('quiz.results_title')} subtitle={quiz.data.topic} />
        <Card elevated className="grid gap-6 md:grid-cols-[auto_1fr] md:items-center">
          <div className="flex flex-col items-center">
            <div className="relative flex h-36 w-36 items-center justify-center rounded-full border-[10px] border-brand-100">
              <div className="absolute inset-0 rounded-full border-[10px] border-brand-600" style={{ clipPath: `inset(${100 - result.percent}% 0 0 0)` }} aria-hidden />
              <div className="text-center">
                <p className="text-3xl font-bold text-ink tabular-nums">{result.percent}%</p>
                <p className="text-xs text-ink-muted">{t('quiz.score', { score: result.score, total: result.total })}</p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Badge tone="amber">
                <LuTrophy className="h-3 w-3" aria-hidden /> {t('quiz.xp_gained', { n: result.xp_gained })}
              </Badge>
            </div>
          </div>
          <div>
            <h2 className="mb-1 text-sm font-semibold text-ink">{t('quiz.feedback')}</h2>
            <Markdown>{result.feedback}</Markdown>
            <div className="mt-2">
              <AiBadge ai={result.ai} />
              <AiNotice ai={result.ai} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" icon={<LuRotateCcw className="h-4 w-4" />} onClick={retake}>
                {t('quiz.retake')}
              </Button>
              <Button variant="secondary" icon={<LuSparkles className="h-4 w-4" />} onClick={() => setShowSimilar((s) => !s)}>
                {t('quiz.similar')}
              </Button>
              <Button variant="ghost" onClick={() => navigate('/app/quizzes')}>
                {t('common.back')}
              </Button>
            </div>
          </div>
        </Card>
        {showSimilar && (
          <Card>
            <CardTitle>{t('quiz.similar')}</CardTitle>
            <QuizGenerateForm defaultTopic={quiz.data.topic} defaultDocumentId={quiz.data.document_id} onCreated={(nq) => navigate(`/app/quizzes/${nq.id}`)} />
          </Card>
        )}
        <ol className="space-y-3">
          {questions.map((x, i) => {
            const r = byId[x.id];
            const ok = r?.correct;
            return (
              <li key={x.id} className={cn('panel p-4 border-s-4', ok ? 'border-s-mint-500' : 'border-s-rose-500')}>
                <div className="flex items-start gap-3">
                  <span className={cn('mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white', ok ? 'bg-mint-500' : 'bg-rose-500')} aria-label={ok ? t('quiz.correct') : t('quiz.incorrect')}>
                    {ok ? <LuCheck className="h-3.5 w-3.5" /> : <LuX className="h-3.5 w-3.5" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-ink-muted">
                      {t('quiz.question_of', { n: i + 1, total: questions.length })} · {t('quiz.skill')}: {x.skill}
                    </p>
                    <p className="mt-0.5 font-medium text-ink">{x.text}</p>
                    {r && (
                      <dl className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="text-xs text-ink-muted">{t('common.you')}</dt>
                          <dd className={cn(ok ? 'text-mint-700' : 'text-rose-600')}>{r.your_answer || '—'}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-ink-muted">{t('quiz.correct_answer')}</dt>
                          <dd className="text-ink">{r.correct_answer}</dd>
                        </div>
                      </dl>
                    )}
                    {r?.explanation && (
                      <div className="mt-2 rounded-xl bg-paper px-3 py-2 text-sm text-ink-soft">
                        <span className="me-1 text-xs font-medium text-ink-muted">{t('quiz.explanation')}:</span>
                        {r.explanation}
                      </div>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="display text-2xl text-ink">{quiz.data.topic}</h1>
          <p className="text-xs text-ink-muted">{t('quiz.question_of', { n: index + 1, total: questions.length })}</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-sm tabular-nums text-ink-soft" aria-label={t('quiz.time')}>
          <LuTimer className="h-4 w-4 text-brand-600" aria-hidden />
          {mm}:{ss}
        </span>
      </div>
      <div className="flex gap-1" aria-hidden>
        {questions.map((x, i) => (
          <button key={x.id} type="button" onClick={() => setIndex(i)} className={cn('h-1.5 flex-1 rounded-full transition-colors', i === index ? 'bg-brand-600' : answers[x.id]?.trim() ? 'bg-mint-400' : 'bg-brand-100')} />
        ))}
      </div>

      {q && (
        <Card elevated className="animate-rise" key={q.id}>
          <Badge tone="neutral" className="mb-3">
            {t('quiz.skill')}: {q.skill}
          </Badge>
          <p className="text-lg font-semibold leading-snug text-ink">{q.text}</p>
          {q.type === 'mcq' ? (
            <div role="radiogroup" className="mt-4 grid gap-2">
              {q.options?.map((o) => {
                const selected = answers[q.id] === o.id;
                return (
                  <button
                    key={o.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: o.id }))}
                    className={cn('flex items-start gap-3 rounded-2xl border p-3.5 text-start text-sm transition-colors', selected ? 'border-brand-600 bg-brand-50' : 'border-line bg-white hover:border-brand-300')}
                  >
                    <span className={cn('mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold', selected ? 'border-brand-600 bg-brand-600 text-white' : 'border-line text-ink-muted')}>
                      {o.id.toUpperCase().slice(0, 1)}
                    </span>
                    {o.text}
                  </button>
                );
              })}
            </div>
          ) : (
            <Input className="mt-4" value={answers[q.id] ?? ''} onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))} placeholder={t('quiz.short_placeholder')} aria-label={t('quiz.short_placeholder')} />
          )}
        </Card>
      )}

      {submitting && <StagedProgress stages={GRADE_STAGES} startedAt={startedAt} note={t('quiz.grading')} compact />}
      {error && <ErrorState message={error} />}

      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0} icon={<LuChevronLeft className="h-4 w-4 rtl:rotate-180" />}>
          {t('common.previous')}
        </Button>
        <span className="text-xs text-ink-muted">{unanswered > 0 && t('quiz.unanswered', { n: unanswered })}</span>
        {index < questions.length - 1 ? (
          <Button variant="secondary" onClick={() => setIndex((i) => i + 1)} icon={<LuChevronRight className="h-4 w-4 rtl:rotate-180" />}>
            {t('common.next')}
          </Button>
        ) : (
          <Button onClick={() => void submit()} loading={submitting}>
            {t('quiz.submit')}
          </Button>
        )}
      </div>
    </div>
  );
}

export default Quizzes;
