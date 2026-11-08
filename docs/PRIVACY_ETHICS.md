# Privacy and ethical safeguards

The challenge rules require: no sensitive personal data, anonymous or synthetic test data, no names,
photos, voices or addresses, no discrimination, AI that supports — not replaces — teachers, and
credentials that are never exposed. EdNova implements the following.

## Data minimisation

| Data | Policy |
|---|---|
| Identity | email (login only) + a **pseudonymous display name**; the UI explicitly says "no real names needed" |
| Profile | learning style, level, language, goal — pedagogical signals only |
| Content | learner questions, quiz answers, room messages, roadmap/notes — needed for the service |
| Uploaded files | **not stored**: only extracted text chunks are kept; deleting the document deletes the chunks |
| Photos, voice, address, phone | **never collected** (no fields exist) |
| Prompts | never logged by default (`AI_LOG_PROMPTS=false`); only task, category, latency and outcome are logged |
| Credentials | environment variables only; `.env` is git-ignored; `.env.example` holds no secrets |

## Learner control

* `DELETE /api/auth/me` erases the account and every linked record (conversations, documents, chunks,
  quizzes, attempts, roadmaps, notes, events, badges, AI logs); room messages are anonymised to
  "deleted learner" so that peers' discussions remain coherent.
* Documents, conversations and notes can be deleted individually.
* The settings page explains the policy in the learner's language.

## Fairness and inclusion

* Prompts instruct the models to be inclusive and neutral regarding gender, region, language level or
  background, never to judge a question as too simple, and to adapt to the learner's level and language —
  including **Tunisian Darija**, so learners can ask in the language they think in.
* The diagnostic items are domain-neutral and the questionnaire asks about *preferences*, not abilities.
* The moderator is designed to **rebalance** participation (invite quiet members by name, thank active
  ones, never blame) and to make simple questions safe to ask.

## Supporting teachers, not replacing them

* Hint-first pedagogy keeps the learner doing the work; the full answer is given only when requested.
* The teacher dashboard shows **aggregates only** (style distribution, weak skills, confusion hotspots,
  participation balance) — never individual transcripts.
* Every AI output is labelled with its category, cache/fallback state and, in offline mode, the fact that
  it was *not* produced by a language model.

## Testing data

The automated tests and the demo seeder use only **synthetic** accounts (`*@demo.ednova`, `*@example.test`)
and synthetic teaching material (`backend/scripts/sample_docs/`). Real user testing (bonus criterion)
should use anonymised accounts and the consent note in the report.

## Platform usage rules

* One configured set of team credentials; no second accounts or replacement services during the demo.
  Any additional external service would be declared explicitly in the report.
* Only public, fictional, synthetic or anonymised data is sent to the service.
* Latency and queueing are handled as expected behaviour (see `docs/MODEL_ROUTING.md`), not as errors.
