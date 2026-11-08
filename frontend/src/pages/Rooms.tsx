import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LuUsers, LuPlus, LuBot, LuSend, LuCopy, LuCheck, LuMegaphone, LuCircleHelp, LuShieldCheck, LuScrollText, LuListChecks, LuTrophy, LuLogIn } from 'react-icons/lu';
import { useNavigate, useParams } from '../lib/router';
import { useI18n, formatDate, formatTime } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, LANGUAGES, type Language, type Participation, type Room, type RoomMessage } from '../lib/api';
import { useQuery, useInterval } from '../lib/hooks';
import { Button, Card, CardTitle, EmptyState, ErrorState, Field, Input, Modal, PageHeader, Select, SkeletonList, Badge, cn } from '../components/ui';
import { Markdown } from '../lib/markdown';
import { AiBadge, AiNotice, StagedProgress, GRADE_STAGES } from '../lib/progress';
import type { TranslationKey } from '../i18n/en';

export function Rooms() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const rooms = useQuery(() => api.rooms(), []);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState<Language>(locale);
  const [code, setCode] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const r = await api.createRoom({ name: name.trim(), topic: topic.trim(), language });
      navigate(`/app/rooms/${r.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  const join = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setPending(true);
    setError(null);
    try {
      const r = await api.joinRoom(code.trim().toUpperCase());
      navigate(`/app/rooms/${r.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('room.title')}
        subtitle={t('landing.f4_desc')}
        action={
          <Button icon={<LuPlus className="h-4 w-4" />} onClick={() => setCreateOpen(true)}>
            {t('room.create')}
          </Button>
        }
      />
      <Card>
        <form onSubmit={join} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field label={t('room.join')} className="flex-1">
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder={t('room.join_placeholder')} className="uppercase tracking-widest" maxLength={8} />
          </Field>
          <Button type="submit" variant="secondary" loading={pending} icon={<LuLogIn className="h-4 w-4" />}>
            {t('common.join')}
          </Button>
        </form>
        {error && !createOpen && <ErrorState message={error} className="mt-3" />}
      </Card>

      {rooms.loading && <SkeletonList rows={3} />}
      {rooms.error && <ErrorState message={rooms.error} onRetry={() => void rooms.reload()} />}
      {rooms.data && rooms.data.length === 0 && <EmptyState icon={<LuUsers className="h-6 w-6" />} title={t('room.empty')} description={t('room.empty_sub')} action={<Button onClick={() => setCreateOpen(true)}>{t('room.create')}</Button>} />}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {rooms.data?.map((r) => (
          <li key={r.id}>
            <button type="button" onClick={() => navigate(`/app/rooms/${r.id}`)} className="panel flex h-full w-full flex-col p-4 text-start transition-colors hover:border-brand-300">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-ink">{r.name}</h3>
                <span className="rounded-lg bg-ink px-2 py-0.5 font-mono text-xs tracking-widest text-white">{r.code}</span>
              </div>
              <p className="mt-1 text-sm text-ink-soft">{r.topic}</p>
              <div className="mt-auto flex items-center justify-between pt-3 text-xs text-ink-muted">
                <span className="flex items-center gap-1">
                  <LuUsers className="h-3.5 w-3.5" aria-hidden /> {t('room.members', { n: r.member_count })}
                </span>
                <span>
                  {r.is_owner && <Badge tone="brand">{t('room.owner')}</Badge>} {formatDate(r.created_at, locale)}
                </span>
              </div>
            </button>
          </li>
        ))}
      </ul>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title={t('room.create')}>
        <form onSubmit={create} className="space-y-4">
          <Field label={t('room.name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} required maxLength={60} />
          </Field>
          <Field label={t('room.topic')}>
            <Input value={topic} onChange={(e) => setTopic(e.target.value)} required maxLength={120} />
          </Field>
          <Field label={t('common.language')}>
            <Select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
              {LANGUAGES.map((l) => (
                <option key={l} value={l}>
                  {t(`lang.${l}` as TranslationKey)}
                </option>
              ))}
            </Select>
          </Field>
          {error && <ErrorState message={error} />}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" loading={pending}>
              {t('common.create')}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function ParticipationPanel({ room, participation }: { room: Room; participation: Participation }) {
  const { t } = useI18n();
  const max = Math.max(...room.members.map((m) => m.message_count), 1);
  const balanced = participation.balance_score >= 0.6;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">{t('room.participation')}</h3>
        <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-medium', balanced ? 'bg-mint-50 text-mint-700' : 'bg-amber-50 text-amber-600')}>{balanced ? t('room.balanced') : t('room.unbalanced')}</span>
      </div>
      <div className="mb-3">
        <div className="mb-1 flex justify-between text-xs text-ink-muted">
          <span>{t('room.balance')}</span>
          <span className="tabular-nums">{Math.round(participation.balance_score * 100)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-brand-50" role="meter" aria-valuenow={Math.round(participation.balance_score * 100)} aria-valuemin={0} aria-valuemax={100}>
          <div className={cn('h-full rounded-full transition-[width]', balanced ? 'bg-mint-500' : 'bg-amber-400')} style={{ width: `${participation.balance_score * 100}%` }} />
        </div>
      </div>
      <ul className="space-y-2">
        {room.members.map((m) => (
          <li key={m.user_id} className="text-sm">
            <div className="flex justify-between">
              <span className="truncate font-medium text-ink">{m.display_name}</span>
              <span className="text-xs tabular-nums text-ink-muted">{m.message_count}</span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-paper">
              <div className="h-full rounded-full bg-brand-500" style={{ width: `${(m.message_count / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      {participation.quiet_members.length > 0 && <p className="mt-3 text-xs text-amber-600">{t('room.quiet', { names: participation.quiet_members.join(', ') })}</p>}
      {participation.dominant_member && <p className="mt-1 text-xs text-ink-muted">{t('room.dominant', { name: participation.dominant_member })}</p>}
    </div>
  );
}

export function RoomView() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const room = useQuery(() => api.room(id), [id]);
  const leaderboard = useQuery(() => api.leaderboard(id), [id]);
  const [messages, setMessages] = useState<RoomMessage[]>([]);
  const [participation, setParticipation] = useState<Participation | null>(null);
  const [msgError, setMsgError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [moderating, setModerating] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [launching, setLaunching] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastId = useMemo(() => (messages.length ? messages[messages.length - 1].id : ''), [messages]);

  const poll = async (full = false) => {
    try {
      const res = await api.roomMessages(id, full ? '' : lastId, 50);
      if (res.messages.length) {
        setMessages((prev) => {
          const seen = new Set(prev.map((m) => m.id));
          const next = [...prev, ...res.messages.filter((m) => !seen.has(m.id))];
          return next;
        });
      }
      setParticipation(res.participation);
      setMsgError(null);
    } catch (e) {
      setMsgError(errorMessage(e));
    }
  };

  useEffect(() => {
    setMessages([]);
    void poll(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  useInterval(() => void poll(), 3000);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length, moderating]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = input.trim();
    if (!content) return;
    setSending(true);
    try {
      const res = await api.sendRoomMessage(id, content);
      setInput('');
      setMessages((prev) => {
        const seen = new Set(prev.map((m) => m.id));
        const add = [res.message, res.moderator_message].filter((m): m is RoomMessage => !!m && !seen.has(m.id));
        return [...prev, ...add];
      });
      void room.reload();
    } catch (err) {
      setMsgError(errorMessage(err));
    } finally {
      setSending(false);
    }
  };

  const moderate = async (action: 'nudge' | 'check_explanation' | 'summarize' | 'guiding_question') => {
    setModerating(true);
    setStartedAt(Date.now());
    setMsgError(null);
    try {
      const res = await api.moderate(id, action, action === 'check_explanation' ? selected : null);
      setMessages((prev) => (prev.some((m) => m.id === res.moderator_message.id) ? prev : [...prev, res.moderator_message]));
      setSelected(null);
    } catch (err) {
      setMsgError(errorMessage(err));
    } finally {
      setModerating(false);
    }
  };

  const launchQuiz = async () => {
    setLaunching(true);
    try {
      const q = await api.roomQuiz(id, 5);
      navigate(`/app/quizzes/${q.id}`);
    } catch (err) {
      setMsgError(errorMessage(err));
    } finally {
      setLaunching(false);
    }
  };

  const copy = async () => {
    if (!room.data) return;
    try {
      await navigator.clipboard.writeText(room.data.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked */
    }
  };

  if (room.loading) return <SkeletonList rows={4} />;
  if (room.error || !room.data) return <ErrorState message={room.error ?? t('common.error')} onRetry={() => void room.reload()} />;
  const r = room.data;
  const part = participation ?? r.participation;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="display text-2xl text-ink">{r.name}</h1>
          <p className="text-sm text-ink-soft">
            {r.topic} · {t(`lang.${r.language}` as TranslationKey)}
          </p>
        </div>
        <button type="button" onClick={() => void copy()} className="flex items-center gap-2 rounded-2xl border border-line bg-white px-3 py-2 text-start hover:border-brand-300" title={t('room.share_hint')}>
          <div>
            <p className="text-[11px] text-ink-muted">{t('room.code')}</p>
            <p className="font-mono text-lg font-semibold tracking-[0.3em] text-ink">{r.code}</p>
          </div>
          {copied ? <LuCheck className="h-4 w-4 text-mint-600" aria-hidden /> : <LuCopy className="h-4 w-4 text-ink-muted" aria-hidden />}
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <Card className="flex h-[calc(100vh-14rem)] min-h-[480px] flex-col p-0">
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4 scrollbar-thin">
            {messages.length === 0 && !msgError && <p className="py-10 text-center text-sm text-ink-muted">{t('room.no_messages')}</p>}
            {messages.map((m) => {
              const mine = m.user_id === user?.id;
              const mod = m.role === 'moderator';
              if (mod) {
                return (
                  <div key={m.id} className="flex gap-3">
                    <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
                      <LuBot className="h-4 w-4" aria-hidden />
                    </span>
                    <div className="max-w-[88%] rounded-2xl rounded-ss-md border border-brand-200 bg-brand-50/70 px-4 py-3">
                      <p className="mb-1 text-[11px] font-medium text-brand-700">
                        {t('room.moderator')} {m.meta?.action && <span className="text-ink-muted">· {String(m.meta.action)}</span>}
                      </p>
                      <Markdown>{m.content}</Markdown>
                      <AiNotice ai={m.meta?.ai} />
                      <div className="mt-2 flex items-center justify-between gap-2">
                        <AiBadge ai={m.meta?.ai} />
                        <span className="text-[11px] text-ink-muted">{formatTime(m.created_at, locale)}</span>
                      </div>
                    </div>
                  </div>
                );
              }
              return (
                <div key={m.id} className={cn('flex', mine ? 'justify-end' : 'justify-start')}>
                  <button
                    type="button"
                    onClick={() => setSelected((s) => (s === m.id ? null : m.id))}
                    aria-pressed={selected === m.id}
                    title={t('room.act_check')}
                    className={cn(
                      'max-w-[85%] rounded-2xl px-4 py-2.5 text-start text-sm transition-shadow',
                      mine ? 'rounded-ee-md bg-brand-600 text-white' : 'rounded-ss-md border border-line bg-white text-ink',
                      selected === m.id && 'ring-2 ring-amber-400 ring-offset-2',
                    )}
                  >
                    {!mine && <span className="mb-0.5 block text-[11px] font-semibold text-brand-700">{m.display_name}</span>}
                    <span className="whitespace-pre-wrap">{m.content}</span>
                    <span className={cn('mt-1 block text-[10px]', mine ? 'text-white/70' : 'text-ink-muted')}>{formatTime(m.created_at, locale)}</span>
                  </button>
                </div>
              );
            })}
            {moderating && (
              <div className="flex gap-3">
                <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
                  <LuBot className="h-4 w-4" aria-hidden />
                </span>
                <div className="max-w-[88%] flex-1">
                  <StagedProgress stages={GRADE_STAGES} startedAt={startedAt} note={t('room.moderating')} compact />
                </div>
              </div>
            )}
            {msgError && <ErrorState message={msgError} />}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={send} className="flex items-center gap-2 border-t border-line p-3">
            <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t('room.placeholder')} aria-label={t('room.placeholder')} disabled={sending} />
            <Button type="submit" disabled={!input.trim()} loading={sending} icon={<LuSend className="h-4 w-4 rtl:-scale-x-100" />} aria-label={t('common.send')} />
          </form>
        </Card>

        <div className="space-y-4">
          <Card>
            <ParticipationPanel room={r} participation={part} />
          </Card>
          <Card>
            <CardTitle>
              <span className="flex items-center gap-2">
                <LuBot className="h-4 w-4 text-brand-600" aria-hidden />
                {t('room.moderator')}
              </span>
            </CardTitle>
            <p className="mb-3 text-xs text-ink-muted">{t('room.moderator_desc')}</p>
            <div className="grid gap-2">
              <Button variant="secondary" size="sm" className="justify-start" icon={<LuMegaphone className="h-4 w-4 text-brand-600" />} onClick={() => void moderate('nudge')} disabled={moderating}>
                {t('room.act_nudge')}
              </Button>
              <Button variant="secondary" size="sm" className="justify-start" icon={<LuCircleHelp className="h-4 w-4 text-brand-600" />} onClick={() => void moderate('guiding_question')} disabled={moderating}>
                {t('room.act_question')}
              </Button>
              <Button variant="secondary" size="sm" className="justify-start" icon={<LuShieldCheck className="h-4 w-4 text-brand-600" />} onClick={() => void moderate('check_explanation')} disabled={moderating || !selected} title={!selected ? t('room.select_message') : undefined}>
                {t('room.act_check')}
              </Button>
              <Button variant="secondary" size="sm" className="justify-start" icon={<LuScrollText className="h-4 w-4 text-brand-600" />} onClick={() => void moderate('summarize')} disabled={moderating}>
                {t('room.act_summarize')}
              </Button>
            </div>
            <p className="mt-2 text-[11px] text-ink-muted">{selected ? t('room.selected') : t('room.select_message')}</p>
          </Card>
          <Card>
            <CardTitle>
              <span className="flex items-center gap-2">
                <LuListChecks className="h-4 w-4 text-brand-600" aria-hidden />
                {t('quiz.title')}
              </span>
            </CardTitle>
            <div className="flex flex-col gap-2">
              <Button size="sm" onClick={() => void launchQuiz()} loading={launching}>
                {t('room.launch_quiz')}
              </Button>
              {r.quiz_id && (
                <Button size="sm" variant="secondary" onClick={() => navigate(`/app/quizzes/${r.quiz_id}`)}>
                  {t('room.open_quiz')}
                </Button>
              )}
            </div>
            <h3 className="mt-4 flex items-center gap-1.5 text-sm font-semibold text-ink">
              <LuTrophy className="h-4 w-4 text-amber-500" aria-hidden />
              {t('room.leaderboard')}
            </h3>
            {leaderboard.data && leaderboard.data.length === 0 && <p className="mt-1 text-xs text-ink-muted">{t('room.leaderboard_empty')}</p>}
            <ol className="mt-2 space-y-1.5">
              {leaderboard.data?.map((e, i) => (
                <li key={`${e.display_name}-${i}`} className="flex items-center justify-between rounded-lg bg-paper px-2.5 py-1.5 text-sm">
                  <span className="flex items-center gap-2">
                    <span className="w-5 text-xs font-semibold text-ink-muted">{i + 1}</span>
                    {e.display_name}
                  </span>
                  <span className="font-semibold tabular-nums text-ink">{Math.round(e.percent)}%</span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Rooms;
