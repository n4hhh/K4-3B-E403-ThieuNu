# Phase 3A.5 — Design Document (for approval before coding)

**Status:** DESIGN ONLY — awaiting approval
**Phase 3A:** COMPLETE & READ-ONLY (do not modify)
**Phase 3A.5:** NOT implemented in this document — contract + plan only
**Target feature:** Teach-Back slide-based learning

---

## 0. Scope & Non-Goals

### In scope (this document)
- Architecture diagram for Phase 3A.5
- Data flow RawDocument → Published Lesson
- Structured Lesson schema designed for Teach-Back
- Documentizer input/output contract
- Validation rules (source grounding + JSON schema + confidence)
- Retry / fallback behavior
- Gemini API abstraction (provider/model swappable)
- Proposed file structure
- Implementation plan (steps + test plan)

### Out of scope (do not design here)
- Actual Gemini API call implementation
- Any change to Phase 3A code
- Any change to existing Lesson/LessonChunk/TeachingSession semantics beyond what is strictly required to plug in a Structured Lesson
- New UI/UX

### Invariants (must hold)
- Phase 3A files are **not modified**.
- API keys are **never hardcoded**; read from `GEMINI_API_KEY` env var at runtime.
- Model name is **never hardcoded**; read from `GEMINI_MODEL` env var at runtime.
- Provider is **never hardcoded**; read from `AI_PROVIDER` env var (default `gemini`).
- `RawDocument` is **immutable source evidence** — Documentizer reads but never writes to it.

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 3A (READ-ONLY)                            │
│                                                                         │
│   ../data/lesson/<file>.pdf                                              │
│            │                                                            │
│            ▼                                                            │
│   ┌────────────────┐      ┌──────────────────────┐                      │
│   │   PDFReader    │ ───► │   RawDocument        │  ── immutable ──►    │
│   │   (pypdf)      │      │   (per-page text)    │      source          │
│   └────────────────┘      └──────────┬───────────┘      evidence       │
│                                     │                                  │
│                                     ▼                                  │
│                          data/processed/{doc_id}/raw.json               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │  read-only input
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PHASE 3A.5 (THIS DESIGN)                          │
│                                                                         │
│  ┌─────────────────────┐    optional                                     │
│  │  PDF Page Images    │◄──────── pdf2image / pypdf rendering            │
│  │  page_NN.png        │   (one image per source page)                  │
│  └─────────┬───────────┘                                                │
│            │                                                            │
│            │ + RawDocument (text + page numbers)                        │
│            ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   GeminiDocumentizer                             │   │
│  │  (orchestrator — depends only on AIProvider abstraction)         │   │
│  └───────────────┬──────────────────────────┬───────────────────────┘   │
│                  │                          │                           │
│                  ▼                          ▼                           │
│   ┌────────────────────────┐    ┌────────────────────────────────┐      │
│   │  AIProvider interface  │    │ SourceGroundingValidator       │      │
│   │  (Gemini, Mock, …)     │    │ + JSON Schema Validator        │      │
│   └────────────┬───────────┘    └────────────────┬───────────────┘      │
│                │                                  │                    │
│                ▼                                  ▼                    │
│   ┌────────────────────────┐    ┌────────────────────────────────┐      │
│   │ CleanDocument          │    │ ValidationReport               │      │
│   │ (noise removed,        │    │  - grounding score             │      │
│   │  blocks normalised)    │    │  - schema errors               │      │
│   └────────────┬───────────┘    │  - confidence per chunk        │      │
│                │                └────────────────────────────────┘      │
│                ▼                                                        │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │             DocumentizerPipeline (orchestrator)             │       │
│   │  CleanDocument → LessonBuilder → StructuredLesson            │       │
│   │       + teach-back targets + provenance + confidence        │       │
│   └────────────┬───────────────────────────────────────────────┘       │
│                │                                                        │
│   retry/fallback │ (on grounding/schema failure)                        │
│                │                                                        │
│                ▼                                                        │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │                  Published Lesson                           │       │
│   │  data/processed/{doc_id}/lesson.json  (versioned, immutable)│       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │  loaded by existing
                                      ▼
                          LessonRepository (PDF path) /
                          LessonService / TeachingService / UI
                          (NO CHANGES to existing wiring logic
                           besides reading lesson.json if present)

┌─────────────────────────────────────────────────────────────────────────┐
│                  CROSS-CUTTING (this design)                            │
│                                                                         │
│  • AIProvider abstraction  — provider/model/key swappable at runtime   │
│  • StructuredLesson schema — Pydantic model + JSON Schema export       │
│  • Validation             — source-grounding + JSON-schema + confidence│
│  • Retry/Fallback         — see §6                                     │
│  • Configuration          — .env only, never hardcoded                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

Key idea: **Documentizer is a pure transformation**. It takes `RawDocument + optional page images` and emits a `StructuredLesson`. Everything between the input and the output is orchestrator logic and AI calls; no domain models in Phase 3A are touched.

---

## 2. Data Flow (end-to-end)

```
[1] Cold start
    Phase3APipeline.run()
        → reads PDFs in ../data/lesson
        → emits RawDocument per PDF
        → persists data/processed/{doc_id}/raw.json     (PHASE 3A)

[2] Phase 3A.5 trigger (CLI / scheduled / manual / on-demand at lesson load)
    DocumentizerPipeline.process(document_id)
        │
        ├─► load RawDocument (read-only)
        │
        ├─► optional: render page images (off by default)
        │
        ├─► Documentize step
        │       ├─ build DocumentizerInput (clean text + per-page chunks + optional images)
        │       ├─ call AIProvider.documentize(input)         ← Gemini (stubbed)
        │       └─ parse → CleanDocument
        │
        ├─► Validation step (gate)
        │       ├─ SourceGroundingValidator.score(CleanDocument, RawDocument)
        │       ├─ JsonSchemaValidator.validate(CleanDocument)
        │       └─ ConfidenceGate.decide(score, schema_ok, ...)
        │           │
        │           ├─ PASS  ─────────────────────────────────────► [3]
        │           │
        │           └─ FAIL  ──► RetryPolicy.apply(...) ───────────► retry or fallback
        │
        ├─► Build step
        │       └─ LessonBuilder.build(CleanDocument) → StructuredLesson
        │
        └─► Publish step
                ├─ SourceGroundingValidator.score(StructuredLesson, RawDocument)
                ├─ JsonSchemaValidator.validate(StructuredLesson)
                ├─ persist data/processed/{doc_id}/lesson.json
                └─ write ValidationReport sidecar (next to lesson.json)

[3] Teach-back consumes StructuredLesson
    LessonRepository (extended, additive only) → LessonService → UI
    UI/render code is unchanged.
```

### Data lifecycle invariants

| Object | Lifecycle |
|---|---|
| `RawDocument` | Created by Phase 3A. **Never modified by Phase 3A.5.** |
| `CleanDocument` | In-memory only. Not persisted. Re-derivable from RawDocument + AI call. |
| `StructuredLesson` | Persisted to `lesson.json`. Versioned. Immutable once published. |
| `ValidationReport` | Persisted sidecar. Updated each Documentizer run. |
| `PageImage` | Optional, rendered to `processed/{doc_id}/pages/page_NN.png`. Not source-of-truth. |

---

## 3. Structured Lesson Schema (designed for Teach-Back)

### 3.1 Design goals
- Concept-oriented, not page-oriented (but every concept carries page provenance).
- Every `Concept`, `Definition`, `Example`, `Relationship`, `Table`, `Diagram` carries `source_pages: List[int]` (1-based) and a `citation` (short quoted text).
- Chunks (Teach-Back units) reference Concepts, not raw text.
- Each chunk carries explicit **Teach-Back Targets** — the contract the validator must enforce.
- **No invented knowledge**: any field requiring source must include `citation` + `source_pages`.
- Versioned: schema version is part of the file.

### 3.2 Top-level shape

```json
{
  "schema_version": "3a5.lesson.v1",
  "lesson_id": "rest-api-http-methods",
  "source_document_id": "rest-api-http-methods",
  "source_file": "REST-API.pdf",
  "language": "en",
  "generated_at": "2026-09-18T11:00:00Z",
  "generated_by": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "pipeline_version": "3a5.0.0"
  },
  "title": "REST API & HTTP Methods",
  "summary": "...",
  "learning_objectives": ["..."],
  "sections": [ /* Section */ ],
  "chunks": [   /* TeachBackChunk */ ],
  "provenance": { /* aggregate stats */ },
  "validation": { /* last ValidationReport summary */ }
}
```

### 3.3 Section (slide-aligned)

```json
{
  "id": "sec-http-methods",
  "title": "HTTP Methods",
  "page_start": 3,
  "page_end": 4,
  "blocks": [ /* Block (heading|bullet|definition|example|table|diagram|relationship|note) */ ]
}
```

A Section is **slide-aligned** when possible (one or more contiguous source pages). The Documentizer never splits a single source page across two Sections.

### 3.4 Block (slide-specific structure)

All blocks share a common envelope:

```json
{
  "id": "blk-uuid",
  "type": "heading|bullet|definition|example|table|diagram|relationship|note",
  "text": "...",            // human-readable
  "source_pages": [3, 4],   // 1-based, non-empty
  "citation": "GET retrieves a representation of the specified resource.",
  "confidence": 0.92        // 0.0 - 1.0 (provider's self-reported or computed)
}
```

Per-type schemas:

| type | Extra fields |
|---|---|
| `heading` | `level: int (1..6)` |
| `bullet` | `marker: enum {disc, dash, numbered, check}` |
| `definition` | `term: str`, `definition: str` (also in `text`) |
| `example` | `caption: str?` |
| `table` | `headers: List[str]`, `rows: List[List[str]]` |
| `diagram` | `kind: enum {flowchart, sequence, tree, free}`, `description: str`, `nodes: List[{id,label}]?`, `edges: List[{from,to,label?}]?` |
| `relationship` | `subject: str`, `predicate: str`, `object: str`, `kind: enum {is-a, has-a, depends-on, contrasts-with, causes, enables}` |
| `note` | (no extras; free-form text used for noise that was kept deliberately) |

### 3.5 Concept

The atomic knowledge unit. Anything the Teach-Back validator checks for.

```json
{
  "id": "con-get-method",
  "name": "GET method",
  "summary": "HTTP GET retrieves a representation of a resource.",
  "source_pages": [3],
  "citation": "GET retrieves a representation of the specified resource.",
  "kind": "method|term|principle|process|entity|property",
  "aliases": ["HTTP GET"],
  "confidence": 0.93
}
```

### 3.6 Teach-Back Chunk

```json
{
  "id": "chunk-http-methods",
  "title": "HTTP Methods",
  "summary": "Common HTTP methods used in APIs and their semantics.",
  "page_start": 3,
  "page_end": 4,
  "concept_ids": ["con-get-method", "con-post-method", "con-put-method", "con-delete-method"],
  "key_points": [
    { "id": "kp-1", "text": "GET retrieves a resource", "concept_id": "con-get-method", "source_pages": [3] },
    { "id": "kp-2", "text": "POST creates a resource",  "concept_id": "con-post-method", "source_pages": [3] }
  ],
  "examples": [
    { "id": "ex-1", "text": "GET /users/42 returns user 42", "source_pages": [4] }
  ],
  "teach_back": {
    "must_understand":      ["...", "..."],
    "acceptable_explanation": "A short sentence describing the bar the explanation must clear.",
    "common_misconception":  "...",
    "clarification_trigger": "If the student confuses X with Y, ask: ..."
  },
  "confidence": 0.9
}
```

### 3.7 Teach-Back Targets (semantics)

| Field | Used by | Meaning |
|---|---|---|
| `must_understand` | Validator | Each entry must be present (semantically) in the student's explanation. |
| `acceptable_explanation` | Validator + UI prompt | One-sentence description of "good enough". Displayed to the student. |
| `common_misconception` | Agent follow-up generator | The most likely wrong answer; used to seed clarifying questions. |
| `clarification_trigger` | Agent follow-up generator | A natural-language rule that tells the agent when to ask back. |

### 3.8 Provenance aggregate

```json
{
  "total_blocks": 220,
  "grounded_blocks": 218,
  "ungrounded_block_ids": ["blk-..."],
  "page_coverage": { "1": 1.0, "2": 0.95, "3": 1.0 }
}
```

`page_coverage[p]` = fraction of textual content on page `p` that is represented by some block. Used to detect silent drops.

### 3.9 Validation summary

```json
{
  "status": "passed|warned|failed",
  "grounding_score": 0.93,
  "schema_ok": true,
  "low_confidence_chunk_ids": ["chunk-..."],
  "issues": [
    { "severity": "warn", "code": "low_confidence", "target": "chunk-x", "detail": "..." }
  ],
  "performed_at": "2026-09-18T11:01:00Z",
  "policy": { "grounding_threshold": 0.80, "min_confidence": 0.65 }
}
```

---

## 4. Documentizer Input / Output Contract

### 4.1 Input (`DocumentizerInput`)

```python
class DocumentizerInput:
    document_id: str                 # id of the RawDocument
    raw_document: RawDocument        # READ-ONLY
    page_images: Optional[List[Path]]  # ordered by page_number; optional
    language_hint: str = "auto"      # "en" | "vi" | "auto"
    options: DocumentizerOptions
```

`DocumentizerOptions`:
- `include_definitions: bool = True`
- `include_examples: bool = True`
- `include_tables: bool = True`
- `include_diagrams: bool = True`
- `include_relationships: bool = True`
- `target_chunks_min: int = 3`
- `target_chunks_max: int = 12`
- `language: str = "en"` (forced; auto-detect only if `auto`)

The orchestrator assembles `DocumentizerInput` from a `RawDocument` (loaded from disk) and optional rendered page images. **No PDF I/O happens inside the AI call.**

### 4.2 Output (`DocumentizerOutput`)

```python
class DocumentizerOutput:
    clean_document: CleanDocument      # parsed & validated against schema
    raw_response: dict                 # original provider payload (for debugging/audit)
    provider_metadata: ProviderMetadata
```

`ProviderMetadata`:
- `provider: str`     ("gemini" / "mock" / ...)
- `model: str`
- `request_id: Optional[str]`
- `latency_ms: int`
- `usage: dict`       (tokens / cost if available)

### 4.3 CleanDocument (intermediate schema)

The Documentizer **only** emits this schema; the `LessonBuilder` later turns it into a `StructuredLesson`.

```json
{
  "schema_version": "3a5.clean.v1",
  "document_id": "...",
  "title": "...",
  "summary": "...",
  "sections": [ /* Section */ ],
  "concepts": [ /* Concept */ ],
  "removed_noise": [
    { "kind": "page_number|footer|header|decorative", "source_page": 1, "excerpt": "..." }
  ]
}
```

`Section` and `Concept` are the same shape as the Structured Lesson. The Documentizer is responsible for **noise removal** — page numbers, repeating footers, decorative artifacts — and must declare what it removed in `removed_noise` for audit.

### 4.4 Provider contract (`AIProvider`)

```python
class AIProvider(Protocol):
    name: str
    model: str

    def documentize(self, input: DocumentizerInput) -> DocumentizerOutput: ...
```

- One concrete implementation: `GeminiProvider` (stub now, real later).
- A `MockProvider` exists for tests/dry-run that returns deterministic JSON.
- Provider selection is **runtime**: `AI_PROVIDER` env var (`gemini` | `mock`).
- Model is **runtime**: `GEMINI_MODEL` env var.
- Key is **never** passed through constructor in production code paths; the provider reads `GEMINI_API_KEY` from env at construction time only.

---

## 5. Validation Rules

There are **three independent gates**. A lesson is `published` only if all three pass; otherwise the Documentizer retries or falls back.

### 5.1 Gate A — JSON Schema Validation

- `CleanDocument` and `StructuredLesson` are validated against Pydantic models AND exported JSON Schemas (`schema/clean_document.schema.json`, `schema/structured_lesson.schema.json`).
- **Hard requirement**: schema must validate. Any error → retry.
- Schemas are versioned via `schema_version`.

### 5.2 Gate B — Source Grounding

For every claim-bearing field, the validator checks that it can be linked back to `RawDocument` text.

**Definitions:**

- `citation`: short verbatim quote (or close paraphrase) from `RawDocument`.
- `source_pages`: list of 1-based page numbers.
- `grounded(citation, page)`: function that checks whether `citation` (case/whitespace-normalized) appears (substring) on the given page's text. If not, fallback: fuzzy match with ratio ≥ 0.85.

**Rules:**

1. Every Concept, every Block with `type ∈ {definition, example, relationship}`, every key_point, and every example MUST have non-empty `citation` and non-empty `source_pages`.
2. `citation` MUST ground on at least one of its declared `source_pages`. If not, that field is **ungrounded**.
3. `page_coverage[p]` MUST be ≥ 0.60 for every source page that has non-trivial text. Pages below this threshold MUST appear in `provenance.ungrounded_block_ids` (with at least one block referencing them) OR be explicitly listed as `intentionally_dropped` (e.g. decorative spreads).
4. The validator MUST refuse to mark `grounding_score ≥ grounding_threshold` if any key concept is ungrounded.

**Score:**

```
grounding_score = grounded_fields / total_claim_fields
                 * page_coverage_factor
```

Where:
- `grounded_fields` = claim-bearing fields that pass rule 2.
- `total_claim_fields` = all claim-bearing fields.
- `page_coverage_factor` = mean(page_coverage[p] for p in pages_with_text). Penalises silent drops.

Defaults:
- `grounding_threshold = 0.80`
- `page_coverage_floor = 0.60`

### 5.3 Gate C — Confidence / Error Handling

For every Concept and every Teach-Back Chunk:

- `confidence` ∈ [0.0, 1.0]. If provider does not emit one, the validator assigns `confidence = 0.5` (unknown).
- `min_confidence = 0.65`. Chunks below this are flagged `low_confidence` and re-attempted.
- **Hallucination guard**: any block whose `citation` appears on **zero** pages AND whose text overlaps no other block's source pages → confidence is forced to `0.0` and the block is dropped (with reason in `validation.issues`).

**Final status:**

| Gate A | Gate B | Gate C | Status |
|---|---|---|---|
| pass | pass | pass | `passed` (publish) |
| pass | pass | warn | `warned` (publish with issues) |
| fail | — | — | `failed` (retry/fallback) |
| pass | fail | — | `failed` (retry/fallback) |
| pass | pass | fail | `failed` (retry/fallback; cannot publish a chunk below confidence floor) |

---

## 6. Retry / Fallback Behaviour

A single `DocumentizerPipeline.process(document_id)` performs **at most N attempts** before falling back. Each attempt differs in prompt or chunking strategy, never in input data.

### 6.1 Attempt ladder

| # | Strategy | Trigger |
|---|---|---|
| 1 | Default prompt, default chunking | first attempt |
| 2 | Stricter grounding prompt (force citations on every concept) | Gate B fail |
| 3 | Smaller `target_chunks_max` to reduce chunk-level error probability | Gate C fail (low confidence) |
| 4 | `MockProvider` deterministic output (last-resort fallback) | All retries exhausted |

Total attempts: 3 AI attempts + 1 deterministic fallback = 4.

### 6.2 Backoff
- Per-attempt timeout: 30 s (configurable).
- Between attempts: linear backoff, 1 s, 2 s, 4 s.
- Total worst-case wall time per document: ~3 minutes.

### 6.3 Cache
- The provider response for each attempt is **always cached** to `data/processed/{doc_id}/documentizer/attempt_N.json` (full request + response payload). Re-runs replay from cache when inputs match.
- `lesson.json` is only written on a successful publish (Gate A & B pass, Gate C ≥ warn).

### 6.4 Observability
Each attempt writes a structured log:

```
event=documentizer.attempt
document_id=...
attempt=2
provider=gemini
model=gemini-2.5-flash
grounding_score=0.74
schema_ok=true
low_confidence_chunks=2
duration_ms=8421
issue_codes=[grounding_below_threshold]
```

`issue_codes` is a closed list (see §5.3). The pipeline never publishes a lesson with an `issue_code` not in this list.

---

## 7. Proposed File Structure (additive only — no Phase 3A file changes)

```
vlearn-teach-back-mvp/
├── app/
│   ├── models/
│   │   ├── raw_document.py            (UNCHANGED — Phase 3A)
│   │   ├── clean_document.py          NEW — CleanDocument schema
│   │   ├── structured_lesson.py       NEW — StructuredLesson schema
│   │   ├── teach_back_chunk.py        NEW — TeachBackChunk + targets
│   │   ├── lesson.py                  (UNCHANGED — exists for backward compat;
│   │   │                              adapters translate StructuredLesson → Lesson)
│   │   └── validation_report.py       NEW — ValidationReport model
│   │
│   ├── schemas/                       NEW
│   │   ├── clean_document.schema.json
│   │   └── structured_lesson.schema.json
│   │
│   ├── services/
│   │   ├── raw_document_service.py   (UNCHANGED)
│   │   ├── phase3a_pipeline.py       (UNCHANGED)
│   │   ├── page_renderer.py           NEW — optional: PDF → PNG per page
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── ai_provider.py         NEW — AIProvider Protocol
│   │   │   ├── gemini_provider.py     NEW — Gemini concrete (stubbed — no real call)
│   │   │   ├── mock_provider.py       NEW — deterministic provider for tests
│   │   │   └── provider_factory.py    NEW — selects provider via AI_PROVIDER env
│   │   │
│   │   ├── documentizer_input.py      NEW — assembles DocumentizerInput
│   │   ├── documentizer.py            NEW — calls AIProvider.documentize + parses CleanDocument
│   │   ├── grounding_validator.py     NEW — Gate B (source grounding)
│   │   ├── json_schema_validator.py   NEW — Gate A (Pydantic + JSON Schema)
│   │   ├── confidence_validator.py    NEW — Gate C
│   │   ├── lesson_builder.py          NEW — CleanDocument → StructuredLesson
│   │   ├── documentizer_pipeline.py   NEW — orchestrates retry/fallback/publish
│   │   ├── lesson_service.py          UNCHANGED
│   │   └── lesson_repository.py       UNCHANGED (consumes StructuredLesson via adapter)
│   │
│   ├── repositories/
│   │   ├── structured_lesson_repository.py   NEW — read/write lesson.json
│   │   └── validation_report_repository.py   NEW — read/write validation sidecar
│   │
│   ├── adapters/
│   │   └── structured_lesson_adapter.py      NEW — StructuredLesson → Lesson (for UI)
│   │
│   ├── config.py                      UNCHANGED — already loads GEMINI_* env
│   ├── main.py                        UNCHANGED
│   ├── routers/
│   │   ├── api.py                     UNCHANGED
│   │   └── pages.py                   UNCHANGED
│   └── ...
│
├── tests/
│   ├── test_phase3a_pipeline.py       (UNCHANGED)
│   ├── test_phase3a5_clean_document.py          NEW
│   ├── test_phase3a5_structured_lesson.py       NEW
│   ├── test_phase3a5_provider_factory.py        NEW
│   ├── test_phase3a5_provider_mock.py           NEW
│   ├── test_phase3a5_provider_gemini_stub.py    NEW (provider invoked but real call disabled)
│   ├── test_phase3a5_grounding.py               NEW
│   ├── test_phase3a5_json_schema.py             NEW
│   ├── test_phase3a5_confidence.py              NEW
│   ├── test_phase3a5_pipeline_retry.py          NEW
│   ├── test_phase3a5_pipeline_fallback.py       NEW
│   └── test_phase3a5_adapter.py                 NEW
│
├── data/
│   └── processed/{doc_id}/
│       ├── raw.json                          (Phase 3A — unchanged)
│       ├── documentizer/attempt_1.json       NEW
│       ├── documentizer/attempt_2.json       NEW
│       ├── documentizer/attempt_3.json       NEW
│       ├── documentizer/attempt_fallback.json NEW
│       ├── lesson.json                       NEW
│       └── validation.json                   NEW
│
├── .env                                  (UNCHANGED — already has GEMINI_*)
├── .env.example                          (UNCHANGED)
├── PHASE3A_PDF_AUDIT.md                  (UNCHANGED — read-only)
├── PHASE3A5_DESIGN.md                    ← THIS FILE
└── PHASE3A5_AUDIT.md                     NEW — written only after implementation
```

### 7.1 Configuration (additions to .env.example only — no runtime hardcoding)

```
GEMINI_API_KEY=               # already present; required for live provider
GEMINI_MODEL=gemini-2.5-flash  # already present
AI_PROVIDER=gemini             # already present
DOC3A5_ATTEMPTS=3
DOC3A5_GROUNDING_THRESHOLD=0.80
DOC3A5_MIN_CONFIDENCE=0.65
DOC3A5_TIMEOUT_SECONDS=30
DOC3A5_ENABLE_PAGE_IMAGES=false
DOC3A5_PAGE_IMAGE_DPI=150
DOC3A5_LANGUAGE=en
```

---

## 8. Implementation Plan (Phase 3A.5)

Phases are ordered. Each phase ends with a test gate. Phase 3A tests MUST stay green throughout.

### Phase 3A.5.1 — Schemas & Validation Reports (no AI)
1. Implement `CleanDocument`, `StructuredLesson`, `TeachBackChunk`, `ValidationReport` Pydantic models.
2. Export JSON Schemas to `app/schemas/`.
3. Unit tests for every model (round-trip, defaults, edge cases, version field).
4. **Gate:** all Phase 3A tests still pass.

### Phase 3A.5.2 — Provider Abstraction (no real AI call)
1. Implement `AIProvider` Protocol.
2. Implement `MockProvider` with deterministic JSON output.
3. Implement `ProviderFactory` selecting on `AI_PROVIDER` env.
4. Implement `GeminiProvider` **class skeleton only** — constructor reads env, but `documentize()` raises `NotImplementedError("Phase 3A.5.x: real Gemini call not enabled")` until later phase.
5. Tests for factory (env-driven selection) and mock round-trip.
6. **Gate:** no Phase 3A code touched; all Phase 3A tests still pass.

### Phase 3A.5.3 — Documentizer (no real AI call)
1. Implement `DocumentizerInput` builder.
2. Implement `Documentizer.documentize(input, provider=mock)` — calls provider, parses, validates against `CleanDocument` schema.
3. Unit tests with `MockProvider`.
4. **Gate:** clean document round-trip works end-to-end.

### Phase 3A.5.4 — Validators (Gate A + B + C)
1. Implement `JsonSchemaValidator` (Gate A).
2. Implement `GroundingValidator` against `RawDocument` (Gate B).
3. Implement `ConfidenceValidator` (Gate C) including hallucination guard.
4. Tests with crafted `RawDocument` and `CleanDocument` fixtures (ungrounded blocks, low-confidence blocks, dropped pages).
5. **Gate:** all validator unit tests pass.

### Phase 3A.5.5 — Lesson Builder
1. Implement `LessonBuilder.build(clean_document) → StructuredLesson` (assigns chunk ids, fills teach-back targets, attaches provenance).
2. Tests for builder output shape and target population.
3. **Gate:** all unit tests pass.

### Phase 3A.5.6 — Pipeline Orchestrator
1. Implement `DocumentizerPipeline.process(document_id)`:
   - Loads `RawDocument` (read-only).
   - Runs attempt ladder.
   - Validates each attempt.
   - On success: builds `StructuredLesson`, writes `lesson.json` + `validation.json`.
   - On failure: writes best-attempt artifact + raises `DocumentizerFailed`.
2. Tests for: happy path, retry ladder, fallback to `MockProvider`, cache replay.
3. **Gate:** integration test runs end-to-end with `MockProvider`.

### Phase 3A.5.7 — Adapter (UI compatibility)
1. Implement `StructuredLessonAdapter.to_lesson(structured) → Lesson`.
2. Wire `LessonRepository` (existing, unchanged) to consume `lesson.json` **only when present**, fall back to existing behaviour otherwise. This is purely additive — Phase 3A behaviour is preserved.
3. **Gate:** existing UI tests still pass; new tests cover the new branch.

### Phase 3A.5.8 — Audit
1. Write `PHASE3A5_AUDIT.md` mirroring `PHASE3A_PDF_AUDIT.md`.
2. Add a section to the repo root `README.md` describing the new pipeline boundary.
3. **Gate:** documentation matches implementation.

### Out of scope (NOT in this plan)
- Real Gemini API call implementation (deferred — only stubbed provider class).
- UI changes.
- Persistence beyond the JSON files described.

---

## 9. Test Plan (additive; Phase 3A tests untouched)

### Unit
- Schema round-trips for every model.
- Provider factory env selection.
- `MockProvider` deterministic output.
- `GeminiProvider` constructor raises on missing key; does not call network.
- Grounding validator: substring match, fuzzy match, page coverage, hallucination guard.
- JSON schema validator: success/failure cases.
- Confidence validator: floor enforcement, low-confidence flagging.

### Integration
- `DocumentizerPipeline` happy path with `MockProvider`:
  - given a known `RawDocument` → produces a valid `lesson.json` + `validation.json`.
- `DocumentizerPipeline` retry:
  - given a `MockProvider` that fails Gate B on attempt 1 and passes on attempt 2 → retries and publishes.
- `DocumentizerPipeline` fallback:
  - given all attempts fail → publishes `attempt_fallback.json` and `lesson.json` from `MockProvider`; does not raise.
- `LessonRepository` integration:
  - given `lesson.json` present → returns the adapter-produced `Lesson`;
  - given `lesson.json` absent → existing JSON fallback or PDF path runs unchanged.

### Non-regression
- All 61 Phase 3A tests still pass.
- `lesson.html` still renders with the new `Lesson` shape.

### Property / fuzz
- Grounding validator never raises on arbitrary input; returns score in [0, 1].
- `MockProvider` produces a `CleanDocument` that round-trips through the schema validator 100% of the time.

---

## 10. Risk Register

| Risk | Mitigation |
|---|---|
| Phase 3A invariants accidentally violated | Read-only contract on `RawDocument` enforced by tests; CI gate. |
| API key leak | Never logged; `.env` in `.gitignore`; provider reads env at construction only. |
| Provider outage | Attempt ladder + deterministic fallback (`MockProvider`). |
| Silent content drops | `page_coverage` floor + `ungrounded_block_ids` in provenance. |
| Hallucinated content | `citation` grounding + hallucination guard in confidence gate. |
| Schema drift | Versioned `schema_version` + JSON Schema exported to disk; CI validates. |
| Cost overrun | Hard cap on attempts (`DOC3A5_ATTEMPTS=3`); provider response cached. |

---

## 11. Open Questions (please confirm before implementation)

1. **Language default**: Default `DOC3A5_LANGUAGE=en` or auto-detect? (default proposed: `en`)
2. **Page images**: Enable by default? (default proposed: `false` — text-only is sufficient for our slide decks; flip the flag to add visual grounding.)
3. **Adapter strategy**: Convert `StructuredLesson → existing Lesson` for UI compatibility, OR replace the UI contract? (default proposed: adapter; existing UI keeps working.)
4. **Chunk granularity**: 3–12 chunks per lesson, or derive from PDF section count? (default proposed: 3–12.)
5. **Persistence**: Write `lesson.json` on every successful publish (overwrites prior), or version it (`lesson.v1.json`, `lesson.v2.json`)? (default proposed: overwrite + bump `validation.json.performed_at`.)

---

## 12. Deliverables Checklist (for the implementation phase, not this design phase)

- [ ] All files in §7 created.
- [ ] No Phase 3A file modified.
- [ ] All Phase 3A tests still pass.
- [ ] All §9 tests pass.
- [ ] `PHASE3A5_AUDIT.md` written with same structure as `PHASE3A_PDF_AUDIT.md`.
- [ ] Root `README.md` updated to mention the new pipeline boundary.
- [ ] `.env.example` updated with the new keys from §7.1.

---

**Awaiting approval.** No code will be written until §11 questions are answered (or accepted as-is) and this design is approved.