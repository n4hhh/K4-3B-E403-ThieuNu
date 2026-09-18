# User Input Grid — Teach Back Agent (Pink Panther) 🐾

## Bài học: Day 1 Foundation — Transformer, Attention & LLM

## Nguồn transcript: `data/vlearn-pack/transcript/transcript-04-clean.md` + `transcript-06-clean.md`

---

## 5 Chiều Phân Tích Đầu Vào Người Học

| Chiều                  | Các mức           | Mô tả                                                                                                                                  |
| ---------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Dim 1** Chunk chủ đề | T, A, C, P, R, Ev | **T**ransformer/RNN · **A**ttention & Multi-head · **C**ontext/Token · **P**arameter/RLHF · **R**einforcement/History · **Ev**aluation |
| **Dim 2** Mức đúng/sai | ✅ / 🟡 / ❌ / 🔀 | Đúng hoàn toàn / Đúng nhưng thiếu / Sai hoàn toàn / Nhầm lẫn (đúng+sai lẫn)                                                            |
| **Dim 3** Mức chi tiết | 💎 / 📋 / ✂️      | Chi tiết có ví dụ / Khái quát đủ ý / Cụt 1-2 từ                                                                                        |
| **Dim 4** Phạm vi      | 🎯 / 🔗 / 🌐      | Đúng phạm vi transcript / Liên quan nhưng ngoài transcript / Hoàn toàn ngoài bài                                                       |
| **Dim 5** Dạng input   | 💬 / 📋 / ❓ / 🎁 | Tự giải thích / Copy transcript verbatim / Hỏi ngược agent / Xin đáp án                                                                |

---

## Ma Trận Coverage — Case ID theo 5 Chiều

| Case ID | Dim1 Chunk                  | Dim2 Đúng/Sai       | Dim3 Chi tiết    | Dim4 Phạm vi        | Dim5 Dạng        | Layer           |
| ------- | --------------------------- | ------------------- | ---------------- | ------------------- | ---------------- | --------------- |
| **C01** | T (AI/ML/DL phân cấp)       | ✅ Đúng hoàn toàn   | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C02** | T (Transformer vs RNN)      | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C03** | C (Token)                   | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C04** | C (Context window)          | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C05** | P (RLHF)                    | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C06** | A (Multi-head)              | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C07** | C (Knowledge cutoff/RAG)    | ✅ Đúng hoàn toàn   | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C08** | C (Temperature/sampling)    | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C09** | Ev (Evaluation)             | ✅ Đúng hoàn toàn   | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C10** | T (AI Agent)                | ✅ Đúng hoàn toàn   | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | normal          |
| **C11** | T (Transformer origin)      | ❌ Sai sự thật      | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | source_of_truth |
| **C12** | A (Implementation detail)   | — N/A               | ✂️ Cụt/hỏi       | 🌐 Ngoài transcript | ❓ Hỏi ngược     | source_of_truth |
| **C13** | C (Context rot nguyên nhân) | 🔀 Thông tin ngoài  | 📋 Khái quát     | 🔗 Ngoài transcript | ❓ Hỏi ngược     | source_of_truth |
| **C14** | A (Attention mechanism)     | 🟡 Đúng nhưng thiếu | ✂️ Cụt mơ hồ     | 🎯 Trong bài        | 💬 Tự giải       | ambiguous_input |
| **C15** | T (Transformer parallel)    | 🟡 Đúng nhưng thiếu | ✂️ Cụt 1 câu     | 🎯 Trong bài        | 💬 Tự giải       | ambiguous_input |
| **C16** | T (LLM vs RNN)              | 🔀 Đúng+sai lẫn     | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | ambiguous_input |
| **C17** | — (Benchmark model)         | — N/A               | ✂️ Hỏi trực tiếp | 🌐 Ngoài bài        | ❓ Hỏi ngược     | out_of_scope    |
| **C18** | C (Autoregressive)          | — N/A               | ✂️ Hỏi trực tiếp | 🎯 Trong bài        | 🎁 Xin đáp án    | out_of_scope    |
| **C19** | — (Git issue)               | — N/A               | ✂️ Hỏi trực tiếp | 🌐 Ngoài bài        | ❓ Hỏi ngược     | out_of_scope    |
| **C20** | T (LLM tuần tự/song song)   | ❌ Sai kỹ thuật     | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | domain_specific |
| **C21** | R (AlphaGo)                 | ❌ Sai cơ chế       | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | domain_specific |
| **C22** | R (Symbolic AI)             | ❌ Sai lịch sử      | 📋 Khái quát     | 🎯 Trong bài        | 💬 Tự giải       | domain_specific |
| **C23** | A (Attention matrix)        | ✅ Đúng hoàn toàn   | 💎 Chi tiết      | 🎯 Trong bài        | 📋 Copy verbatim | edge            |
| **C24** | — (Phản hồi rỗng)           | — N/A               | ✂️ 1 từ          | 🎯 Trong bài        | 💬 Tự giải       | edge            |

---

## Phân Tích Coverage và Điểm Hổng

### Ô đã cover tốt ✅

- Dim2 ✅ Đúng hoàn toàn × Dim5 💬 Tự giải → **C01–C10** (10 case)
- Dim2 ❌ Sai hoàn toàn × Dim5 💬 Tự giải → **C11, C20, C21, C22** (4 case)
- Dim5 📋 Copy verbatim → **C23** (1 case — edge)
- Dim5 🎁 Xin đáp án → **C18** (1 case — out_of_scope)

### Ô hổng (Gap) ⚠️

| Dim1              | Dim2            | Gap                                                                          |
| ----------------- | --------------- | ---------------------------------------------------------------------------- |
| A (Attention)     | ❌ Sai kỹ thuật | Chưa có case học viên nhầm attention = chú ý đơn giản kiểu sai               |
| Ev (Evaluation)   | 🟡 Thiếu        | Chưa có case học viên giải thích eval nhưng thiếu benchmark set              |
| P (Parameter)     | ❌ Sai          | Chưa có case nhầm parameter = số lớp mạng                                    |
| Dim5 ❓ Hỏi ngược | Dim2 ✅ Đúng    | Thiếu case học viên hỏi ngược về chủ đề đúng scope (không hỏi để lấy đáp án) |

> **Ghi chú**: 24 case hiện tại phủ đủ 4 lớp theo yêu cầu rubric (≥2 case/lớp). Gap trên dành cho golden set v2.

---

## Thống Kê Phân Bố from_chatlog

| from_chatlog        | Số case | Case IDs                                                   |
| ------------------- | ------- | ---------------------------------------------------------- |
| TRUE (từ data thật) | 12      | C01, C02, C03, C05, C07, C08, C11, C14, C15, C16, C17, C18 |
| FALSE (nhóm tự xây) | 12      | C04, C06, C09, C10, C12, C13, C19, C20, C21, C22, C23, C24 |

> **Rubric**: ≥10 case phát triển từ data thật ✅ (đạt 12/24)
