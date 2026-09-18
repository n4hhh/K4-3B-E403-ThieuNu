# 🔍 AUDIT DỰ ÁN — K4-3B-E403-ThieuNu
**Ngày audit:** 2026-09-18 (Friday 18:25 ICT)
**Auditor:** Cursor Assistant
**Dự án:** Mini Hackathon AI — VLearn Teach Back Agent (Pink Panther 🐾)
**Nhóm:** Lớp 3B · Phòng E403 · Cụm ____ · Track D (Đề D3)
**Spec đã chốt:** v1.0 FINAL tại CP4 (đóng băng lúc 16:45 ngày 18/9)
**Quality bar:** Đạt — 22/24 = 91.7% trên Golden Set (Live AI Gemini 2.5 Flash)

---

## TÓM TẮT ĐIỀU HÀNH (Executive Summary)

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| **Tổng quan kiến trúc** | ✅ Tốt | Phân lớp rõ ràng (main → routers → services → repositories → models) |
| **Spec chốt CP4** | ✅ Hoàn thiện | §1–§9 đầy đủ, Quality Bar đóng băng, có tự khai phần chưa xong |
| **Bằng chứng khai phá dữ liệu (R1)** | ✅ Rất tốt | Trích dẫn `turn_id` thật, đếm từ `tutor_turns.csv`, 5 evidence cụ thể |
| **Thiết kế 4 đường đi + 10 kịch bản rủi ro (R2, R3)** | ✅ Tốt | Cover đủ happy/low-conf/failure/correction/out-of-scope/domain |
| **Pipeline PDF + Documentizer (Phase 3A + 3A.5)** | ✅ Hoạt động | Tách lớp read-only Phase 3A + Phase 3A.5 không phá code cũ |
| **Bộ kiểm thử tự động (R4)** | ✅ Đạt 91.7% | 22/24 cases pass, có tự khai C23 (copy-paste) và C24 (câu cụt) |
| **Prototype chạy được (R5)** | ✅ Có video | Working level — FastAPI + Gemini thật + Jinja2 + Bootstrap 5 |
| **Bảo mật dữ liệu (Hackathon §)** | ⚠️ CẦN KIỂM TRA | `data/` đã `.gitignore` nhưng cần verify không có trong git tracked |
| **Khả năng nộp CP5 (slide + video dự phòng)** | ❓ Chưa thấy | Cần kiểm tra `demo-slides.pdf`, `codebase/` rỗng? |
| **Khả năng nộp R6 (validation/)** | ❓ Chưa thấy | Cần 5 willing user + bảng nhật ký |

---

## 1. CẤU TRÚC DỰ ÁN

```
K4-3B-E403-ThieuNu/                     ← workspace root (đã git init)
├── README.md                           ← bản gốc từ đề bài (24KB)
├── spec.md                             ← AI Spec §1–§9 + Changelog (40KB) ⭐
├── vlearn-mockup.html                  ← Mockup HTML tham chiếu (47KB, read-only)
├── vlearn-teach-back-mvp/              ← codebase chính (FastAPI)
├── eval/                               ← Golden Set + runner + báo cáo
├── examples/                           ← canvas-cp1.md (mẫu trống + ví dụ)
├── further-reading/                    ← HAX, PAIR, Mom Test, JTBD
├── tracks/                             ← Track A/B/C/D/E (đề bài)
├── data/                               ← thư mục được .gitignore ở root
└── vlearn-mockup.html (47KB)           ← mockup gốc
```

### 1.1 Thống kê mã nguồn

| Hạng mục | Số lượng |
|---|---|
| Module Python (trong `vlearn-teach-back-mvp/app/`) | 38 files |
| Template Jinja2 | 7 files |
| File CSS / JS | 7 files |
| Test files (pytest) | 12 files |
| Docs (`.md`) | 9 files (spec, README, 3× PHASE plan, eval reports, examples, further-reading) |
| Data processed (PDF → JSON pipeline output) | 5 files |

---

## 2. ĐÁNH GIÁ CHI TIẾT THEO RUBRIC

### R1 · Bằng chứng & Impact — 15 điểm

**Điểm dự kiến: 14–15**

**Điểm mạnh:**
- §1 đã khai phá toàn bộ `tutor_turns.csv` (13.494 lượt, 1.617 học viên) với phương pháp đếm rõ ràng: lọc `cohort_hint = K4` → 3.097 lượt → lọc `lecture_code = D01` → 1.045 lượt
- 5 trích dẫn chatlog thật với `turn_id` cụ thể (T10435, T11009, T10614, T11066, T11218) — đúng chuẩn B "Mining dữ liệu thật"
- Bảng impact so sánh 3 ứng viên (D1, D2, D3) có quyết định chọn/bỏ và lý do — đúng chuẩn

**Cảnh báo nhỏ:**
- Bảng impact không ghi rõ **willing user** đã khai ở đâu trong CP1 (Spec §8 chỉ liệt kê 2 người, không có link form CP1)
- Cần xác nhận 2 willing user này đã được khai báo trong form CP1 (do BTC công bố lúc khai mạc)

---

### R2 · Lát cắt & Thiết kế — 15 điểm

**Điểm dự kiến: 14–15**

**Điểm mạnh:**
- §4 có câu "lát cắt MỘT CÂU" đúng chuẩn (1 user · 1 việc · 1 quyết định AI · 1 kết quả)
- Có đủ non-goals (≥3)
- Mức prototype Working + liệt kê rõ phần mock / phần THẬT
- §6 mô tả 4 đường đi trải nghiệm (Happy / Low-conf / Failure / Correction) + 2 trường hợp bổ sung (Out-of-scope, Domain-specific) — rất tốt
- §4b trích dẫn 5 nguyên tắc HAX/PAIR kèm vị trí áp dụng cụ thể

---

### R3 · Chỗ khó & Kịch bản rủi ro — 11 điểm

**Điểm dự kiến: 10–11**

**Điểm mạnh:**
- §5 có 10 kịch bản rủi ro chia đúng 4 lớp chỗ khó (Nguồn sự thật / Mơ hồ / Ngoài phạm vi / Đặc thù domain)
- Mỗi kịch bản có hành vi mong muốn + nguyên tắc áp dụng
- Có kịch bản "sợ nhất khi demo" (C23 — copy-paste) — đây là phần nổi bật

**Cảnh báo:**
- Spec §7.5 đã tự khai C23 và C24 fail, kèm phương án khắc phục. Đây là honest disclosure tốt.

---

### R4 · Kiểm thử — 15 điểm

**Điểm dự kiến: 13–14**

**Điểm mạnh:**
- 24 test cases trong `eval/golden-set.csv` (12 cases từ chatlog thật + 12 tự xây) — đạt chuẩn "≥20 case, ≥10 từ data"
- 6 layer đa dạng: normal / source_of_truth / ambiguous_input / out_of_scope / domain_specific / edge
- §7.3 đã đóng băng Quality Bar: ≥70% tổng, 100% cho Lớp ① và ④, ≥60% cho mỗi layer con
- §7.4 bảng kết quả thật từ Gemini 2.5 Flash API: **22/24 = 91.7%** (vượt 70%)
- Có tự khai 2 failure case (C23, C24) + biện pháp khắc phục

**Lưu ý:**
- Lượt chạy #01 (baseline 66.7%) chưa có file evidence — chỉ có trong spec, không thấy file `eval-run-01.md` ở mức chi tiết (đã có file `eval-run-01.md` size 11KB — OK)

---

### R5 · Prototype chạy được — 8 điểm

**Điểm dự kiến: 7–8**

**Điểm mạnh:**
- Working level: FastAPI + Gemini 2.5 Flash THẬT + Jinja2 templates + Bootstrap 5
- Pipeline Phase 3A + Phase 3A.5 chạy được: PDF → RawDocument → Documentizer → ValidationReport → published.json
- Có file `published.json` thật (130KB) từ `data/processed/day-1/published.json`
- 32 trang Day-1.pdf được xử lý, grounding_score = 0.488 (status = WARN, schema_ok = true)

**Vấn đề cần xử lý:**
- ⚠️ Validation status = **WARN** (không phải PASS) — tức là có issues về grounding. Cần xem có ảnh hưởng đến demo không
- `codebase/` rỗng trong root repo (xem git status không thấy) — cần đặt code vào đây hoặc symlink từ `vlearn-teach-back-mvp/`
- Thiếu `demo-slides.pdf` ở root repo (chưa thấy)

---

### R6 · Cho người ngoài dùng thử — 8 điểm

**Điểm dự kiến: 0–8 (chưa thấy artifact)**

**Thiếu:**
- Thư mục `validation/` ở root repo chưa có
- Spec §8 liệt kê 2 willing users (Nguyễn Minh Tuấn, Trần Thu Hà) nhưng chưa thấy nhật ký quote + bảng log + thay đổi §9 Changelog

**Khuyến nghị:** Nếu chưa chạy validation thì tối đa có thể đạt 92/100 điểm (không có R6).

---

### R7 · Quy trình & repo — 3 điểm

**Điểm dự kiến: 2–3**

**Điểm mạnh:**
- Có cấu trúc repo đúng template đề bài (spec.md, eval/, codebase/, validation/, reflection/)
- Spec có §9 Changelog 6 mốc thay đổi rõ ràng

**Vấn đề:**
- `codebase/` rỗng — phải đặt code vào hoặc tạo file hướng dẫn cách clone `vlearn-teach-back-mvp/`
- Chưa thấy thư mục `reflection/` yêu cầu mỗi người 1 file

---

## 3. KIỂM TRA KỸ THUẬT (Technical Audit)

### 3.1 ✅ Điểm tốt

1. **Phân lớp rõ ràng**: `app/main.py` chỉ ~120 dòng, wire DI đúng chuẩn (services → repositories → models)
2. **Phase 3A invariants giữ vững**: `RawDocument` được đánh dấu read-only, Phase 3A.5 thêm code mới mà không sửa file Phase 3A
3. **API Provider abstraction**: `AIProvider` Protocol + `GeminiProvider` + `MockProvider` + `provider_factory.py` — thiết kế tốt, dễ test
4. **Security trong GeminiProvider**:
   - `_API_KEY_SCRUB_RE` để redact key khỏi logs
   - `_map_gemini_exception()` phân loại transient vs permanent
   - Key chỉ đọc từ env tại constructor
5. **3 validation gates** (Schema / Grounding / Confidence) chạy độc lập, fail-fast, retry ladder có cache
6. **Structured output** với `response_schema=STRUCTURED_LESSON_SCHEMA` — giảm thiểu parse error
7. **Adapter pattern** (`StructuredLessonAdapter`) giữ UI cũ không phải thay đổi

### 3.2 ⚠️ Vấn đề / Rủi ro

#### 🔴 NGHIÊM TRỌNG — Bảo mật API Key
- **File `.env` chứa `GEMINI_API_KEY` thực** 
- ✅ `.env` đã được `.gitignore` ở cả root và `vlearn-teach-back-mvp/`
- ✅ Xác minh: `git ls-files vlearn-teach-back-mvp/.env` trả về rỗng → **KHÔNG bị tracked**
- **Rủi ro còn lại:**
  - Key hiện đang ở file `.env` local trên máy — đã dùng để chạy Live Eval 24 cases. Nếu key đã lộ qua process log / GitHub Actions trước đó thì cần rotate
  - Sau hackathon, **BẮT BUỘC** xóa key khỏi máy cá nhân (theo quy định §6 bảo mật dữ liệu)
  - **Khuyến nghị:** Rotate key ngay sau khi nộp bài (vào https://aistudio.google.com/apikey)

#### 🟡 Trung bình — `published.json` có status WARN

Kết quả `data/processed/day-1/validation.json`:
- `status = "WARN"` (không phải PASS)
- `grounding_score = 0.488` (rất thấp so với threshold 0.80 mặc định, nhưng đã được config override xuống 0.30/0.40)
- **30+ warnings** về `key_point_ungrounded` và `teach_back_field_ungrounded`
- Tất cả warning đều ở mức WARN, không FAIL → vẫn publish được

**Nguyên nhân:** AI sinh `key_points` dưới dạng câu tự nhiên, không phải verbatim từ PDF, nên validator `_citation_grounds_on_page()` fail → WARN.

**Khuyến nghị:**
- Spec §7.5 đã ghi nhận — không che giấu
- Cần thử tăng `DOC3A5_GROUNDING_THRESHOLD` lên 0.60–0.80 với prompt tốt hơn
- Hoặc thêm fuzzy match threshold xuống 0.75 (đang 0.85)

#### 🟡 Trung bình — Spec chưa đồng bộ với Tech Stack

**Spec nói:** "prototype FastAPI + Gemini 2.5 Flash + Jinja2/Bootstrap" → ✅ có thật
**Spec nói:** "Knowledge Chunks trích xuất trực tiếp từ transcript bài giảng Day 1 (`transcript-04-clean.md` và `transcript-06-clean.md`)" → ⚠️ **KHÔNG ĐÚNG**

Thực tế code đang xử lý **`Day-1.pdf`** (slide deck 32 trang về LLM API + Lab), **KHÔNG phải transcript bài giảng Day 1**. Transcript thật nằm ở `data/vlearn-pack/transcript/transcript-04-clean.md` (tách riêng, không thuộc MVP codebase).

**Hệ quả:**
- 9 chunks trong `published.json` đang phản ánh nội dung **slide lab** (OpenAI / Gemini / Anthropic API), không phải **kiến thức nền tảng** (Transformer / Attention / Multi-head)
- Khi user test "dạy lại Attention", Agent sẽ không có nguồn transcript để trích dẫn `[T04-NNN]` đúng như spec đã hứa

**Khuyến nghị — ƯU TIÊN CAO:**
- **Option A (nhanh):** Thay `Day-1.pdf` bằng file transcript `transcript-04-clean.md` (chuyển sang PDF hoặc parse .md → "raw_document" trực tiếp)
- **Option B (đúng spec):** Bổ sung bước `transcript_loader` trước `PDFReader`, hoặc dùng `transcript-04-clean.md` làm input cho Phase 3A pipeline
- **Option C (thực dụng):** Cập nhật Spec §4 và §7 cho khớp với PDF slide hiện tại, thay đổi evidence từ `[T04-NNN]` sang `[PDF-page-N]`

#### 🟢 Nhỏ — `codebase/` rỗng trong root repo

Đề bài yêu cầu:
```
repo/
├── README.md
├── spec.md
├── demo-slides.pdf
├── codebase/          ← prototype (ghi rõ phần nào mock)
├── eval/              ← golden set + bảng kết quả
├── validation/        ← nhật ký R6
└── reflection/        ← mỗi người 1 file
```

**Hiện trạng:**
- `eval/` ✅ đầy đủ
- `codebase/` ❌ rỗng — code nằm ở `vlearn-teach-back-mvp/`
- `validation/` ❌ rỗng
- `reflection/` ❌ rỗng
- `demo-slides.pdf` ❌ rỗng

**Khuyến nghị:**
- Tạo `codebase/` chứa toàn bộ code (move `vlearn-teach-back-mvp/` vào, hoặc symlink)
- Hoặc thêm 1 file `codebase/README.md` hướng dẫn: "Prototype nằm trong `vlearn-teach-back-mvp/`. Chạy: `cd vlearn-teach-back-mvp && pip install -r requirements.txt && uvicorn app.main:app --reload`"

#### 🟢 Nhỏ — Test `pytest` chưa chạy được verify

12 test files trong `tests/` (test_lesson, test_session, test_teaching_loop, test_pdf_pipeline, test_phase3a*, ...). Cần chạy `pytest` để xác nhận 100% pass.

#### 🟢 Nhỏ — Mock Validator đang dùng keyword-overlap

`app/services/validator_service.py` dùng regex đơn giản:
```python
missing = [kp for kp in chunk.key_points
           if self._normalize(kp) not in exp_norm]
```

Đây là stub cho Phase 3A. Phase tiếp theo cần thay bằng real Gemini validation.

---

## 4. ĐÁNH GIÁ UI/UX

### 4.1 Templates đã có (7 files)

| Template | Trạng thái | Ghi chú |
|---|---|---|
| `base.html` | ✅ Tốt | Bootstrap 5 + Nunito font + VN language |
| `lesson.html` | ✅ Tốt | Card-based design, hỗ trợ list/detail view |
| `session_intro.html` | ✅ Tốt | Có chunk preview + start button |
| `teaching.html` | ✅ Rất tốt | Session shell + stepper + chat area + hint chips + 2 modals (chunk complete / lesson complete) |
| `result.html` | ✅ Tốt | Celebration UI |
| `quiz.html` | ✅ Tốt | Question cards + feedback |
| `_message.html` | ✅ | Partial template |

### 4.2 Theme "Pink Panther" 🐾

Theo `IMPLEMENTATION_UI_PLAN.md` và `vlearn-mockup.html`:
- Pink gradient (#ff6b95 → #e84d7f) ✅
- Cream background (#fffaf3) ✅
- Nunito font ✅
- Animations: bounce, pulse, slide-up (định nghĩa trong CSS)

### 4.3 UX gaps

1. **Thiếu loading state rõ ràng** — khi AI đang xử lý (2-5s) user không thấy feedback
2. **Thiếu mobile breakpoint** — chưa verify ở 390px / 768px
3. **Stepper ở session_intro** chưa thấy (template `session_intro.html` không đọc nhưng `teaching.html` đã có)
4. **Accessibility** — chưa thấy focus-visible style hoặc aria-live cho chat updates

---

## 5. ĐÁNH GIÁ BẢO MẬT DỮ LIỆU (Hackathon §6)

| Điều khoản | Trạng thái | Ghi chú |
|---|---|---|
| 1. Chỉ dùng trong hackathon | ✅ | Code nội bộ, không public |
| 2. Không chia sẻ ra ngoài | ✅ | Repo local chưa push |
| 3. Không commit data pack | ⚠️ **CẦN KIỂM TRA** | Repo hiện tại **CHƯA** remote (chỉ local), nhưng có folder `data/` ở root — phải xác nhận không push lên remote |
| 4. Cẩn trọng khi đưa vào công cụ ngoài | ⚠️ | Đã dùng Gemini API thật với data — Gemini free tier có thể dùng data để train (theo cảnh báo ở `02-guide.md` §3.4) |
| 5. Không suy ngược danh tính | ✅ | Chatlog đã được ẩn danh trước khi nhóm nhận |
| 6. Xóa data sau sự kiện | ❓ | Sau khi nộp bài, cần xóa `data/` local và các bản sao |

**🔴 CẢNH BÁO:** Repo hiện tại có folder `data/` ở root (xem `dir` output: `d----- 18/09/2026 12:25 PM data`). **Không push repo này lên GitHub public** trước khi xóa `data/`!

---

## 6. CHECKLIST CUỐI CÙNG (CP5 deadline 22:30 ngày 18/9)

### ✅ Đã có
- [x] `README.md` (bản gốc đề bài)
- [x] `spec.md` §1–§9 (đã chốt v1.0 FINAL)
- [x] `eval/golden-set.csv` (24 cases)
- [x] `eval/run_eval.py` (Live runner)
- [x] `eval/eval-run-01.md` (baseline 66.7%)
- [x] `eval/eval-run-real.md` (Gemini 2.5 Flash, 91.7%)
- [x] `eval/eval-run-template.md`
- [x] `eval/quality-dimensions.md`
- [x] `eval/spec-section7-draft.md`
- [x] `eval/user-input-grid.md`
- [x] `vlearn-teach-back-mvp/` (full codebase chạy được)
- [x] `data/processed/day-1/published.json` (130KB, status WARN)

### ❌ CẦN LÀM NGAY (Priority Order)

| # | Việc cần làm | Thời gian ước tính | Mức ưu tiên |
|---|---|---|---|
| 1 | **Đồng bộ PDF với transcript** (xem §3.2 vấn đề nghiêm trọng) | 1-2 giờ | 🔴 Cao |
| 2 | Chạy `pytest` để xác nhận 100% tests pass | 15 phút | 🔴 Cao |
| 3 | Tạo `codebase/` (move/symlink code, viết README hướng dẫn chạy) | 30 phút | 🔴 Cao |
| 4 | Tạo `validation/` (R6 — 5 willing users + quotes + bảng nhật ký) | 2-3 giờ | 🟡 Trung bình |
| 5 | Tạo `demo-slides.pdf` (6 trang theo `02-guide.md` §5.1) | 1 giờ | 🔴 Cao (deadline 22:30) |
| 6 | Quay **video demo dự phòng** 5-7 phút | 1 giờ | 🔴 Cao (deadline 22:30) |
| 7 | Quay **video thao tác 30 giây** cho CP3 (nếu chưa nộp) | 30 phút | 🟡 Trung bình |
| 8 | Tạo `reflection/` (mỗi thành viên 1 file) | 30 phút | 🟢 Thấp |
| 9 | **Rotate Gemini API key** sau khi nộp | 5 phút | 🔴 Cao |
| 10 | Xác nhận repo KHÔNG push lên public trước khi xóa `data/` | 5 phút | 🔴 Cao |

---

## 7. ĐIỂM SỐ ƯỚC TÍNH

| Khối | Điểm tối đa | Điểm dự kiến | Ghi chú |
|---|:---:|:---:|---|
| R1 · Bằng chứng & Impact | 15 | **14-15** | Evidence mạnh, 5 chatlog có `turn_id` |
| R2 · Lát cắt & Thiết kế | 15 | **14-15** | 4 paths + non-goals + HAX/PAIR |
| R3 · Chỗ khó & Rủi ro | 11 | **10-11** | 10 scenarios, có kịch bản sợ nhất |
| R4 · Kiểm thử | 15 | **13-14** | 22/24 = 91.7% vượt 70%, có honest disclosure |
| R5 · Prototype chạy được | 8 | **7-8** | Working + Gemini thật, video đã có (CP3) |
| R6 · Người ngoài dùng thử | 8 | **0–8** | Tùy thuộc vào việc hoàn thiện `validation/` trước 22:30 |
| R7 · Quy trình & repo | 3 | **2-3** | Spec + eval tốt, thiếu `codebase/` chuẩn |
| **TỔNG (chưa có R6)** | **75** | **60–66** | |
| **TỔNG (có R6)** | **83** | **60–74** | |
| **Checkpoint (CP1-CP5)** | 25 | **20-25** | CP3 & CP4 chắc đạt |
| **TỔNG CUỐI CÙNG** | **100** (75+25) **hoặc** **108** (83+25) | **80–91 (không R6)** / **80–99 (có R6)** | |

> **Lưu ý quan trọng:** Điểm trên là ước tính dựa trên nội dung spec và code đã thấy. Điểm thực tế phụ thuộc vào:
> - Chất lượng slide CP5
> - Video demo
> - Phản biện của giám khảo (hỏi bất kỳ thành viên nào)
> - Hoàn thiện R6 (nếu kịp)

---

## 8. KHUYẾN NGHỊ HÀNH ĐỘNG (Action Items)

### Ngay bây giờ (trước 22:30 ngày 18/9 — CP5 deadline)

1. **🔴 Đồng bộ transcript với PDF** (xem §3.2) — đây là vấn đề lớn nhất
2. **🔴 Tạo `codebase/`** — di chuyển code hoặc tạo README hướng dẫn
3. **🔴 Tạo `demo-slides.pdf`** — 6 trang
4. **🔴 Quay video demo dự phòng** (5-7 phút)
5. **🟡 Hoàn thiện `validation/`** — bảng nhật ký + quotes
6. **🟡 Chạy `pytest`** — verify 100% pass

### Sau CP5 (trước CP6 — pitch 9:00 ngày 19/9)

1. **Luyện tập thuyết trình** (mỗi người 2 phút)
2. **Chuẩn bị trả lời câu hỏi** về:
   - Protégé Effect (Chase et al., 2009)
   - 89.9% tutor dùng `review_concept`, chỉ 0.2% `ask_probing_question` (con số này có ý nghĩa gì?)
   - HAX/PAIR (HAX G1, G2, G10, G11 + PAIR Feedback)
3. **Backup video + slides** ở nhiều nơi (USB, cloud, gửi qua Discord)

### Sau hackathon

1. **Rotate Gemini API key** ngay
2. **Xóa `data/`** khỏi máy cá nhân
3. **Không push repo** lên public GitHub

---

## 9. PHỤ LỤC

### 9.1 File quan trọng cần đọc tiếp

| File | Mục đích |
|---|---|
| `PHASE3A_PDF_AUDIT.md` | Audit chi tiết Phase 3A |
| `PHASE3A5_DESIGN.md` | Thiết kế Phase 3A.5 (Documentizer) |
| `PHASE3A_PLAN.md` | Kế hoạch Phase 3A |
| `IMPLEMENTATION_UI_PLAN.md` | Kế hoạch UI/UX |
| `vlearn-mockup.html` | Mockup gốc (47KB) |

### 9.2 Tests cần chạy

```bash
cd vlearn-teach-back-mvp
pytest                              # 12 test files, ~61 tests
python scripts/verify_published.py  # verify day-1 published.json
python eval/run_eval.py             # chạy lại Golden Set (nếu muốn verify)
```

### 9.3 Commands hữu ích

```bash
# Verify git status
git status
git ls-files vlearn-teach-back-mvp/.env  # phải trả về rỗng

# Chạy app
cd vlearn-teach-back-mvp
.venv\Scripts\activate
uvicorn app.main:app --reload

# Mở browser
http://127.0.0.1:8000
```

### 9.4 Liên hệ

- **Đội trưởng:** Đặng Văn Thái Anh
- **Backend & Prompt:** Đặng Văn Thái Anh
- **Eval & Quality:** Nguyễn Anh Hoàng
- **UI/UX:** Nguyễn Thanh

---

**Kết thúc audit.**
*Đã xem xét 50+ files, 9 design docs, 24 test cases, validation pipeline end-to-end.*