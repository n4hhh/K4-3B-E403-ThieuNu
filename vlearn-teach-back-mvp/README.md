# VLearn Teach Back Agent MVP

A standalone, scaffold-only MVP for the **VLearn Teach Back Agent** — a learning workflow where the student *teaches* a lesson back to an AI Agent chunk by chunk, and the Agent validates understanding before moving on.

This project currently contains the **foundation only** (directory layout, FastAPI skeleton, models, services, repositories, mock data, templates, static assets, and test skeletons). The complete teaching-loop behaviour will be implemented in subsequent phases.

---

## 1. Purpose

The Teach Back Agent replaces the typical "watch video → answer quiz" loop with a **stateful teaching workflow**:

```
Lesson → Knowledge Chunks → Per-chunk Teaching Loop → Validation → Lesson Result → Quiz
```

The student must explain each knowledge chunk. The Agent validates the explanation against the source material. If gaps are detected, the Agent asks targeted follow-up questions. Only when all chunks pass does the session move to the Learning Result and Quiz.

---

## 2. Architecture

A single FastAPI process serving both server-rendered pages (Jinja2 templates + Bootstrap 5) and JSON APIs for client-side calls.

```
Browser ─┬─► /lesson/{id}             (page)
         ├─► /lesson/{id}/teach       (page)
         ├─► /session/{id}            (page)
         ├─► /session/{id}/result     (page)
         ├─► /lesson/{id}/quiz        (page)
         │
         └─► /api/...                 (JSON API for chat, validation, next-chunk)

FastAPI
   ├── routers/pages.py        ─ page routes
   ├── routers/api.py          ─ API routes
   ├── services/
   │     ├── lesson_service.py        ─ load lesson, chunks, quiz
   │     ├── teaching_service.py      ─ session lifecycle, chunk tracking
   │     ├── validator_service.py     ─ mock validator (placeholder)
   │     └── mock_agent_service.py    ─ mock agent response (stub)
   ├── repositories/
   │     ├── lesson_repository.py     ─ reads data/lessons.json
   │     └── session_repository.py    ─ in-memory session store
   └── models/                ─ Pydantic v2 domain models
```

### Key domain concepts

- **Lesson** — the unit the student is studying (e.g. *REST API & HTTP Methods*).
- **LessonChunk** — a discrete knowledge chunk inside a lesson. Each chunk has a title, description, and key points.
- **TeachingSession** — one student attempt at teaching back a single lesson.
- **TeachingMessage** — one turn in the conversation inside a chunk.
- **ValidationResult** — the Agent's verdict on a student's explanation (pass / gap + reasons).
- **Quiz / QuizQuestion** — end-of-lesson assessment.

---

## 3. Directory Structure

```
vlearn-teach-back-mvp/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── pages.py
│   │   └── api.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── lesson.py
│   │   ├── session.py
│   │   └── message.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── lesson_service.py
│   │   ├── teaching_service.py
│   │   ├── validator_service.py
│   │   └── mock_agent_service.py
│   └── repositories/
│       ├── __init__.py
│       ├── lesson_repository.py
│       └── session_repository.py
├── data/
│   └── lessons.json
├── templates/
│   ├── base.html
│   ├── lesson.html
│   ├── session_intro.html
│   ├── teaching.html
│   ├── result.html
│   └── quiz.html
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── layout.css
│   │   └── components.css
│   └── js/
│       ├── app.js
│       ├── teaching.js
│       ├── result.js
│       └── quiz.js
├── tests/
│   ├── __init__.py
│   ├── test_lesson.py
│   ├── test_session.py
│   └── test_teaching_loop.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 4. Requirements

- **Python 3.11+**
- pip

Dependencies (declared in `requirements.txt`):

- `fastapi`
- `uvicorn[standard]`
- `jinja2`
- `pydantic`
- `pytest`
- `httpx`

---

## 5. Setup

From this directory:

```bash
# (recommended) create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## 6. Run

```bash
uvicorn app.main:app --reload
```

Then open:

```
http://127.0.0.1:8000
```

Available routes (scaffold):

| Method | Path                                     | Purpose                          |
|--------|------------------------------------------|----------------------------------|
| GET    | `/`                                      | Index (redirects / placeholder)  |
| GET    | `/lesson/{lesson_id}`                    | Lesson detail page               |
| GET    | `/lesson/{lesson_id}/teach`              | Session intro page               |
| GET    | `/session/{session_id}`                  | Teaching session page            |
| GET    | `/session/{session_id}/result`           | Lesson result page               |
| GET    | `/lesson/{lesson_id}/quiz`               | Quiz page                        |
| GET    | `/api/lessons/{lesson_id}`               | Lesson JSON                      |
| POST   | `/api/teaching-sessions`                 | Create teaching session          |
| GET    | `/api/teaching-sessions/{session_id}`    | Session state JSON               |
| POST   | `/api/teaching-sessions/{session_id}/messages` | Send student message      |
| POST   | `/api/teaching-sessions/{session_id}/next`     | Move to next chunk         |
| GET    | `/api/teaching-sessions/{session_id}/result`    | Lesson learning result    |
| GET    | `/api/lessons/{lesson_id}/quiz`                | Quiz JSON                |

---

## 7. Tests

```bash
pytest
```

Tests are currently **skeletons** that verify the application boots, routes are registered, and the lesson JSON loads. They will be expanded as features are implemented.

---

## 8. Current Scope (this phase)

- ✅ Project layout
- ✅ FastAPI application entry point
- ✅ Page + API route skeletons
- ✅ Pydantic domain models (`Lesson`, `LessonChunk`, `TeachingSession`, `TeachingMessage`, `ValidationResult`, `Quiz`, `QuizQuestion`)
- ✅ Service-layer interfaces (`LessonService`, `TeachingService`, `ValidatorService`, `MockAgentService`)
- ✅ Repository layer (`LessonRepository` reading JSON, `SessionRepository` in-memory)
- ✅ Mock lesson data: **REST API & HTTP Methods** with 5 chunks + 3 quiz questions
- ✅ Jinja2 templates with Bootstrap 5 CDN
- ✅ Static CSS / JS placeholders
- ✅ Test skeletons
- ✅ `requirements.txt`, `README.md`, `.gitignore`

### UI Features

- ✅ **Collapsible long content** on the lesson detail page. Four blocks are now collapsible via a unified helper `bindCollapsibles()` in `static/js/app.js`:
  1. **Description** (`summary` + `description`) — `.collapsible-text` with `data-lines="6"`.
  2. **Transcript Preview** — `.collapsible-text` with `data-lines="6"` inside `.transcript-box`. The toggle button sits inline (overlay on the pink fade gradient) when collapsed, then transitions to an inline-under-text button when expanded.
  3. **Objectives** (Mục tiêu học tập) — `.collapsible-list` wrapping the `<ul>` with `data-lines="4"`.
  4. **Chunks Overview** (Các phần trong bài, sidebar) — `.collapsible-list` wrapping `.chunk-preview` with `data-lines="4"`.

  For all four, the chevron icon rotates 180° when expanded (`aria-expanded="true"`) and the label flips "Xem thêm" → "Thu gọn". If the content fits within the visible lines, the toggle is hidden automatically — short descriptions stay readable without an unnecessary click.

  Implementation:
  - `templates/lesson.html` — markup with `.collapsible-text` / `.collapsible-list` / `.toggle-text-btn` (block-level + inline variants).
  - `static/css/components.css` — collapse / fade styles for both wrappers; pseudo-element fade for lists via `::after` when `.has-overflow`.
  - `static/js/app.js` — `bindCollapsibles()` measures overflow per block (line-height for text, item-height for lists), wires the click handler, and updates `aria-expanded` + `aria-controls` for accessibility.

- ✅ **Structured transcript rendering** (Tóm tắt nội dung). The lesson detail page now shows the transcript as a hierarchy of typed blocks (`heading` / `bullet` / `definition` / `example` / `table` / `note`) instead of a wall of plain text. Three render paths, picked automatically per lesson:
  1. **Structured** — when a `StructuredLesson` is available via `PublishedLessonRepository` (i.e. the Documentizer has run), we render the published `sections[].blocks[]` directly.
  2. **AI-assisted** — `TranscriptFormatterService.format_with_ai()` parses the raw transcript into a focused prompt for the configured AI provider (Gemini by default), parses the JSON response, and persists the result to `data/transcript_cache/{sha256}.json` so re-renders are free.
  3. **Heuristic fallback** — a deterministic, zero-network regex-based formatter that splits transcripts into headings (ALL-CAPS short lines), bullets (`•`, `-`, numbered), `Term: def` definitions, and paragraphs (notes). Used when AI is unavailable or the heuristic already produces well-structured output.

  Each block type has its own CSS class (`.transcript-heading`, `.transcript-bullet`, `.transcript-definition`, `.transcript-example`, `.transcript-table`, `.transcript-note`) and a small "Nguồn: ai | heuristic | structured | cache" badge appears under the block so reviewers know which path produced the output.

  Implementation:
  - `app/services/transcript_formatter_service.py` — the `TranscriptFormatterService` plus heuristic + AI helpers (`_heuristic_format`, `_try_ai_reformat`).
  - `app/routers/pages.py` — `lesson_detail` loads the published `StructuredLesson`, calls `format_with_ai()`, and prefers the structured blocks when available.
  - `templates/lesson.html` — new `{% macro render_block(block) %}` renders each block type; the transcript section iterates over `formatted_transcript.blocks`.
  - `static/css/components.css` — per-block-type styling (pink headings, dashed bullets, definition cards, example callouts, table wrapper, source badge).
  - `data/transcript_cache/` — per-transcript JSON cache, content-hashed so it survives lesson reloads.
  - `requirements.txt` — adds `google-genai>=1.0.0` so the AI path is enabled out of the box.

---

## 9. Out of Scope (next phases)

The following are **explicitly not** implemented in this scaffold:

- ❌ Real AI / LLM integration (Gemini, OpenAI, …)
- ❌ Real transcript mining / lesson-content ingestion
- ❌ Production authentication / user accounts
- ❌ Persistent database (Postgres, SQLite, …)
- ❌ External VLearn API integration
- ❌ Production analytics
- ❌ Production deployment / Docker

These will be added in subsequent phases per the product specification in `.cursor`.
