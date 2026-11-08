import React, { useRef, useState } from 'react';
import { LuFileText, LuUpload, LuTrash2, LuSearch, LuMessageSquare, LuListChecks, LuNotebookPen, LuSparkles, LuCircleCheck, LuCircleX } from 'react-icons/lu';
import { Link, useNavigate, useParams } from '../lib/router';
import { useI18n, formatDate } from '../lib/i18n';
import { api, errorMessage, type AskResponse, type Document, type SearchResult } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, CardTitle, EmptyState, ErrorState, Field, Input, PageHeader, SkeletonList, Badge, cn } from '../components/ui';
import { Markdown } from '../lib/markdown';
import { AiBadge, AiNotice, StagedProgress, DEFAULT_STAGES } from '../lib/progress';

const ACCEPT = '.pdf,.txt,.md,.docx,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const MAX_BYTES = 15 * 1024 * 1024;

export function UploadZone({ onUploaded, compact = false }: { onUploaded: (d: Document) => void; compact?: boolean }) {
  const { t, locale } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState('');
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setError(null);
    if (file.size > MAX_BYTES) return setError(t('doc.too_large'));
    const ext = file.name.toLowerCase().split('.').pop() ?? '';
    if (!['pdf', 'txt', 'md', 'docx'].includes(ext)) return setError(t('doc.bad_type'));
    setProgress(5);
    const timer = window.setInterval(() => setProgress((p) => (p === null ? null : Math.min(90, p + 7))), 400);
    try {
      const d = await api.uploadDocument(file, title.trim() || undefined, locale);
      setProgress(100);
      onUploaded(d);
      setTitle('');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      window.clearInterval(timer);
      window.setTimeout(() => setProgress(null), 600);
    }
  };

  return (
    <div className="space-y-3">
      {!compact && (
        <Field label={t('doc.title_field')} hint={t('common.optional')}>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
        </Field>
      )}
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) void upload(f);
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition-colors',
          drag ? 'border-brand-500 bg-brand-50' : 'border-brand-200 bg-brand-50/40 hover:border-brand-400',
        )}
      >
        <span className="mb-2 flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-brand-600 shadow-soft">
          <LuUpload className="h-5 w-5" aria-hidden />
        </span>
        <p className="text-sm font-medium text-ink">{t('doc.drop_hint')}</p>
        <p className="mt-1 text-xs text-ink-muted">{t('doc.formats')}</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
            e.target.value = '';
          }}
        />
      </div>
      {progress !== null && (
        <div>
          <div className="mb-1 flex justify-between text-xs text-ink-muted">
            <span>{t('doc.uploading')}</span>
            <span className="tabular-nums">{progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-brand-100" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full bg-brand-600 transition-[width]" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      {error && <ErrorState message={error} />}
    </div>
  );
}

export function Documents() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const docs = useQuery(() => api.documents(), []);

  const remove = async (d: Document) => {
    if (!window.confirm(t('doc.delete_confirm'))) return;
    try {
      await api.deleteDocument(d.id);
      await docs.reload();
    } catch {
      /* surfaced via reload error */
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title={t('doc.title')} subtitle={t('landing.f5_desc')} />
      <Card elevated>
        <CardTitle>{t('doc.upload')}</CardTitle>
        <UploadZone onUploaded={(d) => navigate(`/app/documents/${d.id}`)} />
      </Card>
      {docs.loading && <SkeletonList rows={3} />}
      {docs.error && <ErrorState message={docs.error} onRetry={() => void docs.reload()} />}
      {docs.data && docs.data.length === 0 && <EmptyState icon={<LuFileText className="h-6 w-6" />} title={t('doc.empty')} description={t('doc.empty_sub')} />}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {docs.data?.map((d) => (
          <li key={d.id} className="panel group relative flex flex-col p-4">
            <Link to={`/app/documents/${d.id}`} className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                <LuFileText className="h-5 w-5" aria-hidden />
              </span>
              <div className="min-w-0">
                <h3 className="truncate font-semibold text-ink group-hover:text-brand-700">{d.title}</h3>
                <p className="truncate text-xs text-ink-muted">{d.filename}</p>
              </div>
            </Link>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
              {d.status === 'ready' ? (
                <Badge tone="mint">
                  <LuCircleCheck className="h-3 w-3" aria-hidden /> {t('doc.status_ready')}
                </Badge>
              ) : (
                <Badge tone="rose">
                  <LuCircleX className="h-3 w-3" aria-hidden /> {t('doc.status_failed')}
                </Badge>
              )}
              {d.pages > 0 && <span>{t('doc.pages', { n: d.pages })}</span>}
              <span>{t('doc.chunks', { n: d.chunk_count })}</span>
              <span className="ms-auto">{formatDate(d.created_at, locale)}</span>
            </div>
            <button type="button" onClick={() => void remove(d)} className="absolute end-3 top-3 rounded-md p-1 text-ink-muted opacity-0 transition-opacity hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100" aria-label={t('common.delete')}>
              <LuTrash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DocumentView() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const doc = useQuery(() => api.document(id), [id]);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [askError, setAskError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setAskError(null);
    setStartedAt(Date.now());
    try {
      setAnswer(await api.askDocument(id, question.trim(), locale));
    } catch (err) {
      setAskError(errorMessage(err));
    } finally {
      setAsking(false);
    }
  };

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const r = await api.searchDocument(id, query.trim(), 5);
      setResults(r.results);
    } catch (err) {
      setAskError(errorMessage(err));
    } finally {
      setSearching(false);
    }
  };

  if (doc.loading) return <SkeletonList rows={4} />;
  if (doc.error || !doc.data) return <ErrorState message={doc.error ?? t('common.error')} onRetry={() => void doc.reload()} />;
  const d = doc.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={d.title}
        subtitle={`${d.filename} · ${d.pages > 0 ? t('doc.pages', { n: d.pages }) + ' · ' : ''}${t('doc.chunks', { n: d.chunk_count })}`}
        action={
          <>
            <Button variant="secondary" size="sm" icon={<LuMessageSquare className="h-4 w-4" />} onClick={() => navigate(`/app/tutor?document=${d.id}`)}>
              {t('doc.chat_about')}
            </Button>
            <Button variant="secondary" size="sm" icon={<LuListChecks className="h-4 w-4" />} onClick={() => navigate(`/app/quizzes?document=${d.id}`)}>
              {t('doc.quiz_from')}
            </Button>
            <Button variant="secondary" size="sm" icon={<LuNotebookPen className="h-4 w-4" />} onClick={() => navigate(`/app/notes?source=document&id=${d.id}`)}>
              {t('doc.notes_from')}
            </Button>
          </>
        }
      />
      {d.status === 'failed' && <ErrorState message={d.error ?? t('doc.status_failed')} />}

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Card elevated>
            <CardTitle>{t('doc.ask_title')}</CardTitle>
            <form onSubmit={ask} className="flex flex-col gap-2 sm:flex-row">
              <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('doc.ask_placeholder')} aria-label={t('doc.ask_title')} disabled={asking} />
              <Button type="submit" loading={asking} disabled={!question.trim()} icon={<LuSparkles className="h-4 w-4" />}>
                {t('doc.ask')}
              </Button>
            </form>
            {asking && (
              <div className="mt-4">
                <StagedProgress stages={DEFAULT_STAGES} startedAt={startedAt} />
              </div>
            )}
            {askError && <ErrorState message={askError} className="mt-4" />}
            {answer && !asking && (
              <div className="mt-4 animate-rise">
                <h3 className="mb-1 text-sm font-semibold text-ink">{t('doc.answer')}</h3>
                <Markdown>{answer.answer}</Markdown>
                <AiNotice ai={answer.ai} />
                <div className="mt-2">
                  <AiBadge ai={answer.ai} />
                </div>
                {answer.sources.length > 0 && (
                  <>
                    <h4 className="mt-4 text-xs font-semibold text-ink-soft">{t('doc.sources')}</h4>
                    <ol className="mt-2 space-y-2">
                      {answer.sources.map((s, i) => (
                        <li key={s.chunk_id} className="rounded-xl border border-line bg-paper/60 p-3 text-sm text-ink-soft">
                          <span className="me-2 inline-flex h-5 min-w-5 items-center justify-center rounded bg-brand-600 px-1 text-[11px] font-semibold text-white">{i + 1}</span>
                          {s.page !== null && s.page !== undefined && <span className="me-2 text-xs font-medium text-ink">{t('doc.page', { n: s.page })}</span>}
                          <span className="italic">“{s.excerpt}”</span>
                        </li>
                      ))}
                    </ol>
                  </>
                )}
              </div>
            )}
          </Card>

          <Card>
            <CardTitle>{t('doc.search_title')}</CardTitle>
            <form onSubmit={search} className="flex gap-2">
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('doc.search_placeholder')} aria-label={t('doc.search_title')} />
              <Button type="submit" variant="secondary" loading={searching} disabled={!query.trim()} icon={<LuSearch className="h-4 w-4" />}>
                {t('common.search')}
              </Button>
            </form>
            {results && results.length === 0 && <p className="mt-3 text-sm text-ink-muted">{t('doc.no_results')}</p>}
            {results && results.length > 0 && (
              <ol className="mt-3 space-y-2">
                {results.map((r) => (
                  <li key={r.chunk_id} className="rounded-xl border border-line p-3 text-sm">
                    <div className="mb-1 flex items-center justify-between text-xs text-ink-muted">
                      <span>{r.page !== null ? t('doc.page', { n: r.page }) : ''}</span>
                      <span>
                        {t('doc.score')}: {r.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-ink-soft">{r.excerpt}</p>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>

        <Card>
          <CardTitle>{t('doc.preview')}</CardTitle>
          <div className="mb-3 flex flex-wrap gap-2 text-xs">
            <Badge tone={d.status === 'ready' ? 'mint' : 'rose'}>{d.status === 'ready' ? t('doc.status_ready') : t('doc.status_failed')}</Badge>
            {d.language && <Badge tone="neutral">{d.language}</Badge>}
            <Badge tone="neutral">{formatDate(d.created_at, locale)}</Badge>
          </div>
          <p className="max-h-[480px] overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-ink-soft scrollbar-thin">{d.preview || '—'}</p>
        </Card>
      </div>
    </div>
  );
}

export default Documents;
