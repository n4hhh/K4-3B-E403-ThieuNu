"""Tests for the AIProvider abstraction + MockProvider.

Covers:

    * coerce_provider_name accepts supported names + rejects unknown
    * MockProvider returns a deterministic CleanDocument
    * MockProvider strips noise (page numbers, footers, dates)
    * Documentizer retries on transient errors and gives up after N
    * Documentizer fails fast on permanent errors
"""

from __future__ import annotations

import json

import pytest

from app.models.raw_document import PageText, RawDocument
from app.services.ai.ai_provider import (
    AIProviderMisconfiguredError,
    AIProviderPermanentError,
    AIProviderTransientError,
    DocumentizerInput,
    coerce_provider_name,
)
from app.services.ai.documentizer import Documentizer, DocumentizerConfig
from app.services.ai.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# coerce_provider_name
# ---------------------------------------------------------------------------


def test_coerce_provider_name_default_is_gemini():
    assert coerce_provider_name(None) == "gemini"
    assert coerce_provider_name("") == "gemini"
    assert coerce_provider_name("GEMINI") == "gemini"
    assert coerce_provider_name("mock") == "mock"


def test_coerce_provider_name_rejects_unknown():
    with pytest.raises(AIProviderMisconfiguredError):
        coerce_provider_name("openai")


# ---------------------------------------------------------------------------
# MockProvider noise removal
# ---------------------------------------------------------------------------


def _two_page_raw() -> RawDocument:
    return RawDocument(
        document_id="d",
        source_file="d.pdf",
        source_path="d.pdf",
        page_count=2,
        pages=[
            PageText(
                page_number=1,
                text=(
                    "REST API Introduction\n"
                    "REST is an architectural style\n"
                    "Page 1\n"
                    "VLearn © 2026"
                ),
            ),
            PageText(page_number=2, text="HTTP Methods\nGET retrieves a resource"),
        ],
    )


def test_mock_provider_returns_clean_document():
    raw = _two_page_raw()
    out = MockProvider().documentize(DocumentizerInput(document_id="d", raw_document=raw))
    assert "sections" in out.clean_payload
    assert "concepts" in out.clean_payload
    assert "removed_noise" in out.clean_payload
    kinds = {r["kind"] for r in out.clean_payload["removed_noise"]}
    # At least page-number and footer noise should be removed.
    assert "page_number" in kinds or "footer" in kinds


def test_mock_provider_blocks_carry_provenance():
    raw = _two_page_raw()
    out = MockProvider().documentize(DocumentizerInput(document_id="d", raw_document=raw))
    for sec in out.clean_payload["sections"]:
        for blk in sec["blocks"]:
            assert blk["source_pages"], f"block {blk['id']} missing source_pages"
            assert blk["citation"], f"block {blk['id']} missing citation"


# ---------------------------------------------------------------------------
# Documentizer retries
# ---------------------------------------------------------------------------


class _AlwaysTransientProvider:
    """A provider that always raises transient errors."""

    name = "mock"
    model = "always-transient"

    def __init__(self):
        self.calls = 0

    def documentize(self, input):
        self.calls += 1
        raise AIProviderTransientError(f"transient #{self.calls}")


def test_documentizer_gives_up_after_max_attempts():
    prov = _AlwaysTransientProvider()
    d = Documentizer(prov, DocumentizerConfig(max_attempts=3, backoff_seconds=0))
    with pytest.raises(AIProviderTransientError):
        d.documentize(_two_page_raw())
    assert prov.calls == 3


class _FlakyProvider:
    """Succeeds on the Nth call."""

    name = "mock"
    model = "flaky"

    def __init__(self, succeed_on: int):
        self.succeed_on = succeed_on
        self.calls = 0

    def documentize(self, input):
        self.calls += 1
        if self.calls < self.succeed_on:
            raise AIProviderTransientError("not yet")
        return MockProvider().documentize(input)


def test_documentizer_succeeds_on_retry():
    prov = _FlakyProvider(succeed_on=2)
    d = Documentizer(prov, DocumentizerConfig(max_attempts=3, backoff_seconds=0))
    result = d.documentize(_two_page_raw())
    assert result.attempts == 2


class _PermanentProvider:
    name = "mock"
    model = "permanent"

    def documentize(self, input):
        raise AIProviderPermanentError("nope")


def test_documentizer_fails_fast_on_permanent_error():
    prov = _PermanentProvider()
    d = Documentizer(prov, DocumentizerConfig(max_attempts=3, backoff_seconds=0))
    with pytest.raises(AIProviderPermanentError):
        d.documentize(_two_page_raw())