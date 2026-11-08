# EdNova AI — REST API Contract (v1)

Base URL: `/api`. All responses are JSON. Authentication: `Authorization: Bearer <access_token>` (JWT, HS256).
Errors: `{"detail": "message"}` (4xx/5xx) or `{"detail": [ ...validation errors... ]}` (422).

Every AI-generated payload carries an `ai` metadata object:

```json
"ai": {
  "tier": "compact" | "large" | "none",
  "model": "string",
  "provider": "live" | "offline",
  "cached": false,
  "fallback": false,
  "fallback_reason": null | "large_unavailable" | "rate_limited" | "provider_error" | "no_api_key",
  "latency_ms": 1234,
  "notice": null | "human readable notice to show the learner"
}
```

`provider: "offline"` means **no AI API key is configured** – the server returned deterministic, clearly labelled
placeholder content so the UI flow can be exercised. The UI must show the `notice`.

---

## System

### `GET /api/health`
`{"status": "ok", "version": "1.0.0", "db": "sqlite" | "postgresql"}`

### `GET /api/system/status`  (public)
```json
{
  "provider_mode": "live" | "offline",
  "compact_model": "string", "large_model": "string",
  "large_available": true,
  "large_breaker_open_until": null | "ISO-8601",
  "queue_depth": 0, "queue_capacity": 2,
  "stats": {"calls_total": 0, "calls_compact": 0, "calls_large": 0, "cache_hits": 0, "fallbacks": 0, "errors": 0, "avg_latency_ms_compact": 0, "avg_latency_ms_large": 0}
}
```

### `GET /api/system/routing`  (public) – the documented model-routing table
`{"tasks": [{"task": "tutor_triage", "tier": "compact", "rationale": "..."}, ...]}`

---

## Auth

### `POST /api/auth/register`
Body `{"email": "a@b.c", "password": "min 8 chars", "display_name": "pseudonym", "preferred_language": "en|fr|ar|tn", "role": "learner|teacher"}`
→ `201 {"access_token": "...", "token_type": "bearer", "user": User}`

### `POST /api/auth/login`
Body `{"email", "password"}` → `{"access_token", "token_type": "bearer", "user": User}`

### `GET /api/auth/me` → `User`

### `PATCH /api/auth/me`
Body (any subset) `{"display_name", "preferred_language", "learning_style", "level", "darija_script": "arabic|latin"}` → `User`

### `DELETE /api/auth/me` → `204` (erases the account and all its data)

`User`:
```json
{"id": "uuid", "email": "…", "display_name": "…", "role": "learner|teacher",
 "preferred_language": "en|fr|ar|tn", "darija_script": "arabic|latin",
 "learning_style": null | "visual|analogy|step_by_step|examples|repetition|problem_solving",
 "level": null | "beginner|intermediate|advanced",
 "diagnostic_completed": false, "xp": 0, "level_number": 1, "streak_days": 0, "created_at": "ISO"}
```

---

## Diagnostic (learning-style & level)

### `GET /api/diagnostic/questions?language=en`
```json
{"questions": [
  {"id": "q1", "kind": "preference", "text": "...", "options": [{"id": "a", "text": "...", "style": "visual"}, ...]},
  {"id": "q7", "kind": "exercise", "text": "...", "options": [{"id": "a", "text": "..."}], "correct_option_id": "b", "difficulty": "beginner"}
]}
```

### `POST /api/diagnostic/submit`
Body `{"answers": [{"question_id": "q1", "option_id": "a"}, ...], "self_reported_level": "beginner|intermediate|advanced|null", "goal": "free text optional"}`
→
```json
{"profile": {"learning_style": "visual", "secondary_style": "examples", "level": "beginner",
             "style_scores": {"visual": 3, "analogy": 1, ...}, "exercise_score": 2, "exercise_total": 3},
 "recommendations": ["..."], "explanation": "short text in the user's language", "ai": {...}, "user": User}
```

---

## Tutor (conversations)

### `GET /api/tutor/conversations` → `[{"id", "title", "language", "document_id": null|uuid, "created_at", "updated_at", "message_count"}]`
### `POST /api/tutor/conversations` Body `{"title": "optional", "language": "en", "document_id": null}` → Conversation (201)
### `GET /api/tutor/conversations/{id}` → `{"conversation": {...}, "messages": [Message]}`
### `DELETE /api/tutor/conversations/{id}` → 204

`Message`: `{"id", "role": "user|assistant|system", "content": "markdown", "created_at", "meta": {...}}`
Assistant `meta`: `{"ai": {...}, "triage": {"intent": "explain|exercise_help|answer_request|quiz_request|chit_chat|other", "confusion": "none|mild|high", "complexity": "low|high", "language": "en"}, "hint_level": 0|1|2, "sources": [{"chunk_id", "document_id", "page": 3, "excerpt": "..."}], "next_step": "suggested next step", "guiding_question": "..."}`

### `POST /api/tutor/conversations/{id}/messages`
Body `{"content": "text", "mode": "guided|direct", "use_documents": true, "style_override": null|style}`
→ `{"user_message": Message, "assistant_message": Message, "stages": ["triage", "retrieve", "reason", "format"]}`
Latency: several seconds (large model). The client shows staged progress using `stages` hints from `GET /api/tutor/stages`.

### `GET /api/tutor/stages` → `{"stages": [{"key": "triage", "label_key": "stage.triage", "typical_ms": 1500}, ...]}`

### `POST /api/tutor/conversations/{id}/reveal`  (ask for the full answer after hints)
Body `{}` → same shape as messages POST (assistant message with `hint_level: 2`).

---

## Quizzes

### `POST /api/quizzes/generate`
Body `{"topic": "Photosynthesis", "document_id": null|uuid, "num_questions": 5, "difficulty": "beginner|intermediate|advanced|auto", "language": "en", "question_types": ["mcq", "short"], "room_id": null}`
→ `201 Quiz`
```json
{"id": "uuid", "topic", "language", "difficulty", "created_at", "source": "topic|document", "document_id": null,
 "questions": [
   {"id": "uuid", "type": "mcq", "text": "...", "options": [{"id": "a", "text": "..."}], "skill": "tag"},
   {"id": "uuid", "type": "short", "text": "...", "skill": "tag"}
 ],
 "ai": {...}}
```
(`correct_option_id` / `expected_answer` are **not** returned before submission.)

### `GET /api/quizzes` → `[QuizSummary]` `{"id", "topic", "language", "difficulty", "num_questions", "created_at", "best_score": null|number, "attempts": 0}`
### `GET /api/quizzes/{id}` → `Quiz`

### `POST /api/quizzes/{id}/submit`
Body `{"answers": [{"question_id": "uuid", "option_id": "a"} | {"question_id": "uuid", "text": "free answer"}], "time_spent_s": 120}`
→
```json
{"attempt_id": "uuid", "score": 4, "total": 5, "percent": 80,
 "results": [{"question_id", "correct": true, "score": 1.0, "your_answer": "...", "correct_answer": "...", "explanation": "...", "skill": "tag"}],
 "feedback": "personalised feedback in user's language", "xp_gained": 40, "badges_unlocked": ["first_quiz"], "ai": {...}}
```

---

## Collaborative rooms

### `GET /api/rooms` → `[RoomSummary]` `{"id", "code": "ABC123", "name", "topic", "language", "member_count", "created_at", "is_owner": true}`
### `POST /api/rooms` Body `{"name", "topic", "language": "en"}` → `201 Room`
### `POST /api/rooms/join` Body `{"code": "ABC123"}` → `Room`
### `GET /api/rooms/{id}` → `Room`
```json
{"id", "code", "name", "topic", "language", "owner_id", "created_at",
 "members": [{"user_id", "display_name", "joined_at", "message_count"}],
 "participation": {"balance_score": 0.0-1.0, "dominant_member": null|display_name, "quiet_members": ["name"], "total_messages": 12},
 "quiz_id": null}
```
### `GET /api/rooms/{id}/messages?after=<message_id|empty>&limit=50` → `{"messages": [RoomMessage], "participation": {...}}`
`RoomMessage`: `{"id", "room_id", "user_id": null|uuid, "display_name": "...", "role": "member|moderator", "content", "created_at", "meta": {...}}`
### `POST /api/rooms/{id}/messages` Body `{"content"}` → `{"message": RoomMessage, "moderator_message": null|RoomMessage}`
(The AI moderator may answer automatically every N messages or when a question is addressed to `@ednova`.)
### `POST /api/rooms/{id}/moderate` Body `{"action": "nudge|check_explanation|summarize|guiding_question", "message_id": null|uuid}`
→ `{"moderator_message": RoomMessage, "ai": {...}}`
### `POST /api/rooms/{id}/quiz` Body `{"num_questions": 5}` → `Quiz` (collaborative quiz shared with the room; stored on room.quiz_id)
### `GET /api/rooms/{id}/leaderboard` → `[{"display_name", "percent", "submitted_at"}]`

---

## Documents (RAG)

### `POST /api/documents` multipart form: `file` (pdf|txt|md|docx, ≤ 15 MB), `title` (optional), `language` (optional)
→ `201 Document` `{"id", "title", "filename", "mime", "pages", "chunk_count", "chars", "language", "created_at", "status": "ready|failed", "error": null}`
### `GET /api/documents` → `[Document]`
### `GET /api/documents/{id}` → `Document & {"preview": "first 1200 chars"}`
### `DELETE /api/documents/{id}` → 204
### `POST /api/documents/{id}/search` Body `{"query", "k": 5}` → `{"results": [{"chunk_id", "page", "score", "excerpt"}]}` (no LLM call)
### `POST /api/documents/{id}/ask` Body `{"question", "language": "en"}`
→ `{"answer": "markdown with [1] citations", "sources": [{"chunk_id", "page", "excerpt", "score"}], "ai": {...}}`

---

## Roadmaps & revision notes

### `POST /api/roadmaps` Body `{"goal": "Pass my linear algebra exam", "weeks": 4, "hours_per_week": 5, "language": "en", "document_id": null}`
→ `201 Roadmap`
```json
{"id", "goal", "weeks", "language", "created_at", "progress_percent": 0,
 "milestones": [{"id", "week": 1, "title", "objective", "activities": [{"id", "text", "kind": "read|practice|quiz|discuss|watch|recall", "done": false}], "checkpoint": "..."}],
 "ai": {...}}
```
### `GET /api/roadmaps` → `[Roadmap]`
### `GET /api/roadmaps/{id}` → `Roadmap`
### `PATCH /api/roadmaps/{id}/activities/{activity_id}` Body `{"done": true}` → `Roadmap` (xp awarded)

### `POST /api/notes/generate` Body `{"source": "conversation|document|room|topic", "source_id": null|uuid, "topic": null|str, "language": "en", "format": "summary|flashcards|both"}`
→ `201 Note` `{"id", "title", "source", "source_id", "language", "content_md", "flashcards": [{"q", "a"}], "created_at", "ai": {...}}`
### `GET /api/notes` → `[Note]`
### `GET /api/notes/{id}` → `Note`
### `DELETE /api/notes/{id}` → 204

---

## Analytics & gamification

### `GET /api/analytics/overview`
```json
{"xp": 320, "level_number": 3, "level_progress_percent": 40, "streak_days": 4,
 "totals": {"questions_asked": 23, "quizzes_taken": 5, "avg_score_percent": 76, "documents": 2, "rooms": 1, "notes": 3, "study_minutes": 140},
 "skills": [{"skill": "Derivatives", "mastery_percent": 70, "attempts": 3, "trend": "up|flat|down"}],
 "activity_last_14_days": [{"date": "2026-11-01", "questions": 2, "quiz_points": 3, "minutes": 20}],
 "confusion_events": [{"date", "topic", "level": "mild|high"}],
 "learning_style": "visual", "style_scores": {...},
 "badges": [{"id": "first_quiz", "name_key": "badge.first_quiz", "unlocked_at": "ISO"}],
 "next_step": {"text": "...", "action": "tutor|quiz|roadmap|room|document", "target_id": null},
 "ai_efficiency": {"calls_compact": 10, "calls_large": 3, "cache_hits": 4, "fallbacks": 0, "large_share_percent": 23}}
```

### `GET /api/analytics/events?limit=50` → `[{"id", "type", "created_at", "payload": {...}}]`

---

## Teacher (optional, role=teacher)

### `POST /api/classes` Body `{"name"}` → `{"id", "code", "name", "created_at"}`
### `GET /api/classes` → `[{"id", "code", "name", "member_count"}]`
### `POST /api/classes/join` Body `{"code"}` → `{"joined": true}` (learner)
### `GET /api/classes/{id}/dashboard` → aggregated, anonymised:
`{"members": 12, "avg_score_percent": 71, "quizzes_taken": 30, "style_distribution": {"visual": 4, ...}, "weak_skills": [{"skill", "mastery_percent"}], "confusion_hotspots": [{"topic", "count"}], "participation_balance_avg": 0.7}`

---

## Languages

`en` English · `fr` Français · `ar` العربية (Modern Standard) · `tn` تونسي / Tunisian Darija (`darija_script` chooses Arabic or Latin script).
