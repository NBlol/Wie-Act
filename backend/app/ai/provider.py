"""
Inference-platform adapters.

The challenge platform exposes two categories of models behind an HTTP API.
Two wire formats are supported out of the box and selected with `AI_API_STYLE`:

* `openai`    – OpenAI-compatible `POST {AI_BASE_URL}/chat/completions`
                (vLLM, Ollama, OpenRouter, Mistral, Groq, Azure OpenAI, …)
* `anthropic` – `POST {AI_BASE_URL}/messages` (Anthropic Messages API)

Responses are returned as a whole (no streaming), exactly as the challenge
describes. Latency is handled upstream by the router and the UI.
"""
from __future__ import annotations

import time
import typing as t
from dataclasses import dataclass

import requests

from app.config import settings


class ProviderError(Exception):
    def __init__(self, message: str, status: int | None = None, retryable: bool = False, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.retry_after = retry_after


@dataclass
class LLMResult:
    text: str
    model: str
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(t.Protocol):  # pragma: no cover - interface only
    name: str

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> LLMResult: ...


def _retry_after(resp: requests.Response) -> float | None:
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return min(float(raw), 15.0)
    except ValueError:
        return None


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, timeout_s: float, json_mode_supported: bool = False):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.json_mode_supported = json_mode_supported
        self.session = requests.Session()

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, json_mode: bool) -> LLMResult:
        payload: dict[str, t.Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if json_mode and self.json_mode_supported:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        started = time.perf_counter()
        try:
            resp = self.session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=self.timeout_s)
        except requests.Timeout as exc:
            raise ProviderError("Inference request timed out", status=None, retryable=True) from exc
        except requests.RequestException as exc:
            raise ProviderError(f"Network error: {exc}", status=None, retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        if resp.status_code in (408, 409, 425, 429, 500, 502, 503, 504):
            raise ProviderError(f"Provider returned {resp.status_code}", status=resp.status_code, retryable=True, retry_after=_retry_after(resp))
        if resp.status_code >= 400:
            raise ProviderError(f"Provider returned {resp.status_code}: {resp.text[:200]}", status=resp.status_code, retryable=False)
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed provider response", status=resp.status_code, retryable=False) from exc
        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            model=data.get("model", model),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, base_url: str, api_key: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, json_mode: bool) -> LLMResult:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        payload: dict[str, t.Any] = {"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": convo}
        if system:
            payload["system"] = system
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        started = time.perf_counter()
        try:
            resp = self.session.post(f"{self.base_url}/messages", json=payload, headers=headers, timeout=self.timeout_s)
        except requests.Timeout as exc:
            raise ProviderError("Inference request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise ProviderError(f"Network error: {exc}", retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        if resp.status_code in (408, 409, 425, 429, 500, 502, 503, 504, 529):
            raise ProviderError(f"Provider returned {resp.status_code}", status=resp.status_code, retryable=True, retry_after=_retry_after(resp))
        if resp.status_code >= 400:
            raise ProviderError(f"Provider returned {resp.status_code}: {resp.text[:200]}", status=resp.status_code, retryable=False)
        data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            model=data.get("model", model),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
        )


def build_provider() -> LLMProvider | None:
    """Return a live provider, or None when no credentials are configured (offline mode)."""
    if not settings.ai_live:
        return None
    if settings.ai_api_style.lower() == "anthropic":
        return AnthropicProvider(settings.ai_base_url, settings.ai_api_key, settings.ai_timeout_s)
    return OpenAICompatibleProvider(settings.ai_base_url, settings.ai_api_key, settings.ai_timeout_s, json_mode_supported=settings.ai_json_mode)
