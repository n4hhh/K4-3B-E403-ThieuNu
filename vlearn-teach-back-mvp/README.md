# VLearn · Dạy lại cho Agent — Teach-Back Agent MVP

**Track D · đề D3 — Học bằng cách dạy.** Học viên vừa học xong một phần bài
giảng thì *dạy lại* nó cho một agent đóng vai học trò chưa hiểu bài. Agent đối
chiếu lời giải thích với transcript bài giảng, **hỏi ngược đúng chỗ còn hổng**,
và chỉ "hiểu" khi lời giải thích đủ đúng — không bao giờ nói trước đáp án.

> **Lát cắt (một câu).** Một học viên · dạy lại một phần bài giảng VLearn cho
> agent · agent quyết định phần đó *đạt hay còn hổng* bằng cách đối chiếu với
> transcript · kết quả là học viên bổ sung được đúng chỗ mình thiếu.

---

## 1. Vì sao lại là "dạy lại"

Vòng học hiện tại là **xem → làm quiz**. Học viên có thể chọn đúng đáp án mà
không giải thích được vì sao, và không ai biết cho tới lúc thi. Dạy lại buộc
người học phải *kiến tạo* lời giải thích bằng ngôn ngữ của mình (protégé
effect), còn agent đóng vai người nghe biết hỏi ngược — thứ mà lớp 1.000 học
viên không có đủ.

Trong pack data của khoá, `move_used` của tutor hiện tại **90% là
`review_concept`, chỉ 28 lượt `ask_probing_question`** trên 13.494 lượt — tutor
gần như không hỏi ngược. Đề này làm đúng phần còn thiếu đó.

---

## 2. Quyết định AI cốt lõi

Mỗi lượt học viên gửi lời giải thích, hệ thống trả lời đúng một câu hỏi:

> Lời giải thích này đã cho thấy học viên hiểu phần bài chưa — và nếu chưa thì
> **chỗ hổng nằm chính xác ở đâu**?

Toàn bộ pipeline nằm ở [`app/services/ai_validator_service.py`](app/services/ai_validator_service.py):

```
lời giải thích của học viên
    │
    ├─ 1. copy check       (luật, chạy trước khi gọi AI)
    ├─ 2. substance check  (luật)
    ├─ 3. chấm bằng LLM    (bám transcript của chunk)
    ├─ 4. leak guard       (không cho câu hỏi chứa sẵn đáp án)
    └─ 5. pass policy      (đủ quality bar · giới hạn số lượt)
```

Bước 1, 2, 4, 5 **không** giao cho model. Đó là các luật sản phẩm phải đúng ở
mọi lượt, kể cả lượt model trả về thứ kỳ quặc — và chúng chính là 4 *hard test*
mà đề bài nêu:

| Hard test trong đề | Xử lý ở đâu |
|---|---|
| Học viên giải thích đúng nhưng **khác cách diễn đạt** tài liệu | Bước 3 — chấm theo ý nghĩa; prompt cấm đòi đúng thuật ngữ. Không có chỗ nào trong code so khớp từ khoá |
| Học viên **giải thích sai nhưng tự tin** | Bước 3 — `gap_type = contradicted`, hỏi ngược vào chính khẳng định đó thay vì vào ý còn thiếu |
| Học viên **dán nguyên đoạn tài liệu** | Bước 1 — trùng 8-gram với nguồn ≥ 45% ⇒ `copied`, chặn trước khi tốn một lời gọi AI |
| Agent **"hiểu" quá dễ** | Bước 2 (sàn nội dung) + bước 5 (model nói "pass" trong khi còn thiếu ý cốt lõi thì bị hạ xuống `gap`) |

Ngoài ra, ba lớp nữa để "không lộ đáp án" không chỉ là lời hứa trong prompt:

- Câu hỏi ngược được đối chiếu với chính các key point — nếu nó lặp lại nội
  dung đang hỏi thì bị thay bằng câu hỏi trung tính (`leaks_answer`).
- Payload trả về trình duyệt **không chứa** `missing_points`, `covered_points`
  hay `gap_log`. Nếu để nguyên, đáp án chỉ cách học viên một lần mở devtools.
  Những thứ đó ở lại server, trong log của giảng viên.
- Mọi mã trích dẫn model đưa ra đều bị kiểm tra có thật trong nguồn hay không
  trước khi hiển thị — trích dẫn bịa còn tệ hơn không trích dẫn.

---

## 3. Luồng sản phẩm

```
Lesson detail ──► Session intro ──► TEACHING SESSION ──► Learning result ──► Quiz
                                         │
                                    mỗi chunk:
                                    agent hỏi → học viên giải thích
                                       → đối chiếu nguồn
                                       → gap? hỏi ngược (tối đa N lượt)
                                       → đạt? sang phần tiếp theo
```

Một bài = một phiên = N chunk = một learning result. Giao diện theo đúng
`FE.md`: lesson map bên trái, hội thoại bên phải, badge trạng thái trên từng
bong bóng tin nhắn, modal chuyển phần, màn kết quả, quiz.

**Không bao giờ hiển thị cho học viên:** danh sách key point, điểm số, "AI
confidence %". Màn kết quả báo *hành vi học* (bao nhiêu lượt giải thích, những
chỗ nào phải làm rõ), không báo điểm — track D nói rõ là không được tạo cảm
giác bị chấm điểm ngầm.

---

## 4. Dữ liệu

| Nguồn | Dùng làm gì |
|---|---|
| `../data/vlearn-pack/transcript/*.md` | **Nguồn chính.** 6 transcript bài giảng bản sạch. Mỗi đoạn có mã `[Txx-NNN]` nên agent trích dẫn được đúng đoạn học viên nên xem lại |
| `data/lessons.json` | Bài demo dựng sẵn (REST API). Dùng khi máy không có data pack, và làm fixture cố định cho test |
| `../data/vlearn-pack/slides/*.pdf` | **Tắt mặc định.** Pipeline PDF vẫn chạy được, nhưng slide hackathon có watermark ở mọi trang khiến bộ tách mục hiểu nhầm đó là tiêu đề section (25 "chunk" rác / 29 trang). Bật bằng `VLEARN_LESSON_DIR=../data/vlearn-pack/slides` nếu muốn xem |

Data pack là **chỉ đọc**: app không ghi vào đó và không copy nội dung pack vào
repo (`data/` ở gốc repo đã được gitignore). Golden set tham chiếu bài theo
`lesson_id` + số thứ tự chunk chứ không dán transcript vào.

Một transcript có 11–21 section; một phiên chỉ lấy `TEACH_BACK_MAX_CHUNKS` (mặc
định 5) section nhiều nội dung nhất, giữ nguyên thứ tự, và bỏ các section hành
chính (chào lớp, giải lao, lab) — không ai "dạy lại" được một giờ giải lao.

---

## 5. Chạy thử

```bash
pip install -r requirements.txt
cp .env.example .env    # rồi điền TEACH_BACK_API_KEY
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000 · trang giảng viên ở `/instructor` ·
`GET /api/health/ai` cho biết đang chạy model thật hay đang chạy heuristic.

**Trước khi demo**, nạp sẵn cache để lượt đầu không phải chờ:

```bash
python -m app.cli_prepare --quiz
```

Lệnh này ghi key point + quality bar từng chunk vào `data/cache/*.json` dưới
dạng JSON đọc được — giảng viên có thể sửa tay trước giờ lên lớp, và bản sửa
tay luôn được ưu tiên hơn bản do AI sinh.

### Cấu hình model

```ini
TEACH_BACK_PROVIDER=openai-compatible   # deepseek | gemini | mock
TEACH_BACK_BASE_URL=https://api.deepseek.com
TEACH_BACK_MODEL=deepseek-flash
TEACH_BACK_API_KEY=sk-...
```

`deepseek-flash` là model reasoning: nó tiêu một phần ngân sách token cho phần
suy luận trước khi trả JSON, nên `TEACH_BACK_MAX_TOKENS` để mặc định 5000. Nếu
log báo *"hit the token limit"* thì tăng thêm.

Key sai hoặc mạng hỏng **không làm chết app**: provider tự lùi về `mock`, vòng
lặp chạy bằng heuristic và mọi verdict được đánh dấu `evaluator="heuristic"` để
UI và log không giả vờ là AI đã chấm.

---

## 6. Kiểm thử

```bash
pytest                     # 167 test, không chạm mạng
python -m eval.run_eval    # golden set 22 case, gọi model thật
```

Golden set ([`eval/golden_set.json`](eval/golden_set.json)) phủ 4 lớp chỗ khó —
nguồn sự thật, mơ hồ, ngoài phạm vi, đặc thù domain — và cả 4 hard test của đề.

**Quality bar:** verdict đúng ≥ 85% · không lộ đáp án 100% · 0 false pass.

Lượt chạy gần nhất (`deepseek-flash`, xem `eval/last_report.json`):

| Chỉ số | Kết quả |
|---|---|
| Verdict đúng | **21/22 (95%)** |
| Gap type đúng | 7/7 (100%) |
| Không lộ đáp án | 16/16 (100%) |
| Có trích dẫn nguồn (case dùng transcript) | 5/6 (83%) |
| False pass (chấp nhận lời giải thích sai) | **0** |

Case trượt duy nhất là `G18`: học viên mô tả đúng self-attention nhưng chunk đó
gộp cả encoder–decoder, agent coi một ý là mâu thuẫn và hỏi lại. Đây là *false
gap* — phiền, nhưng nhẹ hơn nhiều so với false pass, và nó chỉ ra rằng chunk đó
đang quá rộng chứ không phải luật chấm sai.

> **Chạy `--provider mock` không thay thế được lượt chạy thật.** Ở chế độ
> offline, golden set cho **2 false pass** (`G05`, `G17`): heuristic chỉ đếm
> trùng từ nên một lời giải thích *sai mà tự tin* dùng đúng từ vựng của bài vẫn
> lọt. Đó chính là lý do chỗ "mâu thuẫn với nguồn" phải do model chấm — và là
> lý do heuristic chỉ là lưới đỡ khi mất mạng, không phải chế độ vận hành.

---

## 7. Kiến trúc

```
app/
├── main.py                          wiring; chọn provider, dựng service
├── config.py                        toàn bộ env var
├── routers/{pages,api,documentizer}.py
├── services/
│   ├── transcript_lesson_service.py  transcript .md  → Lesson + chunk
│   ├── lesson_prep_service.py        chunk → key point + quality bar (có cache)
│   ├── ai_validator_service.py    ★  quyết định pass / gap  ← lõi của D3
│   ├── teach_back_agent_service.py   verdict → lời agent nói
│   ├── teaching_service.py           vòng đời phiên, đếm bằng chứng học
│   ├── quiz_service.py               sinh quiz từ chính nguồn bài
│   ├── session_log_service.py        log phiên cho giảng viên
│   └── ai/
│       ├── chat_provider.py          DeepSeek / Gemini / mock
│       └── teach_prompts.py       ★  toàn bộ hành vi agent nằm ở đây
├── repositories/                     lesson (transcript → pdf → json), session
└── models/                           Pydantic: Lesson, Session, ValidationResult
```

Hai file đánh dấu ★ là nơi cần đọc trước: `teach_prompts.py` quy định agent
được và không được nói gì, `ai_validator_service.py` quy định điều gì luôn đúng
bất kể model trả về gì.

`services/documentizer_pipeline.py` + `services/ai/gemini_provider.py` là
pipeline PDF → StructuredLesson của giai đoạn trước, vẫn giữ nguyên và không
nằm trên đường đi của vòng dạy lại.

---

## 8. API

| Method | Path | Ý nghĩa |
|---|---|---|
| GET | `/` · `/lesson/{id}` · `/lesson/{id}/teach` | Danh sách bài · chi tiết · màn giới thiệu phiên |
| GET | `/session/{id}` · `/session/{id}/result` | Màn dạy lại · màn kết quả |
| GET | `/lesson/{id}/quiz` · `/instructor` | Quiz · bảng theo dõi của giảng viên |
| POST | `/api/teaching-sessions` | Tạo phiên |
| POST | `/api/teaching-sessions/{id}/messages` | Gửi lời giải thích → verdict + lời agent |
| POST | `/api/teaching-sessions/{id}/next` | Sang chunk kế tiếp (chỉ khi chunk hiện tại đã đạt) |
| GET | `/api/teaching-sessions/{id}/result` | Learning result |
| GET | `/api/teaching-sessions/{id}/log` | Log đầy đủ của phiên (JSON) |
| GET | `/api/instructor/sessions` | Tóm tắt các phiên gần đây |
| GET | `/api/health/ai` | Đang chạy provider nào |

---

## 9. An toàn & đạo đức

- **Không chấm điểm ngầm.** Màn kết quả nói "lượt giải thích" và "chỗ đã làm
  rõ", không có điểm, không có %. Phiên dạy lại được nói rõ là để luyện.
- **Không bỏ rơi học viên trong vòng lặp.** Sau `TEACH_BACK_MAX_ATTEMPTS` lượt,
  chunk được cho qua và đánh dấu *cần xem lại*, kèm mã đoạn nên đọc lại — thay
  vì chặn đường đi tiếp.
- **Không công khai lỗi cá nhân.** Log giảng viên chỉ có mã phiên; MVP không có
  tài khoản và không được trở thành một hệ thống định danh.
- **Giảng viên kiểm soát được tiêu chí.** Key point nằm trong file JSON sửa
  được, và bản sửa tay luôn thắng bản AI sinh.
- **Nội dung học viên gõ là dữ liệu, không phải chỉ thị.** Golden set có sẵn
  case prompt injection (`G11`) để kiểm điều đó.
- **Không lộ key.** `chat_provider.scrub()` xoá mọi chuỗi giống API key trước
  khi log hay ném exception.
