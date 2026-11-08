"""
Lexical retrieval (BM25, Okapi variant) implemented in pure Python.

Why BM25 and not dense embeddings? The challenge platform offers no embedding
endpoint and no fine-tuning; BM25 runs locally in milliseconds, needs no model
call, works for Arabic/French/English tokens alike, and narrows the context
handed to the language model – which is exactly the "retrieval before
generation" purpose described in the brief.  An embedding provider can be
plugged in later behind the same `search()` interface (hybrid scoring).
"""
from __future__ import annotations

import math
import re
import typing as t
import unicodedata
from collections import Counter

_TOKEN = re.compile(r"[\w؀-ۿ]+", re.UNICODE)
_ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")

STOPWORDS = {
    # English
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "were", "be", "it", "this",
    "that", "these", "those", "as", "by", "at", "from", "but", "not", "what", "which", "who", "how", "why", "when", "do",
    "does", "can", "will", "we", "you", "they", "i", "he", "she", "my", "your", "our",
    # French
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "en", "dans", "pour", "par", "sur", "avec", "est", "sont",
    "ce", "cette", "ces", "que", "qui", "quoi", "comment", "pourquoi", "pas", "ne", "se", "au", "aux", "il", "elle", "nous", "vous",
    # Arabic (MSA + Tunisian)
    "في", "من", "على", "إلى", "الى", "عن", "أن", "ان", "ما", "هو", "هي", "هذا", "هذه", "ذلك", "التي", "الذي", "كان", "مع", "أو", "او",
    "و", "ثم", "لا", "نعم", "كل", "شنوة", "شنوّة", "كيفاش", "علاش", "برشا", "باهي", "متاع", "إلّي", "اللي", "الي",
}


def normalize_token(token: str) -> str:
    token = unicodedata.normalize("NFKC", token).lower()
    token = _ARABIC_DIACRITICS.sub("", token)
    token = token.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    if not re.search(r"[؀-ۿ]", token):  # strip Latin accents (é → e)
        token = "".join(c for c in unicodedata.normalize("NFD", token) if unicodedata.category(c) != "Mn")
    if token.startswith("ال") and len(token) > 4:
        token = token[2:]
    # light stemming (plural / verb endings)
    for suffix in ("ing", "tion", "ments", "ment", "ées", "ée", "és", "es", "s", "ات", "ين", "ون", "ها", "هم"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _TOKEN.findall(text or ""):
        tok = normalize_token(raw)
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        tokens.append(tok)
    return tokens


class BM25Index:
    def __init__(self, documents: t.Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(d) for d in documents]
        self.doc_len = [len(toks) for toks in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.tf = [Counter(toks) for toks in self.doc_tokens]
        df: Counter[str] = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        n = len(documents)
        self.idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def __len__(self) -> int:
        return len(self.doc_tokens)

    def scores(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        out = [0.0] * len(self.doc_tokens)
        if not q_tokens or not self.doc_tokens:
            return out
        for i, tf in enumerate(self.tf):
            dl = self.doc_len[i]
            s = 0.0
            for term in q_tokens:
                f = tf.get(term)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                s += idf * f * (self.k1 + 1) / denom
            out[i] = s
        return out

    def search(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        """Return [(doc_index, normalised_score 0..1)] sorted by relevance (only positive matches)."""
        raw = self.scores(query)
        best = max(raw) if raw else 0.0
        ranked = sorted(((i, s) for i, s in enumerate(raw) if s > 0), key=lambda x: -x[1])[:k]
        if best <= 0:
            return []
        return [(i, round(s / best, 4)) for i, s in ranked]
