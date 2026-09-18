# FE.md — D · VLearn — Teach Back Agent MVP

## 0. Mục đích tài liệu

Tài liệu này là **Frontend Specification + UI/UX implementation brief** để Claude/Cursor có thể dựa vào đó xây dựng một **mockup frontend chạy được và bấm được** cho tính năng:

> **D · VLearn — Dạy lại cho Agent**

MVP mô phỏng tính năng sẽ được tích hợp trực tiếp vào VLearn. Không sử dụng bước copy/paste transcript từ người dùng.

Frontend cần thể hiện được learning workflow:

**Learn → Teach → Detect Gap → Ask Back → Re-explain → Validate → Next Chunk → Lesson Complete → Quiz**

---

# 1. Product Context

## 1.1. Feature

Học viên vừa hoàn thành một bài học ngắn trên VLearn. Thay vì chuyển ngay sang quiz, học viên chọn:

> **Dạy lại cho Agent**

AI đóng vai một "học trò" chưa hiểu bài.

Học viên phải giải thích lại nội dung bài học bằng lời của mình.

Agent:

- đọc nội dung bài học/transcript từ VLearn;
- chia bài thành các knowledge chunk;
- yêu cầu học viên giải thích từng chunk;
- đối chiếu lời giải thích với transcript/key points;
- phát hiện chỗ thiếu, mơ hồ hoặc sai;
- hỏi ngược đúng chỗ;
- không tiết lộ đáp án;
- không xác nhận "đã hiểu" khi quality bar chưa đạt;
- chỉ chuyển sang chunk tiếp theo khi chunk hiện tại đạt;
- chỉ hoàn thành session khi toàn bộ lesson chunks đạt.

---

# 2. Core Product Model

## 2.1. Hierarchy

```text
VLearn Lesson
│
└── Teaching Session
    │
    ├── Chunk 1
    │   └── Teaching Loop(s)
    │
    ├── Chunk 2
    │   └── Teaching Loop(s)
    │
    ├── Chunk 3
    │   └── Teaching Loop(s)
    │
    └── Chunk N
        └── Teaching Loop(s)
```

## 2.2. Three loop levels

### Level 1 — Lesson Loop

```text
Lesson
  ↓
Chunk 1
  ↓
Chunk 2
  ↓
Chunk 3
  ↓
...
  ↓
All chunks passed
  ↓
Lesson complete
```

### Level 2 — Chunk Loop

```text
Agent asks
  ↓
Student explains
  ↓
Validate
  ↓
Gap?
 ├── YES → Agent asks targeted question
 │           ↓
 │         Student clarifies
 │           ↓
 │         Validate again
 │
 └── NO → Chunk PASS
```

### Level 3 — Conversation Loop

```text
Agent message
  ↓
Student message
  ↓
Agent detects gap
  ↓
Agent follow-up
  ↓
Student explanation
  ↓
Agent validation
```

---

# 3. MVP Scope

## 3.1. MVP MUST HAVE

- VLearn-like lesson detail page.
- Lesson transcript/content represented as existing lesson data.
- "Dạy lại cho Agent" CTA.
- Teaching Session introduction.
- Automatic lesson chunking represented by mock data.
- Chunk progress.
- Chat-based teaching interface.
- Agent asks student to teach.
- Student can type an explanation.
- Agent can return scripted/mock AI responses based on the current state.
- Gap detection state.
- Targeted follow-up question state.
- Re-explanation state.
- Chunk PASS state.
- Next chunk transition.
- Overall lesson progress.
- Lesson completion screen.
- Learning result summary.
- Continue to Quiz CTA.
- Quiz screen with at least 3 mock questions.
- Back/navigation controls.
- Session state preserved while navigating within the prototype.
- Responsive desktop + mobile layout.

## 3.2. MVP DOES NOT NEED

- Real Gemini/OpenAI API.
- Real VLearn backend.
- Real authentication.
- Real database.
- Real transcript extraction.
- Real speech-to-text.
- Real analytics backend.
- Production-grade AI evaluation.
- Payment.
- Admin interface.

The mockup must **look and behave as if these services exist**, but frontend can use local JavaScript mock data/state.

---

# 4. Primary User

## Student

Context:

- Has just completed a 1–3 minute lesson.
- Wants to make sure they actually understand.
- Is about to take a quiz.
- May know the answer but cannot explain why.
- Needs an agent that asks back instead of giving the answer.

---

# 5. User Flow

```text
START
  │
  ▼
[Lesson Detail]
  │
  │ Student finishes lesson
  ▼
[Click "Dạy lại cho Agent"]
  │
  ▼
[Teaching Session Intro]
  │
  │ Start
  ▼
[Teaching Session]
  │
  ▼
[Current Chunk]
  │
  ▼
[Agent asks student to teach]
  │
  ▼
[Student explains]
  │
  ▼
[Agent / Validator]
  │
  ├─────────────── GAP ───────────────┐
  │                                   │
  │                                   ▼
  │                           [Targeted Question]
  │                                   │
  │                                   ▼
  │                           [Student Clarifies]
  │                                   │
  │                                   └──► Validate
  │
  └──────────── PASS ────────────────►
                                      │
                                      ▼
                              [Chunk Complete]
                                      │
                                      ▼
                                Next Chunk?
                               /          \
                             YES           NO
                              │             │
                              ▼             ▼
                       [Current Chunk]  [Lesson Result]
                                             │
                                             ▼
                                       [Continue Quiz]
                                             │
                                             ▼
                                           [Quiz]
```

---

# 6. Screen Inventory

## SF-01 — Lesson Detail

Purpose:

Show a normal VLearn lesson and make the new feature discoverable.

Required UI:

- VLearn-style header/sidebar.
- Breadcrumb.
- Course name.
- Lesson title.
- Lesson progress.
- Video/transcript content.
- Learning objectives.
- "Dạy lại cho Agent" primary CTA.
- "Làm Quiz" secondary action.

Example:

```text
VLearn
─────────────────────────────────────────────
Course: Backend Fundamentals

Lesson 03
REST API & HTTP Methods

[ Video / Transcript Area ]

Learning objectives
✓ Understand REST API
✓ Explain HTTP methods
✓ Distinguish GET / POST / PUT / DELETE

─────────────────────────────────────────────
[ Dạy lại cho Agent ]      [ Làm Quiz ]
```

Interaction:

```text
Click "Dạy lại cho Agent"
        ↓
SF-02
```

---

# 7. SF-02 — Teaching Session Introduction

Purpose:

Explain the activity before starting.

UI:

```text
Dạy lại cho Agent

Bạn sẽ đóng vai người dạy.
Agent sẽ đóng vai học trò.

Bạn sẽ:
1. Giải thích từng phần của bài.
2. Trả lời các câu hỏi agent hỏi ngược.
3. Làm rõ những điểm còn thiếu hoặc chưa chính xác.

Agent sẽ không đưa đáp án khi bạn đang giải thích.

Lesson
REST API & HTTP Methods

5 phần cần dạy lại

[ Bắt đầu phiên học ]
```

Optional:

- Estimated time: 3–5 minutes.
- Progress indicator.
- Back to lesson.

Interaction:

```text
Click "Bắt đầu phiên học"
        ↓
SF-03
```

---

# 8. SF-03 — Teaching Session

This is the **PRIMARY SCREEN**.

## Layout

Desktop:

```text
┌───────────────────────────────────────────────────────────┐
│ VLearn       REST API & HTTP Methods       2 / 5          │
├───────────────┬───────────────────────────────────────────┤
│               │                                           │
│ Lesson Map    │          Teaching Conversation           │
│               │                                           │
│ ✓ REST API    │ 🤖 Agent                                  │
│ ✓ Client      │ Hãy dạy lại cho tôi khái niệm REST API.  │
│ ● HTTP        │                                           │
│ ○ Status      │ 👤 You                                    │
│ ○ Stateless   │ REST API là một kiến trúc...              │
│               │                                           │
│ Progress      │ 🤖 Agent                                  │
│ ██████░░ 40%  │ Tôi chưa rõ một điểm...                   │
│               │                                           │
│               │ ┌───────────────────────────────────────┐ │
│               │ │ Type your explanation...              │ │
│               │ └───────────────────────────────────────┘ │
│               │                         [ Gửi ]           │
└───────────────┴───────────────────────────────────────────┘
```

Mobile:

```text
┌─────────────────────────┐
│ REST API        2 / 5   │
│ ██████░░░░              │
├─────────────────────────┤
│                         │
│ 🤖 Agent                │
│                         │
│ Hãy dạy lại cho tôi...  │
│                         │
│ 👤 You                  │
│                         │
│ REST API là...          │
│                         │
│ 🤖 Agent                │
│                         │
│ Tôi chưa rõ...          │
│                         │
├─────────────────────────┤
│ Type explanation...     │
│                         │
│               [Gửi]     │
└─────────────────────────┘
```

---

# 9. Teaching Session Components

## 9.1. Header

Display:

- Course/Lesson title.
- Current chunk number.
- Total chunks.
- Overall progress.
- Exit/back button.

Example:

```text
← Exit     REST API & HTTP Methods       2 / 5
           ████████░░░░░░ 40%
```

---

## 9.2. Lesson Map

Show:

```text
✓ REST API
✓ Client – Server
● HTTP Methods
○ Status Codes
○ Stateless
```

States:

- `completed`
- `current`
- `locked`
- optionally `needs-review`

Rules:

- Future chunks remain locked.
- Current chunk is highlighted.
- Completed chunks show check icon.
- Do not allow skipping locked chunks in MVP.

---

# 10. Chat Message Types

Frontend should support these message types:

```javascript
{
  role: "agent",
  type: "prompt",
  content: "Hãy dạy lại cho tôi..."
}
```

```javascript
{
  role: "student",
  type: "explanation",
  content: "REST API là..."
}
```

```javascript
{
  role: "agent",
  type: "gap",
  content: "Tôi chưa hiểu..."
}
```

```javascript
{
  role: "agent",
  type: "validation",
  content: "Phần giải thích đã đạt..."
}
```

```javascript
{
  role: "system",
  type: "chunk_complete",
  content: "Phần này đã hoàn thành."
}
```

---

# 11. Core Teaching Loop UI States

The frontend must visually represent these states.

## State A — Agent Prompt

```text
🤖 Agent

Hãy dạy lại cho tôi:
"HTTP Methods"

Hãy giải thích bằng lời của bạn.
```

Input active.

---

## State B — Student Explanation

```text
👤 Bạn

HTTP Methods là các phương thức HTTP
dùng để xác định loại operation mà client
muốn thực hiện với resource.
```

---

## State C — Agent Detects Gap

```text
🤖 Agent

Tôi hiểu rằng HTTP Methods xác định
operation của client.

Nhưng tôi chưa rõ một điểm:

GET và POST khác nhau như thế nào
về mục đích sử dụng?

Bạn giải thích thêm được không?
```

Important:

- Use visual "Agent chưa hiểu" / "Cần làm rõ".
- Do not show answer.
- Do not expose validator internals.
- Optional source reference:

```text
📖 Tham chiếu: Lesson transcript · Section 2
```

---

## State D — Student Clarifies

```text
👤 Bạn

GET thường dùng để lấy dữ liệu,
còn POST thường dùng để gửi dữ liệu
để tạo resource mới.
```

---

## State E — Validation PASS

```text
🤖 Agent

Đã rõ.

Phần giải thích của bạn đã bao phủ
các ý chính cần thiết của phần này.
```

Then show:

```text
✓ Chunk completed

[ Sang phần tiếp theo ]
```

---

# 12. Mock AI Behavior

Because MVP does not require real AI, use deterministic mock behavior.

## Mock lesson

```javascript
const lesson = {
  id: "lesson-rest-api-01",
  title: "REST API & HTTP Methods",
  duration: "3 min",
  chunks: [
    {
      id: "chunk-1",
      title: "REST API",
      keyPoints: [
        "REST is an architectural style",
        "Resources are identified by URLs",
        "Client and server are separated"
      ]
    },
    {
      id: "chunk-2",
      title: "Client – Server",
      keyPoints: [
        "Client sends requests",
        "Server processes requests",
        "Separation of concerns"
      ]
    },
    {
      id: "chunk-3",
      title: "HTTP Methods",
      keyPoints: [
        "GET retrieves data",
        "POST creates/submits data",
        "PUT updates/replaces",
        "DELETE removes"
      ]
    },
    {
      id: "chunk-4",
      title: "HTTP Status Codes",
      keyPoints: [
        "2xx success",
        "4xx client error",
        "5xx server error"
      ]
    },
    {
      id: "chunk-5",
      title: "Stateless",
      keyPoints: [
        "Each request contains required context",
        "Server does not rely on previous request state"
      ]
    }
  ]
};
```

---

# 13. Mock Loop Logic

Implement a simple state machine.

```javascript
const sessionState = {
  currentChunkIndex: 0,
  loopCount: 0,
  status: "teaching",
  completedChunks: [],
  messages: []
};
```

Possible states:

```text
INTRO
TEACHING
WAITING_FOR_STUDENT
VALIDATING
GAP_FOUND
WAITING_CLARIFICATION
CHUNK_PASSED
LESSON_COMPLETED
QUIZ
```

---

# 14. Suggested Mock Interaction

For demo reliability, use predefined responses.

### First student explanation

If student sends any non-empty response:

```text
Agent:
"Tôi hiểu phần chính. Nhưng tôi chưa rõ một điểm:
[follow-up question]. Bạn giải thích thêm được không?"
```

Set:

```javascript
state = "gap_found";
```

### Second explanation

After second response:

```text
Agent:
"Đã rõ. Phần giải thích đã đạt tiêu chí của phần này."
```

Set:

```javascript
state = "chunk_passed";
```

Then display:

```text
✓ Completed

[ Sang phần tiếp theo ]
```

This allows a predictable live demo.

---

# 15. Do NOT expose fake AI certainty

Avoid UI such as:

```text
AI confidence: 98%
You understand: 100%
```

Do not present unsupported claims.

Use:

```text
✓ Phần giải thích đạt tiêu chí kiểm tra
```

or:

```text
Needs clarification
```

---

# 16. SF-04 — Chunk Complete

After each successful chunk:

```text
┌────────────────────────────────────┐
│             ✓ Hoàn thành           │
│                                    │
│       HTTP Methods                 │
│                                    │
│ Bạn đã giải thích được các ý      │
│ chính của phần này.                │
│                                    │
│ Progress                           │
│ ████████░░░░░░ 60%                │
│                                    │
│         [ Sang phần tiếp theo ]    │
└────────────────────────────────────┘
```

Do not automatically jump to next chunk immediately.

Give student a clear transition.

---

# 17. SF-05 — Lesson Complete

Shown only when all chunks pass.

```text
┌──────────────────────────────────────────┐
│                                          │
│              ✓ Lesson Complete           │
│                                          │
│        REST API & HTTP Methods            │
│                                          │
│  5 / 5 parts completed                   │
│                                          │
│  ✓ REST API                              │
│  ✓ Client – Server                       │
│  ✓ HTTP Methods                          │
│  ✓ HTTP Status Codes                     │
│  ✓ Stateless                             │
│                                          │
│  Teaching loops: 9                       │
│  Clarifications: 4                       │
│                                          │
│  [ Continue to Quiz ]                    │
│                                          │
└──────────────────────────────────────────┘
```

---

# 18. Learning Result

Result should emphasize learning behavior, not generic chatbot performance.

Show:

- Chunks completed.
- Number of teaching loops.
- Number of clarification questions.
- Weak points detected.
- Whether each chunk eventually passed.

Example:

```text
Learning Result

Chunks completed       5 / 5
Teaching interactions  9
Clarifications         4

Areas clarified
• GET vs POST
• Stateless request context

All lesson sections passed the session quality criteria.
```

---

# 19. SF-06 — Quiz

After lesson completion:

```text
Quiz
REST API & HTTP Methods

Question 1 / 3

Which HTTP method is normally used
to retrieve a resource?

○ POST
○ GET
○ DELETE
○ PUT

[ Next ]
```

At least 3 questions.

The quiz is **not the core AI feature**. It exists to demonstrate the original pain point:

```text
Passive learning
      ↓
Teach-back
      ↓
Knowledge validation
      ↓
Quiz
```

---

# 20. Navigation Flow

```text
Lesson Detail
    │
    ├── Back → Course/Lesson
    │
    └── Dạy lại cho Agent
             │
             ▼
       Session Intro
             │
             ▼
       Teaching Session
             │
             ├── Exit → confirmation modal
             │
             ├── Current chunk
             │      │
             │      └── loops
             │
             └── Chunk complete
                    │
                    ▼
                 Next chunk
                    │
                    └── ...
                         │
                         ▼
                   Lesson Complete
                         │
                         ▼
                        Quiz
```

---

# 21. Exit Confirmation

If user clicks Exit during a session:

```text
Bạn muốn thoát phiên dạy lại?

Tiến trình hiện tại sẽ được lưu trong phiên demo.

[ Tiếp tục ]       [ Thoát ]
```

For MVP localStorage can preserve state.

---

# 22. Feature Tree

```text
D · VLEARN — TEACH BACK AGENT
│
├── 1. Lesson Integration
│   ├── Lesson Detail
│   ├── Transcript
│   ├── Learning Objectives
│   └── Teach Back CTA
│
├── 2. Teaching Session
│   ├── Session Intro
│   ├── Session State
│   ├── Progress
│   ├── Lesson Map
│   └── Session History
│
├── 3. Knowledge Chunking
│   ├── Concept Extraction
│   ├── Chunk List
│   ├── Key Points
│   └── Quality Criteria
│
├── 4. Teaching Loop ★ CORE
│   ├── Agent Prompt
│   ├── Student Explanation
│   ├── Explanation Validation
│   ├── Gap Detection
│   ├── Targeted Follow-up
│   ├── Student Clarification
│   └── Re-validation
│
├── 5. Progress Tracking
│   ├── Current Chunk
│   ├── Completed Chunks
│   ├── Loop Count
│   └── Overall Progress
│
├── 6. Learning Result
│   ├── Completed Chunks
│   ├── Detected Gaps
│   ├── Clarifications
│   ├── Teaching Interactions
│   └── Session Summary
│
└── 7. Continue Learning
    ├── Continue to Quiz
    ├── Review Result
    └── Return to Lesson
```

---

# 23. Screen Flow Diagram

```text
SF-01 Lesson Detail
       │
       │ Click Teach Back
       ▼
SF-02 Session Intro
       │
       │ Start
       ▼
SF-03 Teaching Session
       │
       ├──────────────────────────────┐
       │                              │
       │ Student explanation          │
       ▼                              │
    Validate                          │
       │                              │
    ┌──┴───────┐                      │
    │          │                      │
   GAP       PASS                     │
    │          │                      │
    ▼          ▼                      │
Ask Back   SF-04 Chunk Complete       │
    │          │                      │
    ▼          │                      │
Student        │                      │
clarifies      │                      │
    │          │                      │
    └──────────┘                      │
       │                              │
       └────── loop ──────────────────┘
                   │
                   │ all chunks pass
                   ▼
             SF-05 Lesson Complete
                   │
                   ▼
             SF-06 Quiz
```

---

# 24. UI Design Direction

## Overall style

Use a modern VLearn-like learning platform.

Characteristics:

- Clean.
- Academic/productivity oriented.
- Not overly playful.
- Strong visual hierarchy.
- White/light gray background.
- Primary brand color can be blue/purple.
- Rounded cards.
- Subtle borders/shadows.
- Accessible contrast.
- Responsive.

## Typography

Recommended:

- Inter or system sans-serif.
- Large lesson title.
- Medium-weight section titles.
- Compact metadata.
- Chat messages easy to scan.

---

# 25. Bootstrap Requirements

Use:

- Bootstrap 5.x
- Bootstrap Icons
- CSS custom variables
- Vanilla JavaScript

CDN is acceptable for mockup.

Example:

```html
<link
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
  rel="stylesheet"
/>

<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
/>
```

No React/Vue required for this MVP unless explicitly requested later.

---

# 26. Recommended File Structure

```text
vlearn-teach-back/
│
├── index.html
├── lesson.html
├── teaching.html
├── result.html
├── quiz.html
│
├── css/
│   ├── style.css
│   ├── layout.css
│   ├── components.css
│   └── responsive.css
│
├── js/
│   ├── app.js
│   ├── data.js
│   ├── state.js
│   ├── lesson.js
│   ├── teaching.js
│   ├── result.js
│   └── quiz.js
│
└── assets/
    └── icons/
```

Alternative: For a faster Claude-generated prototype, a single `index.html` + `style.css` + `app.js` is acceptable, but keep modules/components logically separated in JS.

---

# 27. Frontend State Model

Recommended:

```javascript
const appState = {
  lessonId: "lesson-rest-api-01",

  session: {
    id: "session-demo-001",
    status: "in_progress",

    currentChunkIndex: 0,

    chunks: [
      {
        id: "chunk-1",
        status: "completed",
        loopCount: 2
      },
      {
        id: "chunk-2",
        status: "current",
        loopCount: 1
      },
      {
        id: "chunk-3",
        status: "locked",
        loopCount: 0
      }
    ],

    messages: [],

    totalLoops: 3,
    clarifications: 1
  }
};
```

---

# 28. localStorage

Persist:

```javascript
localStorage.setItem(
  "vlearn_teach_back_session",
  JSON.stringify(appState)
);
```

Use it for:

- Current chunk.
- Completed chunks.
- Messages.
- Loop count.
- Session status.

This makes the prototype feel like a real product.

---

# 29. Interaction Requirements

## Button: Dạy lại cho Agent

```text
lesson.html
    ↓
teaching.html?lesson=lesson-rest-api-01
```

## Button: Start

```text
Create/reset session
    ↓
Load chunk 1
    ↓
Render first agent message
```

## Button: Send

```text
Read textarea
    ↓
Add student message
    ↓
Disable input briefly
    ↓
Show typing indicator
    ↓
Mock agent response
    ↓
Update loop state
```

## Button: Sang phần tiếp theo

```text
currentChunkIndex++
    ↓
reset current loop state
    ↓
load next chunk
    ↓
agent asks new teaching question
```

## Button: Continue to Quiz

```text
result.html
    ↓
quiz.html
```

---

# 30. Typing Indicator

When mock agent responds:

```text
🤖 Agent is thinking...
   • • •
```

Use a short delay around 500–1000ms.

Do not make the demo unnecessarily slow.

---

# 31. Progress Calculation

```javascript
progress =
  completedChunks / totalChunks * 100;
```

Example:

```text
1 / 5 = 20%
2 / 5 = 40%
3 / 5 = 60%
4 / 5 = 80%
5 / 5 = 100%
```

Show both:

```text
2 / 5
40%
```

---

# 32. Responsive Requirements

Desktop:

- Sidebar lesson map.
- Main conversation panel.
- Fixed input area.
- Max content width.

Tablet:

- Collapsible lesson map.
- Main chat remains dominant.

Mobile:

- Hide desktop sidebar.
- Show progress in header.
- Chat takes full width.
- Input fixed at bottom.
- Buttons full-width where appropriate.

---

# 33. Accessibility

Must include:

- Semantic buttons.
- Keyboard-accessible input.
- Visible focus states.
- `aria-label` where icon-only.
- Sufficient contrast.
- Do not rely on color alone for chunk status.
- Enter to send.
- Shift+Enter for newline.

---

# 34. Important UX Rules

## Rule 1

Do not make the agent look like a teacher.

Agent role:

> **Learner / Protégé**

Not:

> Teacher / Answer provider.

---

## Rule 2

The agent should ask targeted questions.

Bad:

> "Bạn có chắc không?"

Good:

> "Bạn đã nói GET dùng để lấy dữ liệu. Nhưng tại sao GET thường không được dùng để tạo resource mới?"

---

## Rule 3

Do not reveal answer in the follow-up question.

Bad:

> "POST dùng để tạo resource, đúng không?"

Better:

> "Bạn phân biệt mục đích của GET và POST như thế nào?"

---

## Rule 4

Do not pass the chunk too early.

The UI must visibly show:

```text
Current chunk
    ↓
Gap
    ↓
Clarification
    ↓
Validation
    ↓
Pass
```

---

## Rule 5

Do not claim absolute learning.

Use:

> "Đạt tiêu chí kiểm tra của phiên học."

Not:

> "Bạn đã hiểu hoàn toàn."

---

# 35. Demo Script

For the prototype demo:

### Step 1

Open:

```text
Lesson Detail
```

### Step 2

Click:

```text
Dạy lại cho Agent
```

### Step 3

Start session.

### Step 4

Agent:

> "Hãy dạy lại cho tôi REST API."

### Step 5

Student enters:

> "REST API là một cách thiết kế API dựa trên HTTP và resource."

### Step 6

Agent:

> "Tôi hiểu phần resource. Nhưng client và server tương tác với nhau như thế nào trong REST API?"

### Step 7

Student explains.

### Step 8

Agent passes chunk.

### Step 9

Click:

```text
Sang phần tiếp theo
```

### Step 10

Repeat for 3–5 chunks.

### Step 11

Show:

```text
5 / 5 chunks completed
```

### Step 12

Click:

```text
Continue to Quiz
```

### Step 13

Show quiz.

---

# 36. Acceptance Criteria

## AC-01 — Start session

Given the student is on a VLearn lesson,

when they click "Dạy lại cho Agent",

then the Teaching Session Intro is displayed.

---

## AC-02 — Lesson chunks

Given a lesson has N chunks,

when the session starts,

then chunk 1 is active and all later chunks are locked.

---

## AC-03 — Teaching

Given a chunk is active,

when the student starts the chunk,

then the agent asks the student to explain the current concept.

---

## AC-04 — Gap detection

Given the student's explanation does not cover a required point,

then the agent must ask a targeted clarification question.

---

## AC-05 — No answer leakage

The agent must not directly provide the missing answer during the clarification question.

---

## AC-06 — Re-validation

After the student clarifies,

the system must validate again before marking the chunk complete.

---

## AC-07 — Chunk completion

A chunk can only become `completed` after passing its quality criteria.

---

## AC-08 — Lesson completion

The lesson can only become `completed` when all chunks are completed.

---

## AC-09 — Quiz transition

After lesson completion, the student can navigate to the quiz.

---

## AC-10 — Session progress

The interface must display:

- Current chunk.
- Completed chunks.
- Total chunks.
- Overall progress.
- Loop count.

---

# 37. Quality Bar for Prototype

The prototype should demonstrate that the AI feature is **not just chat**.

The evaluator should be able to observe:

```text
Student explanation
        ↓
Gap detected
        ↓
Targeted question
        ↓
Student re-explains
        ↓
Validation
        ↓
Chunk PASS
```

And at lesson level:

```text
Chunk 1 PASS
Chunk 2 PASS
Chunk 3 PASS
Chunk 4 PASS
Chunk 5 PASS
        ↓
Lesson Complete
        ↓
Quiz
```

---

# 38. Future VLearn Integration

MVP should be designed so the mock data can later be replaced by APIs.

Future:

```text
GET /api/lessons/{lessonId}
GET /api/lessons/{lessonId}/transcript
GET /api/lessons/{lessonId}/objectives

POST /api/teaching-sessions
POST /api/teaching-sessions/{sessionId}/messages
POST /api/teaching-sessions/{sessionId}/validate
GET /api/teaching-sessions/{sessionId}

POST /api/teaching-sessions/{sessionId}/complete
GET /api/lessons/{lessonId}/quiz
```

Frontend should isolate API calls in one module:

```javascript
const api = {
  getLesson(),
  createSession(),
  sendMessage(),
  getSession(),
  completeSession(),
  getQuiz()
};
```

For MVP:

```javascript
const api = {
  // mock/local implementation
};
```

Later:

```javascript
// replace with real fetch()
```

No major UI rewrite should be required.

---

# 39. Claude/Cursor Implementation Prompt

Use this section as the implementation instruction.

```text
Build a clickable frontend prototype for the D · VLearn "Teach Back Agent" feature based strictly on this FE.md specification.

Goal:
Create a realistic VLearn learning workflow where a student finishes a lesson and teaches the lesson back to an AI agent acting as a learner.

Important product model:
1 Lesson = 1 Teaching Session = N Knowledge Chunks = multiple Teaching Loops.

The core interaction is NOT generic chatbot Q&A.

The core loop is:
Student explains → system validates against lesson knowledge → detects gap → agent asks targeted clarification → student re-explains → system validates → chunk passes.

The agent must not reveal the answer or claim understanding prematurely.

Required screens:
1. Lesson Detail
2. Teaching Session Intro
3. Teaching Session
4. Chunk Complete
5. Lesson Complete / Learning Result
6. Quiz

Use:
- HTML5
- CSS3
- Bootstrap 5
- Bootstrap Icons
- Vanilla JavaScript
- localStorage for session persistence
- mock local data
- responsive design

Do not require a real backend or LLM API.

The prototype must be fully clickable:
Lesson → Teach Back → Start → chat loops → chunk pass → next chunk → all chunks complete → result → quiz.

Implement a deterministic mock agent so the demo is reliable:
- first meaningful student explanation triggers a targeted gap question;
- second explanation can trigger validation pass;
- allow repeated loops where appropriate;
- each chunk must pass before moving to the next.

Use the REST API & HTTP Methods lesson data defined in FE.md.

Keep API integration isolated behind an api/service layer so real VLearn APIs can replace mock data later.

Do not expose internal validator scores or fake AI confidence.

The UI should communicate:
"Agent is checking whether the student can explain the lesson", not "AI is grading the student".

Ensure there are no dead buttons or fake navigation.
```

---

# 40. Definition of Done

The frontend prototype is considered complete when:

- [ ] User can enter from Lesson Detail.
- [ ] User can start a Teach Back Session.
- [ ] Lesson is divided into multiple chunks.
- [ ] Current chunk is clearly visible.
- [ ] Future chunks are locked.
- [ ] Student can send explanations.
- [ ] Agent responds.
- [ ] Agent can identify a mock knowledge gap.
- [ ] Agent asks a targeted follow-up.
- [ ] Student can clarify.
- [ ] Agent validates again.
- [ ] Chunk can become PASS.
- [ ] User can move to next chunk.
- [ ] Multiple chunks can be completed.
- [ ] Overall progress updates.
- [ ] Loop count updates.
- [ ] Lesson cannot complete before all chunks pass.
- [ ] Lesson Result is shown.
- [ ] Quiz is accessible after completion.
- [ ] Back/exit works.
- [ ] Session state persists with localStorage.
- [ ] Desktop responsive.
- [ ] Mobile responsive.
- [ ] No dead-end buttons.
- [ ] No real API key is committed.
- [ ] Code is organized and readable.
- [ ] Prototype can run locally by opening/serving the HTML files.

---

# 41. Final Product Principle

The frontend must make this product idea immediately understandable:

> **Học viên không chỉ trả lời câu hỏi về bài học. Học viên phải dạy lại bài học cho Agent. Agent chỉ "hiểu" sau khi học viên giải thích đủ đúng và xử lý được các câu hỏi hỏi ngược tại những điểm còn hổng.**

Core UX:

```text
LEARN
  ↓
TEACH
  ↓
AGENT LISTENS
  ↓
DETECT GAP
  ↓
ASK BACK
  ↓
RE-EXPLAIN
  ↓
VALIDATE
  ↓
CHUNK PASS
  ↓
NEXT CHUNK
  ↓
ALL CHUNKS PASS
  ↓
LESSON COMPLETE
  ↓
QUIZ
```
