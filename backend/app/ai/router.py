"""
ModelRouter – the orchestration layer between the application and the two
model categories.

Responsibilities (all documented in the technical report):

1. **Tier selection** from the routing table (`tasks.py`), possibly dynamic.
2. **Response cache**: equivalent requests (same task + tier + normalised
   inputs) are never regenerated (in-memory LRU + persistent `ai_cache` table).
3. **Concurrency queue** for the scarce large model (bounded semaphore with a
   maximum wait; the queue depth is exposed to the UI).
4. **Retries** with exponential back-off honouring `Retry-After`.
5. **Circuit breaker**: repeated large-model failures open the breaker for a
   while and route straight to the compact model, with an explicit notice.
6. **Graceful degradation**: large → compact → offline generators; the
   `ai` metadata tells the learner what happened instead of failing silently.
7. **Telemetry**: every call is logged (`ai_calls`) so the analytics page can
   show the compact/large split, cache-hit ratio and fallbacks.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import typing as t
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.ai import offline, prompts
from app.ai.provider import LLMProvider, LLMResult, ProviderError, build_provider
from app.ai.tasks import COMPACT, LARGE, TASKS, TaskSpec
from app.config import settings
from app.utils import dumps, extract_json, new_id, normalize_text, now_iso

log = logging.getLogger("ednova.ai")


class AIUnavailable(Exception):
    pass


@dataclass
class AIOutput:
    data: t.Any
    ai: dict[str, t.Any]
    raw_text: str | None = None


@dataclass
class _Stats:
    calls_total: int = 0
    calls_compact: int = 0
    calls_large: int = 0
    calls_offline: int = 0
    cache_hits: int = 0
    fallbacks: int = 0
    errors: int = 0
    latency_compact: list[int] = field(default_factory=list)
    latency_large: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        def avg(values: list[int]) -> int:
            return int(sum(values) / len(values)) if values else 0

        return {
            "calls_total": self.calls_total,
            "calls_compact": self.calls_compact,
            "calls_large": self.calls_large,
            "calls_offline": self.calls_offline,
            "cache_hits": self.cache_hits,
            "fallbacks": self.fallbacks,
            "errors": self.errors,
            "avg_latency_ms_compact": avg(self.latency_compact[-200:]),
            "avg_latency_ms_large": avg(self.latency_large[-200:]),
        }


class _Breaker:
    """Failure-count circuit breaker for one tier."""

    def __init__(self, failures: int, window_s: int, open_s: int):
        self.failures = failures
        self.window_s = window_s
        self.open_s = open_s
        self._events: list[float] = []
        self._open_until: float = 0.0
        self._lock = threading.Lock()

    def record_failure(self) -> None:
        with self._lock:
            now = time.time()
            self._events = [e for e in self._events if now - e < self.window_s] + [now]
            if len(self._events) >= self.failures:
                self._open_until = now + self.open_s
                self._events.clear()

    def record_success(self) -> None:
        with self._lock:
            self._events.clear()
            self._open_until = 0.0

    def force_open(self, seconds: float | None = None) -> None:
        with self._lock:
            self._open_until = time.time() + (seconds or self.open_s)

    @property
    def is_open(self) -> bool:
        return time.time() < self._open_until

    @property
    def open_until_iso(self) -> str | None:
        if not self.is_open:
            return None
        return datetime.fromtimestamp(self._open_until, tz=timezone.utc).isoformat(timespec="seconds")


class _Queue:
    """Bounded concurrency for the scarce tier, with a visible queue depth."""

    def __init__(self, capacity: int, max_wait_s: float):
        self.capacity = max(1, capacity)
        self.max_wait_s = max_wait_s
        self._sem = threading.BoundedSemaphore(self.capacity)
        self._waiting = 0
        self._lock = threading.Lock()

    @property
    def depth(self) -> int:
        return self._waiting

    def acquire(self) -> bool:
        with self._lock:
            self._waiting += 1
        try:
            return self._sem.acquire(timeout=self.max_wait_s)
        finally:
            with self._lock:
                self._waiting -= 1

    def release(self) -> None:
        try:
            self._sem.release()
        except ValueError:  # pragma: no cover - defensive
            pass


class ModelRouter:
    def __init__(self, provider: LLMProvider | None = None, *, db_factory: t.Callable[[], t.Any] | None = None):
        self.provider: LLMProvider | None = provider if provider is not None else build_provider()
        self.compact_model = settings.ai_compact_model
        self.large_model = settings.ai_large_model
        self.stats = _Stats()
        self.breaker_large = _Breaker(settings.ai_breaker_failures, settings.ai_breaker_window_s, settings.ai_breaker_open_s)
        self.breaker_compact = _Breaker(settings.ai_breaker_failures + 2, settings.ai_breaker_window_s, 30)
        self.queue_large = _Queue(settings.ai_large_concurrency, settings.ai_large_queue_wait_s)
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._db_factory = db_factory
        self.cache_ttl_s = settings.ai_cache_ttl_s

    # ------------------------------------------------------------------ status
    @property
    def live(self) -> bool:
        return self.provider is not None

    def status(self) -> dict:
        return {
            "provider_mode": "live" if self.live else "offline",
            "compact_model": self.compact_model,
            "large_model": self.large_model,
            "large_available": self.live and not self.breaker_large.is_open,
            "large_breaker_open_until": self.breaker_large.open_until_iso,
            "queue_depth": self.queue_large.depth,
            "queue_capacity": self.queue_large.capacity,
            "stats": self.stats.as_dict(),
        }

    # ------------------------------------------------------------------ cache
    def _cache_key(self, spec: TaskSpec, tier: str, inputs: dict) -> str:
        keys = spec.cache_keys or tuple(sorted(k for k in inputs.keys() if k != "history"))
        material: dict[str, t.Any] = {}
        for k in keys:
            v = inputs.get(k)
            if isinstance(v, str):
                v = normalize_text(v)
            material[k] = v
        payload = json.dumps({"task": spec.name, "tier": tier, "inputs": material}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str, db: t.Any = None) -> dict | None:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry:
                if time.time() - entry["ts"] < self.cache_ttl_s:
                    self._cache.move_to_end(key)
                    return entry
                self._cache.pop(key, None)
        if db is not None:
            row = db.fetchone("SELECT response_json, created_at FROM ai_cache WHERE cache_key = ?", (key,))
            if row:
                try:
                    created = datetime.fromisoformat(row["created_at"])
                except ValueError:
                    created = datetime.now(timezone.utc)
                if datetime.now(timezone.utc) - created < timedelta(seconds=self.cache_ttl_s):
                    db.execute("UPDATE ai_cache SET hits = hits + 1 WHERE cache_key = ?", (key,))
                    entry = {"ts": time.time(), "response": json.loads(row["response_json"])}
                    with self._cache_lock:
                        self._cache[key] = entry
                    return entry
                db.execute("DELETE FROM ai_cache WHERE cache_key = ?", (key,))
        return None

    def _cache_put(self, key: str, spec: TaskSpec, tier: str, response: dict, db: t.Any = None) -> None:
        with self._cache_lock:
            self._cache[key] = {"ts": time.time(), "response": response}
            while len(self._cache) > 512:
                self._cache.popitem(last=False)
        if db is not None:
            try:
                db.execute("DELETE FROM ai_cache WHERE cache_key = ?", (key,))
                db.execute(
                    "INSERT INTO ai_cache (cache_key, task, tier, response_json, hits, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                    (key, spec.name, tier, dumps(response), now_iso()),
                )
            except Exception as exc:  # pragma: no cover - cache must never break a request
                log.warning("cache write failed: %s", exc)

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    # ------------------------------------------------------------------ telemetry
    def _log_call(self, db: t.Any, user_id: str | None, spec: TaskSpec, ai: dict, ok: bool = True) -> None:
        self.stats.calls_total += 1
        tier = ai.get("tier")
        if ai.get("cached"):
            self.stats.cache_hits += 1
        elif ai.get("provider") == "offline":
            self.stats.calls_offline += 1
        elif tier == COMPACT:
            self.stats.calls_compact += 1
            self.stats.latency_compact.append(int(ai.get("latency_ms") or 0))
        elif tier == LARGE:
            self.stats.calls_large += 1
            self.stats.latency_large.append(int(ai.get("latency_ms") or 0))
        if ai.get("fallback"):
            self.stats.fallbacks += 1
        if not ok:
            self.stats.errors += 1
        if db is None:
            return
        try:
            db.execute(
                "INSERT INTO ai_calls (id, user_id, task, tier, model, cached, fallback, fallback_reason, latency_ms, ok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id(), user_id, spec.name, tier or "none", ai.get("model") or "", int(bool(ai.get("cached"))),
                    int(bool(ai.get("fallback"))), ai.get("fallback_reason"), int(ai.get("latency_ms") or 0), int(ok), now_iso(),
                ),
            )
        except Exception as exc:  # pragma: no cover
            log.warning("ai_calls log failed: %s", exc)

    # ------------------------------------------------------------------ provider call
    def _call_tier(self, spec: TaskSpec, tier: str, messages: list[dict[str, str]]) -> LLMResult:
        assert self.provider is not None
        model = self.large_model if tier == LARGE else self.compact_model
        breaker = self.breaker_large if tier == LARGE else self.breaker_compact
        if breaker.is_open:
            raise ProviderError(f"{tier} model circuit breaker open", retryable=False)
        attempts = settings.ai_max_retries + 1
        delay = 0.8
        last_exc: ProviderError | None = None
        for attempt in range(attempts):
            try:
                result = self.provider.complete(
                    model=model, messages=messages, max_tokens=spec.max_tokens, temperature=spec.temperature, json_mode=spec.json_output
                )
                breaker.record_success()
                return result
            except ProviderError as exc:
                last_exc = exc
                log.warning("%s call failed (attempt %d/%d): %s", tier, attempt + 1, attempts, exc)
                if not exc.retryable or attempt == attempts - 1:
                    break
                time.sleep(min(exc.retry_after or delay, 10.0))
                delay *= 2.5
        breaker.record_failure()
        assert last_exc is not None
        raise last_exc

    def _parse(self, spec: TaskSpec, text: str) -> t.Any:
        if not spec.json_output:
            return {"text": text}
        data = extract_json(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"items": data}
        # JSON expected but not returned: keep the raw text usable
        return {"_raw": text}

    # ------------------------------------------------------------------ main entry point
    def run(self, task: str, inputs: dict, *, user_id: str | None = None, db: t.Any = None, prefer_tier: str | None = None) -> AIOutput:
        spec = TASKS[task]
        tier = prefer_tier or spec.resolve_tier(inputs)
        language = inputs.get("language") or inputs.get("preferred_language") or "en"
        notice_lang = language if language in offline.NOTICE else "en"

        # 1) offline mode -------------------------------------------------------
        if not self.live:
            data = offline.OFFLINE_GENERATORS[task](inputs)
            ai = {
                "tier": "none", "model": "rules", "provider": "offline", "cached": False, "fallback": True,
                "fallback_reason": "no_api_key", "latency_ms": 0, "intended_tier": tier, "notice": offline.NOTICE[notice_lang],
            }
            self._log_call(db, user_id, spec, ai)
            return AIOutput(data=data, ai=ai)

        # 2) cache ------------------------------------------------------------------
        cache_key = self._cache_key(spec, tier, inputs) if spec.cacheable else None
        if cache_key:
            hit = self._cache_get(cache_key, db)
            if hit:
                ai = dict(hit["response"]["ai"])
                ai.update({"cached": True, "latency_ms": 0, "notice": None})
                self._log_call(db, user_id, spec, ai)
                return AIOutput(data=hit["response"]["data"], ai=ai)

        messages = prompts.PROMPT_BUILDERS[task](inputs)
        if settings.ai_log_prompts:  # never on by default: prompts may contain learner text
            log.debug("prompt[%s/%s]: %s", task, tier, dumps(messages)[:2000])

        fallback_reason: str | None = None
        attempted_tier = tier
        result: LLMResult | None = None

        # 3) large tier: breaker + queue ----------------------------------------------
        if tier == LARGE:
            if self.breaker_large.is_open:
                fallback_reason, tier = "large_unavailable", COMPACT
            elif not self.queue_large.acquire():
                fallback_reason, tier = "queue_full", COMPACT
            else:
                try:
                    result = self._call_tier(spec, LARGE, messages)
                except ProviderError as exc:
                    fallback_reason = "rate_limited" if exc.status == 429 else "large_unavailable"
                    tier = COMPACT
                finally:
                    self.queue_large.release()

        # 4) compact tier (primary or fallback) ----------------------------------------
        if result is None:
            try:
                result = self._call_tier(spec, COMPACT, messages)
            except ProviderError as exc:
                # 5) last resort: offline generators, clearly labelled
                log.error("all model tiers failed for %s: %s", task, exc)
                data = offline.OFFLINE_GENERATORS[task](inputs)
                ai = {
                    "tier": "none", "model": "rules", "provider": "offline", "cached": False, "fallback": True,
                    "fallback_reason": fallback_reason or ("rate_limited" if exc.status == 429 else "provider_error"),
                    "latency_ms": 0, "intended_tier": attempted_tier,
                    "notice": _notice("provider_down", notice_lang),
                }
                self._log_call(db, user_id, spec, ai, ok=False)
                return AIOutput(data=data, ai=ai)

        data = self._parse(spec, result.text)
        ai = {
            "tier": tier,
            "model": result.model,
            "provider": "live",
            "cached": False,
            "fallback": tier != attempted_tier,
            "fallback_reason": fallback_reason,
            "latency_ms": result.latency_ms,
            "intended_tier": attempted_tier,
            "notice": _notice(fallback_reason, notice_lang) if fallback_reason else None,
        }
        self._log_call(db, user_id, spec, ai)
        if cache_key and "_raw" not in data:
            self._cache_put(cache_key, spec, tier, {"data": data, "ai": ai}, db)
        return AIOutput(data=data, ai=ai, raw_text=result.text)


_NOTICES = {
    "large_unavailable": {
        "en": "The large model is temporarily unavailable, so this answer was produced by the faster compact model. It may be less detailed.",
        "fr": "Le grand modèle est temporairement indisponible : cette réponse provient du modèle compact, plus rapide mais parfois moins détaillé.",
        "ar": "النموذج الكبير غير متاح مؤقتاً، لذا أُنتجت هذه الإجابة بالنموذج المدمج الأسرع، وقد تكون أقل تفصيلاً.",
        "tn": "الموديل الكبير موش متاح توا، الجواب هذا خرج من الموديل الصغير الأسرع، يمكن يكون أقل تفصيل.",
    },
    "rate_limited": {
        "en": "The usage limit of the large model was reached; the compact model answered instead. Please retry later for a more detailed answer.",
        "fr": "La limite d'utilisation du grand modèle est atteinte ; le modèle compact a répondu. Réessayez plus tard pour une réponse plus détaillée.",
        "ar": "تم الوصول إلى حد استخدام النموذج الكبير؛ أجاب النموذج المدمج بدلاً منه. أعد المحاولة لاحقاً للحصول على إجابة أكثر تفصيلاً.",
        "tn": "وصلنا للحدّ الأقصى متاع الموديل الكبير؛ جاوب الموديل الصغير عوضو. عاود جرّب بعد شوية باش تاخذ جواب أدقّ.",
    },
    "queue_full": {
        "en": "Many learners are using the large model right now; to avoid a long wait the compact model answered. You can ask again in a moment.",
        "fr": "Beaucoup d'apprenants utilisent le grand modèle en ce moment ; pour éviter l'attente, le modèle compact a répondu. Vous pouvez redemander dans un instant.",
        "ar": "يستخدم كثير من المتعلمين النموذج الكبير الآن؛ لتجنب الانتظار الطويل أجاب النموذج المدمج. يمكنك السؤال مجدداً بعد لحظات.",
        "tn": "برشا ناس يستعملو الموديل الكبير توا؛ باش ما تستنّاش برشا جاوب الموديل الصغير. تنجم تعاود تسأل بعد شوية.",
    },
    "provider_down": {
        "en": "The AI service is not reachable at the moment. EdNova switched to its built-in offline mode so you can keep working; please retry in a few minutes.",
        "fr": "Le service d'IA est injoignable pour le moment. EdNova est passé en mode hors ligne intégré pour vous laisser continuer ; réessayez dans quelques minutes.",
        "ar": "خدمة الذكاء الاصطناعي غير متاحة حالياً. انتقل EdNova إلى وضعه المدمج دون اتصال لتتمكن من المتابعة؛ أعد المحاولة بعد بضع دقائق.",
        "tn": "خدمة الـ AI موش متاحة توا. EdNova عدّى للوضع المدمج بلاش اتصال باش تكمّل خدمتك؛ عاود جرّب بعد دقايق.",
    },
}


def _notice(reason: str | None, language: str) -> str | None:
    if not reason or reason not in _NOTICES:
        return None
    table = _NOTICES[reason]
    return table.get(language, table["en"])


router = ModelRouter()


def get_router() -> ModelRouter:
    return router
