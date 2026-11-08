import React, { useEffect, useState } from 'react';
import { LuNotebookPen, LuPlus, LuDownload, LuTrash2, LuChevronLeft, LuChevronRight, LuSparkles } from 'react-icons/lu';
import { useSearchParams } from '../lib/router';
import { useI18n, formatDate } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, type Note } from '../lib/api';
import { useQuery } from '../lib/hooks';
import { Button, Card, CardTitle, EmptyState, ErrorState, Field, Input, PageHeader, Select, SkeletonList, Tabs, Badge, cn } from '../components/ui';
import { Markdown } from '../lib/markdown';
import { AiBadge, AiNotice, StagedProgress, GENERATE_STAGES } from '../lib/progress';
import type { TranslationKey } from '../i18n/en';

type Source = Note['source'];
type Format = 'summary' | 'flashcards' | 'both';

function Flashcards({ cards }: { cards: Note['flashcards'] }) {
  const { t } = useI18n();
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  useEffect(() => setFlipped(false), [i]);
  if (!cards.length) return null;
  const c = cards[i];
  return (
    <div className="space-y-3">
      <div className="[perspective:1200px]">
        <button type="button" onClick={() => setFlipped((f) => !f)} className={cn('card-flip relative h-56 w-full text-start', flipped && 'is-flipped')} aria-label={t('notes.flip')}>
          <div className="card-face absolute inset-0 flex flex-col justify-between rounded-3xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-6 shadow-soft">
            <span className="text-xs font-medium text-brand-700">Q</span>
            <p className="text-lg font-semibold text-ink">{c.q}</p>
            <span className="text-xs text-ink-muted">{t('notes.flip')}</span>
          </div>
          <div className="card-face card-face-back absolute inset-0 flex flex-col justify-between rounded-3xl bg-ink p-6 text-white shadow-lift">
            <span className="text-xs font-medium text-mint-300">A</span>
            <p className="text-base leading-relaxed">{c.a}</p>
            <span className="text-xs text-white/60">{t('notes.flip')}</span>
          </div>
        </button>
      </div>
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => setI((x) => Math.max(0, x - 1))} disabled={i === 0} icon={<LuChevronLeft className="h-4 w-4 rtl:rotate-180" />}>
          {t('common.previous')}
        </Button>
        <span className="text-xs text-ink-muted">{t('notes.card_of', { n: i + 1, total: cards.length })}</span>
        <Button variant="ghost" size="sm" onClick={() => setI((x) => Math.min(cards.length - 1, x + 1))} disabled={i === cards.length - 1} icon={<LuChevronRight className="h-4 w-4 rtl:rotate-180" />}>
          {t('common.next')}
        </Button>
      </div>
    </div>
  );
}

export function Notes() {
  const { t, locale } = useI18n();
  const { refresh } = useAuth();
  const search = useSearchParams();
  const notes = useQuery(() => api.notes(), []);
  const convs = useQuery(() => api.conversations(), []);
  const docs = useQuery(() => api.documents(), []);
  const rooms = useQuery(() => api.rooms(), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(!!search.get('source'));
  const [source, setSource] = useState<Source>((search.get('source') as Source) || 'topic');
  const [sourceId, setSourceId] = useState(search.get('id') ?? '');
  const [topic, setTopic] = useState('');
  const [format, setFormat] = useState<Format>('both');
  const [pending, setPending] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'summary' | 'flashcards'>('summary');

  useEffect(() => {
    if (!selectedId && notes.data?.length) setSelectedId(notes.data[0].id);
  }, [notes.data, selectedId]);

  const selected = notes.data?.find((n) => n.id === selectedId);

  const options: { id: string; label: string }[] =
    source === 'conversation'
      ? (convs.data ?? []).map((c) => ({ id: c.id, label: c.title || t('tutor.untitled') }))
      : source === 'document'
        ? (docs.data ?? []).map((d) => ({ id: d.id, label: d.title }))
        : source === 'room'
          ? (rooms.data ?? []).map((r) => ({ id: r.id, label: r.name }))
          : [];

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (source === 'topic' ? !topic.trim() : !sourceId) return;
    setPending(true);
    setError(null);
    setStartedAt(Date.now());
    try {
      const n = await api.generateNote({ source, source_id: source === 'topic' ? null : sourceId, topic: source === 'topic' ? topic.trim() : null, language: locale, format });
      notes.setData((prev) => [n, ...(prev ?? [])]);
      setSelectedId(n.id);
      setShowForm(false);
      void refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  const remove = async (n: Note) => {
    if (!window.confirm(t('notes.delete_confirm'))) return;
    try {
      await api.deleteNote(n.id);
      notes.setData((prev) => (prev ?? []).filter((x) => x.id !== n.id));
      setSelectedId(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const download = (n: Note) => {
    const md = `# ${n.title}\n\n${n.content_md}\n\n${n.flashcards.length ? '## Flashcards\n\n' + n.flashcards.map((c) => `- **Q:** ${c.q}\n  **A:** ${c.a}`).join('\n') : ''}`;
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${n.title.replace(/[^\w؀-ۿ-]+/g, '_').slice(0, 60) || 'notes'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('notes.title')}
        subtitle={t('notes.empty_sub')}
        action={
          <Button icon={<LuPlus className="h-4 w-4" />} onClick={() => setShowForm((s) => !s)}>
            {t('notes.generate_title')}
          </Button>
        }
      />

      {showForm && (
        <Card elevated>
          <CardTitle>{t('notes.generate_title')}</CardTitle>
          <form onSubmit={generate} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t('notes.source')}>
                <Select
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value as Source);
                    setSourceId('');
                  }}
                >
                  <option value="topic">{t('notes.source_topic')}</option>
                  <option value="conversation">{t('notes.source_conversation')}</option>
                  <option value="document">{t('notes.source_document')}</option>
                  <option value="room">{t('notes.source_room')}</option>
                </Select>
              </Field>
              {source === 'topic' ? (
                <Field label={t('notes.source_topic')}>
                  <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t('notes.topic_placeholder')} maxLength={120} />
                </Field>
              ) : (
                <Field label={t('notes.pick_source')}>
                  <Select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
                    <option value="">{t('notes.pick_source')}</option>
                    {options.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.label}
                      </option>
                    ))}
                  </Select>
                </Field>
              )}
            </div>
            <div>
              <p className="mb-1.5 text-sm font-medium text-ink">{t('notes.format')}</p>
              <Tabs
                value={format}
                onChange={(k) => setFormat(k as Format)}
                items={[
                  { key: 'summary', label: t('notes.format_summary') },
                  { key: 'flashcards', label: t('notes.format_flashcards') },
                  { key: 'both', label: t('notes.format_both') },
                ]}
              />
            </div>
            {pending && <StagedProgress stages={GENERATE_STAGES} startedAt={startedAt} note={t('notes.generating')} compact />}
            {error && <ErrorState message={error} />}
            <Button type="submit" loading={pending} icon={<LuSparkles className="h-4 w-4" />} disabled={source === 'topic' ? !topic.trim() : !sourceId}>
              {t('common.generate')}
            </Button>
          </form>
        </Card>
      )}

      {notes.loading && <SkeletonList rows={3} />}
      {notes.error && <ErrorState message={notes.error} onRetry={() => void notes.reload()} />}
      {notes.data && notes.data.length === 0 && !showForm && <EmptyState icon={<LuNotebookPen className="h-6 w-6" />} title={t('notes.empty')} description={t('notes.empty_sub')} action={<Button onClick={() => setShowForm(true)}>{t('notes.generate_title')}</Button>} />}

      {notes.data && notes.data.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <Card className="p-3">
            <ul className="space-y-1">
              {notes.data.map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => setSelectedId(n.id)} className={cn('w-full rounded-xl px-3 py-2 text-start text-sm', n.id === selectedId ? 'bg-brand-50 text-brand-800' : 'text-ink hover:bg-paper')}>
                    <span className="block truncate font-medium">{n.title}</span>
                    <span className="block text-xs text-ink-muted">
                      {t(`notes.source_${n.source}` as TranslationKey)} · {formatDate(n.created_at, locale)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          {selected && (
            <Card elevated>
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{selected.title}</h2>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{t(`notes.source_${selected.source}` as TranslationKey)}</Badge>
                    <Badge tone="neutral">{t(`lang.${selected.language}` as TranslationKey)}</Badge>
                    <AiBadge ai={selected.ai} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" icon={<LuDownload className="h-4 w-4" />} onClick={() => download(selected)}>
                    {t('notes.download')}
                  </Button>
                  <Button variant="ghost" size="sm" icon={<LuTrash2 className="h-4 w-4" />} onClick={() => void remove(selected)} aria-label={t('common.delete')} />
                </div>
              </div>
              <AiNotice ai={selected.ai} />
              {selected.flashcards.length > 0 && selected.content_md && (
                <Tabs
                  className="mb-4"
                  value={view}
                  onChange={(k) => setView(k as 'summary' | 'flashcards')}
                  items={[
                    { key: 'summary', label: t('notes.summary') },
                    { key: 'flashcards', label: `${t('notes.flashcards')} (${selected.flashcards.length})` },
                  ]}
                />
              )}
              {(view === 'summary' || selected.flashcards.length === 0) && selected.content_md ? <Markdown>{selected.content_md}</Markdown> : <Flashcards cards={selected.flashcards} />}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

export default Notes;
