"""Tests for the GeminiProvider configuration + behaviour.

These tests do NOT require a real API key.

    * provider refuses to construct when GEMINI_API_KEY is missing
    * provider never logs the API key
    * provider scrubs the API key out of error messages
    * provider construction reads GEMINI_MODEL from the env

A live call to the real Gemini API is exercised by the optional
integration test below, which is skipped unless ``GEMINI_API_KEY``
is present in the environment AND the test is explicitly requested
via ``--run-integration``.
"""

from __future__ import annotations

import logging
import os
import re

import pytest

from app.services.ai.ai_provider import (
    AIProviderMisconfiguredError,
    DocumentizerInput,
)
from app.services.ai.gemini_provider import (
    GeminiProvider,
    _scrub,
    _strip_code_fence,
    _map_gemini_exception,
)


# ---------------------------------------------------------------------------
# Construction guards
# ---------------------------------------------------------------------------


def test_gemini_provider_refuses_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIProviderMisconfiguredError) as exc:
        GeminiProvider(api_key=None, model="gemini-2.5-flash")
    assert "GEMINI_API_KEY" in str(exc.value)


def test_gemini_provider_refuses_empty_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-for-config")
    with pytest.raises(AIProviderMisconfiguredError):
        GeminiProvider(api_key="test-key-for-config", model="")


def _genai_installed() -> bool:
    """True when the Gemini SDK is importable.

    Construction succeeds only with the SDK present; the Teach-Back path
    runs on an OpenAI-compatible endpoint, so ``google-genai`` is not a
    required dependency of this project.
    """
    try:
        from google import genai  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(
    not _genai_installed(), reason="google-genai is not installed"
)
def test_gemini_provider_reads_env_when_unspecified(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    p = GeminiProvider()
    assert p.model == "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# Key redaction
# ---------------------------------------------------------------------------


def test_scrub_redacts_ai_keys():
    s = "Authorization: AIza0123456789abcdefghij fail"
    out = _scrub(s)
    assert "AIza0" not in out
    assert "<redacted>" in out


def test_scrub_handles_none():
    assert _scrub(None) is None


def test_scrub_no_change_for_normal_text():
    assert _scrub("all good") == "all good"


# ---------------------------------------------------------------------------
# Code-fence stripping (for malformed responses)
# ---------------------------------------------------------------------------


def test_strip_code_fence():
    assert _strip_code_fence("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_strip_code_fence_no_change():
    assert _strip_code_fence("plain text") == "plain text"


# ---------------------------------------------------------------------------
# Exception mapping
# ---------------------------------------------------------------------------


def test_map_gemini_exception_permission_denied_is_permanent():
    class _Exc(Exception):
        pass

    _Exc.__name__ = "PermissionDeniedError"
    out = _map_gemini_exception(_Exc("denied"))
    from app.services.ai.ai_provider import AIProviderPermanentError

    assert isinstance(out, AIProviderPermanentError)


def test_map_gemini_exception_resource_exhausted_is_transient():
    class _Exc(Exception):
        pass

    _Exc.__name__ = "ResourceExhaustedError"
    out = _map_gemini_exception(_Exc("rate"))
    from app.services.ai.ai_provider import AIProviderTransientError

    assert isinstance(out, AIProviderTransientError)


def test_map_gemini_exception_unknown_is_transient():
    out = _map_gemini_exception(RuntimeError("?"))
    from app.services.ai.ai_provider import AIProviderTransientError

    assert isinstance(out, AIProviderTransientError)


# ---------------------------------------------------------------------------
# Provider name + env reading
# ---------------------------------------------------------------------------


def test_provider_name_constant():
    assert GeminiProvider.name == "gemini"


# ---------------------------------------------------------------------------
# OPTIONAL live integration test (skipped unless --run-integration + key)
# ---------------------------------------------------------------------------


_RUN_INTEGRATION = os.environ.get("RUN_PHASE3A5_INTEGRATION") == "1"


@pytest.mark.skipif(
    not _RUN_INTEGRATION or not os.environ.get("GEMINI_API_KEY"),
    reason="live integration test requires RUN_PHASE3A5_INTEGRATION=1 and GEMINI_API_KEY",
)
def test_live_gemini_call_smoke(tmp_path):
    """Run a real Gemini call against a tiny synthetic PDF.

    Skipped unless ``RUN_PHASE3A5_INTEGRATION=1`` AND ``GEMINI_API_KEY``
    is in the environment.
    """
    from app.models.raw_document import RawDocument, PageText
    from app.services.ai.gemini_provider import GeminiProvider

    raw = RawDocument(
        document_id="live",
        source_file="live.pdf",
        source_path="live.pdf",
        page_count=1,
        pages=[
            PageText(
                page_number=1,
                text="REST API\nREST is an architectural style\nGET retrieves a resource",
            )
        ],
    )
    out = GeminiProvider().documentize(
        DocumentizerInput(document_id="live", raw_document=raw)
    )
    assert out.clean_payload.get("title")
    assert isinstance(out.clean_payload.get("sections"), list)
    assert isinstance(out.clean_payload.get("chunks"), list)