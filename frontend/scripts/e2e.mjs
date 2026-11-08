// End-to-end smoke test against the REAL backend (no mocks).
// Prerequisites: backend on :8000 (any AI mode) and `node scripts/dev.mjs` on :5173.
// Usage: node scripts/e2e.mjs [--shots docs/screenshots]  → prints a JSON summary of the flows that passed.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const BASE = process.env.E2E_BASE ?? 'http://127.0.0.1:5173';
const API = process.env.E2E_API ?? 'http://127.0.0.1:8000';
const shotsDir = process.argv.includes('--shots') ? process.argv[process.argv.indexOf('--shots') + 1] : null;
if (shotsDir) fs.mkdirSync(shotsDir, { recursive: true });

const results = [];
const errors = [];
const stamp = Date.now();
const email = `e2e-${stamp}@example.test`;
const password = 'E2E-Pass-2026!';

async function step(name, fn) {
  const t0 = Date.now();
  try {
    await fn();
    results.push({ flow: name, ok: true, ms: Date.now() - t0 });
    console.log(`✓ ${name} (${Date.now() - t0} ms)`);
  } catch (err) {
    results.push({ flow: name, ok: false, ms: Date.now() - t0, error: String(err.message ?? err).slice(0, 300) });
    console.log(`✗ ${name}: ${String(err.message ?? err).slice(0, 300)}`);
  }
}

async function shot(page, name) {
  if (!shotsDir) return;
  await page.screenshot({ path: path.join(shotsDir, `${name}.png`), fullPage: false });
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await context.newPage();
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text().slice(0, 200)}`); });

await step('landing renders', async () => {
  await page.goto(`${BASE}/`);
  await page.waitForSelector('text=EdNova', { timeout: 15000 });
  await shot(page, 'real-landing');
});

await step('register through the UI', async () => {
  await page.goto(`${BASE}/register`);
  await page.fill('input[autocomplete="nickname"]', 'Nour');
  await page.fill('input[autocomplete="email"]', email);
  await page.fill('input[autocomplete="new-password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/onboarding/, { timeout: 15000 });
});

await step('onboarding diagnostic', async () => {
  for (let i = 0; i < 9; i++) {
    const options = page.locator('main button[aria-pressed]');
    await options.first().waitFor({ timeout: 10000 });
    await options.nth(i < 6 ? 0 : 1).click();
    await page.waitForTimeout(260);
  }
  await page.waitForSelector('select', { timeout: 10000 });
  await page.selectOption('select', 'intermediate');
  await page.fill('input[maxlength="200"]', 'Pass my biology exam');
  await shot(page, 'real-onboarding');
  await page.click('main button:has-text("profile"), main button:has-text("Profile"), main button:has-text("Finish"), main button:has-text("See"), main button:has-text("Discover")');
  await page.waitForSelector('text=/visual|analog|step|example|repetition|problem/i', { timeout: 20000 });
  await shot(page, 'real-onboarding-result');
});

await step('dashboard', async () => {
  await page.goto(`${BASE}/app`);
  await page.waitForSelector('text=/Nour/', { timeout: 15000 });
  await page.waitForTimeout(800);
  await shot(page, 'real-dashboard');
});

let docId = null;
await step('upload document + ask (RAG)', async () => {
  await page.goto(`${BASE}/app/documents`);
  const input = page.locator('input[type="file"]');
  await input.waitFor({ state: 'attached', timeout: 10000 });
  await input.setInputFiles(path.resolve('../backend/scripts/sample_docs/photosynthesis_course.md'));
  await page.waitForSelector('text=/passages indexed/i', { timeout: 20000 });
  await page.click('text=photosynthesis_course');
  await page.waitForURL(/\/app\/documents\//, { timeout: 10000 });
  docId = page.url().split('/').pop();
  const ask = page.locator('input[placeholder*="author"], textarea[placeholder*="author"]');
  await ask.fill('Which enzyme fixes carbon dioxide in the Calvin cycle?');
  await page.click('button:has-text("Ask")');
  await page.waitForSelector('text=/RuBisCO/', { timeout: 30000 });
  await shot(page, 'real-document-ask');
});

await step('tutor: guided hint, then reveal', async () => {
  await page.goto(`${BASE}/app/tutor`);
  const composer = page.locator('textarea, input[placeholder*="Ask anything"]').first();
  await composer.waitFor({ timeout: 10000 });
  await composer.fill("I don't understand this exercise: solve 2x + 3 = 11");
  await composer.press('Enter');
  await page.waitForSelector('text=/Guiding question/i', { timeout: 40000 });
  await shot(page, 'real-tutor');
  const reveal = page.locator('button:has-text("Reveal full answer")');
  if (await reveal.count()) {
    await reveal.first().click();
    await page.waitForSelector('text=/Hint 3|full answer|here is what/i', { timeout: 40000 }).catch(() => {});
  }
});

await step('quiz: generate, answer, submit', async () => {
  await page.goto(`${BASE}/app/quizzes`);
  const topicInput = page.locator('input[placeholder*="Photosynthesis"]');
  if (!(await topicInput.count())) await page.click('button:has-text("Generate a quiz")');
  await topicInput.fill('Photosynthesis');
  await page.click('form button[type="submit"]:has-text("Generate")');
  await page.waitForURL(/\/app\/quizzes\//, { timeout: 40000 });
  await page.waitForSelector('text=/Question 1 of/i', { timeout: 15000 });
  for (let i = 0; i < 10; i++) {
    const radio = page.locator('input[type="radio"], button[role="radio"]').first();
    if (await radio.count()) await radio.click().catch(() => {});
    const short = page.locator('input[placeholder*="Type your answer"], textarea[placeholder*="Type your answer"]');
    if (await short.count()) await short.first().fill('Chlorophyll absorbs light energy').catch(() => {});
    const next = page.locator('button:has-text("Next")');
    if ((await next.count()) && (await next.first().isEnabled())) { await next.first().click(); await page.waitForTimeout(150); } else break;
  }
  await page.click('button:has-text("Submit answers")');
  await page.waitForSelector('text=/Results/i', { timeout: 40000 });
  await shot(page, 'real-quiz-results');
});

await step('room: create, chat, moderator nudge, check explanation', async () => {
  await page.goto(`${BASE}/app/rooms`);
  await page.click('button:has-text("Create a room")').catch(() => {});
  const nameInput = page.locator('input[maxlength="60"]');
  await nameInput.waitFor({ timeout: 10000 });
  await nameInput.fill('Bio study crew');
  await page.fill('input[maxlength="120"]', 'Photosynthesis');
  await page.click('[role="dialog"] button[type="submit"]');
  await page.waitForURL(/\/app\/rooms\//, { timeout: 15000 });
  const box = page.locator('input[aria-label*="Write to the group"]');
  await box.waitFor({ timeout: 10000 });
  for (const text of ['Photosynthesis converts light into chemical energy.', 'Chlorophyll absorbs blue and red light.', 'I think photosynthesis produces CO2, right?']) {
    await box.fill(text);
    await box.press('Enter');
    await page.waitForTimeout(500);
  }
  await page.click('button:has-text("Nudge participation")');
  await page.waitForTimeout(1500);
  await page.click('button:has-text("Check this explanation")').catch(() => {});
  await page.waitForTimeout(1500);
  await page.waitForSelector('text=/EdNova moderator/i', { timeout: 15000 });
  await shot(page, 'real-room');
});

await step('roadmap: create and tick an activity', async () => {
  await page.goto(`${BASE}/app/roadmap`);
  const goal = page.locator('input[maxlength="300"], input[placeholder*="exam"], textarea').first();
  await goal.waitFor({ timeout: 10000 });
  await goal.fill('Master photosynthesis for my exam');
  await page.click('button:has-text("Generate"), button:has-text("Create")');
  await page.waitForSelector('text=/Week 1/i', { timeout: 40000 });
  const checkbox = page.locator('input[type="checkbox"]').first();
  if (await checkbox.count()) await checkbox.check().catch(() => {});
  await page.waitForTimeout(600);
  await shot(page, 'real-roadmap');
});

await step('notes from document', async () => {
  await page.goto(`${BASE}/app/notes?source=document&id=${docId}`);
  await page.click('button:has-text("Generate")');
  await page.waitForSelector('text=/Flashcards|Summary/i', { timeout: 40000 });
  await page.waitForTimeout(800);
  await shot(page, 'real-notes');
});

await step('analytics', async () => {
  await page.goto(`${BASE}/app/analytics`);
  await page.waitForSelector('text=/compact|large/i', { timeout: 15000 });
  await page.waitForTimeout(800);
  await shot(page, 'real-analytics');
});

await step('settings in Arabic (RTL) + Darija', async () => {
  const pickLanguage = async (label) => {
    await page.click('button[aria-label="Language"], button[aria-haspopup="listbox"]');
    await page.click(`[role="option"]:has-text("${label}")`);
    await page.waitForTimeout(900);
  };
  await page.goto(`${BASE}/app/settings`);
  await page.waitForSelector('select', { timeout: 10000 });
  await pickLanguage('العربية');
  const dir = await page.evaluate(() => document.documentElement.dir);
  if (dir !== 'rtl') throw new Error(`expected dir=rtl, got ${dir}`);
  await page.goto(`${BASE}/app`);
  await page.waitForTimeout(1200);
  await shot(page, 'real-dashboard-ar');
  await pickLanguage('تونسي');
  await page.goto(`${BASE}/app/tutor`);
  await page.waitForTimeout(1200);
  await shot(page, 'real-tutor-tn');
  await pickLanguage('English');
});

await step('teacher dashboard (seeded demo account)', async () => {
  await page.goto(`${BASE}/login`);
  await page.evaluate(() => { localStorage.removeItem('ednova_token'); });
  await page.goto(`${BASE}/login`);
  await page.fill('input[autocomplete="email"]', 'prof@demo.ednova');
  await page.fill('input[type="password"]', 'Demo-Pass-2026');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
  await page.goto(`${BASE}/app/teacher`);
  await page.waitForSelector('text=/Biologie 1A/', { timeout: 15000 });
  await page.click('text=Biologie 1A');
  await page.waitForTimeout(1200);
  await shot(page, 'real-teacher');
});

await step('seeded room with unbalanced participation (Amal)', async () => {
  await page.goto(`${BASE}/login`);
  await page.evaluate(() => { localStorage.removeItem('ednova_token'); });
  await page.goto(`${BASE}/login`);
  await page.fill('input[autocomplete="email"]', 'amal@demo.ednova');
  await page.fill('input[type="password"]', 'Demo-Pass-2026');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
  await page.goto(`${BASE}/app/rooms`);
  await page.click('text=Bio study crew');
  await page.waitForURL(/\/app\/rooms\//, { timeout: 10000 });
  await page.waitForSelector('text=/Lina/', { timeout: 15000 });
  await page.waitForTimeout(1500);
  await shot(page, 'real-room-seeded');
  await page.goto(`${BASE}/app`);
  await page.waitForTimeout(1500);
  await shot(page, 'real-dashboard-amal');
});

await step('mobile viewport (tutor)', async () => {
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const mp = await mobile.newPage();
  await mp.goto(`${BASE}/login`);
  await mp.fill('input[autocomplete="email"]', 'amal@demo.ednova');
  await mp.fill('input[type="password"]', 'Demo-Pass-2026');
  await mp.click('button[type="submit"]');
  await mp.waitForURL(/\/app/, { timeout: 15000 });
  await mp.goto(`${BASE}/app/tutor`);
  await mp.waitForTimeout(1500);
  await shot(mp, 'real-mobile-tutor');
  await mobile.close();
});

await browser.close();

const status = await fetch(`${API}/api/system/status`).then((r) => r.json()).catch(() => null);
const summary = { base: BASE, passed: results.filter((r) => r.ok).length, total: results.length, results, page_errors: errors.slice(0, 20), ai_status: status };
fs.writeFileSync(shotsDir ? path.join(shotsDir, '..', 'e2e-results.json') : 'e2e-results.json', JSON.stringify(summary, null, 2));
console.log(JSON.stringify({ passed: summary.passed, total: summary.total, page_errors: errors.length }, null, 0));
process.exit(summary.passed === summary.total ? 0 : 1);
