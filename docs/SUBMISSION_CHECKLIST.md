# Submission checklist — EdNova Challenge (WIE ACT 5.0)

## Phase 1 — Preselection (deadline: 10 November)

### Technical report (≤ 6 pages) — `submission/EdNova_AI_Technical_Report.pdf`
- [x] Project objective
- [x] System architecture (+ diagrams)
- [x] AI model / API used and **how the two model categories are combined** (routing table)
- [x] RAG workflow
- [x] Privacy and ethical safeguards
- [x] Testing strategy and results (real, with what remains untested stated explicitly)
- [x] Behaviour under limited capacity / temporary unavailability
- [x] Business-model note: target users, value proposition, adoption path, sustainability
- [ ] Team names and roles filled in (placeholders in the report cover) ← **to complete**
- [ ] Page count verified ≤ 6 after edits

### GitHub repository
- [x] Source code (backend + frontend + Docker)
- [x] Setup instructions (README: Docker and local)
- [x] README
- [x] Prototype screenshots (`docs/screenshots/`)
- [x] Technical explanation of the GenAI module (`docs/MODEL_ROUTING.md`)
- [x] Configuration template without credentials (`.env.example`)
- [x] `.gitignore` excludes `.env`, databases, uploads, `node_modules`, `dist`
- [ ] Repository pushed, public (or shared with the organisers), link copied into the report ← **to do**
- [ ] `git log` contains no secrets (search for `AI_API_KEY=` values) ← **verify before pushing**

### Demonstration / simulation
- [ ] 90-second video recorded following `docs/DEMO_VIDEO_STORYBOARD.md` (≤ 1:30) ← **to record**
- [ ] No credentials, tokens or real names visible; synthetic accounts only
- [ ] Shows waiting/fallback behaviour (staged progress + banner)
- [ ] Link (unlisted video or file) added to the report and README

### Before submitting
- [ ] `docker compose up --build` runs on a clean machine with real credentials in `.env`
- [ ] `pip install -r requirements.txt` + `pytest` pass with the real FastAPI
- [ ] `npm install && npm run build` passes with a standard npm install
- [ ] One end-to-end run with the real platform: tutor turn, quiz, room moderation, document Q&A, roadmap, notes
- [ ] Measured latencies written into the report (replace "not yet measured")
- [ ] Optional bonus: real user testing session (5–10 learners, consent, anonymised), summarised in the report

## Phase 2 — Final (selected teams, 3 days)

- [ ] Presentation ≤ 4 minutes, delivered by two team members (`submission/EdNova_AI_Presentation.pptx`)
- [ ] Team introduction with roles and expertise (slide 2)
- [ ] Problem · solution · methodology (models, RAG, tools, platform) · implementation & impact · business model
- [ ] How the two categories are combined + behaviour when usage is limited (slides 7–8)
- [ ] Demo video (previous or new version) ≤ 1:30
- [ ] Q&A preparation: cost per learner, privacy, why BM25, what happens at 429, how Darija is handled
- [ ] Team ≤ 3 people; entrepreneurship angle covered by one member

## Rules compliance
- [x] No sensitive personal data stored; synthetic testing data
- [x] No names/photos/voices/addresses collected
- [x] Non-discrimination instructions in prompts; AI supports teachers
- [x] Credentials never in code, logs, screenshots or videos
- [x] No bypass of usage limits; any additional external service would be declared
- [x] Only public/synthetic/anonymised data sent to the service
