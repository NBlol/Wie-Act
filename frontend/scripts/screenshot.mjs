#!/usr/bin/env node
// Captures UI screenshots with Playwright against a running dev server (default http://127.0.0.1:5173).
// Usage: node scripts/screenshot.mjs [outDir] [baseUrl]
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const outDir = process.argv[2] || path.resolve('..', 'docs', 'screenshots');
const base = process.argv[3] || 'http://127.0.0.1:5173';
fs.mkdirSync(outDir, { recursive: true });

const pages = [
  { name: 'landing', url: '/', locale: 'en' },
  { name: 'login', url: '/login', locale: 'en' },
  { name: 'register', url: '/register', locale: 'fr' },
  { name: 'landing-ar', url: '/', locale: 'ar' },
  { name: 'landing-tn-mobile', url: '/', locale: 'tn', viewport: { width: 390, height: 844 } },
];

const browser = await chromium.launch();
const errors = [];
for (const p of pages) {
  const context = await browser.newContext({ viewport: p.viewport ?? { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('pageerror', (e) => errors.push(`${p.name}: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error' && !/api\//.test(m.text()) && !/Failed to load resource/.test(m.text())) errors.push(`${p.name}: console ${m.text()}`);
  });
  await page.addInitScript((locale) => localStorage.setItem('ednova_locale', locale), p.locale);
  await page.goto(base + p.url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(outDir, `${p.name}.png`), fullPage: p.name.startsWith('landing') });
  console.log(`saved ${p.name}.png  dir=${await page.evaluate(() => document.documentElement.dir)} title=${await page.title()}`);
  await context.close();
}
await browser.close();
if (errors.length) {
  console.error('Runtime errors:\n' + errors.join('\n'));
  process.exit(1);
}
console.log('no runtime errors');
