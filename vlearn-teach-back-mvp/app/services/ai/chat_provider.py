"""ChatProvider — the chat-completion contract used by the Teach-Back loop.

This is deliberately separate from :mod:`app.services.ai.ai_provider`.
That one models a *document* transformation (PDF → StructuredLesson) and
is owned by the Documentizer. The teach-back loop needs something much
smaller: send a system prompt + a few turns, get a JSON object back.

Providers
---------

``openai-compatible``
    Any endpoint speaking the OpenAI ``/chat/completions`` shape. This is
    the production path for DeepSeek (``TEACH_BACK_BASE_URL=https://api.deepseek.com``).
    Reasoning models such as ``deepseek-flash`` return their scratchpad in
    ``message.reasoning_content``; we read ``message.content`` only.

``gemini``
    Uses the ``google.genai`` SDK when it is installed.

``mock``
    Deterministic, offline. Used by tests and by the "zero paid calls"
    demo mode. It never reaches the network.

Every provider reads its configuration from the environment at
construction time. Keys are never logged and are scrubbed from any error
text before it leaves this module.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ChatProviderError(Exception):
    """Base class for chat-provider failures."""


class ChatProviderTransientError(ChatProviderError):
    """Timeout, 5xx, rate limit, unparseable JSON — worth one retry."""


class ChatProviderPermanentError(ChatProviderError):
    """Bad key, unknown model, 4xx — retrying will not help."""


class ChatProviderMisconfiguredError(ChatProviderPermanentError):
    """Missing base URL / key / model at construction time."""


# Never let an API key reach a log line or an exception message.
_KEY_SCRUB_RE = re.compile(r"(sk-[0-9A-Za-z_\-]{10,}|AIza[0-9A-Za-z_\-]{20,})")


def scrub(text: Optional[str]) -> str:
    """Return ``text`` with anything that looks like an API key removed."""
    if not text:
        return ""
    return _KEY_SCRUB_RE.sub("<redacted>", text)


# ---------------------------------------------------------------------------
# I/O types
# ---------------------------------------------------------------------------


@dataclass
class ChatMessage:
    """One turn handed to the model."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResult:
    """What a provider returns.

    ``data`` is the parsed JSON object when the call asked for JSON;
    ``text`` is always the verbatim model output, kept for the session
    log so an instructor can audit what the agent actually saw.
    """

    text: str
    data: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    usage: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ChatProvider(Protocol):
    """Send messages, get a JSON object back."""

    name: str
    model: str

    def complete_json(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Run the model and parse its reply as a JSON object.

        Raises:
            ChatProviderTransientError: recoverable.
            ChatProviderPermanentError: not recoverable.
        """
        ...


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def parse_json_object(text: str) -> Dict[str, Any]:
    """Pull a JSON object out of a model reply.

    Models wrap JSON in prose or code fences often enough that a bare
    ``json.loads`` is not good enough. We try, in order: the whole
    string, the contents of a fenced block, then the outermost
    ``{...}`` span.
    """
    candidates: List[str] = [text.strip()]

    fenced = _FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())

    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ChatProviderTransientError(
        "Model reply was not a JSON object: " + scrub(text[:200])
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (DeepSeek and friends)
# ---------------------------------------------------------------------------


class OpenAICompatibleChatProvider:
    """Talks to any ``/chat/completions`` endpoint over plain HTTP.

    We use ``httpx`` directly rather than the ``openai`` SDK: it is
    already a dependency (FastAPI's TestClient pulls it in) and the
    surface we need is one POST.
    """

    name = "openai-compatible"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self._base_url = (
            base_url
            if base_url is not None
            else os.environ.get("TEACH_BACK_BASE_URL", "")
        ).strip().rstrip("/")
        self._api_key = (
            api_key if api_key is not None else os.environ.get("TEACH_BACK_API_KEY", "")
        ).strip()
        self.model = (
            model if model is not None else os.environ.get("TEACH_BACK_MODEL", "")
        ).strip()
        self._timeout = timeout_seconds or int(
            os.environ.get("TEACH_BACK_TIMEOUT", "90")
        )
        self._max_tokens = max_tokens or int(
            os.environ.get("TEACH_BACK_MAX_TOKENS", "5000")
        )

        if not self._base_url:
            raise ChatProviderMisconfiguredError(
                "TEACH_BACK_BASE_URL is not set. Add it to your .env file."
            )
        if not self._api_key:
            raise ChatProviderMisconfiguredError(
                "TEACH_BACK_API_KEY is not set. Add it to your .env file."
            )
        if not self.model:
            raise ChatProviderMisconfiguredError(
                "TEACH_BACK_MODEL is not set. Add it to your .env file."
            )

    # ------------------------------------------------------------------

    @property
    def endpoint(self) -> str:
        """Return the completions URL, tolerating a base that already
        ends in ``/v1`` (OpenAI style) or not (DeepSeek style)."""
        if self._base_url.endswith("/chat/completions"):
            return self._base_url
        return f"{self._base_url}/chat/completions"

    def complete_json(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        import httpx

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or self._max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        started = time.time()
        try:
            response = httpx.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise ChatProviderTransientError(
                f"Chat request timed out after {self._timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChatProviderTransientError(
                f"Chat request failed: {scrub(str(exc))}"
            ) from exc

        latency_ms = int((time.time() - started) * 1000)

        if response.status_code == 429 or response.status_code >= 500:
            raise ChatProviderTransientError(
                f"Provider returned {response.status_code}: "
                f"{scrub(response.text[:200])}"
            )
        if response.status_code >= 400:
            raise ChatProviderPermanentError(
                f"Provider returned {response.status_code}: "
                f"{scrub(response.text[:200])}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise ChatProviderTransientError("Provider reply was not JSON") from exc

        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ChatProviderTransientError(
                "Provider reply had no choices[0].message"
            ) from exc

        # Reasoning models (deepseek-flash) put their scratchpad in
        # ``reasoning_content``. The answer is always in ``content``.
        text = (message.get("content") or "").strip()
        if not text:
            raise ChatProviderTransientError(
                "Provider returned an empty message — the token budget was "
                "probably spent on reasoning. Raise TEACH_BACK_MAX_TOKENS."
            )

        # A truncated reply is unparseable JSON. Say why, rather than
        # letting it surface as a mysterious parse error downstream.
        finish_reason = (body.get("choices") or [{}])[0].get("finish_reason")
        if finish_reason == "length":
            raise ChatProviderTransientError(
                "Provider hit the token limit before finishing the JSON. "
                "Raise TEACH_BACK_MAX_TOKENS."
            )

        return ChatResult(
            text=text,
            data=parse_json_object(text),
            provider=self.name,
            model=self.model,
            latency_ms=latency_ms,
            usage=body.get("usage") or {},
        )


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


class GeminiChatProvider:
    """Chat provider backed by ``google.genai``.

    Kept so the project can switch back to Gemini without touching any
    caller — the teach-back services only know ``ChatProvider``.
    """

    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        ).strip()
        self.model = (
            model
            if model is not None
            else os.environ.get("TEACH_BACK_MODEL")
            or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        ).strip()
        self._max_tokens = max_tokens or int(
            os.environ.get("TEACH_BACK_MAX_TOKENS", "5000")
        )

        if not self._api_key:
            raise ChatProviderMisconfiguredError("GEMINI_API_KEY is not set.")

        try:
            from google import genai  # type: ignore
        except ImportError as exc:  # pragma: no cover - import guard
            raise ChatProviderMisconfiguredError(
                "google-genai is not installed. Either `pip install google-genai` "
                "or set TEACH_BACK_PROVIDER=openai-compatible."
            ) from exc

        self._client = genai.Client(api_key=self._api_key)

    def complete_json(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        from google.genai import types as genai_types  # type: ignore

        system = "\n\n".join(m.content for m in messages if m.role == "system")
        turns = [
            genai_types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[genai_types.Part.from_text(text=m.content)],
            )
            for m in messages
            if m.role != "system"
        ]

        started = time.time()
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=turns,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system or None,
                    temperature=temperature,
                    max_output_tokens=max_tokens or self._max_tokens,
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:  # noqa: BLE001 - SDK raises many types
            raise ChatProviderTransientError(scrub(str(exc))) from exc

        latency_ms = int((time.time() - started) * 1000)
        text = (getattr(response, "text", "") or "").strip()
        if not text:
            raise ChatProviderTransientError("Gemini returned an empty reply")

        return ChatResult(
            text=text,
            data=parse_json_object(text),
            provider=self.name,
            model=self.model,
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockChatProvider:
    """Offline provider used by tests and the no-API demo mode.

    It answers by *shape*: each caller tags its request with a
    ``"task"`` marker in the system prompt, and the mock returns a
    plausible payload for that task. The teach-back services degrade to
    their heuristic path when a field is missing, so the mock only needs
    to be well-formed, not clever.
    """

    name = "mock"

    def __init__(self, model: str = "mock-model") -> None:
        self.model = model
        self.calls: List[List[ChatMessage]] = []

    def complete_json(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        self.calls.append(list(messages))
        joined = " ".join(m.content for m in messages)

        if "TASK:ANALYZE_CHUNK" in joined:
            data: Dict[str, Any] = {
                "key_points": [
                    "Ý chính thứ nhất của phần này",
                    "Ý chính thứ hai của phần này",
                ],
                "quality_bar": "Nêu được hai ý chính bằng lời của mình.",
                "key_concepts": ["khái niệm A", "khái niệm B"],
            }
        elif "TASK:VALIDATE_EXPLANATION" in joined:
            data = {
                "covered_points": [],
                "missing_points": ["Ý chính thứ nhất của phần này"],
                "gap_type": "incomplete",
                "verdict": "gap",
                "confidence": 0.5,
                "ask_back": "Bạn giải thích rõ hơn ý đầu tiên được không?",
                "citations": [],
                "is_copied": False,
                "note_for_instructor": "mock",
            }
        elif "TASK:GENERATE_QUIZ" in joined:
            data = {
                "questions": [
                    {
                        "prompt": "Câu hỏi mẫu số %d?" % i,
                        "options": ["A", "B", "C", "D"],
                        "correct_index": 0,
                        "explanation": "Giải thích mẫu.",
                    }
                    for i in range(1, 4)
                ]
            }
        else:
            data = {}

        text = json.dumps(data, ensure_ascii=False)
        return ChatResult(
            text=text, data=data, provider=self.name, model=self.model, latency_ms=0
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


SUPPORTED_CHAT_PROVIDERS = ("openai-compatible", "deepseek", "gemini", "mock")


def build_chat_provider(name: Optional[str] = None) -> ChatProvider:
    """Return a fresh provider for ``name`` (or ``TEACH_BACK_PROVIDER``).

    ``"deepseek"`` is accepted as an alias for ``"openai-compatible"``
    so a .env written either way works.
    """
    raw = name if name is not None else os.environ.get("TEACH_BACK_PROVIDER", "mock")
    provider_name = (raw or "mock").strip().lower()

    if provider_name in ("openai-compatible", "openai_compatible", "deepseek", "openai"):
        logger.info("ChatProvider: OpenAI-compatible endpoint")
        return OpenAICompatibleChatProvider()
    if provider_name == "gemini":
        logger.info("ChatProvider: Gemini")
        return GeminiChatProvider()
    if provider_name == "mock":
        logger.info("ChatProvider: mock (no network calls)")
        return MockChatProvider()

    raise ChatProviderMisconfiguredError(
        f"Unsupported TEACH_BACK_PROVIDER={raw!r}. "
        f"Supported: {SUPPORTED_CHAT_PROVIDERS}"
    )


def build_chat_provider_safe(name: Optional[str] = None) -> ChatProvider:
    """Like :func:`build_chat_provider` but never raises.

    A misconfigured key must not take the whole app down — the demo has
    to stay clickable. We fall back to the mock provider and log loudly.
    """
    try:
        return build_chat_provider(name)
    except ChatProviderError as exc:
        logger.warning(
            "Chat provider unavailable (%s) — falling back to mock. "
            "The teach-back loop will use heuristics only.",
            scrub(str(exc)),
        )
        return MockChatProvider()


__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatProviderError",
    "ChatProviderMisconfiguredError",
    "ChatProviderPermanentError",
    "ChatProviderTransientError",
    "ChatResult",
    "GeminiChatProvider",
    "MockChatProvider",
    "OpenAICompatibleChatProvider",
    "SUPPORTED_CHAT_PROVIDERS",
    "build_chat_provider",
    "build_chat_provider_safe",
    "parse_json_object",
    "scrub",
]
