# IMPLEMENTATION PLAN — PHASE 3A: Connect Real PDF Lesson Data

## Current State

- `/data/lesson/` directory does NOT exist in the repo
- No PDF files exist anywhere in the project
- Existing code uses `data/lessons.json` as the lesson source
- 15/15 tests pass

## Approach

Since no PDFs exist yet, but the architecture must be PDF-driven:

1. **Build the full PDF pipeline** so when PDFs are placed in `../data/lesson/`, they work
2. **Graceful fallback** — if no PDFs found, log a warning and fall back to JSON so the app stays runnable
3. **Configurable path** via `VLEARN_LESSON_DIR` env var, defaulting to `../data/lesson`
4. **Cross-platform** — use `pathlib`, never absolute Windows paths
5. **PDF safety** — never modify, rename, move, delete any PDF

## Architecture

```
[App Startup]
   ↓
PDFLessonService.discover() → finds *.pdf in lesson_dir
   ↓
For each PDF: PDFReader.extract_text() → (pages, full_text)
   ↓
SectionDetector.detect_sections(pages) → [Section(title, start_page, content)]
   ↓
ChunkBuilder.build_chunks(sections) → [LessonChunk]
   ↓
LessonBuilder.build_lesson() → Lesson
   ↓
Cached in-memory → LessonRepository
   ↓
FastAPI routes → Templates (unchanged)
```

## Files to Create

| File | Purpose |
|------|---------|
| `app/config.py` | Settings via env vars |
| `app/services/pdf_lesson_service.py` | PDF discovery + extraction |
| `app/services/pdf_reader.py` | Low-level pypdf wrapper |
| `app/services/section_detector.py` | Heading/section detection |
| `tests/test_pdf_pipeline.py` | New tests for PDF flow |

## Files to Modify

| File | Change |
|------|--------|
| `app/repositories/lesson_repository.py` | Use PDFLessonService |
| `app/main.py` | Wire PDFLessonService into app.state |
| `requirements.txt` | Add pypdf |

## Section Detection Heuristic

For each page text:
1. Find lines matching heading patterns:
   - `^[A-Z][A-Z\s\d\.\-:]+$` (ALL CAPS lines)
   - `^\d+\.\s+[A-Z].+` (numbered headings)
   - `^Chapter\s+\d+` (chapter markers)
   - `^Section\s+\d+` (section markers)
2. Fallback: split by page boundary (each page = one chunk)
3. If a page has no heading, use the previous section's title or "Section N"

## Robustness

- Missing directory → log warning, fall back to JSON
- Empty directory → log warning, fall back to JSON
- PDFs with no detectable headings → per-page chunks
- Corrupted PDFs → skip with error log, continue with others
- Unicode/PDF text encoding issues → strip problematic chars

## Tests

- PDF discovery (existing + missing dir)
- Text extraction from a synthetic PDF
- Section detection
- Chunk creation
- Repository integration
- Fallback behavior

## Definition of Done

- [x] Real PDFs discovered (or graceful fallback)
- [x] PDF text extracted
- [x] Lesson created from PDF
- [x] Sections/chunks created
- [x] Page metadata preserved
- [x] LessonRepository uses PDF source
- [x] Existing UI still works
- [x] Existing tests pass (15/15)
- [x] PDF tests pass
- [x] No Gemini integration
- [x] No files outside vlearn-teach-back-mvp modified
