# IMPLEMENTATION UI PLAN — VLearn Teach Back MVP

## Source Audit Summary

### 1. Product Behavior (`.cursor`)
- **Core Loop**: Lesson → Chunk → Conversation
- **7 Screens**: Lesson Detail, Session Intro, Teaching Session, Chunk Complete, Lesson Result, Quiz
- **Teaching Loop**: Student explains → Agent validates → Gap? → Ask back → Clarify → Validate → Pass → Next chunk
- **Key Models**: TeachingSession, ValidationResult, ChunkStatus
- **Agent Rules**: Never reveals answers, only asks clarifying questions

### 2. Visual Design (vlearn-mockup.html)
- **Theme**: Pink/hồng phấn with Duolingo-like friendly feel
- **Colors**: Pink gradient (#ff6b95 → #e84d7f), cream background (#fffaf3)
- **Components**: Session shell, chat bubbles, stepper, gap badge, hint chips, mascot concept
- **Typography**: Nunito font, rounded corners, soft shadows
- **Animations**: Bounce, pulse, slide-up for messages

### 3. Existing Backend (vlearn-teach-back-mvp)
- **Framework**: FastAPI + Jinja2 + Bootstrap 5 + Bootstrap Icons
- **Routes**: 6 page routes, 7 API routes
- **Services**: TeachingService, ValidatorService, MockAgentService (all working)
- **State**: In-memory session repository, JSON lesson data

---

## Product Mapping

| .cursor Requirement | Screen | Component | API |
|---|---|---|---|
| Lesson selection | Lesson Detail | Lesson card, CTA | GET /api/lessons/{id} |
| Session intro | Session Intro | Chunk preview, start button | POST /api/teaching-sessions |
| Teaching loop | Teaching Session | Chat area, composer, stepper | POST /api/teaching-sessions/{id}/messages |
| Gap detection | Chat (gap badge) | Agent follow-up question | Included in message response |
| Chunk pass | UI state change | Next chunk button enabled | ValidationResult.passed |
| Lesson complete | Result screen | Celebration, summary | GET /session/{id}/result |
| Quiz | Quiz screen | Question cards, feedback | GET /api/lessons/{id}/quiz |

---

## Mockup Mapping

| Mockup Component | Implementation | CSS File |
|---|---|---|
| `.topbar` + `.nav-pills` | Enhanced navbar in base.html | style.css |
| `.card` | Bootstrap card with custom shadows | components.css |
| `.btn` (primary) | Pink gradient button style | components.css |
| `.session-shell` | Teaching session container | components.css |
| `.session-header` + `.stepper` | Progress stepper with dots | components.css |
| `.chat-area` + `.msg` | Message bubbles (agent/user) | components.css |
| `.bubble` | Chat bubble styling | components.css |
| `.gap-badge` | Gap detection indicator | components.css |
| `.composer` + `textarea` | Input area | components.css |
| `.hint-chip` | Hint suggestion buttons | components.css |
| `.mascot` + animations | Mascot emoji/decorations | style.css |
| `.chunk-row` | Chunk list item | components.css |
| `.celebrate` | Success celebration | components.css |
| `.quiz-*` | Quiz UI components | components.css |

---

## Existing Code Mapping

| Existing Route/Service | UI Template | JS File |
|---|---|---|
| `/lesson/{id}` | lesson.html | (static) |
| `/lesson/{id}/teach` | session_intro.html | app.js |
| `/session/{id}` | teaching.html | teaching.js |
| `/session/{id}/result` | result.html | result.js |
| `/lesson/{id}/quiz` | quiz.html | quiz.js |
| TeachingService | teaching.html | teaching.js |
| ValidatorService | (server-side) | (server-side) |
| MockAgentService | (server-side) | (server-side) |

---

## Files to CREATE

```
vlearn-teach-back-mvp/
├── static/css/
│   └── (update existing files with VLearn styling)
└── templates/
    └── (update existing templates with mockup-inspired UI)
```

---

## Files to MODIFY

| File | Changes |
|---|---|
| `static/css/style.css` | Add VLearn colors, theme variables, mascot styles |
| `static/css/components.css` | Add session shell, chat UI, stepper, quiz components |
| `templates/base.html` | Enhanced navbar with VLearn branding |
| `templates/lesson.html` | VLearn cards, progress, CTA styling |
| `templates/session_intro.html` | Chunk preview, mascot, start button |
| `templates/teaching.html` | Session shell, stepper, chat, hints |
| `templates/result.html` | Celebration, summary stats |
| `templates/quiz.html` | Quiz progress, feedback UI |
| `static/js/teaching.js` | Loading state, typing indicator, better UX |
| `static/js/quiz.js` | Quiz flow with answer feedback |
| `static/js/result.js` | Enhanced result display |

---

## Files to PRESERVE (untouched)

- `.cursor` — READ ONLY
- `vlearn-mockup.html` — READ ONLY
- `README.md` (parent) — READ ONLY
- `vlearn-teach-back-mvp/app/` — Existing backend architecture
- `vlearn-teach-back-mvp/data/` — Existing lesson data
- `vlearn-teach-back-mvp/tests/` — Existing tests

---

## CSS Architecture

```css
/* style.css — Global theme */
:root {
    --vl-pink-50: #fff5f7;
    --vl-pink-100: #ffe4ec;
    --vl-pink-500: #ff6b95;
    --vl-pink-700: #c83768;
    --vl-cream: #fffaf3;
    --vl-green: #58cc02;
    --vl-orange: #ff9600;
}

/* components.css — UI components */
.session-shell { ... }
.stepper { ... }
.chat-area { ... }
.msg.agent { ... }
.msg.user { ... }
.bubble { ... }
.gap-badge { ... }
.composer { ... }
.hint-chip { ... }
.chunk-row { ... }
.celebrate { ... }
.quiz-* { ... }

/* layout.css — Unchanged */
```

---

## JavaScript Architecture

```javascript
// app.js — Global utilities (EXISTING, minimal changes)
// teaching.js — Teaching session interaction
//   - appendMessage(author, content)
//   - showTypingIndicator()
//   - hideTypingIndicator()
//   - enableNextChunk()
//   - handleValidation(response)
// quiz.js — Quiz interaction
//   - pickAnswer(option, questionId)
//   - showFeedback(isCorrect, explanation)
//   - nextQuestion()
// result.js — Result display (EXISTING, minimal changes)
```

---

## Responsive Behavior

| Viewport | Teaching Layout |
|---|---|
| 1440px+ | Sidebar (chunks) + Main (chat) |
| 1024px | Same as above |
| 768px | Collapsible chunk sidebar |
| 390px | Full-width chat, collapsible progress |

---

## Accessibility

- Semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>`
- Keyboard navigation: Tab through buttons, Enter to send
- Focus visible: Custom focus styles matching theme
- Aria labels: On icon-only buttons
- Screen reader: Proper heading hierarchy
- Color contrast: Main text on cream/pink passes AA

---

## Implementation Priority

1. **Phase 1**: CSS theming (VLearn colors, components)
2. **Phase 2**: Template updates (base, lesson, session_intro)
3. **Phase 3**: Teaching session UI (teaching.html + teaching.js)
4. **Phase 4**: Result + Quiz UI
5. **Phase 5**: Polish (animations, responsive, accessibility)

---

## Definition of Done Checklist

- [ ] .cursor read and understood
- [ ] vlearn-mockup.html inspected and mapped
- [ ] Existing backend verified (15/15 tests pass)
- [ ] CSS files updated with VLearn styling
- [ ] base.html updated with enhanced navbar
- [ ] lesson.html updated with VLearn cards
- [ ] session_intro.html updated with chunk preview
- [ ] teaching.html updated with session shell, stepper, chat
- [ ] result.html updated with celebration UI
- [ ] quiz.html updated with progress + feedback
- [ ] teaching.js enhanced with loading/typing states
- [ ] quiz.js enhanced with answer feedback
- [ ] Responsive design verified at 390px, 768px, 1024px, 1440px
- [ ] All existing tests still pass
- [ ] No files outside vlearn-teach-back-mvp/ modified
