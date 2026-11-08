import React, { useMemo } from 'react';

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function inline(src: string): string {
  let s = src;
  // inline code first so its content is not formatted
  const codes: string[] = [];
  s = s.replace(/`([^`\n]+)`/g, (_, c: string) => {
    codes.push(`<code>${c}</code>`);
    return `\u0000${codes.length - 1}\u0000`;
  });
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>');
  s = s.replace(/(^|[^_\w])_([^_\n]+)_(?!\w)/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  s = s.replace(/\u0000(\d+)\u0000/g, (_, i: string) => codes[Number(i)]);
  return s;
}

/** Convert a safe subset of Markdown to HTML. Input is HTML-escaped first. */
export function markdownToHtml(md: string): string {
  const lines = escapeHtml(md.replace(/\r\n/g, '\n')).split('\n');
  const out: string[] = [];
  let i = 0;
  let para: string[] = [];
  let list: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushPara = () => {
    if (para.length) {
      out.push(`<p>${inline(para.join('<br/>'))}</p>`);
      para = [];
    }
  };
  const flushList = () => {
    if (list) {
      out.push(`<${list.type}>${list.items.map((it) => `<li>${inline(it)}</li>`).join('')}</${list.type}>`);
      list = null;
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      flushPara();
      flushList();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) {
        buf.push(lines[i]);
        i++;
      }
      out.push(`<pre><code>${buf.join('\n')}</code></pre>`);
      i++;
      continue;
    }
    const h = /^(#{1,3})\s+(.*)$/.exec(line);
    if (h) {
      flushPara();
      flushList();
      const level = h[1].length;
      out.push(`<h${level}>${inline(h[2])}</h${level}>`);
      i++;
      continue;
    }
    const ul = /^\s*[-*•]\s+(.*)$/.exec(line);
    const ol = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (ul || ol) {
      flushPara();
      const type = ul ? 'ul' : 'ol';
      const text = (ul ?? ol)![1];
      if (!list || list.type !== type) {
        flushList();
        list = { type, items: [] };
      }
      list.items.push(text);
      i++;
      continue;
    }
    const bq = /^>\s?(.*)$/.exec(line);
    if (bq) {
      flushPara();
      flushList();
      out.push(`<blockquote>${inline(bq[1])}</blockquote>`);
      i++;
      continue;
    }
    if (line.trim() === '') {
      flushPara();
      flushList();
      i++;
      continue;
    }
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      flushPara();
      flushList();
      out.push('<hr/>');
      i++;
      continue;
    }
    flushList();
    para.push(line);
    i++;
  }
  flushPara();
  flushList();
  return out.join('\n');
}

export function Markdown({ children, className = '' }: { children: string; className?: string }) {
  const html = useMemo(() => markdownToHtml(children ?? ''), [children]);
  return <div className={`prose-md ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}

export default Markdown;
export type MarkdownProps = React.ComponentProps<typeof Markdown>;
