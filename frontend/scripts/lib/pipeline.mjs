// Shared build helpers: esbuild bundling + Tailwind v4 compile() without the oxide scanner.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'tailwindcss';
import * as esbuild from 'esbuild';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const srcDir = path.join(root, 'src');
export const distDir = path.join(root, 'dist');
export const assetsDir = path.join(distDir, 'assets');
export const publicDir = path.join(root, 'public');

const CANDIDATE_RE = /^[a-zA-Z0-9:_\-\/\[\]\.\(\)%#!@,&>+*~]+$/;

export function walk(dir, exts, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, exts, out);
    else if (exts.some((e) => entry.name.endsWith(e))) out.push(full);
  }
  return out;
}

/** Scan source files for Tailwind class candidates (replacement for @tailwindcss/oxide). */
export function collectCandidates() {
  const files = [...walk(srcDir, ['.ts', '.tsx']), path.join(root, 'index.html')];
  const set = new Set();
  for (const file of files) {
    if (!fs.existsSync(file)) continue;
    const text = fs.readFileSync(file, 'utf8');
    for (const raw of text.split(/[\s"'`<>{}=;]+/)) {
      const token = raw.trim();
      if (!token || token.length > 120) continue;
      if (!CANDIDATE_RE.test(token)) continue;
      set.add(token);
    }
  }
  return [...set];
}

export async function buildCss() {
  const twEntry = fileURLToPath(import.meta.resolve('tailwindcss'));
  const twDir = path.dirname(twEntry); // .../tailwindcss/dist
  const cssSource = fs.readFileSync(path.join(srcDir, 'styles.css'), 'utf8');
  const compiler = await compile(cssSource, {
    base: root,
    loadStylesheet: async (id) => {
      const name = id === 'tailwindcss' ? 'index.css' : id.replace('tailwindcss/', '');
      const p = path.join(twDir, '..', name.endsWith('.css') ? name : name + '.css');
      return { base: path.dirname(p), content: fs.readFileSync(p, 'utf8') };
    },
    loadModule: async () => {
      throw new Error('Tailwind plugins are not supported in this offline pipeline');
    },
  });
  return compiler.build(collectCandidates());
}

export function hashOf(content) {
  let h = 0x811c9dc5;
  for (let i = 0; i < content.length; i++) {
    h ^= content.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}

export function copyPublic() {
  if (!fs.existsSync(publicDir)) return;
  fs.mkdirSync(distDir, { recursive: true });
  for (const entry of fs.readdirSync(publicDir)) {
    fs.cpSync(path.join(publicDir, entry), path.join(distDir, entry), { recursive: true });
  }
}

export function writeIndexHtml({ jsFile, cssFile }) {
  const template = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const html = template
    .replace('%CSS%', `/assets/${cssFile}`)
    .replace('%JS%', `/assets/${jsFile}`);
  fs.writeFileSync(path.join(distDir, 'index.html'), html);
}

export function esbuildOptions({ production }) {
  return {
    entryPoints: [path.join(srcDir, 'main.tsx')],
    bundle: true,
    outdir: assetsDir,
    entryNames: production ? '[name]-[hash]' : '[name]',
    format: 'esm',
    target: 'es2020',
    jsx: 'automatic',
    minify: production,
    sourcemap: production ? false : 'inline',
    metafile: true,
    logLevel: 'silent',
    define: { 'process.env.NODE_ENV': production ? '"production"' : '"development"' },
    absWorkingDir: root,
    charset: 'utf8',
  };
}

/** Full production build: JS + CSS + index.html + public files. */
export async function buildAll({ production }) {
  fs.rmSync(distDir, { recursive: true, force: true });
  fs.mkdirSync(assetsDir, { recursive: true });
  const result = await esbuild.build(esbuildOptions({ production }));
  const jsOutput = Object.keys(result.metafile.outputs).find((f) => f.endsWith('.js'));
  const jsFile = path.basename(jsOutput);
  const css = await buildCss();
  const cssFile = production ? `styles-${hashOf(css)}.css` : 'styles.css';
  fs.writeFileSync(path.join(assetsDir, cssFile), css);
  copyPublic();
  writeIndexHtml({ jsFile, cssFile });
  return { jsFile, cssFile, jsBytes: fs.statSync(jsOutput).size, cssBytes: Buffer.byteLength(css) };
}
