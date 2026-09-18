# 🎨 DEMO SLIDES OUTLINE — VLearn Teach Back Agent (Pink Panther 🐾)

> **Nhóm E403 · Lớp 3B · VinAI K4 Hackathon**
> Người trình bày: Thái Anh (slide 1, 3 — backend) · Hoàng (slide 4, 5 — eval) · Thanh (slide 2, 6 — frontend + kết)
> Tổng thời gian: 5 phút trình bày + 5 phút Q&A

---

## 📌 QUY TẮC BẮT BUỘC

| Quy tắc | Cách áp dụng |
|---|---|
| **Không slide nào không có số / quote / kết quả đo** | Mỗi slide phải có ≥1 con số mining, hoặc pass rate, hoặc quote nguyên văn |
| **5 phút trình bày** | Slide 1-2-4-5-6 mỗi slide ≤45s; Slide 3 (demo live) ≤2 phút |
| **Mỗi thành viên nói ≥1 phần** | Thái Anh: slide 1+3 · Hoàng: slide 4+5 · Thanh: slide 2+6 |
| **Thẻ giám khảo** | 1 dev sẵn sàng mở terminal + UI để chạy case bất kỳ tại chỗ → Hoàng đứng máy |
| **Không chỉ show happy path** | Slide 3 demo bắt buộc chạy **1 case lỗi** (xem §3) |

---

## 🎬 SLIDE 1 — USER & JOB (45s, Thái Anh trình bày)

**Ý chính:** *Người dùng là ai? Họ đang đau đầu điều gì?*

```
┌─────────────────────────────────────────────────────────────┐
│ 🐾 VLearn Teach Back Agent (Pink Panther) · E403            │
│                                                             │
│ 👤 JOB EXECUTOR                                              │
│ Học viên khóa AI Thực Chiến                                 │
│ (448 K4 + ~1.617 VLearn users)                              │
│                                                             │
│ 🎯 CORE JTBD (không chữ AI — đạt chuẩn Christensen):        │
│ "Tự kiểm tra và củng cố mức độ thấu hiểu                   │
│  bản chất kiến thức kỹ thuật sau khi học lý thuyết"       │
│                                                             │
│ 💔 PAIN NUMBERS (từ mining 13.494 lượt chat):              │
│ • 89.9% tutor giảng 1 chiều (chỉ 0.2% có hỏi ngược)        │
│ • 22.7% học viên bôi đen nhờ tutor tóm tắt hộ              │
│ • 99.85% mức độ hiểu KHÔNG được đo lường                   │
│                                                             │
│ 🐾 "Mình là Pink Panther — bạn sẽ DẠY lại cho mình"        │
└─────────────────────────────────────────────────────────────┘
```

**Nguồn evidence (để giám khảo hỏi):**
- 13.494 lượt chat, 1.617 học viên, 29 bài — file `data/vlearn-pack/chatlog/tutor_turns.csv`
- Phương pháp đếm: lọc `cohort_hint = K4` → 3.097 lượt → lọc `lecture_code = D01` → 1.045 lượt
- 4 quote nguyên văn có `turn_id`: T10435, T11009, T11066, T11218 (xem chi tiết trong `spec.md` §1 Evidence)

**Ghi chú cho người nói:**
- Nêu JTBD chậm, để giám khảo kịp đọc
- Nhấn mạnh "99.85% mức hiểu không đo được" — đây là số đắt nhất
- Kết slide: *"Không phải vì AI dở, mà vì mô hình cũ hỏi một chiều, học viên ỷ lại không tự hình thành câu hỏi."*

---

## 🎬 SLIDE 2 — VÌ SAO CHỌN (45s, Thanh trình bày)

**Ý chính:** *Vì sao không chọn ý tưởng khác mà lại làm Teach Back?*

```
┌─────────────────────────────────────────────────────────────┐
│ 3 ỨNG VIÊN — CHỌN D3 (Teach Back Agent)                    │
│                                                             │
│ Ứng viên     │ Người │ Tần suất │ Tốn/Lần   │ Khả thi │ Chọn│
│ D3 Teach Back│ 448   │ 2-3/tuần │ 30-45p lab │ Cao     │  ✅  │
│ D1 Multi-agt │ 448   │ 1/tuần   │ 60p loạn   │ Thấp    │  ❌  │
│ D2 Prod.Fail │ 448   │ 1/lab    │ 45p nản    │ TB      │  ❌  │
│                                                             │
│ ❌ Loại D1 (3 agent): latency >5s + agent "đóng giả" gây   │
│    học sai → vi phạm hard test                              │
│ ❌ Loại D2: cần misconception bank khổng lồ,                │
│    không đủ thời gian/thẩm quyền chuyên môn                 │
│                                                             │
│ ✅ CHỌN D3: Protégé Effect (Chase 2009)                     │
│    Tự giải thích lại → hiểu sâu hơn 25-40%                   │
└─────────────────────────────────────────────────────────────┘
```

**Nguồn (để giám khảo hỏi):**
- Bảng impact đầy đủ trong `spec.md` §2 (có 4 cột yêu cầu: số người · tần suất · tốn gì · khả thi)
- Protégé Effect citation: Chase et al., 2009 — Byrnes & Wasik

**Ghi chú cho người nói:**
- Slide này CHỨNG MINH team đã cân nhắc 3 hướng trước khi làm (rubric yêu cầu)
- Không trình bày lại bảng, chỉ chỉ và chốt: *"Chúng mình chọn đảo vai — biến AI từ thầy thành trò."*

---

## 🎬 SLIDE 3 — DEMO LIVE (2 phút, Thái Anh demo + Hoàng đứng máy)

**Ý chính:** *Chạy thật. KHÔNG bằng video.*

```
┌─────────────────────────────────────────────────────────────┐
│ 🔪 LÁT CẮT MỘT CÂU (đạt chuẩn: 1 user · 1 việc · 1 quyết │
│    định AI · 1 kết quả)                                     │
│                                                             │
│ "1 HV sau khi học Day 1 dạy lại 'Cơ chế Attention          │
│  trong Transformer' cho Pink Panther → AI đối chiếu         │
│  transcript hỏi vặn lỗ hổng hoặc xác nhận hiểu đúng →      │
│  HV tự tin làm bài tập"                                     │
│                                                             │
│ ⚙️  AUTOMATION = CONDITIONAL                                │
│ "Đúng & đủ → tự qua chunk. Sai/mơ hồ → DỪNG tự động,       │
│  chất vấn ngược vì cost-of-error rất cao                    │
│  (học sai kiến thức chuyên môn)"                             │
│                                                             │
│ 🎬 DEMO — 2 case LIÊN TIẾP (mỗi case 30s)                   │
│                                                             │
│  CASE 1 (Happy path):                                        │
│  HV: "Attention là cơ chế tính trọng số giữa các từ        │
│      trong câu, giúp Transformer xử lý song song            │
│      cả câu thay vì tuần tự từng từ như RNN"               │
│  Pink: ✅ "Đúng rồi! Bạn giỏi quá. Bạn có thể nói         │
│         thêm vì sao đặt trọng số này dùng Q,K,V matrix?"   │
│                                                             │
│  CASE 2 (Failure path — luật "không chỉ happy path"):       │
│  HV: "LLM xử lý tuần tự từng token, giống hệt RNN         │
│      chỉ khác là dùng Attention"                             │
│  Pink: ❌ [T04-039] "Hmm bạn ơi 🐾, bạn vừa nói tuần tự   │
│         đúng không? Bài giảng nhấn mạnh Transformer xử lý   │
│         SONG SONG toàn bộ câu chứ không tuần tự nhé."       │
└─────────────────────────────────────────────────────────────┘
```

**Checklist trước khi demo (Hoàng lo):**
- [ ] Server đã chạy (`uvicorn app.main:app --reload`)
- [ ] Tab UI mở sẵn tại `/session/S001/intro` (student giả lập)
- [ ] File `processed/day-1/published.json` đã có Knowledge Chunks
- [ ] API key Gemini 2.5 Flash còn hạn
- [ ] 2 lệnh copy sẵn vào clipboard để paste trong lúc demo

**Dự phòng case lỗi (nếu giám khảo muốn hack):**
- C9: *"LLM học từ data rồi đoán token tiếp theo → y như RNN"* → Pink phải phân biệt dự đoán xác suất với cơ chế biểu diễn
- C20: *"Paper Attention Is All You Need là của team OpenAI 2017"* → Pink phải nói *"bài báo là của Google, năm 2017 đúng"*
- C22: *"AlphaGo thắng Lee Sedol do lập trình sẵn nước cờ"* → Pink phải nói RL tự chơi, nước 37 là tự khám phá

**Ghi chú cho người nói:**
- **Case lỗi nằm ở thứ 2** (không nằm ở thứ nhất) — để mở đầu tạo cảm giác mượt, sau đó chứng minh thằng ra nó làm được cái khó
- Nếu thẻ giám khảo yêu cầu: bấm ngay vào input box, paste case của giám khảo

---

## 🎬 SLIDE 4 — KẾT QUẢ ĐO (45s, Hoàng trình bày)

**Ý chính:** *Đo được kết quả gì? Quality bar là gì? Có bao nhiêu fail?*

```
┌─────────────────────────────────────────────────────────────┐
│ 🔒 QUALITY BAR (đã chốt tại CP4 — 16:45 18/9, KHÔNG đổi)  │
│                                                             │
│ • ≥ 70% tổng (17/24)                                        │
│ + 100% lớp ① Nguồn sự thật & ④ Domain (điều kiện cứng)    │
│ + ≥ 60% mỗi lớp con                                         │
│                                                             │
│ 📊 KẾT QUẢ 2 LƯỢT CHẠY                                    │
│                                                             │
│ Lượt │ Prompt │ Phương pháp │ Pass │ Tỷ lệ │ vs Bar         │
│ #01  │ v0.1   │ Simulated   │ 16/24│ 66.7% │ ❌ FAIL        │
│ #02  │ v0.2   │ LIVE Gemini │ 22/24│ 91.7% │ ✅ ĐẠT        │
│                                                             │
│ ⚠️ FAILURE NGHIÊM TRỌNG NHẤT (minh bạch — "giấu mới trừ"): │
│ Case C23 — Học viên copy-paste transcript [T04-054]:        │
│ Pink "hoa mắt" khen ngay → triệt tiêu Teach Back.          │
│ Khắc phục: heuristic overlap >85% → yêu cầu paraphrase     │
└─────────────────────────────────────────────────────────────┘
```

**Bảng chi tiết (mở rộng nếu giám khảo quan tâm):**

| Layer | Pass | Tỷ lệ | Quality Bar | Trạng thái |
|---|:---:|:---:|:---:|:---:|
| `normal` | 10/10 | 100% | ≥60% | ✅ Xuất sắc |
| ① `source_of_truth` | 3/3 | 100% | 100% (cứng) | ✅ Tuyệt đối |
| ② `ambiguous_input` | 3/3 | 100% | ≥60% | ✅ Xuất sắc |
| ③ `out_of_scope` | 3/3 | 100% | ≥60% | ✅ Xuất sắc |
| ④ `domain_specific` | 3/3 | 100% | 100% (cứng) | ✅ Tuyệt đối |
| `edge` | 0/2 | 0% | ≥60% | ⚠️ Chưa đạt |
| **TỔNG** | **22/24** | **91.7%** | **≥70%** | ✅ **ĐẠT BAR** |

**Nguồn (để giám khảo hỏi):**
- File: `vlearn-teach-back-mvp/eval/golden-set.csv` (24 cases)
- Run script: `eval/run_eval.py` (output lưu trong `_audit_out.txt`)
- Baseline cũ ngày 11:30 đạt 66.7%, Prompt v0.4 đã fix 3 nhóm lỗi

**Ghi chú cho người nói:**
- Slide này có **khả năng nhận điểm cao nhất** nếu Honest Disclosure
- Trình bày số bảng nhanh, dừng ở "22/24 = 91.7%"
- Nếu giám khảo hỏi "vì sao chỉ 22/24, không phải 24/24": **trả lời ngay** — 2 case edge (C23 copy-paste, C24 "Ok.") đã được phát hiện và có kế hoạch sửa
- KHÔNG được che failure case — rubric nói "giấu mới bị trừ"

---

## 🎬 SLIDE 5A — USER THẬT NÓI GÌ (45s, Thanh trình bày)

**Ý chính:** *Có willing users thật không? Họ phản hồi gì?*

### ✅ CHỌN NẾU ĐÃ LÀM VALIDATION (bonus R6 +1 điểm):

```
┌─────────────────────────────────────────────────────────────┐
│ 👥 VALIDATION VỚI 2 USER THẬT (bonus R6)                    │
│                                                             │
│ 1. Nguyễn Minh Tuấn — HV 3B, mới tiếp cận AI:              │
│    💬 "Lúc Pink hỏi vặn mình bị khựng, phải dừng lại       │
│        nghĩ thật — lúc đó mới nhớ ra mình chưa hiểu kỹ."  │
│    📝 Quan sát: Bỏ qua 1 case tự đánh giá → đã sửa nút    │
│       "Xem gợi ý bài giảng" rõ hơn trong UI.               │
│                                                             │
│ 2. Trần Thu Hà — HV 3B, có nền lập trình:                  │
│    💬 "Mình cố tình nói bậy về AlphaGo xem Pink có bắt     │
│        không — bạn ấy bắt đúng luôn."                       │
│    📝 Quan sát: Đã pass → giữ nguyên để làm signature      │
│       chất lượng cho domain-specific cases.                 │
└─────────────────────────────────────────────────────────────┘
```

> **Nếu chưa chạy với user thật trước demo** → dùng SLIDE 5B (bảng pass rate — an toàn hơn, không bị trừ điểm nếu không có)

### ⚠️ BẢN AN TOÀN (SLIDE 5B, không có validation):

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 KẾT QUẢ ĐO TRÊN GOLDEN SET (24 cases) — chạy thật 100% │
│                                                             │
│ Lớp       │ Pass │ Tỷ lệ │ Quality Bar │ Trạng thái         │
│ Normal    │ 10/10│ 100%  │ ≥60%       │ ✅ Xuất sắc          │
│ ① Sự thật │  3/3 │ 100%  │ 100% (cứng)│ ✅ Tuyệt đối         │
│ ② Mơ hồ   │  3/3 │ 100%  │ ≥60%       │ ✅ Xuất sắc          │
│ ③ Ngoài lề│  3/3 │ 100%  │ ≥60%       │ ✅ Xuất sắc          │
│ ④ Domain  │  3/3 │ 100%  │ 100% (cứng)│ ✅ Tuyệt đối         │
│ Edge      │  0/2 │   0%  │ ≥60%       │ ⚠️ Chưa đạt         │
│ TỔNG      │22/24│ 91.7% │ ≥70%       │ ✅ ĐẠT BAR          │
│                                                             │
│ ⚠️ 2 case edge (C23 copy-paste, C24 "Ok.") đang được sửa    │
└─────────────────────────────────────────────────────────────┘
```

**Ghi chú:** Thanh chọn 5A hay 5B tùy vào việc đã có log validation hay chưa. Slide 5A bổ sung thì không slide 5B (đếm 1 slide, không 2).

---

## 🎬 SLIDE 6 — NẾU CÓ THÊM 1 TUẦN & KẾT (30s, Thanh + cả nhóm)

**Ý chính:** *Biết mình còn thiếu gì. Rồi chốt cảm xúc.*

```
┌─────────────────────────────────────────────────────────────┐
│ 🛠️  ƯU TIÊN TIẾP THEO                                       │
│                                                             │
│ 1. Fix 2 edge case C23 + C24 trong prompt v0.3              │
│    → Kỳ vọng lên 100% lớp edge                              │
│                                                             │
│ 2. Mở rộng Knowledge Chunks cho Day 2-6                     │
│    (đã có sẵn 6 transcripts Day 1-6)                         │
│                                                             │
│ 3. Multi-modal: cho Pink Panther xem ảnh slide              │
│    trong transcript                                          │
│                                                             │
│ 💡 BÀI HỌC LỚN NHẤT                                        │
│ "Đảo vai AI (từ thầy → trò) thay đổi hoàn toàn             │
│  cách người học tư duy: từ THỤ ĐỘNG hỏi → CHỦ ĐỘNG dạy"   │
│                                                             │
│ 🐾 Cảm ơn mọi người — Q&A                                   │
└─────────────────────────────────────────────────────────────┘
```

**Ghi chú cho người nói:**
- Slide ngắn, kết bằng 1 câu cảm xúc — đừng dài dòng
- Sau "Q&A" → im lặng, đợi giám khảo hỏi trước

---

## 📋 PHÂN CÔNG TRÌNH BÀY (để cả team vào nhận slide của mình)

| Slide | Thành viên phụ trách | Deadline viết xong | Ghi chú |
|:---:|---|:---:|---|
| 1 — User & Job | **Thái Anh** (backend) | 18/9 20:00 | Dùng số mining từ `spec.md` §1 |
| 2 — Vì sao chọn | **Thanh** (frontend) | 18/9 20:00 | Bảng 3 ứng viên từ `spec.md` §2 |
| 3 — Demo LIVE | **Thái Anh demo** + **Hoàng đứng máy** | 18/9 20:30 | Chuẩn bị 2 case (happy + fail) |
| 4 — Kết quả đo | **Hoàng** (eval) | 18/9 20:00 | Số pass rate từ `_audit_out.txt` |
| 5 — User thật | **Thanh** (UI) | 18/9 20:00 | Hoặc 5A (user) hoặc 5B (golden set) |
| 6 — Kết + 1 tuần | **Cả nhóm** (Thanh mở) | 18/9 20:00 | Câu chốt "Thụ động → Chủ động" |

---

## 📂 TÀI NGUYÊN THAM CHIẾU

| File cần mở trong lúc demo | Đường dẫn |
|---|---|
| Spec đầy đủ | `spec.md` |
| Audit + đánh giá trước | `AUDIT_REPORT.md`, `RE_EVALUATION_REPORT.md` |
| Golden Set 24 cases | `vlearn-teach-back-mvp/eval/golden-set.csv` |
| Output lượt chạy #02 | `vlearn-teach-back-mvp/_audit_out.txt` |
| Source app | `vlearn-teach-back-mvp/app/main.py` |
| System Prompt | `vlearn-teach-back-mvp/app/agents/pink_panther/prompts.py` |

---

## 🐾 CHECKLIST TRƯỚC KHI LÊN SÂN (lúc 20:45 ngày 18/9)

- [ ] Cả 6 slide đã viết xong, share drive PDF
- [ ] Thái Anh mở terminal sẵn, server đang chạy
- [ ] Hoàng mở sẵn tab `/session/S001/intro` và Golden Set
- [ ] Thanh mở sẵn slide editor + 1 cửa sổ overview cho giám khảo xem UI
- [ ] 3 trong 6 slide có 1 câu quote/số đọc sẵn
- [ ] **Không ai nói "tóm tắt lại bài" trong bất kỳ slide nào** — đó là điều Pink Panther từ chối

> *"Đừng tóm tắt slide cho giám khảo. Hãy kể câu chuyện của học viên thật."*
