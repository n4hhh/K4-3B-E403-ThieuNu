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
