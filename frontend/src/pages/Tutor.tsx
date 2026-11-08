import { useEffect, useMemo, useRef, useState } from "react";
import { LuPlus, LuSend, LuTrash2, LuLightbulb, LuFileText, LuEye, LuMessageSquare, LuChevronDown, LuArrowRight, LuTriangleAlert, LuUpload } from 'react-icons/lu';
import { useNavigate, useParams, useSearchParams } from '../lib/router';
import { useI18n, formatDate } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, LEARNING_STYLES, type Conversation, type Document, type LearningStyle, type Message, type Source } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, Chip, EmptyState, ErrorState, Select, Skeleton, Textarea, Toggle, cn } from '../components/ui';
import { Markdown } from '../lib/markdown';
import { AiBadge, AiNotice, StagedProgress, useTutorStages } from '../lib/progress';
import type { TranslationKey } from '../i18n/en';
import { UploadZone } from './Documents';

function SourcesList({ sources }: { sources: Source[] }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="mt-3 rounded-xl border border-line bg-paper/60">
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-ink-soft hover:text-ink" aria-expanded={open}>
        <span className="flex items-center gap-1.5">
          <LuFileText className="h-3.5 w-3.5 text-brand-600" aria-hidden />
          {t('tutor.sources')} ({sources.length})
        </span>
        <LuChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} aria-hidden />
      </button>
      {open && (
        <ol className="space-y-2 px-3 pb-3">
          {sources.map((s, i) => (
            <li key={s.chunk_id} className="rounded-lg bg-white p-2.5 text-xs text-ink-soft">
              <span className="me-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-brand-600 px-1 text-[10px] font-semibold text-white">{i + 1}</span>
              {s.page !== null && s.page !== undefined && <span className="me-1.5 font-medium text-ink">{t('doc.page', { n: s.page })}</span>}
              <span className="italic">“{s.excerpt}”</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function AssistantMessage({ m, canReveal, onReveal, revealing }: { m: Message; canReveal: boolean; onReveal: () => void; revealing: boolean }) {
  const { t } = useI18n();
  const meta = m.meta ?? {};
  const hint = meta.hint_level ?? 0;
  return (
    <div className="flex gap-3">
      <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
        <LuMessageSquare className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0 max-w-[88%] flex-1 rounded-2xl rounded-ss-md border border-line bg-white px-4 py-3 shadow-soft">
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
          {hint > 0 && hint < 2 && <span className="rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-600">{t('tutor.hint_level', { n: hint })}</span>}
          {meta.triage?.confusion === 'high' && (
            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 font-medium text-rose-600">
              <LuTriangleAlert className="h-3 w-3" aria-hidden />
              {t('tutor.confusion_detected')}
            </span>
          )}
        </div>
        <Markdown>{m.content}</Markdown>
        {meta.guiding_question && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-ink">
            <LuLightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
            <div>
              <p className="text-[11px] font-medium text-amber-600">{t('tutor.guiding_question')}</p>
              <p>{meta.guiding_question}</p>
            </div>
          </div>
        )}
        {meta.next_step && (
          <div className="mt-2 flex items-start gap-2 rounded-xl bg-mint-50 px-3 py-2 text-sm text-ink">
            <LuArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-mint-600 rtl:rotate-180" aria-hidden />
            <div>
              <p className="text-[11px] font-medium text-mint-700">{t('tutor.next_step')}</p>
              <p>{meta.next_step}</p>
            </div>
          </div>
        )}
        {meta.sources && <SourcesList sources={meta.sources} />}
        <AiNotice ai={meta.ai} />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <AiBadge ai={meta.ai} />
          {canReveal && (
            <Button size="sm" variant="secondary" icon={<LuEye className="h-3.5 w-3.5" />} onClick={onReveal} loading={revealing}>
              {t('tutor.reveal')}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function Tutor() {
  const { t, locale } = useI18n();
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const search = useSearchParams();
  const stages = useTutorStages();

  const convs = useQuery(() => api.conversations(), []);
  const docs = useQuery(() => api.documents(), []);
  const thread = useQuery(() => (id ? api.conversation(id) : Promise.resolve(null)), [id], !!id);

  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'guided' | 'direct'>('guided');
  const [useDocs, setUseDocs] = useState(false);
  const [style, setStyle] = useState<LearningStyle | null>(null);
  const [sending, setSending] = useState(false);
  const [revealing, setRevealing] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [sendError, setSendError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const conversation: Conversation | undefined = id ? thread.data?.conversation : undefined;
  const messages: Message[] = id ? (thread.data?.messages ?? []) : [];

  useEffect(() => {
    if (conversation?.document_id) setUseDocs(true);
  }, [conversation?.document_id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length, sending]);

  // Deep link: /app/tutor?document=<id> creates a conversation about a document.
  const wantedDoc = search.get('document');
  useEffect(() => {
    if (!wantedDoc || id || creating) return;
    setCreating(true);
    api
      .createConversation({ language: locale, document_id: wantedDoc })
      .then((c) => navigate(`/app/tutor/${c.id}`, { replace: true }))
      .catch((e) => setSendError(errorMessage(e)))
      .finally(() => setCreating(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantedDoc, id]);

  const createConversation = async (documentId: string | null = null) => {
    setCreating(true);
    try {
      const c = await api.createConversation({ language: locale, document_id: documentId });
      await convs.reload();
      navigate(`/app/tutor/${c.id}`);
    } catch (e) {
      setSendError(errorMessage(e));
    } finally {
      setCreating(false);
    }
  };

  const startDocumentConversation = async (document: Document) => {
    setShowUpload(false);
    await createConversation(document.id);
  };

  const send = async () => {
    const content = input.trim();
    if (!content || sending) return;
    let convId = id;
    setSending(true);
    setSendError(null);
    setStartedAt(Date.now());
    try {
      if (!convId) {
        const c = await api.createConversation({ language: locale, document_id: null, title: content.slice(0, 60) });
        convId = c.id;
        navigate(`/app/tutor/${c.id}`, { replace: true });
      }
      setInput('');
      const optimistic: Message = { id: `tmp-${Date.now()}`, role: 'user', content, created_at: new Date().toISOString(), meta: {} };
      thread.setData((prev) => (prev ? { ...prev, messages: [...prev.messages, optimistic] } : prev));
      const res = await api.sendMessage(convId, { content, mode, use_documents: useDocs, style_override: style });
      thread.setData((prev) =>
        prev
          ? { ...prev, messages: [...prev.messages.filter((m) => m.id !== optimistic.id), res.user_message, res.assistant_message] }
          : { conversation: { id: convId!, title: content.slice(0, 60), language: locale, document_id: null, created_at: '', updated_at: '', message_count: 2 }, messages: [res.user_message, res.assistant_message] },
      );
      void convs.reload();
      void refresh();
      if (!id) await thread.reload();
    } catch (e) {
      setSendError(errorMessage(e));
      setInput(content);
    } finally {
      setSending(false);
    }
  };

  const reveal = async () => {
    if (!id || revealing) return;
    setRevealing(true);
    setSendError(null);
    setStartedAt(Date.now());
    try {
      const res = await api.revealAnswer(id);
      thread.setData((prev) => (prev ? { ...prev, messages: [...prev.messages, res.assistant_message] } : prev));
    } catch (e) {
      setSendError(errorMessage(e));
    } finally {
      setRevealing(false);
    }
  };

  const remove = async (cid: string) => {
    if (!window.confirm(t('tutor.delete_confirm'))) return;
    try {
      await api.deleteConversation(cid);
      await convs.reload();
      if (cid === id) navigate('/app/tutor');
    } catch (e) {
      setSendError(errorMessage(e));
    }
  };

  const lastAssistant = useMemo(() => [...messages].reverse().find((m) => m.role === 'assistant'), [messages]);
  const canReveal = !!lastAssistant && (lastAssistant.meta?.hint_level ?? 2) < 2;
  const activeDoc: Document | undefined = docs.data?.find((d) => d.id === conversation?.document_id);

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      {/* conversation list */}
      <Card className="hidden h-[calc(100vh-9rem)] flex-col p-3 lg:flex">
        <Button className="w-full" icon={<LuPlus className="h-4 w-4" />} onClick={() => void createConversation()} loading={creating}>
          {t('tutor.new_conversation')}
        </Button>
        <div className="mt-3 flex-1 overflow-y-auto scrollbar-thin">
          {convs.loading && <Skeleton className="h-40 w-full" />}
          {convs.error && <ErrorState message={convs.error} onRetry={() => void convs.reload()} />}
          {convs.data && convs.data.length === 0 && <p className="px-2 py-6 text-center text-sm text-ink-muted">{t('tutor.no_conversations')}</p>}
          <ul className="space-y-1">
            {convs.data?.map((c) => (
              <li key={c.id} className="group relative">
                <button
                  type="button"
                  onClick={() => navigate(`/app/tutor/${c.id}`)}
                  className={cn('w-full rounded-xl px-3 py-2 pe-9 text-start text-sm transition-colors', c.id === id ? 'bg-brand-50 text-brand-800' : 'text-ink hover:bg-paper')}
                >
                  <span className="block truncate font-medium">{c.title || t('tutor.untitled')}</span>
                  <span className="block text-xs text-ink-muted">
                    {formatDate(c.updated_at, locale)} · {c.message_count}
                  </span>
                </button>
                <button type="button" onClick={() => void remove(c.id)} className="absolute end-2 top-2 rounded-md p-1 text-ink-muted opacity-0 transition-opacity hover:bg-white hover:text-rose-600 group-hover:opacity-100 focus:opacity-100" aria-label={t('common.delete')}>
                  <LuTrash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </Card>

      {/* thread */}
      <Card className="flex h-[calc(100vh-9rem)] flex-col p-0">
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <div className="lg:hidden">
            <Select value={id ?? ''} onChange={(e) => (e.target.value ? navigate(`/app/tutor/${e.target.value}`) : navigate('/app/tutor'))} aria-label={t('tutor.title')}>
              <option value="">{t('tutor.new_conversation')}</option>
              {convs.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title || t('tutor.untitled')}
                </option>
              ))}
            </Select>
          </div>
          <h1 className="hidden min-w-0 flex-1 truncate text-base font-semibold text-ink lg:block">{conversation?.title || t('tutor.title')}</h1>
          <div className="ms-auto flex items-center gap-2">
            <div className="inline-flex rounded-xl bg-paper p-1" role="radiogroup" aria-label="mode">
              {(['guided', 'direct'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  role="radio"
                  aria-checked={mode === m}
                  onClick={() => setMode(m)}
                  title={m === 'guided' ? t('tutor.mode_guided_hint') : t('tutor.mode_direct_hint')}
                  className={cn('rounded-lg px-3 py-1.5 text-xs font-medium', mode === m ? 'bg-white text-ink shadow-soft' : 'text-ink-soft')}
                >
                  {m === 'guided' ? t('tutor.mode_guided') : t('tutor.mode_direct')}
                </button>
              ))}
            </div>
            <span className="hidden rounded-full border border-line px-2 py-1 text-[11px] text-ink-muted sm:inline">{t(`lang.${conversation?.language ?? locale}` as TranslationKey)}</span>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 scrollbar-thin">
          {thread.loading && id && (
            <div className="space-y-3">
              <Skeleton className="ms-auto h-10 w-2/3" />
              <Skeleton className="h-24 w-5/6" />
            </div>
          )}
          {thread.error && <ErrorState message={thread.error} onRetry={() => void thread.reload()} />}
          {!id && !sending && (
            <EmptyState
              icon={<LuMessageSquare className="h-6 w-6" />}
              title={t('tutor.empty_thread')}
              description={t('tutor.empty_thread_sub')}
              className="mx-auto mt-8 max-w-lg"
            />
          )}
          {id && !thread.loading && messages.length === 0 && !sending && (
            <EmptyState icon={<LuMessageSquare className="h-6 w-6" />} title={t('tutor.empty_thread')} description={t('tutor.empty_thread_sub')} className="mx-auto mt-8 max-w-lg" />
          )}
          {messages.map((m, idx) =>
            m.role === 'user' ? (
              <div key={m.id} className="flex justify-end">
                <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-ee-md bg-brand-600 px-4 py-2.5 text-sm text-white">{m.content}</p>
              </div>
            ) : (
              <AssistantMessage key={m.id} m={m} canReveal={canReveal && idx === messages.length - 1} onReveal={() => void reveal()} revealing={revealing} />
            ),
          )}
          {(sending || revealing) && (
            <div className="flex gap-3">
              <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
                <LuMessageSquare className="h-4 w-4" aria-hidden />
              </span>
              <div className="max-w-[88%] flex-1">
                <StagedProgress stages={useDocs ? stages : stages.filter((s) => s.key !== 'retrieve')} startedAt={startedAt} />
              </div>
            </div>
          )}
          {sendError && <ErrorState message={sendError} />}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-line p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-xs text-ink-muted">{t('tutor.style_override')}:</span>
            <Chip active={style === null} onClick={() => setStyle(null)}>
              {t('tutor.style_auto')}
              {user?.learning_style && style === null && <span className="opacity-80">({t(`style.${user.learning_style}` as TranslationKey)})</span>}
            </Chip>
            {LEARNING_STYLES.map((s) => (
              <Chip key={s} active={style === s} onClick={() => setStyle(s)}>
                {t(`style.${s}` as TranslationKey)}
              </Chip>
            ))}
          </div>
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <Toggle checked={useDocs} onChange={setUseDocs} label={t('tutor.use_documents')} />
            <Button
              type="button"
              size="sm"
              variant="secondary"
              icon={<LuUpload className="h-3.5 w-3.5" />}
              onClick={() => setShowUpload((open) => !open)}
            >
              {t('doc.upload')}
            </Button>
            {useDocs && (
              <div className="flex items-center gap-2 text-xs">
                <LuFileText className="h-4 w-4 text-brand-600" aria-hidden />
                {conversation ? (
                  <span className="text-ink-soft">{activeDoc ? activeDoc.title : docs.data && docs.data.length > 0 ? `${docs.data.length} ${t('nav.documents').toLowerCase()}` : t('tutor.no_document')}</span>
                ) : (
                  <span className="text-ink-soft">{docs.data?.length ? `${docs.data.length} ${t('nav.documents').toLowerCase()}` : t('tutor.no_document')}</span>
                )}
                {!conversation && docs.data && docs.data.length > 0 && (
                  <Select className="h-8 w-56 text-xs" aria-label={t('tutor.pick_document')} defaultValue="" onChange={(e) => e.target.value && void createConversation(e.target.value)}>
                    <option value="">{t('tutor.pick_document')}</option>
                    {docs.data.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.title}
                      </option>
                    ))}
                  </Select>
                )}
              </div>
            )}
          </div>
          {showUpload && (
            <div className="mb-3 rounded-xl border border-line bg-paper/50 p-3">
              <UploadZone compact onUploaded={(document) => void startDocumentConversation(document)} />
            </div>
          )}
          <form
            className="flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              placeholder={t('tutor.placeholder')}
              rows={2}
              className="min-h-[52px]"
              aria-label={t('tutor.placeholder')}
              disabled={sending}
            />
            <Button type="submit" size="lg" className="h-[52px] px-4" disabled={!input.trim()} loading={sending} icon={<LuSend className="h-4 w-4 rtl:-scale-x-100" />} aria-label={t('common.send')} />
          </form>
        </div>
      </Card>
    </div>
  );
}

export default Tutor;
