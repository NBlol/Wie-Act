import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { LuCircleCheck, LuCircleAlert, LuInfo, LuX, LuAward } from 'react-icons/lu';

export type ToastKind = 'success' | 'error' | 'info' | 'badge';

interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  body?: string;
}

interface ToastState {
  toast: (kind: ToastKind, title: string, body?: string) => void;
}

const ToastContext = createContext<ToastState | null>(null);

const ICONS: Record<ToastKind, React.ReactNode> = {
  success: <LuCircleCheck className="h-5 w-5 text-mint-600" aria-hidden />,
  error: <LuCircleAlert className="h-5 w-5 text-rose-500" aria-hidden />,
  info: <LuInfo className="h-5 w-5 text-brand-600" aria-hidden />,
  badge: <LuAward className="h-5 w-5 text-amber-500" aria-hidden />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => setToasts((prev) => prev.filter((t) => t.id !== id)), []);

  const toast = useCallback(
    (kind: ToastKind, title: string, body?: string) => {
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev.slice(-3), { id, kind, title, body }]);
      window.setTimeout(() => dismiss(id), kind === 'error' ? 7000 : 4500);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 end-4 z-[100] flex w-[min(92vw,360px)] flex-col gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto flex items-start gap-3 rounded-2xl border border-line bg-white p-3 shadow-lift animate-rise">
            <div className="mt-0.5 shrink-0">{ICONS[t.kind]}</div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ink">{t.title}</p>
              {t.body && <p className="mt-0.5 text-sm text-ink-soft">{t.body}</p>}
            </div>
            <button type="button" onClick={() => dismiss(t.id)} className="rounded-lg p-1 text-ink-muted hover:bg-brand-50 hover:text-ink" aria-label="Dismiss">
              <LuX className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastState['toast'] {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx.toast;
}
