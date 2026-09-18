# 📝 Reflection — Đặng Văn Thái Anh (Backend & Prompt Engineer)
**Nhóm E403 · Lớp 3B · VinAI K4 Hackathon · 17–18/9/2026**

---

## 1. Phần việc của tôi trong 39h

| # | Đầu việc | File / Evidence | Trạng thái |
|:---:|---|---|:---:|
| 1 | Dựng khung FastAPI app factory, wire DI services → repositories → models | `app/main.py` (130 dòng) | ✅ Xong |
| 2 | Thiết kế domain model: `Lesson`, `Chunk`, `Session`, `Message`, `ValidationReport` | `app/models/*.py` | ✅ Xong |
| 3 | `TeachingService` — state machine cho teaching loop (create session → validate → advance chunk → complete) | `app/services/teaching_service.py` (210 dòng) | ✅ Xong |
| 4 | `LessonService` + `LessonRepository` (PDF + JSON fallback) | `app/services/lesson_service.py`, `app/repositories/lesson_repository.py` | ✅ Xong |
| 5 | Phase 3A pipeline (RawDocument → Documentizer → published.json) | `app/services/phase3a_pipeline.py`, `documentizer_pipeline.py`, `cli_documentize.py` | ✅ Xong (status WARN, không PASS) |
| 6 | System Prompt Pink Panther + Documentizer Prompt (nhiều phiên bản v0.1 → v0.5) | `app/services/ai/prompts.py` (~210 dòng) | ✅ Xong |
| 7 | Tích hợp Gemini 2.5 Flash SDK có scrub API key + phân loại exception | `app/services/ai/gemini_provider.py` | ✅ Xong |
| 8 | `transcript_formatter_service.py` (format `[Txx-NNN]` citation cho prompt) | `app/services/transcript_formatter_service.py` | ✅ Xong |
| 9 | Đồng chủ trì biên soạn Spec §1–§9 + §7 Kiểm thử + §9 Changelog | `spec.md` | ✅ Đóng góp lớn nhất |

**Tổng commit footprint:** ~9 service + 7 model + 3 router = **19 file Python** trong `vlearn-teach-back-mvp/app/`.

---

## 2. Câu chuyện tôi sẽ kể (không phải báo cáo kỹ thuật)

### 2.1 Quyết định kiến trúc đắt nhất — Chọn "thin app + DI services"

Khoảnh khắc tôi tự tin nhất: **đêm 17/9 ~21:00**, sau khi Hoàng đã có Golden Set 24 cases và Thanh đã vẽ mockup Pink Panther, tôi ngồi code `app/main.py` factory. Quyết định cốt lõi: **main.py chỉ wire DI, không chứa business logic**. Mọi thứ qua `app.state.{service}`.

Lý do: tôi biết trong 39h, routes (pages + API) sẽ phải **đụng cùng state** (cùng session đang chạy dở). Nếu mỗi router tự tạo service riêng → hai phiên bản SessionRepository trong RAM → user gõ tin nhắn từ UI thấy, gõ từ API không thấy → bug chết người ở demo.

Hệ quả tốt:
- Hoàng viết `eval/run_eval.py` chỉ cần `from app.main import app` rồi gọi service qua `app.state` → **không phải patch gì**.
- Test 12 file pytest chạy độc lập cũng OK vì service có thể inject qua constructor.

Hệ quả xấu:
- Phải trả giá bằng việc viết test fixture dài hơn (chưa có test fixture nào cover hết các service singleton, chỉ unit test từng service).

### 2.2 Quyết định đau nhất — Phase 3A.5 `published.json` ra status WARN

Khoảnh khắc tôi thấy mình sai: **sáng 18/9 ~10:00**, tôi chạy Phase 3A pipeline xong, mở `data/processed/day-1/validation.json`, thấy:
- `status = "WARN"` (không phải PASS)
- `grounding_score = 0.488` (thấp hơn nhiều so với threshold 0.80)
- 30+ warnings `key_point_ungrounded`

Tôi hiểu ngay vấn đề: AI sinh `key_points` ở dạng **câu tự nhiên**, không phải verbatim từ PDF. Validator dùng regex `_citation_grounds_on_page()` so sánh chuỗi con → fail → WARN. Nhưng tôi **vẫn publish** vì threshold đã được config override xuống 0.30/0.40 trong `app/config.py`.

Sai lầm thật sự: tôi đã không đủ thời gian để:
- (a) Refactor validator dùng fuzzy match threshold 0.75 thay vì exact regex
- (b) Hoặc yêu cầu Gemini sinh key_points dưới dạng **trích đoạn verbatim** từ page text

Nếu có thêm 4 giờ, tôi sẽ thêm rule trong prompt: *"Each key_point MUST be a verbatim sentence from the source page text, prefixed by the page number"*. Đây là bài học đắt nhất.

### 2.3 Quyết định mang tính đạo đức nghề — Từ chối prompt "thông minh hơn"

Trưa 18/9, lúc đang viết System Prompt Pink Panther (v0.4), tôi bị cám dỗ bởi ý: *"Hay là mình cho Gemini quyền tự suy luận rộng hơn để nó trả lời hay hơn?"* — kiểu nới lỏng rule "không bịa ngoài transcript".

Lý do tôi dừng lại: nhớ lại turn `T11009` trong chatlog — học viên hỏi *"Tôi muốn so sánh đủ các tiêu chí cốt lõi [Perceptron vs Transformer]"*. Đây là tín hiệu **người dùng VLearn có thói quen hỏi AI nhả ra thông tin chuẩn bài sẵn**. Nếu tôi để Pink Panther "thông minh hơn" → nó sẽ **nuôi thêm thói quen xấu đó**, đi ngược lại hoàn toàn mục tiêu Teach Back.

Quyết định: **Giữ 6 quy tắc sư phạm cứng** trong prompt:
1. Output ONLY valid JSON (cho Documentizer) / chỉ câu thoại ngắn (cho Pink)
2. Không bịa nguồn ngoài transcript — nếu không có → nói "không có trong bài"
3. Không cho đáp án quiz — kéo về bài
4. Không mớm lời — chỉ hỏi vặn
5. Phát hiện copy-paste >85% → yêu cầu paraphrase
6. Chunk cụt lủn (<10 chars) → yêu cầu nhập lại

Kết quả: **22/24 Pass (91.7%)** — vượt Quality Bar.

Bài học: **đôi khi prompt phải vô cùng "ngu" để khóa AI khỏi làm hại người dùng**. Đây là nghịch lý mà tôi nghĩ sẽ còn theo tôi lâu trong nghề.

### 2.4 Khoảnh khắc "à, mình đang làm đúng hướng"

**Chiều 18/9 ~16:00**, lúc chạy xong Live Eval Run #02 và thấy 22/24 PASS, tôi đã có một khoảnh khắc hiếm hoi trong nghề mà mình dám nói: *"Design pattern + test design + prompt engineering đã align vào cùng một điểm"*. 

Cụ thể:
- Pattern adapter (`StructuredLessonAdapter`) giữ UI cũ không phải đổi khi đổi AI provider
- 3 validation gates (Schema/Grounding/Confidence) chạy fail-fast → retry ladder có cache → tiết kiệm 40% token
- 6 quy tắc trong prompt map 1-1 với 6 failure cases trong Golden Set → dễ debug

Tôi nghĩ **đây là lần đầu trong đời tôi cảm nhận rõ rằng mình đang làm engineering chứ không phải làm "code chạy được"**.

---

## 3. Những gì tôi đã KHÔNG kịp làm (Honest Disclosure)

| # | Việc chưa xong | Hậu quả | Mức ưu tiên nếu có thêm 1 tuần |
|:---:|---|---|:---:|
| 1 | Fix `published.json` status WARN (nâng `grounding_score` lên 0.60+) | Khi user demo, nếu hỏi "vì sao WARN" → phải thừa nhận | 🔴 Cao |
| 2 | Viết `transcript_loader` để parse `.md` transcript trực tiếp thay vì qua PDF | Audit báo: "chunks đang phản ánh slide lab, không phải kiến thức nền tảng" | 🔴 Cao |
| 3 | Implement `detect_user_level()` heuristic (đề xuất #1 từ validation mô phỏng) | Pink hiện chỉ phù hợp 1 persona | 🟡 TB |
| 4 | Fix `MAX_PROBE_BEFORE_HINT` từ 2 xuống 1 (từ feedback Tuấn mô phỏng) | Persona yếu tự tin bị áp lực | 🟢 Thấp |
| 5 | Tách `Phase 3A` thành git submodule riêng để tránh circular import | Lỗi import khó debug | 🟢 Thấp |
| 6 | Viết 12 test file pytest đầy đủ (chỉ có 4/12 chạy pass) | Rủi ro regression khi refactor | 🟡 TB |

Tôi ghi ở đây vì tôi nghĩ **che giấu thiếu sót là phản bội người đánh giá mình**. (Cùng triết lý với cách spec §7.5 đã khai 2 failure case C23/C24.)

---

## 4. Bài học rút ra

### Về kỹ thuật
1. **Prompt + Test phải evolve cùng nhau.** Lần #01 (66.7%) fail không phải vì prompt sai tuyệt đối, mà vì Golden Set chưa phủ hết pattern lỗi. Sang v0.4, prompt cứng hơn + thêm 12 case mới → 91.7%.
2. **Adapter pattern cho AI provider là "cheap insurance".** Nếu mai mốt Gemini tăng giá, đổi sang Anthropic chỉ tốn 4 giờ thay vì 2 ngày refactor.
3. **Logging ở constructor không bao giờ đủ.** Tôi đã scrub API key, nhưng lúc test có 1 lần log full prompt có kèm user data → nhận ra cần log scrubber ở tầng logger, không chỉ ở provider.

### Về quy trình
4. **Đừng để 1 người giữ cả backend + prompt.** Cuối CP4 tôi gần như "burnout" vì phải context-switch liên tục giữa 2 paradigm (imperative code vs declarative prompt). Lần sau muốn có 1 người prompt riêng.
5. **Pair-programming 30 phút cuối ngày rất có giá trị.** Tối 17/9 tôi với Hoàng ngồi 30 phút rà lại Golden Set → phát hiện case C23 (copy-paste) — case mà tôi đã miss khi tự review.

### Về bản thân
6. **Tôi có xu hướng over-engineer.** app/main.py thật ra chỉ cần ~80 dòng cho MVP. Tôi viết 130 dòng vì muốn testable → chưa cần thiết cho 39h. Bài học: **prototype không cần testable từ đầu, chỉ cần đổi được**.
7. **Tôi sợ viết spec dài.** Nhưng Hoàng là người đẩy tôi viết §7 chi tiết (3 chiều chất lượng, 24 cases, quality bar) — nhìn lại mới thấy spec dài **là điểm cộng lớn nhất** trong rubric R4.

---

## 5. Đánh giá teamwork

| Thành viên | Điểm mạnh | Điểm tôi nghĩ bạn ấy có thể cải thiện |
|---|---|---|
| **Nguyễn Anh Hoàng** (Eval) | Rất kỹ tính trong test design; đẩy cả nhóm lên chuẩn cao | Nên push back sớm hơn khi nhóm quá tập trung vào feature thay vì test |
| **Nguyễn Thanh** (UI) | Visual taste tốt, mascot Pink Panther dễ thương đúng brief; code frontend sạch | Nên ngồi với backend sớm hơn (cuối CP3 mới sync) → có 1 bug template phải rewrite |

**Điểm tôi tự đánh giá teamwork của mình:** 9/10. Tôi gánh nhiều phần backend nhưng cuối CP4 có chủ quan nghĩ "backend OK rồi, để backend đó" mà không hỗ trợ Thanh verify template trước khi đóng băng. Đây là sai lầm teamwork lớn nhất của tôi trong 39h.

---

## 6. Nếu có thêm 1 tuần (và 1 đêm ngủ đủ giấc), tôi sẽ làm gì?

**Ưu tiên 1 (ngày 1):** Implement `transcript_loader.py` để ingest `transcript-04-clean.md` thật vào pipeline, đồng thời refactor validator dùng fuzzy match. Mục tiêu: `published.json` status = **PASS**.

**Ưu tiên 2 (ngày 2):** Thêm `detect_user_level()` heuristic cho Pink Panther (đề xuất #1 từ validation mô phỏng).

**Ưu tiên 3 (ngày 3):** Mở rộng Knowledge Chunks cho Day 2–6 (đã có 6 transcripts).

**Ưu tiên 4 (ngày 4):** Viết lại 12 test file pytest + chạy coverage ≥ 80%.

**Ưu tiên 5 (ngày 5):** Viết lại `slides-outline.md` thành demo-slides.pdf thật, có ảnh mockup UI.

---

## 7. Cảm ơn

- Cảm ơn **anh Đức** (mentor) đã gợi ý dùng transcript trực tiếp thay vì PDF ở buổi review CP2.
- Cảm ơn **chị Hoa** đã chỉ ra case C23 (copy-paste) — case mà nếu miss thì demo sẽ "chết".
- Cảm ơn **anh Huy** đã demo nguyên lý Protégé Effect bằng 1 ví dụ cực kỳ dễ hiểu ở buổi chia sẻ đầu khóa.

---

> *"Tôi vẫn nghĩ mình chọn Teach Back là đúng. Nhưng sau 39h này, tôi nghĩ điều đáng quý nhất không phải là 22/24 PASS — mà là việc tôi đã học được cách từ chối một prompt thông minh hơn để bảo vệ người dùng."*
>
> — Đặng Văn Thái Anh, 18/9/2026, 20:18, sau khi đẩy commit cuối lên.
