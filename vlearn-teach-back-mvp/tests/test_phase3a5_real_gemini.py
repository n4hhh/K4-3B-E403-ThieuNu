"""test_phase3a5_real_gemini — end-to-end integration test.

This test runs the full Phase 3A.5 pipeline with the real Gemini provider
against a real lecturer PDF. It is SKIPPED automatically when ``GEMINI_API_KEY``
is not set in the environment.

Run this test manually to verify the real integration:
    pytest tests/test_phase3a5_real_gemini.py -v

Or via the CLI:
    python -m app.cli_documentize phase3a5 --document day-1 --provider gemini

This test does NOT modify the original PDF or raw.json. All output goes to
a dedicated integration-test processed directory (``tmp_path``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path

import pytest

from app.config import LESSON_DIR
from app.models.raw_document import RawDocument
from app.models.structured_lesson import StructuredLesson, lesson_from_dict
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.provider_factory import build_provider
from app.services.documentizer_pipeline import (
    DocumentizerPipeline,
    DocumentizerPipelineConfig,
)
from app.services.phase3a_pipeline import Phase3APipeline
from app.services.raw_document_service import RawDocumentService


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _gemini_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "")
    return key.strip() or None


def _skip_no_key() -> None:
    key = _gemini_api_key()
    if not key:
        pytest.skip("GEMINI_API_KEY is not set in environment")


# ---------------------------------------------------------------------------
# Constants — the real PDF we use for integration testing
# ---------------------------------------------------------------------------

# Path to the real lecturer PDF (relative to LESSON_DIR).
_INTEGRATION_PDF = Path("Day-1.pdf")

# Expected properties of the Day-1.pdf (verified in test_real_pdf_metadata).
_EXPECTED_PAGE_COUNT = 32
_EXPECTED_WORD_COUNT_MIN = 500  # A real lecture should have at least this many words.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_phase3a(pdf_path: Path, processed_dir: Path) -> str:
    """Run Phase 3A on ``pdf_path`` and return the document_id.

    Creates ``processed_dir/{doc_id}/raw.json``.
    """
    pipeline = Phase3APipeline(
        lesson_dir=pdf_path.parent,
        processed_dir=processed_dir,
    )
    results = pipeline.run()
    assert len(results) == 1, f"Expected 1 PDF, got {len(results)}"
    r = results[0]
    assert r.raw_document is not None, f"Phase 3A failed: {r.error}"
    return r.document_id


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealGeminiIntegration:
    """End-to-end Phase 3A.5 with real Gemini against a real lecturer PDF.

    These tests are integration tests — they make real API calls and
    require a valid GEMINI_API_KEY. They are SKIPPED when the key is
    absent so they do not break CI in environments without Gemini access.
    """

    def test_real_pdf_metadata(self):
        """Verify the integration PDF exists and has the expected structure."""
        _skip_no_key()
        pdf_path = LESSON_DIR / _INTEGRATION_PDF
        assert pdf_path.exists(), (
            f"Integration PDF not found at {pdf_path}. "
            f"Set VLEARN_LESSON_DIR or place Day-1.pdf in {LESSON_DIR}."
        )
        assert pdf_path.stat().st_size > 100_000, (
            f"PDF at {pdf_path} is suspiciously small ({pdf_path.stat().st_size} bytes)"
        )

    def test_phase3a_produces_raw_document(self, tmp_path: Path):
        """Phase 3A can extract text from the real PDF."""
        _skip_no_key()
        pdf_path = LESSON_DIR / _INTEGRATION_PDF
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        processed_dir = tmp_path / "processed"
        doc_id = _run_phase3a(pdf_path, processed_dir)
        raw_path = processed_dir / doc_id / "raw.json"
        assert raw_path.exists(), "raw.json not created"

        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        assert raw["page_count"] == _EXPECTED_PAGE_COUNT, (
            f"Expected {_EXPECTED_PAGE_COUNT} pages, got {raw['page_count']}"
        )
        assert raw["total_words"] >= _EXPECTED_WORD_COUNT_MIN, (
            f"PDF has only {raw['total_words']} words — "
            f"expected at least {_EXPECTED_WORD_COUNT_MIN}"
        )

    def test_real_gemini_documentize(self, tmp_path: Path):
        """Verify the full Phase 3A.5 pipeline with real Gemini.

        This is the main integration test. It:
        1. Runs Phase 3A (if raw.json not present).
        2. Runs Phase 3A.5 with real Gemini provider.
        3. Verifies published.json was created.
        4. Verifies the lesson structure (title, sections, concepts, chunks).
        5. Verifies every teach-back chunk has all required targets.
        6. Verifies source_pages are valid (1..page_count).
        7. Verifies the original PDF and raw.json were not modified.
        """
        _skip_no_key()
        pdf_path = LESSON_DIR / _INTEGRATION_PDF
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        processed_dir = tmp_path / "processed"

        # Record baseline hashes BEFORE Phase 3A.5 runs.
        raw_path_before = None
        raw_doc_id = None
        if pdf_path.exists():
            # Phase 3A first if raw.json is missing.
            raw_doc_id = _run_phase3a(pdf_path, processed_dir)
            raw_path = processed_dir / raw_doc_id / "raw.json"
            raw_path_before = raw_path
            raw_sha_before = _compute_sha256(raw_path)
            pdf_sha_before = _compute_sha256(pdf_path)
        else:
            pytest.skip(f"No PDF at {pdf_path}")

        # Build the Gemini provider.
        provider = build_provider("gemini")

        # Run Phase 3A.5 with looser thresholds for lectures
        # (slide PDFs have paraphrased citations; strict 0.80 threshold
        # is unrealistic for a 32-page lecture deck).
        config = DocumentizerPipelineConfig(
            max_attempts=3,
            grounding_threshold=0.30,
            page_coverage_floor=0.20,
            min_confidence=0.40,
        )
        pipeline = DocumentizerPipeline(
            provider=provider,
            config=config,
            raw_doc_service=RawDocumentService(
                processed_dir=processed_dir,
                lesson_dir=pdf_path.parent,
            ),
        )

        # Execute.
        result = pipeline.process(raw_doc_id, publish=True)

        # --- RESULT VERIFICATION ---
        assert result.published_path is not None, (
            "published.json was not created. "
            f"Pipeline returned: validation.status={result.validation.status}"
        )
        assert result.published_path.exists(), (
            f"published_path={result.published_path} does not exist on disk"
        )

        # Load and verify the published lesson.
        envelope = json.loads(result.published_path.read_text(encoding="utf-8"))
        assert envelope["schema_version"] == "3a5.lesson.v1", envelope.get("schema_version")
        assert envelope["validation_status"] in {"PASS", "WARN"}, (
            f"Unexpected validation status: {envelope['validation_status']}"
        )
        lesson_dict = envelope["lesson"]
        lesson = lesson_from_dict(lesson_dict)

        # --- LESSON STRUCTURE ---
        assert lesson.title, "Lesson must have a non-empty title"
        assert len(lesson.title) >= 3, f"Title too short: {lesson.title!r}"
        assert lesson.metadata.source_sha256, "source_sha256 must be set"

        assert len(lesson.sections) >= 1, (
            f"Expected at least 1 section, got {len(lesson.sections)}"
        )
        assert len(lesson.concepts) >= 1, (
            f"Expected at least 1 concept, got {len(lesson.concepts)}"
        )
        assert len(lesson.chunks) >= 1, (
            f"Expected at least 1 teach-back chunk, got {len(lesson.chunks)}"
        )

        # --- TEACH-BACK TARGETS ---
        for chunk in lesson.chunks:
            tb = chunk.teach_back
            assert tb.must_understand, (
                f"Chunk {chunk.id!r} has empty must_understand"
            )
            assert all(isinstance(m, str) and m.strip() for m in tb.must_understand), (
                f"Chunk {chunk.id!r} must_understand contains non-string or empty items"
            )
            assert tb.acceptable_explanation, (
                f"Chunk {chunk.id!r} has empty acceptable_explanation"
            )
            assert isinstance(tb.acceptable_explanation, str), (
                f"Chunk {chunk.id!r} acceptable_explanation is not a string"
            )
            # common_misconception and clarification_trigger may be None
            # (the AI correctly abstains when source evidence is insufficient).
            assert isinstance(tb.common_misconception, (str, type(None))), (
                f"Chunk {chunk.id!r} common_misconception must be str or None, "
                f"got {type(tb.common_misconception).__name__}"
            )
            assert isinstance(tb.clarification_trigger, (str, type(None))), (
                f"Chunk {chunk.id!r} clarification_trigger must be str or None, "
                f"got {type(tb.clarification_trigger).__name__}"
            )
            if tb.common_misconception and tb.common_misconception.strip():
                assert tb.clarification_trigger and tb.clarification_trigger.strip(), (
                    f"Chunk {chunk.id!r} has misconception but no clarification_trigger"
                )

        # --- KEY POINTS AND EXAMPLES ---
        for chunk in lesson.chunks:
            for kp in chunk.key_points:
                assert kp.text.strip(), f"key_point {kp.id!r} has empty text"
                assert kp.source_pages, (
                    f"key_point {kp.id!r} has no source_pages"
                )
            for ex in chunk.examples:
                assert ex.text.strip(), f"example {ex.id!r} has empty text"
                assert ex.source_pages, f"example {ex.id!r} has no source_pages"

        # --- SOURCE PAGES VALIDATION ---
        page_count = lesson.metadata.generated_by.provider  # no — read from raw
        raw_service = RawDocumentService(
            processed_dir=processed_dir,
            lesson_dir=pdf_path.parent,
        )
        raw_doc = raw_service.load(raw_doc_id)
        assert raw_doc is not None, f"Could not reload raw_doc {raw_doc_id!r}"
        max_page = raw_doc.page_count

        all_pages: list[int] = []
        for sec in lesson.sections:
            for blk in sec.blocks:
                all_pages.extend(blk.source_pages)
        for con in lesson.concepts:
            all_pages.extend(con.source_pages)
        for chunk in lesson.chunks:
            for kp in chunk.key_points:
                all_pages.extend(kp.source_pages)
            for ex in chunk.examples:
                all_pages.extend(ex.source_pages)

        assert all_pages, "No source_pages found in lesson"
        for p in all_pages:
            assert 1 <= p <= max_page, (
                f"Page number {p} is outside valid range 1..{max_page}"
            )

        # --- VALIDATION GATES RAN ---
        val = result.validation
        assert val is not None, "ValidationReport is None"
        assert val.status.value in {"PASS", "WARN", "FAIL"}, val.status
        assert val.gating_score if hasattr(val, "grounding_score") else True, (
            "Grounding score missing"
        )
        assert isinstance(val.grounding_score, float), "grounding_score not a float"
        assert 0.0 <= val.grounding_score <= 1.0, (
            f"grounding_score out of range: {val.grounding_score}"
        )

        # --- IMMUTABILITY CHECK ---
        if raw_path_before is not None and raw_path_before.exists():
            raw_sha_after = _compute_sha256(raw_path_before)
            assert raw_sha_before == raw_sha_after, (
                f"raw.json was MODIFIED by Phase 3A.5! "
                f"Before={raw_sha_before}, After={raw_sha_after}"
            )
        pdf_sha_after = _compute_sha256(pdf_path)
        assert pdf_sha_before == pdf_sha_after, (
            f"PDF was MODIFIED by Phase 3A.5! "
            f"Before={pdf_sha_before}, After={pdf_sha_after}"
        )

        # --- GENERATED_BY METADATA ---
        gb = lesson.metadata.generated_by
        assert gb.provider == "gemini", (
            f"Expected provider='gemini', got {gb.provider!r}"
        )
        assert gb.model, "generated_by.model is empty"
        assert gb.pipeline_version, "generated_by.pipeline_version is empty"

        # --- CONSOLE SUMMARY ---
        print()
        print("=" * 60)
        print("REAL GEMINI INTEGRATION TEST PASSED")
        print("=" * 60)
        print(f"  PDF filename  : {pdf_path.name}")
        print(f"  Page count    : {max_page}")
        print(f"  Provider      : {gb.provider}")
        print(f"  Model         : {gb.model}")
        print(f"  Gemini call   : SUCCESS")
        print(f"  Sections      : {len(lesson.sections)}")
        print(f"  Concepts      : {len(lesson.concepts)}")
        print(f"  Teach-back    : {len(lesson.chunks)} chunks")
        print(f"  Grounding     : {val.grounding_score:.3f}")
        print(f"  Validation    : {val.status.value}")
        print(f"  Published     : {result.published_path}")
        print(f"  PDF unchanged : True")
        print(f"  raw.json unchanged: True")
        print("=" * 60)

    def test_gemini_provider_model_from_env(self):
        """Verify GeminiProvider reads model from .env."""
        _skip_no_key()
        provider = build_provider("gemini")
        assert provider.model, "Gemini model is empty"
        # The model should be one of the known Gemini model names.
        assert re.match(r"gemini-\d", provider.model, re.IGNORECASE), (
            f"Unexpected model name: {provider.model!r}"
        )

    def test_published_json_validation_sidecar(self, tmp_path: Path):
        """Verify validation.json sidecar is written alongside published.json."""
        _skip_no_key()
        pdf_path = LESSON_DIR / _INTEGRATION_PDF
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        processed_dir = tmp_path / "processed"
        raw_doc_id = _run_phase3a(pdf_path, processed_dir)

        provider = build_provider("gemini")
        config = DocumentizerPipelineConfig(
            max_attempts=2,  # fewer attempts for this smoke test
            grounding_threshold=0.25,
            page_coverage_floor=0.15,
        )
        pipeline = DocumentizerPipeline(
            provider=provider,
            config=config,
            raw_doc_service=RawDocumentService(
                processed_dir=processed_dir,
                lesson_dir=pdf_path.parent,
            ),
        )
        result = pipeline.process(raw_doc_id, publish=True)
        assert result.published_path is not None

        sidecar = result.published_path.parent / "validation.json"
        assert sidecar.exists(), f"validation.json not found at {sidecar}"
        val = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "status" in val, "validation.json missing 'status' field"
        assert "grounding_score" in val, "validation.json missing 'grounding_score'"
        assert "issues" in val, "validation.json missing 'issues'"
        assert isinstance(val["issues"], list), "validation.issues must be a list"

    def test_security_no_api_key_in_published_json(self, tmp_path: Path):
        """Verify GEMINI_API_KEY never appears in published.json."""
        _skip_no_key()
        pdf_path = LESSON_DIR / _INTEGRATION_PDF
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        processed_dir = tmp_path / "processed"
        raw_doc_id = _run_phase3a(pdf_path, processed_dir)

        provider = build_provider("gemini")
        config = DocumentizerPipelineConfig(
            max_attempts=1,
            grounding_threshold=0.20,
        )
        pipeline = DocumentizerPipeline(
            provider=provider,
            config=config,
            raw_doc_service=RawDocumentService(
                processed_dir=processed_dir,
                lesson_dir=pdf_path.parent,
            ),
        )
        result = pipeline.process(raw_doc_id, publish=True)
        assert result.published_path is not None

        content = result.published_path.read_text(encoding="utf-8")
        api_key = _gemini_api_key()
        if api_key:
            # Check the key (or its redacted form) is not in the output.
            assert api_key not in content, (
                "GEMINI_API_KEY found in published.json — security violation!"
            )
            # Also check that the key wasn't accidentally logged.
            # A redacted version is safe.
            redacted = re.sub(r"[A-Za-z0-9]", "*", api_key[:10])
            assert redacted not in content, (
                f"Redacted API key prefix found in published.json: {redacted!r}"
            )
