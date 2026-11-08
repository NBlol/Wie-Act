#!/usr/bin/env node
// UI smoke test with a MOCKED API (fixtures shaped like docs/API.md). It does not exercise the real backend;
// it only verifies that every authenticated page renders without runtime errors and captures preview screenshots.
// Usage: node scripts/smoke-mock.mjs [outDir] [baseUrl]
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const outDir = process.argv[2] || path.resolve('..', 'docs', 'screenshots');
const base = process.argv[3] || 'http://127.0.0.1:5173';
fs.mkdirSync(outDir, { recursive: true });

const now = new Date().toISOString();
const ai = (tier, extra = {}) => ({ tier, model: tier === 'large' ? 'large-model' : 'compact-model', provider: 'live', cached: false, fallback: false, fallback_reason: null, latency_ms: tier === 'large' ? 5400 : 900, notice: null, ...extra });
const user = { id: 'u1', email: 'demo@example.com', display_name: 'Nour', role: 'teacher', preferred_language: 'en', darija_script: 'arabic', learning_style: 'visual', level: 'intermediate', diagnostic_completed: true, xp: 320, level_number: 3, streak_days: 4, created_at: now };
const status = { provider_mode: 'live', compact_model: 'compact-model', large_model: 'large-model', large_available: false, large_breaker_open_until: now, queue_depth: 1, queue_capacity: 2, stats: { calls_total: 13, calls_compact: 10, calls_large: 3, cache_hits: 4, fallbacks: 1, errors: 0, avg_latency_ms_compact: 900, avg_latency_ms_large: 5400 } };
const conversation = { id: 'c1', title: 'Dividing by zero', language: 'en', document_id: null, created_at: now, updated_at: now, message_count: 2 };
const messages = [
  { id: 'm1', role: 'user', content: 'Why does dividing by zero break everything?', created_at: now, meta: {} },
  {
    id: 'm2',
    role: 'assistant',
    content: 'Before I answer, think about what **6 ÷ 2** means in words.\n\n- Division asks *how many groups*.\n- `6 ÷ 0` asks how many groups of nothing fit into six.',
    created_at: now,
    meta: { ai: ai('compact'), triage: { intent: 'explain', confusion: 'mild', complexity: 'high', language: 'en' }, hint_level: 1, sources: [{ chunk_id: 'k1', document_id: 'd1', page: 3, excerpt: 'Division by zero is undefined because…' }], next_step: 'Try 6 ÷ 0.1, then 6 ÷ 0.01. What happens?', guiding_question: 'How many zeros fit into six?' },
  },
];
const quiz = { id: 'q1', topic: 'Photosynthesis', language: 'en', difficulty: 'intermediate', created_at: now, source: 'topic', document_id: null, questions: [{ id: 'qq1', type: 'mcq', text: 'Where does photosynthesis take place?', options: [{ id: 'a', text: 'Mitochondria' }, { id: 'b', text: 'Chloroplasts' }, { id: 'c', text: 'Nucleus' }], skill: 'Cell biology' }, { id: 'qq2', type: 'short', text: 'Name the gas released by photosynthesis.', skill: 'Gas exchange' }], ai: ai('large') };
const room = { id: 'r1', code: 'AB12CD', name: 'Thermo study group', topic: 'Entropy', language: 'en', owner_id: 'u1', created_at: now, members: [{ user_id: 'u1', display_name: 'Nour', joined_at: now, message_count: 5 }, { user_id: 'u2', display_name: 'Sami', joined_at: now, message_count: 1 }, { user_id: 'u3', display_name: 'Ines', joined_at: now, message_count: 0 }], participation: { balance_score: 0.42, dominant_member: 'Nour', quiet_members: ['Ines'], total_messages: 6 }, quiz_id: 'q1' };
const roomMessages = [
  { id: 'rm1', room_id: 'r1', user_id: 'u2', display_name: 'Sami', role: 'member', content: 'Entropy always increases, right?', created_at: now, meta: {} },
  { id: 'rm2', room_id: 'r1', user_id: 'u1', display_name: 'Nour', role: 'member', content: 'In an isolated system, yes.', created_at: now, meta: {} },
  { id: 'rm3', room_id: 'r1', user_id: null, display_name: 'EdNova', role: 'moderator', content: 'Ines, what do you think happens in an open system?', created_at: now, meta: { ai: ai('compact'), action: 'nudge' } },
];
const doc = { id: 'd1', title: 'Thermodynamics chapter 2', filename: 'thermo-ch2.pdf', mime: 'application/pdf', pages: 12, chunk_count: 38, chars: 24000, language: 'en', created_at: now, status: 'ready', error: null, preview: 'Entropy is a measure of the number of microscopic configurations…' };
const roadmap = { id: 'rd1', goal: 'Pass my thermodynamics exam', weeks: 2, language: 'en', created_at: now, progress_percent: 25, milestones: [{ id: 'w1', week: 1, title: 'Foundations', objective: 'Understand state functions', activities: [{ id: 'a1', text: 'Read chapter 2', kind: 'read', done: true }, { id: 'a2', text: 'Solve 5 entropy problems', kind: 'practice', done: false }], checkpoint: 'Explain entropy to a peer in 2 minutes' }, { id: 'w2', week: 2, title: 'Cycles', objective: 'Carnot and real cycles', activities: [{ id: 'a3', text: 'Quiz on cycles', kind: 'quiz', done: false }, { id: 'a4', text: 'Discuss in a room', kind: 'discuss', done: false }], checkpoint: 'Score 80% on the cycles quiz' }], ai: ai('large') };
const note = { id: 'n1', title: 'Entropy essentials', source: 'document', source_id: 'd1', language: 'en', content_md: '# Entropy\n\n- A **state function**.\n- Increases in isolated systems.', flashcards: [{ q: 'Is entropy a state function?', a: 'Yes.' }, { q: 'What happens to entropy in an isolated system?', a: 'It never decreases.' }], created_at: now, ai: ai('large', { cached: true }) };
const analytics = { xp: 320, level_number: 3, level_progress_percent: 40, streak_days: 4, totals: { questions_asked: 23, quizzes_taken: 5, avg_score_percent: 76, documents: 2, rooms: 1, notes: 3, study_minutes: 140 }, skills: [{ skill: 'Cell biology', mastery_percent: 80, attempts: 3, trend: 'up' }, { skill: 'Gas exchange', mastery_percent: 45, attempts: 2, trend: 'down' }], activity_last_14_days: Array.from({ length: 14 }, (_, i) => ({ date: new Date(Date.now() - (13 - i) * 864e5).toISOString().slice(0, 10), questions: i % 3, quiz_points: i % 4, minutes: i * 3 })), confusion_events: [{ date: now, topic: 'Entropy', level: 'high' }], learning_style: 'visual', style_scores: { visual: 4, analogy: 2, step_by_step: 3, examples: 1, repetition: 1, problem_solving: 2 }, badges: [{ id: 'first_question', name_key: 'badge.first_question', unlocked_at: now }, { id: 'first_quiz', name_key: 'badge.first_quiz', unlocked_at: now }, { id: 'streak_7', name_key: 'badge.streak_7', unlocked_at: null }, { id: 'collaborator', name_key: 'badge.collaborator', unlocked_at: null }], next_step: { text: 'Revise gas exchange with a 5-question quiz.', action: 'quiz', target_id: null }, ai_efficiency: { calls_compact: 10, calls_large: 3, cache_hits: 4, fallbacks: 1, large_share_percent: 23 } };
const classroom = { id: 'k1', code: 'CL4SS1', name: 'Physics 2A', created_at: now, member_count: 12 };
const classDashboard = { members: 12, avg_score_percent: 71, quizzes_taken: 30, style_distribution: { visual: 4, analogy: 2, step_by_step: 3, examples: 2, repetition: 1 }, weak_skills: [{ skill: 'Entropy', mastery_percent: 42 }, { skill: 'Carnot cycle', mastery_percent: 55 }], confusion_hotspots: [{ topic: 'Entropy', count: 7 }, { topic: 'Enthalpy', count: 3 }], participation_balance_avg: 0.68 };
const diagnostic = { questions: [{ id: 'q1', kind: 'preference', text: 'When a concept is new, what helps most?', options: [{ id: 'a', text: 'A diagram', style: 'visual' }, { id: 'b', text: 'A comparison with something I know', style: 'analogy' }, { id: 'c', text: 'Small ordered steps', style: 'step_by_step' }] }, { id: 'q7', kind: 'exercise', text: 'What is 15% of 200?', options: [{ id: 'a', text: '25' }, { id: 'b', text: '30' }, { id: 'c', text: '35' }], correct_option_id: 'b', difficulty: 'beginner' }] };

const routes = [
  ['GET', '/api/system/status', status],
  ['GET', '/api/auth/me', user],
  ['PATCH', '/api/auth/me', user],
  ['GET', '/api/tutor/stages', { stages: [{ key: 'triage', label_key: 'stage.triage', typical_ms: 1500 }, { key: 'retrieve', label_key: 'stage.retrieve', typical_ms: 800 }, { key: 'reason', label_key: 'stage.reason', typical_ms: 6000 }, { key: 'format', label_key: 'stage.format', typical_ms: 1000 }] }],
  ['GET', '/api/tutor/conversations', [conversation]],
  ['GET', '/api/tutor/conversations/c1', { conversation, messages }],
  ['GET', '/api/quizzes', [{ id: 'q1', topic: 'Photosynthesis', language: 'en', difficulty: 'intermediate', num_questions: 2, created_at: now, best_score: 50, attempts: 1 }]],
  ['GET', '/api/quizzes/q1', quiz],
  ['GET', '/api/rooms', [{ id: 'r1', code: 'AB12CD', name: 'Thermo study group', topic: 'Entropy', language: 'en', member_count: 3, created_at: now, is_owner: true }]],
  ['GET', '/api/rooms/r1', room],
  ['GET', '/api/rooms/r1/messages', { messages: roomMessages, participation: room.participation }],
  ['GET', '/api/rooms/r1/leaderboard', [{ display_name: 'Nour', percent: 80, submitted_at: now }]],
  ['GET', '/api/documents', [doc]],
  ['GET', '/api/documents/d1', doc],
  ['GET', '/api/roadmaps', [roadmap]],
  ['GET', '/api/notes', [note]],
  ['GET', '/api/analytics/overview', analytics],
  ['GET', '/api/classes', [classroom]],
  ['GET', '/api/classes/k1/dashboard', classDashboard],
  ['GET', '/api/diagnostic/questions', diagnostic],
];

const pages = [
  { name: 'app-dashboard', url: '/app' },
  { name: 'app-tutor', url: '/app/tutor/c1' },
  { name: 'app-quizzes', url: '/app/quizzes' },
  { name: 'app-quiz-take', url: '/app/quizzes/q1' },
  { name: 'app-rooms', url: '/app/rooms' },
  { name: 'app-room', url: '/app/rooms/r1' },
  { name: 'app-documents', url: '/app/documents' },
  { name: 'app-document', url: '/app/documents/d1' },
  { name: 'app-roadmap', url: '/app/roadmap' },
  { name: 'app-notes', url: '/app/notes' },
  { name: 'app-analytics', url: '/app/analytics' },
  { name: 'app-settings', url: '/app/settings' },
  { name: 'app-teacher', url: '/app/teacher' },
  { name: 'onboarding', url: '/onboarding' },
  { name: 'app-dashboard-ar', url: '/app', locale: 'ar' },
  { name: 'app-tutor-mobile-fr', url: '/app/tutor/c1', locale: 'fr', viewport: { width: 390, height: 844 } },
];

const browser = await chromium.launch();
const errors = [];
for (const p of pages) {
  const context = await browser.newContext({ viewport: p.viewport ?? { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('pageerror', (e) => errors.push(`${p.name}: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`${p.name}: console ${m.text()}`);
  });
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const hit = routes.find(([method, path]) => method === req.method() && url.pathname === path);
    if (hit) {
      // the logged-in user's preferred language follows the page locale so RTL pages can be verified
      const body = url.pathname === '/api/auth/me' ? { ...user, preferred_language: p.locale ?? 'en' } : hit[2];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: `mock: no fixture for ${req.method()} ${url.pathname}` }) });
  });
  await page.addInitScript(
    ({ locale }) => {
      localStorage.setItem('ednova_token', 'mock-token');
      localStorage.setItem('ednova_locale', locale);
    },
    { locale: p.locale ?? 'en' },
  );
  await page.goto(base + p.url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(outDir, `${p.name}.png`), fullPage: true });
  console.log(`saved ${p.name}.png  (${page.url().replace(base, '')})`);
  await context.close();
}
await browser.close();
if (errors.length) {
  console.error('Runtime errors:\n' + errors.join('\n'));
  process.exit(1);
}
console.log('no runtime errors');
