import React from 'react';

export const CHART_COLORS = {
  brand: '#5b4be8',
  brandSoft: '#c3bbff',
  mint: '#2fd4a6',
  mintSoft: '#aeeedb',
  amber: '#f5a524',
  rose: '#e5484d',
  ink: '#1d1a3b',
  muted: '#7b789a',
  line: '#e6e3f5',
};

export interface BarDatum {
  label: string;
  value: number;
  color?: string;
}

/** Vertical bar chart. Responsive via viewBox; labels under the bars. */
export function BarChart({
  data,
  height = 160,
  title,
  maxValue,
  showValues = false,
}: {
  data: BarDatum[];
  height?: number;
  title: string;
  maxValue?: number;
  showValues?: boolean;
}) {
  const width = 400;
  const padX = 8;
  const padTop = 14;
  const padBottom = 26;
  const max = Math.max(maxValue ?? 0, ...data.map((d) => d.value), 1);
  const n = Math.max(data.length, 1);
  const slot = (width - padX * 2) / n;
  const barW = Math.min(slot * 0.62, 34);
  const chartH = height - padTop - padBottom;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={title}>
      <title>{title}</title>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1={padX} x2={width - padX} y1={padTop + chartH * (1 - f)} y2={padTop + chartH * (1 - f)} stroke={CHART_COLORS.line} strokeDasharray="2 4" />
      ))}
      {data.map((d, i) => {
        const h = Math.max((d.value / max) * chartH, d.value > 0 ? 3 : 0);
        const x = padX + slot * i + (slot - barW) / 2;
        const y = padTop + chartH - h;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={h} rx={6} fill={d.color ?? CHART_COLORS.brand} opacity={0.92}>
              <title>{`${d.label}: ${d.value}`}</title>
            </rect>
            {showValues && d.value > 0 && (
              <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontSize="10" fill={CHART_COLORS.muted}>
                {d.value}
              </text>
            )}
            <text x={x + barW / 2} y={height - 8} textAnchor="middle" fontSize="10" fill={CHART_COLORS.muted}>
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Horizontal bars with a label and a percentage. */
export function HBarList({ items, color = CHART_COLORS.brand, suffix = '%' }: { items: { label: string; value: number; extra?: React.ReactNode }[]; color?: string; suffix?: string }) {
  return (
    <ul className="space-y-3">
      {items.map((it, i) => (
        <li key={i}>
          <div className="mb-1 flex items-center justify-between gap-2 text-sm">
            <span className="truncate font-medium text-ink">{it.label}</span>
            <span className="flex items-center gap-1 text-ink-soft">
              {it.extra}
              {Math.round(it.value)}
              {suffix}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-brand-50" role="progressbar" aria-valuenow={Math.round(it.value)} aria-valuemin={0} aria-valuemax={100} aria-label={it.label}>
            <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, it.value))}%`, background: color }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function LineChart({ data, height = 140, title, color = CHART_COLORS.mint }: { data: { label: string; value: number }[]; height?: number; title: string; color?: string }) {
  const width = 400;
  const padX = 10;
  const padY = 12;
  const max = Math.max(...data.map((d) => d.value), 1);
  const n = Math.max(data.length - 1, 1);
  const pts = data.map((d, i) => {
    const x = padX + ((width - padX * 2) * i) / n;
    const y = padY + (height - padY * 2 - 16) * (1 - d.value / max);
    return [x, y] as const;
  });
  const path = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${path} L${pts[pts.length - 1]?.[0] ?? padX},${height - 16} L${padX},${height - 16} Z`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={title}>
      <title>{title}</title>
      <path d={area} fill={color} opacity={0.12} />
      <path d={path} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3} fill="#fff" stroke={color} strokeWidth={2}>
          <title>{`${data[i].label}: ${data[i].value}`}</title>
        </circle>
      ))}
      {data.map((d, i) => (
        <text key={i} x={pts[i][0]} y={height - 2} textAnchor="middle" fontSize="9" fill={CHART_COLORS.muted}>
          {i % Math.ceil(data.length / 7) === 0 ? d.label : ''}
        </text>
      ))}
    </svg>
  );
}

export interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

export function DonutChart({ segments, size = 140, title, centerLabel, centerSub }: { segments: DonutSegment[]; size?: number; title: string; centerLabel?: string; centerSub?: string }) {
  const total = segments.reduce((a, s) => a + s.value, 0);
  const r = 40;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={title} className="shrink-0">
      <title>{title}</title>
      <circle cx="50" cy="50" r={r} fill="none" stroke={CHART_COLORS.line} strokeWidth="12" />
      {total > 0 &&
        segments.map((s, i) => {
          const len = (s.value / total) * c;
          const el = (
            <circle
              key={i}
              cx="50"
              cy="50"
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth="12"
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 50 50)"
              strokeLinecap="butt"
            >
              <title>{`${s.label}: ${s.value}`}</title>
            </circle>
          );
          offset += len;
          return el;
        })}
      {centerLabel && (
        <text x="50" y={centerSub ? 48 : 54} textAnchor="middle" fontSize="16" fontWeight="700" fill={CHART_COLORS.ink}>
          {centerLabel}
        </text>
      )}
      {centerSub && (
        <text x="50" y="61" textAnchor="middle" fontSize="6.5" fill={CHART_COLORS.muted}>
          {centerSub}
        </text>
      )}
    </svg>
  );
}

export function ProgressRing({ percent, size = 96, stroke = 9, color = CHART_COLORS.brand, label, sub }: { percent: number; size?: number; stroke?: number; color?: string; label?: string; sub?: string }) {
  const r = 50 - stroke / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(100, percent));
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`${Math.round(p)}%`} className="shrink-0">
      <circle cx="50" cy="50" r={r} fill="none" stroke={CHART_COLORS.line} strokeWidth={stroke} />
      <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={`${(p / 100) * c} ${c}`} transform="rotate(-90 50 50)" className="transition-[stroke-dasharray] duration-700" />
      <text x="50" y={sub ? 48 : 55} textAnchor="middle" fontSize="20" fontWeight="700" fill={CHART_COLORS.ink}>
        {label ?? `${Math.round(p)}%`}
      </text>
      {sub && (
        <text x="50" y="64" textAnchor="middle" fontSize="9" fill={CHART_COLORS.muted}>
          {sub}
        </text>
      )}
    </svg>
  );
}

/** Radar-like polygon for the six learning-style scores. */
export function StyleRadar({ scores, labels, size = 220 }: { scores: Record<string, number>; labels: Record<string, string>; size?: number }) {
  const keys = Object.keys(labels);
  const n = keys.length;
  const max = Math.max(...keys.map((k) => scores[k] ?? 0), 1);
  const cx = 50;
  const cy = 50;
  const R = 32;
  const point = (i: number, f: number) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * R * f, cy + Math.sin(a) * R * f] as const;
  };
  const poly = keys.map((k, i) => point(i, (scores[k] ?? 0) / max).join(',')).join(' ');
  return (
    <svg viewBox="-12 -6 124 112" width={size} height={size} role="img" aria-label="Learning style profile" className="mx-auto h-auto max-w-full">
      {[0.33, 0.66, 1].map((f) => (
        <polygon key={f} points={keys.map((_, i) => point(i, f).join(',')).join(' ')} fill="none" stroke={CHART_COLORS.line} strokeWidth="0.6" />
      ))}
      {keys.map((_, i) => {
        const [x, y] = point(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={CHART_COLORS.line} strokeWidth="0.6" />;
      })}
      <polygon points={poly} fill={CHART_COLORS.brand} fillOpacity="0.18" stroke={CHART_COLORS.brand} strokeWidth="1.4" strokeLinejoin="round" />
      {keys.map((k, i) => {
        const [x, y] = point(i, (scores[k] ?? 0) / max);
        return <circle key={k} cx={x} cy={y} r="1.6" fill={CHART_COLORS.brand} />;
      })}
      {keys.map((k, i) => {
        const [x, y] = point(i, 1.3);
        return (
          <text key={k} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize="4.2" fill={CHART_COLORS.ink}>
            {labels[k]}
          </text>
        );
      })}
    </svg>
  );
}
