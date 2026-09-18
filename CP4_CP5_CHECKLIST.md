# CHECKPOINT 4 & 5 — ĐỐI CHIẾU TÌNH TRẠNG DỰ ÁN

**Ngày đánh giá:** 2026-09-18 19:00 (UTC+7) — *trước hạn chốt spec CP4 (21:00 18/9)*
**Đối chiếu theo:** `04-rubric.md` (Phần 3 - Checklist xác minh 6 mốc)

---

## 1. TÌNH TRẠNG TỪNG MỐC (theo checklist TA xác minh)

### 🟡 CP3 (16:00 18/9) — ĐÃ NỘP ✅
| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| Lời gọi AI thật, không hardcode | ✅ | `spec.md` §4 đã khai sử dụng Gemini 2.5 Flash API thật (`google.genai`) |
| Golden set đủ case khó | ✅ | `eval/golden-set.csv` 24 cases, có case C23/C24 edge |
| Bảng đủ mọi case kể cả fail | ✅ | `eval/eval-run-real.md` ghi 22/24 Pass, **không giấu 2 case fail** |

---

### 🟡 CP4 (21:00 18/9) — CHECKLIST CỦA TA

Theo `04-rubric.md` Phần 3, CP4 yêu cầu 5 ô tích Có/Không:

| # | Yêu cầu TA xác minh | Trạng thái | Vị trí file |
|---|---|:---:|---|
| 1 | Evidence chuẩn A/B có log | ✅ | `spec.md` §1 (chuẩn B - mining 13.494 lượt chat) + 5 quote nguyên văn từ `turn_id` |
| 2 | Bảng impact + ứng viên đã loại | ✅ | `spec.md` §2 có bảng 3 ứng viên Track D, loại D1 (lớp mô phỏng đa tác tử) + D2 (productive failure) |
| 3 | 4 lớp cụ thể | ✅ | `spec.md` §5 có **10 kịch bản** (≥8), phủ đủ 4 lớp ①②③④ |
| 4 | ≥4 nguyên tắc có vị trí áp dụng | ✅ | `spec.md` §4b có 5 nguyên tắc HAX/PAIR đều trỏ vào file prototype cụ thể |
| 5 | Quality bar bằng số | ✅ | `spec.md` §7.3 chốt: **"≥70% tổng + 100% lớp ①+④ + ≥60% mỗi lớp con"** |

**Kết luận CP4: 5/5 ô ✅ — ĐẠT CHUẨN, đủ điều kiện nộp spec đúng hạn 21:00.**

---

### 🔴 CP5 (22:30 18/9) — CÒN THIẾU NHIỀU

Checklist `04-rubric.md` yêu cầu:

| # | Yêu cầu | Trạng thái | Ghi chú |
|---|---|:---:|---|
| 1 | `demo-slides.pdf` | ❌ **THIẾU** | Chưa có file PDF slide 6 trang |
| 2 | Video demo dự phòng | ❌ **THIẾU** | Chưa có file video backup |
| 3 | Dry run xong | ❓ CHƯA | Cần chạy thử flow trước khi pitch |

**Bonus (R6 - Validation):**
| # | Yêu cầu bonus | Trạng thái | Ghi chú |
|---|---|:---:|---|
| B1 | Feedback log ≥2 willing users | ❌ **THIẾU** | Đã khai 2 willing users (Tuấn + Hà) trong `spec.md` §8 nhưng chưa có log |
| B2 | ≥1 thay đổi từ feedback | ❌ **THIẾU** | Phụ thuộc B1 |

**Repo checklist (`04-rubric.md` §5.2 và R7):**
| # | Thư mục / file | Trạng thái | Ghi chú |
|---|---|:---:|---|
| A | `README.md` phân công có tên | ⚠️ **CHƯA ĐIỀN** | README có **bảng trống**, chưa điền tên thành viên |
| B | `codebase/` | ❌ **THIẾU** | Không có thư mục — cần viết `codebase/architecture.md` |
| C | `eval/` | ✅ CÓ | `golden-set.csv` (24 cases), `quality-dimensions.md`, `run_eval.py`, `eval-run-01.md`, `eval-run-real.md` |
| D | `validation/` | ❌ **THIẾU** | Cần folder feedback log |
| E | `reflection/` | ❌ **THIẾU** | Cần mỗi người 1 file cá nhân |

---

## 2. TÓM TẮT "CÒN THIẾU GÌ"

### 🔴 PHẢI CÓ trước 22:30 (CP5) — bắt buộc

```
3 việc CẦN LÀM NGAY:
─────────────────────────────────────────────────────────────────
1. demo-slides.pdf          ← 6 trang (User&Job | Vì sao chọn | Demo | Đo | User nói | Backlog)
2. video-demo-backup.mp4    ← Quay 5' lại flow chính + 1 case lỗi xử lý được
3. README.md phân công tên  ← Bảng trống trong README chưa điền
```

### 🟡 NÊN CÓ (tăng điểm R7 + R5)

```
2 việc QUAN TRỌNG:
─────────────────────────────────────────────────────────────────
4. codebase/architecture.md ← Mô tả kiến trúc, stack, sơ đồ (nếu có mermaid)
5. code/test chạy được      ← pytest qua, không có lỗi import
```

### 🟢 BONUS — không bắt buộc nhưng cộng điểm R6 (tối đa +8)

```
3 việc BONUS:
─────────────────────────────────────────────────────────────────
6. validation/user-test-log.md  ← Log từ 2 willing users (Tuấn + Hà) theo mẫu §4.2
7. Changelog ghi thay đổi từ feedback  ← Section §9 của spec.md mở rộng
8. reflection/*.md (1 file/người)    ← Mỗi thành viên viết 1 file theo rubric cá nhân
```

---

## 3. CHECKLIST CHI TIẾT THEO RUBRIC

### Phần 2 — 67 điểm + 8 bonus

| Khối | Điểm tối đa | Điểm ước tính | Thiếu gì để đạt max |
|---|:---:|:---:|---|
| R1 · Bằng chứng & impact | 15 | **13–14** | Có log evidence đầy đủ trong `spec.md` §1; impact bảng có 3 ứng viên có số. Trừ 1-2 vì evidence chỉ B (mining), chưa có A (khảo sát 20 người) |
| R2 · Lát cắt & thiết kế | 15 | **14–15** | Lát cắt đúng format 1 câu, có 3+ non-goals, ≥4 nguyên tắc có vị trí. Rất đầy đủ. |
| R3 · Chỗ khó & kịch bản | 11 | **10–11** | 10 kịch bản phủ đủ 4 lớp; 4 đường đi trải nghiệm có sơ đồ. Có kịch bản "sợ nhất khi demo" — rất tốt. |
| R4 · Kiểm thử | 15 | **14** | Golden set 24 cases đạt chuẩn (≥20 + ≥10 từ chatlog); 3 chiều D1/D2/D3 có định nghĩa; quality bar đã chốt bằng số. Trừ nhẹ vì **chưa có lượt đo mới** sau khi fix C23/C24 (theo §7.5 honest disclosure) |
| R5 · Prototype | 8 | **7** | App chạy được end-to-end (đã verify), Gemini thật ở quyết định trung tâm, khai báo mức Working đúng thực tế. Trừ 1 vì flow demo chưa được polish 100% (thuyết trình cần polish) |
| R6 · Validation | +8 | **0** | ❌ **CHƯA LÀM** — không có feedback log từ 2 willing users |
| R7 · Quy trình & repo | 3 | **1** | ❌ `codebase/`, `validation/`, `reflection/` THIẾU; `README.md` chưa điền tên |

**Tổng ước tính hiện tại: ~59/67 (+ 0/8 bonus) — tức trong khoảng 88% điểm Phần 2, chưa tính 25 điểm nộp checkpoint.**

### Phần 1 — 25 điểm nộp checkpoint

| CP | Hạn | Trạng thái | Điểm |
|---|---|:---:|:---:|
| CP1 | 19:30 17/9 | ✅ Đã nộp | 5 |
| CP2 | 21:00 17/9 | ✅ Đã nộp | 5 |
| CP3 | 16:00 18/9 | ✅ Đã nộp | 5 |
| CP4 | 21:00 18/9 | ⏳ **SẮP ĐẾN HẠN** — đã có spec.md đầy đủ, chỉ cần commit | 5 (nếu commit trước 21:00) |
| CP5 | 22:30 18/9 | ❌ Chưa nộp | 0 nếu không nộp / 5 nếu nộp |

---

## 4. KẾ HOẠCH HÀNH ĐỘNG ƯU TIÊN

### 🟥 ƯU TIÊN 1 — NGAY BÂY GIỜ (trước 21:00 để kịp CP4)
- [ ] **Commit `spec.md` lên GitHub** (file đã có đầy đủ 9 sections theo template)
- [ ] **Điền bảng phân công trong `README.md`** (3 thành viên: Đặng Văn Thái Anh, Nguyễn Anh Hoàng, Nguyễn Thanh)

### 🟧 ƯU TIÊN 2 — TRƯỚC 22:30 (CP5)
- [ ] Tạo `demo-slides.pdf` 6 trang (theo `02-guide.md` §5.1):
  1. User & Job (45s)
  2. Vì sao chọn (45s)
  3. Giải pháp & demo live (2')
  4. Kết quả đo (45s)
  5. User thật nói gì (45s)
  6. Nếu có thêm 1 tuần (30s)
- [ ] Quay video demo backup 5 phút (ghi màn hình flow chính)
- [ ] Dry run ≤1 lần, bấm giờ

### 🟨 ƯU TIÊN 3 — TRƯỚC 22:30 (Bonus R6 - cần xong để được +8)
- [ ] Liên hệ 2 willing users (Tuấn + Hà) — nhờ thử 5-10 phút
- [ ] Ghi log theo scaffold §4.2 (context → task → observe → hỏi)
- [ ] Thêm 1 dòng vào Changelog §9 spec.md sau khi có feedback

### 🟦 ƯU TIÊN 4 — TRƯỚC 09:00 NGÀY 19/9 (CP6 trình bày)
- [ ] Tạo `codebase/architecture.md` (mô tả stack + sơ đồ)
- [ ] Mỗi thành viên viết 1 file `reflection/<ten>.md`
- [ ] Mỗi thành viên **luyện nói phần của mình** (vibe-coding rule)

---

## 5. CẢNH BÁO & LƯU Ý

### ⚠️ Rủi ro nếu thiếu CP5 artifact
- `04-rubric.md` ghi rõ: *"Nộp muộn → 0 điểm cho mốc đó"* → mất **5 điểm nộp CP5**.
- Mất luôn cơ hội cộng điểm R6 bonus (+8) vì không có feedback log.

### ⚠️ Rủi ro CP6 nếu không luyện nói
- *"Vibe-coding rule: bị giám khảo hỏi khi thuyết trình mà không giải thích được phần có tên mình → 0 điểm phần cá nhân liên quan."*

### ⚠️ Lưu ý về Quality Bar
- `spec.md` đã chốt bar ở mức **70% tổng + 100% lớp ①+④**. Lượt #02 đạt 91.7% (22/24). **KHÔNG được chỉnh bar xuống** sau khi có kết quả mới (rule "không đổi bar sau khi có kết quả").

---

## 6. TÓM TẮT NHANH

| Hạng mục | Tình trạng |
|---|---|
| `spec.md` §1-§9 | ✅ Đầy đủ, đạt chuẩn nộp CP4 |
| `eval/` (golden set, runner, results) | ✅ Đầy đủ 9 files |
| Evidence (mining 13.494 lượt) | ✅ Đạt chuẩn B + 5 quote thật |
| Quality bar | ✅ Đã đóng băng số (70% + 100% lớp ①④) |
| Prototype chạy thật | ✅ App FastAPI + Gemini API thật |
| **Repo structure `codebase/`, `validation/`, `reflection/`** | ❌ **THIẾU CẢ 3** |
| **`demo-slides.pdf` + video backup** | ❌ **THIẾU** (cho CP5) |
| **Willing users feedback log** | ❌ **THIẾU** (mất 8 điểm bonus) |
| README phân công tên | ⚠️ Có file nhưng bảng trống |

### Tổng kết:
✅ **ĐỦ để nộp CP4 trước 21:00** (nếu commit spec kịp)
❌ **CHƯA ĐỦ để nộp CP5 lúc 22:30** — cần làm 3 việc bắt buộc + bonus
❌ **CHƯA ĐỦ để pitch CP6** — thiếu codebase/, reflection/, validation/

**Cần thêm ~3 giờ làm việc tập trung** để cover hết các mục thiếu.
