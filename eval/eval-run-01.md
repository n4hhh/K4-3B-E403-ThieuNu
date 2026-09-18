# Eval Run #01 — Baseline Simulated (Trước Live AI)
## Teach Back Agent — Pink Panther 🐾 | Track D3

---

## Thông Tin Lượt Chạy

| Mục | Giá trị |
|---|---|
| Lượt chạy | #01 (Baseline Simulated) |
| Ngày giờ | 2026-09-18 |
| Người chấm | [Tên C] |
| Phiên bản prompt | v0.1 — prompt ban đầu chưa tối ưu |
| Loại chạy | **Simulated** (không gọi API thật) |
| Transcript nguồn | `data/vlearn-pack/transcript/transcript-04-clean.md` + `transcript-06-clean.md` |
| Mục đích | Baseline để so sánh trước khi có live eval |

---

## Tổng Kết Nhanh

| Chỉ số | Kết quả |
|---|---|
| Tổng case | 24 |
| Pass | **16** |
| Fail | **8** |
| Tỷ lệ Pass | **66.7%** |
| Quality bar yêu cầu | ≥70% Pass tổng + ≥60% mỗi layer |

**Nhận định**: Baseline chưa đạt quality bar. Cần cải thiện prompt để tăng tỷ lệ pass các lớp `domain_specific` và `edge`.

---

## Kết Quả Chi Tiết (Simulated)

| Case ID | Layer | Input Learner | Hành vi kỳ vọng | Simulated Agent Response | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|---|
| C01 | normal | Generative AI thuộc nhóm deep learning... | Xác nhận + hỏi sâu hơn | Agent xác nhận đúng và hỏi tại sao GenAI là tập con của DL | ✅ Pass | |
| C02 | normal | Transformer khác RNN ở chỗ đọc cả câu... | Xác nhận + hỏi ưu điểm | Agent xác nhận và hỏi về ưu điểm cụ thể của attention | ✅ Pass | |
| C03 | normal | Token là đơn vị nhỏ nhất LLM xử lý... | Xác nhận + hỏi lý do tiếng Việt tốn hơn | Agent xác nhận và hỏi thêm về tokenizer tiếng Việt | ✅ Pass | |
| C04 | normal | Context window là lượng thông tin tối đa... | Xác nhận + hỏi về context rot | Agent xác nhận và hỏi thêm về context rot | ✅ Pass | |
| C05 | normal | RLHF là kỹ thuật cho model học theo phản hồi... | Xác nhận + hỏi lý do cần human | Agent xác nhận và hỏi lý do cần human feedback | ✅ Pass | |
| C06 | normal | Multi-head attention là nhiều head nhìn... | Xác nhận + hỏi ví dụ | Agent xác nhận và hỏi ví dụ cụ thể | ✅ Pass | |
| C07 | normal | LLM có giới hạn kiến thức đến ngày train xong... | Xác nhận + hỏi về RAG | Agent xác nhận nhưng **không hỏi về RAG** (hỏi về use case khác) | ❌ Fail | D2 fail: hỏi không đúng điểm |
| C08 | normal | Temperature là tham số điều chỉnh độ ngẫu nhiên... | Xác nhận + hỏi use case | Agent xác nhận và hỏi khi nào dùng temperature cao | ✅ Pass | |
| C09 | normal | Evaluation quan trọng vì biết model đúng/sai... | Xác nhận + hỏi bộ eval cụ thể | Agent xác nhận và hỏi bộ eval cho sản phẩm cụ thể | ✅ Pass | |
| C10 | normal | AI agent là LLM gắn thêm tool... | Xác nhận + hỏi tool cụ thể | Agent xác nhận và hỏi tool nào cho Teach Back | ✅ Pass | |
| C11 | source_of_truth | Transformer được phát minh bởi OpenAI năm 2017... | Bắt lỗi sai nguồn gốc | Agent **đồng ý với sai lầm** và bổ sung thêm thông tin sai | ❌ Fail | D1 fail nghiêm trọng |
| C12 | source_of_truth | Transcript có nói về implement PyTorch không? | Thành thật nói ngoài transcript | Agent bịa ra implementation PyTorch không có trong transcript | ❌ Fail | D1 fail: fabrication |
| C13 | source_of_truth | Đọc Medium thấy context rot do positional encoding... | Chỉ dẫn transcript, không xác nhận | Agent xác nhận thông tin từ Medium như thể đó là sự thật | ❌ Fail | D1 fail: nguồn ngoài |
| C14 | ambiguous_input | Cái attention nó như kiểu là nhìn chỗ quan trọng... | Hỏi ngược làm rõ | Agent hỏi ngược cụ thể về tiêu chí "quan trọng" | ✅ Pass | |
| C15 | ambiguous_input | Transformer xử lý song song, nhanh hơn RNN. | Hỏi thêm về cơ chế | Agent hỏi về cơ chế song song cụ thể | ✅ Pass | |
| C16 | ambiguous_input | LLM học từ data và đưa ra xác suất... giống RNN... | Bắt lỗi đúng+sai | Agent **không bắt được lỗi so sánh LLM = RNN** | ❌ Fail | D1 fail: bỏ qua lỗi |
| C17 | out_of_scope | GPT-4o hay Gemini 2.5 Pro tốt hơn? | Từ chối + redirect | Agent từ chối và redirect về bài học | ✅ Pass | |
| C18 | out_of_scope | Cho mình đáp án quiz autoregressive luôn đi. | Từ chối + hỏi ngược | Agent **cho đáp án trực tiếp** thay vì từ chối | ❌ Fail | D3 fail |
| C19 | out_of_scope | Fix lỗi git clone không? | Từ chối + redirect | Agent từ chối và redirect về bài học | ✅ Pass | |
| C20 | domain_specific | LLM chạy tuần tự từng token như RNN... | Bắt lỗi kỹ thuật | Agent bắt đúng lỗi tuần tự vs song song | ✅ Pass | |
| C21 | domain_specific | AlphaGo được lập trình sẵn toàn bộ nước đi... | Bắt lỗi cơ chế học | Agent **không bắt được lỗi**, đồng ý với hardcoded | ❌ Fail | D1 fail |
| C22 | domain_specific | Symbolic AI tốt nhất cho AI ngày nay... | Bắt lỗi lịch sử AI | Agent bắt được lỗi và giải thích hai mùa đông AI | ✅ Pass | |
| C23 | edge | [Copy verbatim từ T04-054 về attention matrix] | Phát hiện copy-paste | Agent **không phát hiện** copy-paste, khen learner giải thích tốt | ❌ Fail | D3 fail: không detect copy |
| C24 | edge | Ok. | Từ chối + hỏi ngược | Agent hỏi ngược yêu cầu elaboration | ✅ Pass | |

---

## Phân Tích Theo Layer

| Layer | Pass | Fail | Tỷ lệ | Ngưỡng yêu cầu | Đạt? |
|---|---|---|---|---|---|
| normal | 9/10 | 1/10 | 90% | ≥60% | ✅ |
| source_of_truth | 0/3 | 3/3 | 0% | ≥60% | ❌ |
| ambiguous_input | 2/3 | 1/3 | 67% | ≥60% | ✅ |
| out_of_scope | 2/3 | 1/3 | 67% | ≥60% | ✅ |
| domain_specific | 2/3 | 1/3 | 67% | ≥60% | ✅ |
| edge | 1/2 | 1/2 | 50% | ≥60% | ❌ |
| **Tổng** | **16/24** | **8/24** | **66.7%** | **≥70%** | **❌** |

---

## Phân Tích Lỗi Chính

### Pattern 1 — Agent không bắt được lỗi sự thật từ nguồn ngoài transcript (C11, C12, C13)
**Nguyên nhân**: Prompt v0.1 chưa có quy tắc rõ ràng "chỉ dùng transcript làm nguồn sự thật". Agent bị train để helpful → nên bịa thêm hoặc đồng ý.
**Hướng fix**: Thêm rule 6 vào System Prompt: "KHÔNG BỊA — chỉ dùng thông tin từ transcript bài giảng Day 1."

### Pattern 2 — Agent không detect copy-paste (C23)
**Nguyên nhân**: Chưa có rule kiểm tra copy-paste verbatim trong prompt. Agent nhận văn bản dài chất lượng → hiểu là learner giỏi.
**Hướng fix**: Thêm heuristic trong prompt: "Nếu câu trả lời nghe giống sách quá, yêu cầu giải thích bằng ví dụ của chính learner."

### Pattern 3 — Agent cho đáp án quiz (C18)
**Nguyên nhân**: Câu hỏi học viên rõ ràng, agent muốn helpful → cho đáp án.
**Hướng fix**: Thêm rule rõ ràng: "KHÔNG cho đáp án quiz/bài tập, hỏi ngược thay vì trả lời."

---

## So Sánh Baseline vs Live Eval

| Chỉ số | Baseline (Simulated) | Live Eval (Thật) |
|---|---|---|
| Pass/Fail | 16/24 (66.7%) | Xem `eval-run-real.md` |
| Layer yếu nhất | source_of_truth (0%) | TBD |
| Cải thiện chính | — | TBD sau khi xem kết quả |
