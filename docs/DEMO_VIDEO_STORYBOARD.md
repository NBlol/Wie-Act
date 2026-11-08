# Demonstration video storyboard — 90 seconds

*Format: 1920×1080 screen recording + voice-over, subtitles in English. No credentials, no real names,
synthetic accounts only (Amal, Lina, Sami, Prof. Demo). Hide the `.env` and browser dev-tools.*

| # | Time | Screen | Voice-over (EN) | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:08 | Landing page, slow zoom on the hero; language chips EN · FR · AR · تونسي | "Study groups fail in predictable ways: one voice dominates, questions go unasked, wrong answers go unchallenged. EdNova is a GenAI peer-learning companion that fixes that." | *EdNova AI — tutor · teammate · mediator* |
| 2 | 0:08–0:18 | Onboarding diagnostic: answer 2 questions quickly, submit, profile card appears ("Visual learner · Intermediate") with style bars | "It starts with a 3-minute diagnostic: EdNova learns how *you* learn — visual, analogies, step by step — and your level." | *Diagnostic → personalised* |
| 3 | 0:18–0:36 | Tutor page, language set to French. Type: « Je ne comprends pas le rôle de la chlorophylle ». Staged progress *Understanding → Searching documents → Thinking → Formatting*; answer shows a **hint**, a guiding question, a next step, cited passage [1] from the uploaded PDF, pill "compact · 1.2 s"; click **Reveal full answer** → pill "large" | "Ask in French, Arabic or Darija. The tutor gives a hint first, grounded in your own course document, and asks a guiding question. Simple steps go to the fast compact model; only the full worked solution calls the large model." | *Hint first · RAG citations · compact → large* |
| 4 | 0:36–0:50 | Study room "Bio study crew": Amal's messages dominate; participation gauge turns orange; moderator message appears: "Lina, Sami — what still feels unclear about the Calvin cycle?"; click **Check this explanation** on "photosynthesis produces CO2" → "**Incorrect** — …" | "In study rooms the AI moderator watches participation balance, invites quiet members by name, and fact-checks peer explanations before the group accepts them." | *Equal participation · explanation check* |
| 5 | 0:50–1:02 | Quizzes: generate 5 questions from the document, answer two, submit → results with explanations, personalised feedback, "+20 XP", badge toast | "Quizzes are generated from the material and corrected automatically — multiple choice locally, short answers in a single batched call." | *Auto-correction · XP & badges* |
| 6 | 1:02–1:14 | Analytics page: skill mastery bars, confusion hotspots, **AI-efficiency donut** (e.g. 71 % compact / 29 % large, cache hits); then toggle `AI_FORCE_OFFLINE` demo: banner "Large model temporarily unavailable — using the fast model" and a labelled answer | "Everything is tracked: mastery, confusion, next step — and how efficiently we use the shared service. When the large model is rate-limited or down, EdNova queues, retries, falls back to the compact model and tells you — it never fails silently." | *Analytics · graceful fallback* |
| 7 | 1:14–1:24 | Roadmap timeline + revision notes with flashcards (quick flip) in Arabic UI (RTL) | "Roadmaps and revision notes close the loop, in four languages, right-to-left included." | *Roadmaps · notes · AR/Darija* |
| 8 | 1:24–1:30 | Logo card: repo URL, architecture mini-diagram, team roles | "EdNova AI — structured, inclusive, personalised peer learning. Open-source, Docker-ready, built for the two-model platform." | *github.com/<team>/ednova-ai* |

## Production notes

* Record with the seeded demo data (`python scripts/seed_demo.py`) so the room already shows an
  unbalanced discussion and a document is indexed.
* For scene 6, start the backend with `AI_FORCE_OFFLINE=true` or lower `AI_BREAKER_FAILURES` and point the
  large model name to an invalid one to show the real fallback path and the banner.
* Keep each AI call visible (the staged progress is part of the story: latency is a design budget).
* Subtitles must not show any token/URL of the platform; use the `.env.example` if configuration is shown.
* Export at ≤ 1:30 (hard limit for the final phase).
