import React, { useEffect, useId, useRef } from 'react';
import { LuX, LuCircleAlert, LuChevronDown } from 'react-icons/lu';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Spinner } from '../lib/progress';
import { useT } from '../lib/i18n';

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs));
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'mint';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 shadow-soft disabled:bg-brand-300',
  secondary: 'bg-white text-ink border border-line hover:border-brand-300 hover:bg-brand-50 disabled:text-ink-muted',
  ghost: 'bg-transparent text-ink-soft hover:bg-brand-50 hover:text-ink',
  danger: 'bg-rose-500 text-white hover:bg-rose-600 disabled:bg-rose-500/50',
  mint: 'bg-mint-500 text-ink hover:bg-mint-400 disabled:bg-mint-200',
};
const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-base gap-2 rounded-2xl',
};

export function Button({ variant = 'primary', size = 'md', loading, icon, className, children, disabled, type = 'button', ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-colors disabled:cursor-not-allowed select-none whitespace-nowrap',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading ? <Spinner className="h-4 w-4" /> : icon}
      {children}
    </button>
  );
}

export function Card({ className, children, elevated = false, ...rest }: React.HTMLAttributes<HTMLDivElement> & { elevated?: boolean }) {
  return (
    <div className={cn(elevated ? 'panel-elevated' : 'panel', 'p-5', className)} {...rest}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className, action }: { children: React.ReactNode; className?: string; action?: React.ReactNode }) {
  return (
    <div className={cn('mb-3 flex items-start justify-between gap-3', className)}>
      <h2 className="text-base font-semibold text-ink">{children}</h2>
      {action}
    </div>
  );
}

export function Field({ label, hint, error, children, className }: { label: string; hint?: string; error?: string | null; children: React.ReactElement<{ id?: string; 'aria-describedby'?: string }>; className?: string }) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      {React.cloneElement(children, { id, 'aria-describedby': hint || error ? hintId : undefined })}
      {(error || hint) && (
        <p id={hintId} className={cn('text-xs', error ? 'text-rose-600' : 'text-ink-muted')}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}

const INPUT = 'w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted/70 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:bg-paper';

export function Input({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(INPUT, 'h-10', className)} {...rest} />;
}

export function Textarea({ className, ...rest }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(INPUT, 'min-h-[88px] resize-y leading-relaxed', className)} {...rest} />;
}

export function Select({ className, children, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className="relative block">
      <select className={cn(INPUT, 'h-10 appearance-none pe-8', className)} {...rest}>
        {children}
      </select>
      <LuChevronDown className="pointer-events-none absolute end-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden />
    </span>
  );
}

export function Badge({ children, tone = 'brand', className }: { children: React.ReactNode; tone?: 'brand' | 'mint' | 'amber' | 'rose' | 'neutral'; className?: string }) {
  const tones = {
    brand: 'bg-brand-50 text-brand-700 border-brand-100',
    mint: 'bg-mint-50 text-mint-700 border-mint-200',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
    rose: 'bg-rose-50 text-rose-600 border-rose-500/20',
    neutral: 'bg-paper text-ink-soft border-line',
  } as const;
  return <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium', tones[tone], className)}>{children}</span>;
}

export function Chip({ active, children, onClick, className, title }: { active?: boolean; children: React.ReactNode; onClick?: () => void; className?: string; title?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={active}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white text-ink-soft hover:border-brand-300 hover:text-ink',
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Modal({ open, onClose, title, children, footer, size = 'md' }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; footer?: React.ReactNode; size?: 'md' | 'lg' }) {
  const t = useT();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    ref.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] flex items-end justify-center bg-ink/40 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn('max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 shadow-lift sm:rounded-3xl animate-rise', size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-lg')}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-ink-muted hover:bg-brand-50 hover:text-ink" aria-label={t('common.close')}>
            <LuX className="h-5 w-5" />
          </button>
        </div>
        <div>{children}</div>
        {footer && <div className="mt-5 flex flex-wrap justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon, title, description, action, className }: { icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center rounded-2xl border border-dashed border-brand-200 bg-brand-50/40 px-6 py-10 text-center', className)}>
      {icon && <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-brand-600 shadow-soft">{icon}</div>}
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-ink-soft">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry, className }: { message: string; onRetry?: () => void; className?: string }) {
  const t = useT();
  return (
    <div role="alert" className={cn('flex flex-col items-start gap-3 rounded-2xl border border-rose-500/20 bg-rose-50 p-4 text-sm text-ink sm:flex-row sm:items-center', className)}>
      <LuCircleAlert className="h-5 w-5 shrink-0 text-rose-600" aria-hidden />
      <p className="flex-1">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {t('common.retry')}
        </Button>
      )}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse-soft rounded-xl bg-brand-100/70', className)} aria-hidden />;
}

export function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full" />
      ))}
    </div>
  );
}

export interface TabItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
}

export function Tabs({ items, value, onChange, className }: { items: TabItem[]; value: string; onChange: (k: string) => void; className?: string }) {
  return (
    <div role="tablist" className={cn('inline-flex rounded-xl bg-brand-50 p-1', className)}>
      {items.map((it) => (
        <button
          key={it.key}
          role="tab"
          type="button"
          aria-selected={value === it.key}
          onClick={() => onChange(it.key)}
          className={cn('inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors', value === it.key ? 'bg-white text-ink shadow-soft' : 'text-ink-soft hover:text-ink')}
        >
          {it.icon}
          {it.label}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, icon, tone = 'brand' }: { label: string; value: React.ReactNode; icon?: React.ReactNode; tone?: 'brand' | 'mint' | 'amber' }) {
  const tones = { brand: 'bg-brand-50 text-brand-700', mint: 'bg-mint-50 text-mint-700', amber: 'bg-amber-50 text-amber-600' } as const;
  return (
    <div className="panel flex items-center gap-3 p-4">
      {icon && <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', tones[tone])}>{icon}</div>}
      <div className="min-w-0">
        <p className="text-xl font-semibold leading-tight text-ink tabular-nums">{value}</p>
        <p className="truncate text-xs text-ink-muted">{label}</p>
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="display text-2xl text-ink sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-ink-soft">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 flex-wrap gap-2">{action}</div>}
    </div>
  );
}

export function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  return (
    <label className="flex cursor-pointer items-start gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn('relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors', checked ? 'bg-brand-600' : 'bg-line')}
      >
        <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all', checked ? 'start-[22px]' : 'start-0.5')} />
      </button>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-ink">{label}</span>
        {description && <span className="block text-xs text-ink-muted">{description}</span>}
      </span>
    </label>
  );
}
