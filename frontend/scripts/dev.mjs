#!/usr/bin/env node
// Dev server: rebuilds on change, serves dist/ with SPA fallback, proxies /api to the backend.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import * as esbuild from 'esbuild';
import { buildAll, buildCss, assetsDir, distDir, srcDir, root } from './lib/pipeline.mjs';

const PORT = Number(process.env.PORT || 5173);
const API_PROXY = process.env.API_PROXY || 'http://127.0.0.1:8000';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.map': 'application/json',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
};

await buildAll({ production: false });
console.log('[ednova] initial build done');

let cssTimer = null;
async function rebuildCss() {
  try {
    const css = await buildCss();
    fs.writeFileSync(path.join(assetsDir, 'styles.css'), css);
    console.log('[ednova] css rebuilt');
  } catch (e) {
    console.error('[ednova] css error', e.message);
  }
}

const ctx = await esbuild.context({
  entryPoints: [path.join(srcDir, 'main.tsx')],
  bundle: true,
  outdir: assetsDir,
  entryNames: '[name]',
  format: 'esm',
  target: 'es2020',
  jsx: 'automatic',
  sourcemap: 'inline',
  logLevel: 'warning',
  define: { 'process.env.NODE_ENV': '"development"' },
  absWorkingDir: root,
  charset: 'utf8',
});
await ctx.watch();

fs.watch(srcDir, { recursive: true }, () => {
  clearTimeout(cssTimer);
  cssTimer = setTimeout(rebuildCss, 150);
});

function proxy(req, res) {
  const target = new URL(req.url, API_PROXY);
  const upstream = http.request(
    {
      hostname: target.hostname,
      port: target.port,
      path: target.pathname + target.search,
      method: req.method,
      headers: { ...req.headers, host: target.host },
    },
    (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.pipe(res);
    },
  );
  upstream.on('error', (err) => {
    res.writeHead(502, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ detail: `Backend unreachable at ${API_PROXY}: ${err.message}` }));
  });
  req.pipe(upstream);
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) return proxy(req, res);
  const url = new URL(req.url, 'http://localhost');
  let file = path.join(distDir, decodeURIComponent(url.pathname));
  if (!file.startsWith(distDir)) {
    res.writeHead(403);
    return res.end();
  }
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(distDir, 'index.html');
  const ext = path.extname(file);
  res.writeHead(200, { 'content-type': MIME[ext] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});

server.listen(PORT, () => {
  console.log(`[ednova] dev server http://localhost:${PORT}  (API → ${API_PROXY})`);
});
