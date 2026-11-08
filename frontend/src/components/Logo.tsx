import React, { useId } from 'react';
import { cn } from './ui';

export function LogoMark({ className }: { className?: string }) {
  // unique gradient id per instance: a duplicate id inside a hidden sidebar would break the fill
  const gradientId = `ednova-g-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  return (
    <svg viewBox="0 0 64 64" className={cn('h-8 w-8', className)} aria-hidden>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7C6DF2" />
          <stop offset="1" stopColor="#4636C7" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill={`url(#${gradientId})`} />
      <path d="M18 40c0-9 6-16 14-16s14 7 14 16" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
      <circle cx="32" cy="22" r="4" fill="#2FD4A6" />
      <path d="M22 46h20" stroke="#D9F8EE" strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ className, size = 'md' }: { className?: string; size?: 'sm' | 'md' | 'lg' }) {
  const text = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-base' : 'text-lg';
  const mark = size === 'lg' ? 'h-10 w-10' : size === 'sm' ? 'h-7 w-7' : 'h-8 w-8';
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <LogoMark className={mark} />
      <span className={cn('font-semibold tracking-tight text-ink', text)}>
        EdNova<span className="text-brand-600"> AI</span>
      </span>
    </span>
  );
}

export default Logo;
export type LogoProps = React.ComponentProps<typeof Logo>;
