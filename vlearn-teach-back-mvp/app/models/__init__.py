"""Models package — Pydantic domain models."""

from app.models.clean_document import (  # noqa: F401
    BlockType,
    BulletMarker,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
    ConceptKind,
    DiagramBlock,
    DiagramEdge,
    DiagramKind,
    DiagramNode,
    RelationshipKind,
    RemovedNoise,
    RemovedNoiseKind,
    TableBlock,
)
from app.models.lesson import (  # noqa: F401
    ChunkStatus,
    Lesson,
    LessonChunk,
    Quiz,
    QuizQuestion,
)
from app.models.message import (  # noqa: F401
    MessageAuthor,
    TeachingMessage,
)
from app.models.raw_document import (  # noqa: F401
    PageText,
    RawDocument,
    RawDocumentMetadata,
)
from app.models.session import (  # noqa: F401
    SessionStatus,
    TeachingSession,
    ValidationResult,
)
from app.models.structured_lesson import (  # noqa: F401
    GeneratedBy,
    StructuredLesson,
    StructuredLessonMetadata,
    lesson_from_dict,
    lesson_to_dict,
)
from app.models.teach_back_chunk import (  # noqa: F401
    ChunkExample,
    KeyPoint,
    TeachBackChunk,
    TeachBackTargets,
)
from app.models.validation_report import (  # noqa: F401
    GateName,
    GateOutcome,
    GateResult,
    IssueSeverity,
    ProvenanceStats,
    ValidationIssue,
    ValidationPolicy,
    ValidationReport,
)