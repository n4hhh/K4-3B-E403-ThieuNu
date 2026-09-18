"""MockProvider — deterministic AIProvider for tests and offline runs.

The MockProvider returns a pre-built :class:`CleanDocument`-shaped JSON
derived from the input ``RawDocument``. It is:

    * **deterministic** — same input → same output, every time;
    * **noise-aware** — it removes obvious header/footer/page-number
      noise from the source text before generating blocks, mirroring
      the Documentizer's noise-removal contract;
    * **grounded** — every emitted block carries a ``citation`` that
      actually appears in the source text;
    * **self-contained** — no network, no SDK imports, no env vars.

The mock honours :class:`DocumentizerOptions` lightly: language,
target chunk range, and which block types to include.

It deliberately does NOT try to be smart. Tests that need tailored
behaviour can subclass :class:`MockProvider` and override
:meth:`build_payload`.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, List, Optional

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
    ConceptKind,
    RemovedNoise,
    RemovedNoiseKind,
)
from app.models.raw_document import RawDocument

from app.services.ai.ai_provider import (
    AIProvider,
    DocumentizerInput,
    DocumentizerOutput,
    PageImage,
    ProviderMetadata,
)


# Page-number / footer / header patterns observed in VLearn slide PDFs.
_PAGE_NUMBER_RE = re.compile(r"^\s*(?:page|trang)\s*\d+\s*$", re.IGNORECASE)
_FOOTER_DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"[a-z]*\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)


def _is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _PAGE_NUMBER_RE.match(s):
        return True
    if _FOOTER_DATE_RE.search(s) and len(s) < 80:
        return True
    if s in {"© VLearn", "VLearn ©", "© VinAI", "Internal"}:
        return True
    return False


def _classify_noise(line: str) -> RemovedNoiseKind:
    s = line.strip()
    if _PAGE_NUMBER_RE.match(s):
        return RemovedNoiseKind.PAGE_NUMBER
    if any(token in s.lower() for token in ("vlearn", "vinai", "internal", "©")):
        return RemovedNoiseKind.FOOTER
    return RemovedNoiseKind.OTHER


def _strip_noise_lines(raw_text: str, page_number: int) -> tuple[str, List[RemovedNoise]]:
    """Return (clean_text, removed_noise) for one page's text."""
    removed: List[RemovedNoise] = []
    kept: List[str] = []
    for line in raw_text.splitlines():
        if _is_noise_line(line):
            removed.append(
                RemovedNoise(
                    kind=_classify_noise(line),
                    source_page=page_number,
                    excerpt=line.strip()[:80],
                )
            )
            continue
        kept.append(line)
    return "\n".join(line for line in kept if line.strip()), removed


def _first_meaningful_line(text: str) -> Optional[str]:
    for line in text.splitlines():
        s = line.strip()
        if len(s) >= 4 and not _is_noise_line(s):
            return s
    return None


def _split_into_sections(pages_text: List[tuple[int, str]]) -> List[CleanSection]:
    """Group cleaned pages into slide-aligned sections.

    Strategy:
        * If a page starts with an ALL-CAPS heading or a numbered
          heading, it starts a new section.
        * Otherwise the page is appended to the previous section.

    Pages without any text become 1-block note sections so the source
    remains accounted for in the provenance.
    """
    heading_re = re.compile(
        r"^(?:[A-Z][A-Za-z0-9][A-Za-z0-9 \.\-:&/]{2,}|[0-9]+(?:\.[0-9]+)*\.?\s+[A-Z][^\.]{2,80})$"
    )

    sections: List[CleanSection] = []
    current: Optional[CleanSection] = None
    block_id = 0

    def _new_block_id() -> str:
        nonlocal block_id
        block_id += 1
        return f"blk-{block_id:04d}"

    for page_num, text in pages_text:
        first_line = _first_meaningful_line(text)
        starts_section = bool(first_line and heading_re.match(first_line.strip()))
        if current is None or starts_section:
            current = CleanSection(
                id=f"sec-{page_num:03d}",
                title=(first_line or f"Page {page_num}").strip()[:120],
                page_start=page_num,
                page_end=page_num,
                blocks=[],
            )
            sections.append(current)
        else:
            current.page_end = page_num

        if not text.strip():
            current.blocks.append(
                CleanBlock(
                    id=_new_block_id(),
                    type=BlockType.NOTE,
                    text="(blank slide)",
                    source_pages=[page_num],
                    citation="",
                    confidence=0.4,
                )
            )
            continue

        # Heuristic: any line is a bullet; the first non-empty line is the
        # heading if it isn't already used as the section title.
        is_first = True
        for line in text.splitlines():
            s = line.strip()
            if not s or _is_noise_line(s):
                continue
            if is_first:
                current.blocks.append(
                    CleanBlock(
                        id=_new_block_id(),
                        type=BlockType.HEADING,
                        text=s[:200],
                        source_pages=[page_num],
                        citation=s[:160],
                        confidence=0.95,
                        level=2,
                    )
                )
                is_first = False
                continue
            is_first = False
            current.blocks.append(
                CleanBlock(
                    id=_new_block_id(),
                    type=BlockType.BULLET,
                    text=s[:240],
                    source_pages=[page_num],
                    citation=s[:160],
                    confidence=0.85,
                    marker="dash",
                )
            )

    return sections


class MockProvider:
    """Deterministic AIProvider used by tests and offline runs.

    Implements the :class:`AIProvider` Protocol but is **not** registered
    in :mod:`app.services.ai.provider_factory` for production use — the
    factory only returns ``mock`` when ``AI_PROVIDER=mock``.
    """

    name: str = "mock"
    model: str = "mock-1"

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or self.model

    # ---- AIProvider protocol ------------------------------------------------

    def documentize(self, input: DocumentizerInput) -> DocumentizerOutput:
        started = time.perf_counter()

        # 1) Noise removal.
        cleaned_pages: List[tuple[int, str]] = []
        all_removed: List[RemovedNoise] = []
        for page in input.raw_document.pages:
            cleaned, removed = _strip_noise_lines(page.text, page.page_number)
            all_removed.extend(removed)
            cleaned_pages.append((page.page_number, cleaned))

        # 2) Slide-aligned sections.
        sections = _split_into_sections(cleaned_pages)

        # 3) Concepts (one per non-trivial bullet).
        concepts: List[CleanConcept] = []
        concept_id = 0
        for sec in sections:
            for blk in sec.blocks:
                if blk.type == BlockType.HEADING and len(blk.text) >= 4:
                    concept_id += 1
                    concepts.append(
                        CleanConcept(
                            id=f"con-{concept_id:04d}",
                            name=blk.text.strip()[:80],
                            summary=blk.text.strip(),
                            source_pages=list(blk.source_pages),
                            citation=blk.citation or blk.text[:160],
                            kind=ConceptKind.TERM,
                            aliases=[],
                            confidence=blk.confidence,
                        )
                    )

        # 4) Map back to a CleanDocument-shaped dict.
        clean_doc = CleanDocument(
            document_id=input.document_id,
            source_file=input.raw_document.source_file,
            language=input.options.language or "auto",
            title=_infer_title(input.raw_document),
            summary=_infer_summary(sections),
            sections=sections,
            concepts=concepts,
            removed_noise=all_removed,
            documentizer_run_id=input.run_id or str(uuid.uuid4()),
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata = ProviderMetadata(
            provider=self.name,
            model=self.model,
            request_id=None,
            latency_ms=latency_ms,
            usage={"mode": "mock"},
        )

        return DocumentizerOutput(
            clean_payload=clean_doc.model_dump(mode="json"),
            raw_response="<mock provider>",
            provider_metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Helpers shared with the real provider
# ---------------------------------------------------------------------------


def _infer_title(raw: RawDocument) -> str:
    for page in raw.pages:
        first = _first_meaningful_line(page.text)
        if first and len(first) >= 4:
            return first.strip()[:120]
    stem = raw.source_file.rsplit(".", 1)[0]
    return stem.replace("_", " ").replace("-", " ").title()


def _infer_summary(sections: List[CleanSection]) -> str:
    if not sections:
        return ""
    first = sections[0]
    bullets = [b.text for b in first.blocks if b.type == BlockType.BULLET][:3]
    if not bullets:
        return first.title
    return f"{first.title}: {'; '.join(bullets)}"[:280]


__all__ = ["MockProvider"]


def _coerce_input(obj: Any) -> DocumentizerInput:
    """Test/dev helper: accept a ``RawDocument`` and turn it into a DocumentizerInput."""
    if isinstance(obj, DocumentizerInput):
        return obj
    if isinstance(obj, RawDocument):
        return DocumentizerInput(
            document_id=obj.document_id,
            raw_document=obj,
        )
    raise TypeError(f"Cannot coerce {type(obj).__name__} to DocumentizerInput")


# Avoid name collision with __init__.py above
_ = PageImage