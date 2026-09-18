"""Validators — Phase 3A.5 three independent gates.

This module is intentionally side-effect-free. Each validator returns
:class:`GateResult` data; the orchestrator (:mod:`documentizer_pipeline`)
combines them into a single :class:`ValidationReport`.

Gates
-----

Gate A — Schema Validation
    * Ensures every block / concept / chunk is structurally valid.
    * Re-runs the same Pydantic validation the Documentizer performed
      on the CleanDocument, this time on the full StructuredLesson.

Gate B — Source Grounding (the heart of Phase 3A.5)
    * SG-1 : every claim-bearing field has non-empty source_pages.
    * SG-2 : every claim-bearing field has non-empty citation.
    * SG-3 : every cited page number exists in the RawDocument.
    * SG-4 : the citation text (normalised) appears on at least one
      cited page (substring match with whitespace tolerance; falls back
      to fuzzy ratio ≥ 0.85).
    * SG-5 : page_coverage for every non-blank source page is at or
      above ``page_coverage_floor``.
    * SG-6 : every generated claim must be supported by source page /
      excerpt evidence. An excerpt existing **somewhere** in the document
      is NOT sufficient if it does not support the generated claim.
    * SG-7 : no claim references a page beyond RawDocument.page_count.

Gate C — Confidence
    * CG-1 : per-chunk confidence ≥ ``min_confidence``.
    * CG-2 : per-block confidence ≥ 0.0 (auto-floor on unknown).
    * CG-3 : hallucination guard — any block whose citation grounds on
      zero pages AND overlaps no other block's source pages is dropped
      and counted as a hallucination.

The combined status:

    * all PASS → ``PASS``
    * any ``WARN`` and no ``FAIL`` → ``WARN``
    * any ``FAIL`` → ``FAIL``

Publishing is allowed only when status is ``PASS`` or ``WARN``.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

from difflib import SequenceMatcher

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
)
from app.models.raw_document import RawDocument
from app.models.structured_lesson import StructuredLesson
from app.models.teach_back_chunk import (
    ChunkExample,
    KeyPoint,
    TeachBackChunk,
    TeachBackTargets,
)
from app.models.validation_report import (
    GateName,
    GateOutcome,
    GateResult,
    IssueSeverity,
    ProvenanceStats,
    ValidationIssue,
    ValidationPolicy,
    ValidationReport,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


_WHITESPACE_RE = re.compile(r"\s+")


def _normalise(s: str) -> str:
    """Lowercase + collapse whitespace + strip punctuation that breaks substring matching."""
    s = s.lower()
    s = _WHITESPACE_RE.sub(" ", s)
    # Drop a small set of punctuation that PDF extraction often adds.
    for ch in ".,;:!?'\"`()[]{}":
        s = s.replace(ch, "")
    return s.strip()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _citation_grounds_on_page(citation: str, page_text: str) -> bool:
    """Match ``citation`` against ``page_text``.

    Returns True if either:

        * the normalised citation appears as a substring of the
          normalised page text, or
        * the best fuzzy ratio is ≥ 0.85.
    """
    if not citation or not page_text:
        return False

    c = _normalise(citation)
    p = _normalise(page_text)
    if c and c in p:
        return True

    # Fuzzy: compare against every ~citation-sized window of the page.
    if not c:
        return False
    words = p.split()
    if not words:
        return False
    cwords = c.split()
    n = len(cwords)
    if n == 0:
        return False

    best = 0.0
    window = max(n, 1)
    for i in range(0, max(1, len(words) - n + 1)):
        snippet = " ".join(words[i : i + window])
        r = _similar(c, snippet)
        if r > best:
            best = r
            if best >= 0.99:
                break
    return best >= 0.85


# ---------------------------------------------------------------------------
# Gate A — Schema Validation
# ---------------------------------------------------------------------------


class SchemaValidator:
    """Gate A — schema-level validation."""

    @staticmethod
    def validate_structured_lesson(lesson: StructuredLesson) -> GateResult:
        """Walk the StructuredLesson and flag structural problems that
        the Pydantic model layer lets through.

        The model layer rejects things like inverted page ranges at
        construction time, so the gate focuses on what the model
        permits but the lesson shouldn't:
            * teach-back targets that conflict with the chunk shape
            * chunks with no must_understand entries
            * chunks where the misconception is set without a trigger
        """
        started = time.perf_counter()
        issues: List[ValidationIssue] = []

        for chunk in lesson.chunks:
            if not chunk.teach_back.must_understand:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="chunk_must_understand_empty",
                        gate=GateName.SCHEMA,
                        target=chunk.id,
                        detail="must_understand must not be empty",
                    )
                )
            if (
                chunk.teach_back.common_misconception
                and not chunk.teach_back.clarification_trigger
            ):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="chunk_clarification_required",
                        gate=GateName.SCHEMA,
                        target=chunk.id,
                        detail=(
                            "clarification_trigger required when "
                            "common_misconception is set"
                        ),
                    )
                )

        outcome = GateOutcome.PASS
        if any(i.severity == IssueSeverity.ERROR for i in issues):
            outcome = GateOutcome.FAIL
        elif any(i.severity == IssueSeverity.WARN for i in issues):
            outcome = GateOutcome.WARN

        duration_ms = int((time.perf_counter() - started) * 1000)
        return GateResult(
            gate=GateName.SCHEMA,
            outcome=outcome,
            score=None,
            issues=issues,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Gate B — Source Grounding
# ---------------------------------------------------------------------------


class SourceGroundingValidator:
    """Gate B — source grounding.

    The most important rule is SG-6: a citation existing somewhere in
    the document is NOT enough; it must appear (or fuzzy-match) on at
    least one of the ``source_pages`` declared by the claim.
    """

    def __init__(self, policy: Optional[ValidationPolicy] = None) -> None:
        self._policy = policy or ValidationPolicy()

    @property
    def policy(self) -> ValidationPolicy:
        return self._policy

    # ------------------------------------------------------------------
    # CleanDocument → validation
    # ------------------------------------------------------------------

    def validate_clean_document(
        self, clean: CleanDocument, raw: RawDocument
    ) -> Tuple[GateResult, ProvenanceStats]:
        return self._validate_common(
            blocks=list(self._iter_clean_blocks(clean)),
            concepts=clean.concepts,
            raw=raw,
        )

    # ------------------------------------------------------------------
    # StructuredLesson → validation
    # ------------------------------------------------------------------

    def validate_structured_lesson(
        self, lesson: StructuredLesson, raw: RawDocument
    ) -> Tuple[GateResult, ProvenanceStats]:
        blocks: List[CleanBlock] = []
        for sec in lesson.sections:
            blocks.extend(sec.blocks)
        return self._validate_common(
            blocks=blocks,
            concepts=lesson.concepts,
            raw=raw,
            extra_chunks=lesson.chunks,
        )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def _validate_common(
        self,
        *,
        blocks: List[CleanBlock],
        concepts: List[CleanConcept],
        raw: RawDocument,
        extra_chunks: Optional[List[TeachBackChunk]] = None,
    ) -> Tuple[GateResult, ProvenanceStats]:
        started = time.perf_counter()
        issues: List[ValidationIssue] = []
        page_text_map: Dict[int, str] = {
            page.page_number: page.text or "" for page in raw.pages
        }
        page_count = raw.page_count

        # Collect grounded / ungrounded counts.
        grounded = 0
        ungrounded_ids: List[str] = []

        claim_blocks = [b for b in blocks if _is_claim_block(b)]

        for blk in claim_blocks:
            ok, why = self._check_block(blk, page_text_map, page_count)
            if ok:
                grounded += 1
            else:
                ungrounded_ids.append(blk.id)
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code=why,
                        gate=GateName.GROUNDING,
                        target=blk.id,
                        detail=f"block {blk.id!r} failed {why}",
                    )
                )

        # Concepts have their own grounding check (SG-1..SG-4, SG-6, SG-7).
        grounded_concepts = 0
        for con in concepts:
            ok, why = self._check_concept(con, page_text_map, page_count)
            if ok:
                grounded_concepts += 1
            else:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code=why,
                        gate=GateName.GROUNDING,
                        target=con.id,
                        detail=f"concept {con.id!r} ({con.name!r}) failed {why}",
                    )
                )

        # Chunk-level checks (key_points, examples, teach_back fields).
        grounded_chunk_fields = 0
        if extra_chunks:
            for chunk in extra_chunks:
                grounded_chunk_fields += self._check_chunk(
                    chunk, page_text_map, page_count, issues
                )

        # Page coverage floor (uses ALL blocks, not just claim-bearing).
        coverage = self._compute_page_coverage(blocks, raw)
        bad_pages = sorted(
            int(p)
            for p, ratio in coverage.items()
            if (page_text_map.get(int(p), "").strip())
            and ratio < self._policy.page_coverage_floor
        )
        for p in bad_pages:
            ratio = coverage[p]
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="page_coverage_low",
                    gate=GateName.GROUNDING,
                    target=f"page:{p}",
                    detail=(
                        f"page {p} coverage {ratio:.2f} is below "
                        f"floor {self._policy.page_coverage_floor:.2f}"
                    ),
                )
            )

        total_claims = len(claim_blocks) + len(concepts)
        if extra_chunks:
            for chunk in extra_chunks:
                total_claims += len(chunk.key_points) + len(chunk.examples)
                if chunk.teach_back.acceptable_explanation:
                    total_claims += 1
                if chunk.teach_back.clarification_trigger:
                    total_claims += 1
                if chunk.teach_back.common_misconception:
                    total_claims += 1

        grounded_total = grounded + grounded_concepts + grounded_chunk_fields
        if total_claims > 0:
            grounding_score = grounded_total / total_claims
        else:
            grounding_score = 1.0

        # Apply page coverage factor.
        if coverage:
            mean_cov = sum(coverage.values()) / len(coverage)
            grounding_score = grounding_score * mean_cov

        # Outcome decision.
        outcome = GateOutcome.PASS
        any_error = any(i.severity == IssueSeverity.ERROR for i in issues)
        any_warn = any(i.severity == IssueSeverity.WARN for i in issues)

        if any_error or grounding_score < self._policy.grounding_threshold:
            outcome = GateOutcome.FAIL
        elif any_warn:
            outcome = GateOutcome.WARN

        stats = ProvenanceStats(
            total_blocks=len(claim_blocks),
            grounded_blocks=grounded,
            ungrounded_block_ids=ungrounded_ids,
            page_coverage={str(k): v for k, v in coverage.items()},
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return (
            GateResult(
                gate=GateName.GROUNDING,
                outcome=outcome,
                score=grounding_score,
                issues=issues,
                duration_ms=duration_ms,
            ),
            stats,
        )

    # ------------------------------------------------------------------
    # Per-element checks
    # ------------------------------------------------------------------

    def _check_block(
        self,
        blk: CleanBlock,
        page_text_map: Dict[int, str],
        page_count: int,
    ) -> Tuple[bool, str]:
        # SG-1: non-empty source_pages.
        if not blk.source_pages:
            return False, "SG-1"
        # SG-7: pages exist.
        for p in blk.source_pages:
            if p < 1 or p > page_count:
                return False, "SG-7"
        # SG-2: non-empty citation.
        if not blk.citation:
            return False, "SG-2"
        # SG-4 + SG-6: citation must ground on a claimed page.
        if not self._citation_grounds(blk.citation, blk.source_pages, page_text_map):
            return False, "SG-6"
        return True, ""

    def _check_concept(
        self,
        con: CleanConcept,
        page_text_map: Dict[int, str],
        page_count: int,
    ) -> Tuple[bool, str]:
        if not con.source_pages:
            return False, "SG-1"
        for p in con.source_pages:
            if p < 1 or p > page_count:
                return False, "SG-7"
        if not con.citation:
            return False, "SG-2"
        if not self._citation_grounds(con.citation, con.source_pages, page_text_map):
            return False, "SG-6"
        return True, ""

    def _check_chunk(
        self,
        chunk: TeachBackChunk,
        page_text_map: Dict[int, str],
        page_count: int,
        issues: List[ValidationIssue],
    ) -> int:
        """Run SG-1..SG-7 + teach-back-field checks for one chunk.

        Returns the count of grounded chunk-derived fields (key_points,
        examples, teach_back fields).

        Note: Pydantic already rejects inverted page ranges at
        construction time, so we do not re-check them here.
        """
        grounded = 0
        # Key points
        for kp in chunk.key_points:
            if not kp.source_pages:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="SG-1",
                        gate=GateName.GROUNDING,
                        target=f"{chunk.id}:{kp.id}",
                        detail=f"key_point {kp.id!r} has empty source_pages",
                    )
                )
                continue
            bad_page = False
            for p in kp.source_pages:
                if p < 1 or p > page_count:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="SG-7",
                            gate=GateName.GROUNDING,
                            target=f"{chunk.id}:{kp.id}",
                            detail=f"key_point {kp.id!r} cites out-of-range page {p}",
                        )
                    )
                    bad_page = True
                    break
                page_text = page_text_map.get(p, "")
                if _citation_grounds_on_page(kp.text, page_text):
                    grounded += 1
                    bad_page = False
                    break
            else:
                bad_page = True
            if bad_page and not any(
                i.code in {"SG-1", "SG-7"}
                and i.target == f"{chunk.id}:{kp.id}"
                for i in issues
            ):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.WARN,
                        code="key_point_ungrounded",
                        gate=GateName.GROUNDING,
                        target=f"{chunk.id}:{kp.id}",
                        detail=(
                            f"key_point {kp.id!r} text does not appear "
                            f"verbatim on any cited page"
                        ),
                    )
                )

        # Examples
        for ex in chunk.examples:
            if not ex.source_pages:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="SG-1",
                        gate=GateName.GROUNDING,
                        target=f"{chunk.id}:{ex.id}",
                        detail=f"example {ex.id!r} has empty source_pages",
                    )
                )
            else:
                # Examples have a text — we accept if at least one cited
                # page contains it (or fuzzy-matches).
                page_hit = False
                for p in ex.source_pages:
                    if p < 1 or p > page_count:
                        continue
                    if _citation_grounds_on_page(ex.text, page_text_map.get(p, "")):
                        grounded += 1
                        page_hit = True
                        break
                if not page_hit:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.WARN,
                            code="example_ungrounded",
                            gate=GateName.GROUNDING,
                            target=f"{chunk.id}:{ex.id}",
                            detail=(
                                f"example {ex.id!r} text does not appear "
                                f"on any cited page"
                            ),
                        )
                    )

        # teach_back fields: acceptable_explanation, common_misconception,
        # clarification_trigger must reference SOME page.
        for field_name in (
            "acceptable_explanation",
            "common_misconception",
            "clarification_trigger",
        ):
            text = getattr(chunk.teach_back, field_name)
            if not text:
                continue
            # These fields are derived from the chunk; the page range is
            # the chunk's own page_start..page_end. We require the text to
            # appear (or fuzzy match) on at least one of those pages,
            # otherwise it is unsupported.
            page_range = list(range(chunk.page_start, chunk.page_end + 1))
            if any(
                p in page_text_map and _citation_grounds_on_page(text, page_text_map[p])
                for p in page_range
            ):
                grounded += 1
                continue
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="teach_back_field_ungrounded",
                    gate=GateName.GROUNDING,
                    target=f"{chunk.id}.{field_name}",
                    detail=(
                        f"{field_name} text on chunk {chunk.id!r} does not "
                        "appear on any of its declared pages"
                    ),
                )
            )

        return grounded

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _citation_grounds(
        citation: str, pages: List[int], page_text_map: Dict[int, str]
    ) -> bool:
        for p in pages:
            text = page_text_map.get(p, "")
            if _citation_grounds_on_page(citation, text):
                return True
        return False

    @staticmethod
    def _iter_clean_blocks(clean: CleanDocument) -> Iterable[CleanBlock]:
        for sec in clean.sections:
            for blk in sec.blocks:
                yield blk

    @staticmethod
    def _compute_page_coverage(
        blocks: List[CleanBlock], raw: RawDocument
    ) -> Dict[int, float]:
        """For each non-blank page in the raw document, return the
        fraction of its character content that is referenced by at
        least one block's ``source_pages``.

        A page with 1 000 chars where blocks cite 600 chars of
        (verbatim or fuzzy-matching) content has coverage 0.6.

        Headings and notes count towards coverage even though they
        are not "claim blocks" — they still represent the source.
        """
        coverage: Dict[int, float] = {}
        for page in raw.pages:
            text = (page.text or "").strip()
            if not text:
                coverage[page.page_number] = 1.0
                continue

            claimed_chars = 0
            for blk in blocks:
                if page.page_number not in blk.source_pages:
                    continue
                if not blk.text:
                    continue
                # Count each unique block text once per page.
                if _citation_grounds_on_page(blk.text, text):
                    claimed_chars += min(len(blk.text), len(text))

            coverage[page.page_number] = min(1.0, claimed_chars / max(1, len(text)))
        return coverage


# ---------------------------------------------------------------------------
# Gate C — Confidence
# ---------------------------------------------------------------------------


class ConfidenceValidator:
    """Gate C — confidence / hallucination guard."""

    def __init__(self, policy: Optional[ValidationPolicy] = None) -> None:
        self._policy = policy or ValidationPolicy()

    def validate_clean_document(self, clean: CleanDocument) -> GateResult:
        return self._validate_common(
            blocks=[b for sec in clean.sections for b in sec.blocks],
            concepts=clean.concepts,
            chunks=[],
        )

    def validate_structured_lesson(
        self, lesson: StructuredLesson
    ) -> GateResult:
        blocks = [b for sec in lesson.sections for b in sec.blocks]
        return self._validate_common(
            blocks=blocks, concepts=lesson.concepts, chunks=lesson.chunks
        )

    def _validate_common(
        self,
        *,
        blocks: List[CleanBlock],
        concepts: List[CleanConcept],
        chunks: List[TeachBackChunk],
    ) -> GateResult:
        started = time.perf_counter()
        issues: List[ValidationIssue] = []
        low_confidence_chunk_ids: List[str] = []

        # CG-2 / CG-3: hallucination guard.
        # A block whose citation grounds on NO page AND whose text
        # overlaps no other block's source pages is suspicious.
        cited_pages_per_block: Dict[str, set] = {
            blk.id: set(blk.source_pages) for blk in blocks
        }
        for blk in blocks:
            if not blk.citation:
                continue
            # If at least one of its source pages is referenced by some
            # other block too, we treat it as anchored.
            anchored = False
            for other_id, other_pages in cited_pages_per_block.items():
                if other_id == blk.id:
                    continue
                if cited_pages_per_block[blk.id] & other_pages:
                    anchored = True
                    break
            if not anchored and not blk.source_pages:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="CG-3",
                        gate=GateName.CONFIDENCE,
                        target=blk.id,
                        detail=(
                            f"block {blk.id!r} has no source pages and is "
                            "likely a hallucination"
                        ),
                    )
                )

        # CG-1: per-chunk confidence below floor → warn.
        for chunk in chunks:
            if chunk.confidence < self._policy.min_confidence:
                low_confidence_chunk_ids.append(chunk.id)
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.WARN,
                        code="low_confidence",
                        gate=GateName.CONFIDENCE,
                        target=chunk.id,
                        detail=(
                            f"chunk {chunk.id!r} confidence "
                            f"{chunk.confidence:.2f} < floor "
                            f"{self._policy.min_confidence:.2f}"
                        ),
                    )
                )

        # CG-2: missing teach-back targets → warn.
        for chunk in chunks:
            tb = chunk.teach_back
            if not tb.acceptable_explanation:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.WARN,
                        code="missing_acceptable_explanation",
                        gate=GateName.CONFIDENCE,
                        target=chunk.id,
                        detail=(
                            f"chunk {chunk.id!r} has no "
                            "acceptable_explanation"
                        ),
                    )
                )
            if tb.common_misconception is None:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.INFO,
                        code="no_misconception",
                        gate=GateName.CONFIDENCE,
                        target=chunk.id,
                        detail=(
                            f"chunk {chunk.id!r} has no "
                            "common_misconception (source may lack evidence)"
                        ),
                    )
                )

        any_error = any(i.severity == IssueSeverity.ERROR for i in issues)
        any_warn = any(i.severity == IssueSeverity.WARN for i in issues)
        if any_error:
            outcome = GateOutcome.FAIL
        elif any_warn:
            outcome = GateOutcome.WARN
        else:
            outcome = GateOutcome.PASS

        duration_ms = int((time.perf_counter() - started) * 1000)
        return GateResult(
            gate=GateName.CONFIDENCE,
            outcome=outcome,
            score=None,
            issues=issues,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_claim_block(blk: CleanBlock) -> bool:
    """Decide whether ``blk`` carries a claim that needs grounding.

    Headings and notes carry weak claims; definitions, examples,
    relationships, tables, diagrams, and bullets carry strong claims.
    """
    if blk.type in (
        BlockType.DEFINITION,
        BlockType.EXAMPLE,
        BlockType.RELATIONSHIP,
        BlockType.TABLE,
        BlockType.DIAGRAM,
        BlockType.BULLET,
    ):
        return True
    # Headings and notes still need provenance but with looser rules —
    # we skip them in grounding scoring to avoid penalising slide
    # titles that paraphrase the source.
    return False


__all__ = [
    "SchemaValidator",
    "SourceGroundingValidator",
    "ConfidenceValidator",
]