"""CleanDocument — Phase 3A.5 intermediate schema.

A CleanDocument is the **noise-removed, AI-normalised** representation of a
``RawDocument``. It is produced by the ``Documentizer`` and consumed by the
``LessonBuilder``.

This schema is in-memory only — it is **not persisted**. It can always be
re-derived from the immutable ``RawDocument`` plus the AI provider's
response.

Key invariants:

    * Every claim-bearing block carries ``source_pages`` + ``citation``.
    * Sections never split a single source page across two sections.
    * Only presentation noise is removed — no new content is invented.
    * ``removed_noise`` records what was dropped for audit.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.teach_back_chunk import TeachBackChunk


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RemovedNoiseKind(str, Enum):
    """Categories of presentation noise the Documentizer may drop."""

    PAGE_NUMBER = "page_number"
    FOOTER = "footer"
    HEADER = "header"
    DECORATIVE = "decorative"
    NAVIGATION = "navigation"
    PRIVATE_USE_UNICODE = "private_use_unicode"
    LAYOUT_ARTIFACT = "layout_artifact"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------


class RemovedNoise(BaseModel):
    """One item of presentation noise that the Documentizer dropped."""

    kind: RemovedNoiseKind = Field(..., description="Category of noise removed")
    source_page: int = Field(..., ge=1, description="1-based page the noise came from")
    excerpt: str = Field(..., description="Short verbatim excerpt of the noise")


# ---------------------------------------------------------------------------
# CleanDocument
# ---------------------------------------------------------------------------


class CleanDocument(BaseModel):
    """Noise-removed, normalised view of a ``RawDocument``.

    Intermediate schema — never persisted; lives only for the lifetime of
    one ``DocumentizerPipeline.process(document_id)`` call.
    """

    schema_version: str = "3a5.clean.v1"

    document_id: str = Field(
        ...,
        description="ID of the source RawDocument (stable, kebab-case)",
    )
    source_file: str = Field(..., description="Original PDF filename")
    language: str = Field("auto", description="Detected / forced language code")

    title: str = Field(..., description="Lesson title as inferred from slides")
    summary: str = Field("", description="Short summary derived from the slides")

    sections: List["CleanSection"] = Field(
        default_factory=list,
        description="Slide-aligned sections of the cleaned document",
    )

    concepts: List["CleanConcept"] = Field(
        default_factory=list,
        description="Atomic knowledge units (terms, methods, principles, ...)",
    )

    # Optional Gemini-emitted Teach-Back chunks. When the AI provider
    # returns a top-level ``chunks`` array, it is preserved here so the
    # LessonBuilder can use Gemini's teach_back targets directly
    # instead of re-deriving them via heuristics.
    teach_back_chunks: List[TeachBackChunk] = Field(
        default_factory=list,
        description="AI-emitted Teach-Back chunks (preserved from Gemini)",
    )

    removed_noise: List[RemovedNoise] = Field(
        default_factory=list,
        description="Audit trail of presentation noise that was dropped",
    )

    documentizer_version: str = "3a5.0.0"
    documentizer_run_id: Optional[str] = Field(
        default=None,
        description="Stable run id (used for cache keying)",
    )
    cleaned_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("document_id")
    @classmethod
    def _validate_document_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("document_id must be non-empty")
        return v


# ---------------------------------------------------------------------------
# Section + Block (slide-aligned)
# ---------------------------------------------------------------------------


class BlockType(str, Enum):
    """Slide-specific structural block types."""

    HEADING = "heading"
    BULLET = "bullet"
    DEFINITION = "definition"
    EXAMPLE = "example"
    TABLE = "table"
    DIAGRAM = "diagram"
    RELATIONSHIP = "relationship"
    NOTE = "note"


class BulletMarker(str, Enum):
    DISC = "disc"
    DASH = "dash"
    NUMBERED = "numbered"
    CHECK = "check"


class DiagramKind(str, Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    TREE = "tree"
    FREE = "free"


class RelationshipKind(str, Enum):
    IS_A = "is-a"
    HAS_A = "has-a"
    DEPENDS_ON = "depends-on"
    CONTRASTS_WITH = "contrasts-with"
    CAUSES = "causes"
    ENABLES = "enables"


class TableBlock(BaseModel):
    """Tabular content within a slide."""

    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)


class DiagramNode(BaseModel):
    id: str
    label: str


class DiagramEdge(BaseModel):
    """One edge in a diagram.

    The Documentizer only records simple labelled edges; complex graphs
    are described in ``description``.
    """

    src: str = Field(..., alias="from")
    to: str
    label: Optional[str] = None

    model_config = {"populate_by_name": True}


class DiagramBlock(BaseModel):
    """Visual / structural diagram on a slide."""

    kind: DiagramKind = DiagramKind.FREE
    description: str = ""
    nodes: List[DiagramNode] = Field(default_factory=list)
    edges: List[DiagramEdge] = Field(default_factory=list)


class CleanBlock(BaseModel):
    """One typed block on a slide-aligned section.

    Every claim-bearing field carries ``source_pages`` and ``citation``.
    The Documentizer guarantees them; the validator re-checks them.
    """

    id: str = Field(..., description="Stable block id within the document")
    type: BlockType
    text: str = Field(..., min_length=1)
    source_pages: List[int] = Field(
        default_factory=list,
        description="1-based page numbers this block came from",
    )
    citation: str = Field(
        default="",
        description="Short verbatim quote from the source supporting this block",
    )
    confidence: float = Field(
        0.5, ge=0.0, le=1.0, description="Provider self-reported confidence (0..1)"
    )

    # Per-type extras (all optional; only set when type matches)
    level: Optional[int] = Field(default=None, ge=1, le=6)
    marker: Optional[BulletMarker] = None
    term: Optional[str] = None
    definition: Optional[str] = None
    caption: Optional[str] = None
    table: Optional[TableBlock] = None
    diagram: Optional[DiagramBlock] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    relationship_kind: Optional[RelationshipKind] = None


class CleanSection(BaseModel):
    """One slide-aligned section."""

    id: str = Field(..., description="Stable section id within the document")
    title: str = Field(..., min_length=1)
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    blocks: List[CleanBlock] = Field(default_factory=list)

    @field_validator("page_end")
    @classmethod
    def _validate_page_range(cls, v: int, info) -> int:  # type: ignore[no-untyped-def]
        page_start = info.data.get("page_start")
        if page_start is not None and v < page_start:
            raise ValueError("page_end must be >= page_start")
        return v


# ---------------------------------------------------------------------------
# Concept
# ---------------------------------------------------------------------------


class ConceptKind(str, Enum):
    METHOD = "method"
    TERM = "term"
    PRINCIPLE = "principle"
    PROCESS = "process"
    ENTITY = "entity"
    PROPERTY = "property"


class CleanConcept(BaseModel):
    """Atomic knowledge unit.

    Every concept is grounded in the source via ``source_pages`` +
    ``citation``. ``aliases`` are alternative names mentioned in the
    source that map to the same concept.
    """

    id: str = Field(..., description="Stable concept id within the document")
    name: str = Field(..., min_length=1)
    summary: str = Field("", description="One-sentence description")
    source_pages: List[int] = Field(..., min_length=1)
    citation: str = Field(..., min_length=1)
    kind: ConceptKind = ConceptKind.TERM
    aliases: List[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0.0, le=1.0)


# Resolve forward references
CleanDocument.model_rebuild()

__all__ = [
    "BlockType",
    "BulletMarker",
    "CleanBlock",
    "CleanConcept",
    "CleanDocument",
    "CleanSection",
    "ConceptKind",
    "DiagramBlock",
    "DiagramEdge",
    "DiagramKind",
    "DiagramNode",
    "RelationshipKind",
    "RemovedNoise",
    "RemovedNoiseKind",
    "TableBlock",
]