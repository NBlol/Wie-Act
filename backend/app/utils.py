"""Small shared helpers."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import string
import typing as t
import uuid
from datetime import datetime, timezone

SUPPORTED_LANGUAGES = ("en", "fr", "ar", "tn")
LEARNING_STYLES = ("visual", "analogy", "step_by_step", "examples", "repetition", "problem_solving")
LEVELS = ("beginner", "intermediate", "advanced")

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "ar": "Modern Standard Arabic",
    "tn": "Tunisian Darija (Tunisian Arabic dialect)",
}


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def today_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def dumps(obj: t.Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(raw: str | None, default: t.Any = None) -> t.Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def room_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_ws = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalisation used for cache keys: equivalent requests must collide."""
    return _ws.sub(" ", text.strip().lower()).strip(" .!?؟،,;:")


_ARABIC = re.compile(r"[؀-ۿ]")
_FRENCH_HINTS = re.compile(
    r"\b(le|la|les|des|une|un|est|et|pour|avec|dans|que|qui|pas|je|tu|nous|vous|comment|pourquoi|expliquer|explique|exercice|cours)\b",
    re.I,
)
_DARIJA_HINTS = re.compile(
    r"(شنوة|شنوّة|كيفاش|علاش|برشا|باهي|نحب|تنجم|نجم|توا|ياخي|وقتاش|فمة|مريقل|يعيشك|برشة|chnowa|chnoua|kifech|kifeh|3lech|barcha|bahi|n7eb|tnajem|yezzi|y3ayechek|famma|chbih|chbik)",
    re.I,
)
_LATIN_ARABIZI = re.compile(r"[a-z]*[2379][a-z]+|[a-z]+[2379][a-z]*", re.I)


def detect_language(text: str, fallback: str = "en") -> str:
    """Heuristic language detection (no model call).

    Script-based for Arabic vs Latin, lexical hints for Tunisian Darija and
    French. Used to seed the prompt language and as the offline fallback for
    the compact-model triage step.
    """
    if not text or not text.strip():
        return fallback
    if _ARABIC.search(text):
        return "tn" if _DARIJA_HINTS.search(text) else "ar"
    if _DARIJA_HINTS.search(text) or len(_LATIN_ARABIZI.findall(text)) >= 2:
        return "tn"
    if len(_FRENCH_HINTS.findall(text)) >= 2 or re.search(r"[éèêàçùœ]", text):
        return "fr"
    return "en" if re.search(r"[a-zA-Z]", text) else fallback


def extract_json(text: str) -> t.Any:
    """Extract the first JSON object/array from a model response (robust to prose / code fences)."""
    if text is None:
        return None
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except ValueError:
                        break
    return None


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
