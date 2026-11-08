import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { LuWifiOff, LuTriangleAlert, LuClock } from 'react-icons/lu';
import { api, type SystemStatus } from './api';
import { useI18n, formatTime } from './i18n';

interface StatusState {
  status: SystemStatus | null;
  unreachable: boolean;
  refresh: () => Promise<void>;
}

const StatusContext = createContext<StatusState | null>(null);
const POLL_MS = 20_000;

export function StatusProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await api.systemStatus();
      setStatus(s);
      setUnreachable(false);
    } catch {
      setUnreachable(true);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const value = useMemo(() => ({ status, unreachable, refresh }), [status, unreachable, refresh]);
  return <StatusContext.Provider value={value}>{children}</StatusContext.Provider>;
}

export function useStatus(): StatusState {
  const ctx = useContext(StatusContext);
  if (!ctx) throw new Error('useStatus must be used inside <StatusProvider>');
  return ctx;
}

/** Global banner: offline provider, large model unavailable, queue depth, unreachable backend. */
export function ServiceBanner({ compact = false }: { compact?: boolean }) {
  const { status, unreachable } = useStatus();
  const { t, locale } = useI18n();

  if (unreachable) {
    return (
      <Banner tone="rose" icon={<LuWifiOff className="h-4 w-4" aria-hidden />} compact={compact}>
        {t('common.api_unreachable')}
      </Banner>
    );
  }
  if (!status) return null;

  const items: React.ReactNode[] = [];
  if (status.provider_mode === 'offline') {
    items.push(
      <Banner key="offline" tone="amber" icon={<LuTriangleAlert className="h-4 w-4" aria-hidden />} compact={compact}>
        <span className="font-semibold">{t('banner.offline')}</span>
        {!compact && <span className="ms-1 text-ink-soft">{t('banner.offline_detail')}</span>}
      </Banner>,
    );
  }
  if (status.provider_mode === 'live' && !status.large_available) {
    items.push(
      <Banner key="large" tone="brand" icon={<LuTriangleAlert className="h-4 w-4" aria-hidden />} compact={compact}>
        <span className="font-semibold">{t('banner.large_unavailable')}</span>
        {status.large_breaker_open_until && (
          <span className="ms-1 text-ink-soft">{t('banner.breaker_until', { time: formatTime(status.large_breaker_open_until, locale) })}</span>
        )}
      </Banner>,
    );
  }
  if (status.queue_depth > 0) {
    items.push(
      <Banner key="queue" tone="brand" icon={<LuClock className="h-4 w-4" aria-hidden />} compact={compact}>
        {t('banner.queue', { n: status.queue_depth })}
      </Banner>,
    );
  }
  if (items.length === 0) return null;
  return <div className="flex flex-col gap-2">{items}</div>;
}

function Banner({ tone, icon, children, compact }: { tone: 'amber' | 'rose' | 'brand'; icon: React.ReactNode; children: React.ReactNode; compact: boolean }) {
  const tones = {
    amber: 'border-amber-400/50 bg-amber-50 text-ink',
    rose: 'border-rose-500/30 bg-rose-50 text-ink',
    brand: 'border-brand-200 bg-brand-50 text-ink',
  } as const;
  const iconTones = { amber: 'text-amber-600', rose: 'text-rose-600', brand: 'text-brand-700' } as const;
  return (
    <div role="status" className={`flex items-start gap-2 rounded-xl border px-3 ${compact ? 'py-1.5 text-xs' : 'py-2 text-sm'} ${tones[tone]}`}>
      <span className={`mt-0.5 shrink-0 ${iconTones[tone]}`}>{icon}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
