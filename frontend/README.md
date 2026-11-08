# EdNova AI — frontend

React 19 + TypeScript (strict) + Tailwind CSS 4, bundled with esbuild. No framework-specific router, state or i18n
library: a small history router, a typed fetch client, an i18n provider (English, Français, العربية, تونسي with RTL)
and inline-SVG charts live in `src/lib`.

## Commands

```bash
npm install          # normal install (react, react-dom, react-icons, tailwindcss, esbuild, typescript)
npm run dev          # http://localhost:5173 — rebuilds on change, proxies /api to http://127.0.0.1:8000 (API_PROXY env)
npm run build        # production bundle in dist/ (JS + compiled Tailwind CSS + index.html + public/)
npm run typecheck    # tsc, zero errors expected
```

Optional tooling (needs `playwright` installed): `node scripts/e2e.mjs --shots ../docs/screenshots` drives the **real**
application end-to-end against a running backend (15 flows, screenshots in `docs/screenshots/real-*.png`);
`node scripts/screenshot.mjs` captures the public pages; `node scripts/smoke-mock.mjs` renders every authenticated
page against **mocked** API fixtures to catch runtime errors — it does not test the backend.

## Build pipeline

`scripts/lib/pipeline.mjs` bundles `src/main.tsx` with the esbuild API and compiles `src/styles.css` with Tailwind's
`compile()` API. Class candidates are collected by scanning `src/**/*.{ts,tsx}` and `index.html`, which replaces the
native `@tailwindcss/oxide` scanner so the build runs anywhere Node runs.

## Structure

```
src/
  main.tsx, App.tsx         entry + routes (public, protected, onboarding guard)
  styles.css                Tailwind import, @theme tokens (brand violet, mint accent), component classes
  lib/                      router, api (typed client for docs/API.md), auth, i18n, status (service banner),
                            progress (StagedProgress, AiBadge), markdown, charts, hooks, toast
  i18n/                     en.ts (source of truth, typed keys), fr.ts, ar.ts, tn.ts
  components/               ui kit (Button, Card, Field, Input, Select, Badge, Chip, Modal, Tabs, Toggle, EmptyState,
                            ErrorState, Skeleton, Stat), AppShell, LanguageSwitcher, Logo
  pages/                    Landing, Auth, Onboarding, Dashboard, Tutor, Quizzes, Rooms, Documents, Roadmap,
                            Notes, Analytics, Settings, Teacher
```

## Behaviour worth knowing

- Every AI result shows an `AiBadge` (compact / large model, cached, fallback, latency, offline demo) and any
  `ai.notice` inline. `ServiceBanner` polls `/api/system/status` every 20 s and reports offline mode, large-model
  unavailability, breaker retry time and queue depth. The backend being down is shown, never swallowed.
- `StagedProgress` keeps the user informed while non-streamed answers are produced (triage → retrieve → reason →
  format, with typical durations from `/api/tutor/stages`).
- Locale is persisted in `localStorage` and synced with `user.preferred_language`; `ar` and `tn` switch the document
  to RTL. Numbers always use Latin digits.
