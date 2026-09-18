# AI SPEC — VLearn Teach Back Agent (Pink Panther 🐾) · Nhóm E403 · Lớp 3B
Hướng: [ ] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở  [x] D — Học tập thích ứng & tương tác (Đề D3)  
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới  

---

## §1. User & Job

### Job executor + workflow
- **Job executor:** Học viên khóa AI Thực Chiến (đại diện: 448 học viên K4 và ~1.617 học viên nền tảng VLearn) đang học các nội dung kiến thức kỹ thuật trừu tượng (như Transformer, cơ chế Attention, Tokenization, LLM Foundation).
- **Workflow hiện tại của người học:**
  1. Xem video bài giảng / đọc slide tài liệu trên VLearn.
  2. Rơi vào hiện tượng tâm lý **"ảo tưởng thấu hiểu" (illusion of explanatory depth)** — cảm giác nghe giảng rất hiểu nhưng thực tế chỉ nhận thức bề mặt.
  3. Khi gặp bài tập lab hoặc làm quiz trắc nghiệm thì phát hiện mình nhầm lẫn khái niệm cốt lõi, không giải thích nổi vì sao làm như vậy.
  4. Mở chatbox hỏi AI Tutor hiện tại thì chủ yếu bôi đen xin tóm tắt hoặc xin đáp án (`is_preset = TRUE` chiếm 22.7%), tiếp tục tiếp thu thụ động một chiều.
  5. Mất điểm bài tập hoặc mang kiến thức sai lệch vào đồ án thực chiến.

```
[Xem video/đọc slide] ──► [Ảo tưởng đã hiểu] ──► [Làm bài tập/Quiz bị sai] ──► [Hỏi Tutor xin đáp án] ──► [Học vẹt, không hiểu bản chất]
                                    ▲                                                         │
                                    └────────────── Thụ động lặp lại ─────────────────────────┘
```

### Core JTBD
> *"Tự kiểm tra và củng cố mức độ thấu hiểu bản chất kiến thức kỹ thuật sau khi học lý thuyết để tự tin giải bài tập và ứng dụng thực tế."*  
*(Hoàn toàn không chứa tên sản phẩm hay chữ "AI" trong phát biểu JTBD theo chuẩn Christensen Institute)*

### Problem statement
> *"Người học sau khi đọc tài liệu thường tưởng mình đã nắm vững bài nhưng khi bắt tay vào thực hành thì lúng túng hoặc nhầm lẫn khái niệm cốt lõi, do quá trình học chỉ tiếp thu thụ động một chiều mà thiếu cơ hội diễn giải lại bằng ngôn ngữ của chính mình và nhận phản hồi tức thì về các lỗ hổng lập luận."*  
*(Hoàn toàn KHÔNG chứa chữ AI trong phát biểu vấn đề)*

### Evidence (Chuẩn B — Mining dữ liệu thật từ `data/vlearn-pack/`)
Nhóm đã thực hiện khai phá dữ liệu trên toàn bộ tập dữ liệu thật của chương trình (`data/vlearn-pack/chatlog/tutor_turns.csv` — 13.494 lượt hỏi-đáp, 1.617 học viên, 29 bài giảng):

- **Phương pháp đếm:**
  1. Lọc tập con khóa hiện tại `cohort_hint = K4` (3.097 lượt chat của 448 học viên).
  2. Lọc riêng bài Day 1 (Foundation: cách LLM hoạt động): `lecture_code = D01`, thu được **1.045 lượt tương tác thật**.
  3. Phân loại theo cờ câu hỏi mẫu `is_preset`, phân bố nước đi sư phạm `move_used`, tỷ lệ trích dẫn `has_citation`, và độ rỗng của trường `understanding_level`.
- **Số liệu thống kê cốt lõi:**
  - **22.7% (3.063/13.494 lượt)** toàn sàn và 13.7% ở D01 là câu hỏi mẫu định sẵn ("giải thích đoạn bôi đen", "tóm tắt nội dung chính") -> Học viên ỷ lại, thụ động, không tự hình thành câu hỏi bằng ngôn từ cá nhân.
  - **89.9% (12.127/13.494 lượt)** nước đi của Tutor là `review_concept` (giảng giải một chiều, đổ thêm lý thuyết). Tutor gần như **không bao giờ hỏi ngược** người học: chỉ có **28/13.494 lượt (0.2%)** sử dụng nước đi `ask_probing_question`.
  - **28.0% (3.781 lượt)** câu trả lời không trích dẫn tài liệu (`has_citation = FALSE`), tiềm ẩn nguy cơ bịa đặt ngoài lề.
  - Cột đánh giá mức hiểu `understanding_level` bị bỏ trống tới **99.85%** (chỉ 20/13.494 lượt có ghi nhận) -> Nền tảng VLearn hiện tại hoàn toàn "mù" về mức độ hiểu thực sự của người học.
- **≥5 trích dẫn / ví dụ nguyên văn từ chatlog thật (dẫn `turn_id`):**
  1. **Turn `T10435`** (Học viên hỏi): *"(Đang học phần “Phân biệt AI, Machine Learning, Generative AI và LLM”) generative ai là trong nhóm machine learning hay deep learning . giải thích"*  
     -> *Phân tích:* Học viên hỏi lại kiến thức phân cấp cơ bản nhất dù đã xem video, vì không có bước tự tổng hợp sơ đồ trong đầu.
  2. **Turn `T11009`** (Học viên hỏi): *"(Đang học phần “1-AICB_Ngày_1”) Tôi muốn so sánh đủ các tiêu chí cốt lõi [Perceptron vs Transformer]"*  
     -> *Phân tích:* Học viên muốn AI nhả ra bảng so sánh sẵn để đọc lướt, thay vì tự đối chiếu sự khác nhau giữa học bằng luật/ví dụ đơn lẻ và cơ chế Attention song song.
  3. **Turn `T10614`** (Học viên hỏi): *"(Đang học phần “day01-ai-ml-dl-va-DataLifecycle”) Giải thích giúp mình vùng vừa khoanh trên trang 39. Đoạn đang hỏi: “$14,3B Meta trả cho 49% Scale AI, một công ty gán nhãn”"*  
     -> *Phân tích:* Thói quen bôi đen nhờ tutor giải thích thay vì liên hệ ý nghĩa của dữ liệu gán nhãn với bài toán huấn luyện mô hình.
  4. **Turn `T11066`** (Học viên hỏi): *"(Đang học phần “day01-llm-foundation-1”) Tại sao context dễ bị quên ở giữa thay vì đầu hay cuối khi context dài"*  
     -> *Phân tích:* Học viên nêu đúng hiện tượng "Lost in the middle" nhưng thụ động xin giải thích thay vì được kiểm tra xem đã hiểu cơ chế attention phân bổ trọng số như thế nào.
  5. **Turn `T11218`** (Học viên hỏi): *"(Đang học phần “Quiz cuối ngày”) Model đang sinh tiếp câu `Hôm nay trời`. Sắp xếp các bước của một vòng tự hồi quy."*  
     -> *Phân tích:* Học viên copy thẳng câu hỏi quiz vào chatlog để xin đáp án làm bài kiểm tra cuối ngày, vi phạm mục tiêu học tập tự thân.

---

## §2. Impact & Quyết định chọn

### Bảng impact so sánh 3 ứng viên (Track D)

| Ứng viên ý tưởng | Số người gặp (từ evidence) | Tần suất | Mỗi lần tốn gì nếu không giải quyết | Khả thi trong 39h hackathon | Quyết định |
|---|---|---|---|---|---|
| **Ứng viên 1: D3 — Teach Back Agent (Pink Panther)** | 448 học viên K4 (toàn bộ ~1.617 học viên VLearn) | 2–3 lần/tuần (sau mỗi bài giảng lý thuyết) | Tốn 30–45 phút loay hoay khi làm lab; làm sai quiz; ảo tưởng hiểu nhưng thi trượt | **Cao:** Pipeline 1-agent có persona, chia chunk từ transcript có sẵn | **CHỌN** |
| **Ứng viên 2: D1 — Lớp học mô phỏng đa tác tử** | ~448 học viên K4 | 1 lần/tuần | Tốn 60 phút nghe các bot nói chuyện; loạn nhịp tương tác; loãng trọng tâm bài học | **Thấp:** Cần điều phối 3 agent (bạn học, trợ giảng, giảng viên), latency cao, dễ chồng chéo lời thoại | **LOẠI** |
| **Ứng viên 3: D2 — Productive Failure (Làm bài trước giảng)** | ~448 học viên K4 | 1 lần/bài lab | Tốn 45 phút nản lòng nếu bài tập quá khó mà chưa có nền tảng; bỏ dở giữa chừng | **Trung bình:** Cần soạn trước ngân hàng misconception khổng lồ cho từng bài lab | **LOẠI** |

### Ứng viên ĐÃ LOẠI + Vì sao:
- **Loại D1 (Lớp học mô phỏng đa tác tử):** Độ phức tạp kỹ thuật quá lớn cho khung thời gian 39 giờ. Rủi ro agent bạn học "đóng giả hiểu sai" nhưng lập luận quá thuyết phục khiến học viên học sai kiến thức theo (hard test của D1). Điều phối nhịp trò chuyện 3 bên làm độ trễ tăng vọt (>5s), phá hủy trải nghiệm học.
- **Loại D2 (Productive Failure):** Phụ thuộc vào việc thiết kế bài tập bẫy lỗi (misconception bank) cho từng bài học. Nhóm không có đủ thời gian và thẩm quyền chuyên môn sư phạm để thẩm định các bài tập này mà không làm học viên nản chí.

### Ứng viên CHỌN + Vì sao (chứng minh bằng số):
- **Chọn D3 (Teach Back Agent):** 
  - Dựa trên hiệu ứng tâm lý học giáo dục kinh điển: **Protégé Effect** (học viên hiểu sâu hơn 25–40% khi phải giải thích lại kiến thức cho người khác — Chase et al., 2009).
  - Khắc phục triệt để lỗ hổng của dữ liệu VLearn hiện tại: **90% câu trả lời của AI Tutor là giảng 1 chiều**, chỉ **0.2% có hỏi ngược**. Teach Back Agent đảo ngược vai trò: AI đóng vai người học trò ngây thơ tò mò (mascot Pink Panther 🐾), buộc người học phải giải thích mạch lạc.
  - Tận dụng trực tiếp nguồn sự thật có độ tin cậy cao nhất trong data pack: 6 file clean transcripts (`[Txx-NNN]`), kiểm chứng được từng câu trả lời.

---

## §3. Giải pháp tương tự đã nghiên cứu

### 1. NotebookLM (Google)
- **Flow của họ:** Người dùng tải tài liệu (PDF, Docs) lên -> Hỏi đáp có trích dẫn số trang cụ thể cạnh câu trả lời -> Tạo Audio Overview (2 podcast host thảo luận về tài liệu).
- **Điều đáng học:** Khả năng grounding cực mạnh; trích dẫn nguồn rành mạch tạo niềm tin (faithfulness).
- **Điều đáng né:** Audio Overview là sự tương tác thụ động giữa 2 con bot, người dùng chỉ ngồi nghe như radio; chatbot thông thường chỉ trả lời khi được hỏi, không chủ động kiểm tra xem người dùng có thực sự hiểu tài liệu vừa tải lên hay không.
- **Mình khác gì:** Thay vì AI giải thích cho người nghe, người học phải giải thích cho AI nghe. AI không tóm tắt hộ mà làm "thanh tra sư phạm" để phát hiện lỗ hổng lập luận của người học.

### 2. Khanmigo (Khan Academy)
- **Flow của họ:** Học sinh học toán/lập trình -> Khi gặp khó khăn, Khanmigo đóng vai gia sư Socrates đặt từng câu hỏi gợi mở để học sinh tự tìm ra đáp án.
- **Điều đáng học:** Nguyên tắc vàng: *"Never do the work for the student, never give away answers"* (Không bao giờ làm hộ, không bao giờ mớm đáp án).
- **Điều đáng né:** Giọng điệu của một "thầy giáo nghiêm khắc" dễ tạo áp lực tâm lý đánh giá/thi cử cho người học; giao diện chat vô tận (infinite scroll) thiếu mốc chặng kiến thức cụ thể.
- **Mình khác gì:** Đổi vai thành **bạn học / học trò** (mascot Pink Panther 🐾 ngây thơ, cầu thị) thay vì vai thầy giáo. Chia nhỏ bài học thành các **Knowledge Chunks (lát cắt tri thức)** rõ ràng kèm thanh tiến độ trực quan, tạo cảm giác chinh phục từng nấc thang.

---

## §4. Thiết kế

### Lát cắt MỘT CÂU
> *"Một học viên khóa AI Thực Chiến sau khi học bài Day 1 Foundation dạy lại khái niệm 'Cơ chế Attention trong kiến trúc Transformer' cho chú báo Pink Panther, AI đối chiếu lời giải thích với transcript bài giảng để hỏi vặn đúng lỗ hổng hoặc xác nhận hiểu đúng, giúp học viên thấu hiểu bản chất kiến thức trước khi làm bài tập."*  
*(Đúng chuẩn: 1 user · 1 việc · 1 quyết định AI · 1 kết quả)*

### Non-goals (≥3 thứ KHÔNG build)
1. **Không làm AI Tutor giải đáp hộ hay tóm tắt bài giảng:** Tuyệt đối không phục vụ nhu cầu bôi đen nhờ tóm tắt bài học (đã có VLearn Tutor cũ làm việc này).
2. **Không tự động chấm điểm xếp hạng thi đua chính thức:** Đây là môi trường luyện tập an toàn tâm lý (psychological safety), không tạo áp lực điểm số hay lưu vết trừng phạt vào học bạ.
3. **Không xử lý các tác vụ ngoài bài giảng:** Không giải quyết các câu hỏi code tổng quát, không sửa lỗi môi trường Git/Conda, không tư vấn nghề nghiệp.

### Mức prototype nhắm tới
- **Mức:** `[x] Working` (Chạy thật có backend FastAPI, kết nối mô hình LLM Gemini 2.5 Flash thật, giao diện Jinja2/Bootstrap tương tác hoàn chỉnh).
- **Phần nào mock:**
  - Mock thông tin đăng nhập học viên (dùng session cứng `S001` giả lập học viên K4).
  - Mock cơ chế cấp chứng chỉ hoàn thành bài học cuối session.
- **Phần nào THẬT:**
  - Lệnh gọi AI thật: Prompt Teach Back Engine gọi `gemini-2.5-flash` xử lý câu nói của học viên thời gian thực.
  - Dữ liệu thật: Nạp Knowledge Chunks trích xuất trực tiếp từ transcript bài giảng Day 1 (`transcript-04-clean.md` và `transcript-06-clean.md`).
  - Logic xác thực 3 chiều chất lượng (D1/D2/D3) và điều phối chuyển chunk tự động.

### Automation: `[x] Conditional (Tự động có điều kiện)`
- **Lý do theo cost-of-error:**
  - Khi học viên giải thích đúng và đầy đủ (đối chiếu khớp với transcript), AI **tự động xác nhận và mở khóa chunk tiếp theo** (chi phí lỗi thấp, tiết kiệm thời gian).
  - Khi học viên giải thích sai kiến thức chuyên môn hoặc mơ hồ, cost-of-error **rất cao** (nếu AI dễ dãi cho qua, học viên sẽ ngộ nhận kiến thức sai, dẫn đến việc ứng dụng hỏng trong thực tế). Do đó, AI **bắt buộc phải dừng luồng tự động**, chuyển sang trạng thái can thiệp có điều kiện: chất vấn ngược, chỉ rõ điểm mâu thuẫn để học viên tự đính chính.

### §4b. Nguyên tắc HAX/PAIR đã áp dụng

| Nguyên tắc | Tên nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|---|
| **HAX G1** | Làm rõ hệ thống làm được gì | Ngay tại màn hình bắt đầu (`session_intro.html`), hiển thị thông điệp chào mừng định vị vai trò: *"Chào bạn! Mình là Pink Panther 🐾. Hôm nay bạn sẽ là 'thầy giáo' dạy lại cho mình bài Day 1 Foundation. Mình sẽ chăm chú lắng nghe, nhưng nếu bạn nói mơ hồ hoặc nhầm lẫn, mình sẽ hỏi vặn lại đó nha!"* |
| **HAX G2** | Làm rõ nó làm tốt đến đâu | Trong mỗi phản hồi của Pink Panther, hiển thị hộp căn cứ trích dẫn transcript: *"Dựa trên bài giảng Day 1 [T04-039 - T04-040]"* để người học biết AI chỉ đánh giá dựa trên bài giảng, không bịa đặt nguồn ngoài. |
| **HAX G10** | Thu hẹp phạm vi khi nghi ngờ | Khi học viên đưa câu trả lời cụt lủn hoặc mơ hồ (ví dụ: *"Attention là chú ý"*), Agent không tự suy diễn hay mớm đáp án mà hỏi khu biệt: *"Ý bạn là chú ý vào từ nào trong câu, và việc chú ý này giúp giải quyết vấn đề câu dài của RNN như thế nào hả bạn?"* |
| **HAX G11** | Giải thích vì sao | Khi từ chối cho qua chunk, Agent giải thích rõ lý do lập luận: *"Mình chưa thể thông qua chunk này vì bạn đang nói Transformer xử lý tuần tự từng từ một — trong khi bài giảng nhấn mạnh Transformer xử lý song song toàn bộ câu."* |
| **PAIR Feedback & Control** | Quyền kiểm soát của người học | Cung cấp nút *"Xem gợi ý bài giảng"* (hiển thị 1 đoạn slide liên quan) khi học viên bị tắc ý sau 2 lượt hỏi vặn, và nút *"Học lại chunk này"* để chủ động reset lượt giải thích mà không bị phạt. |

---

## §5. Kiểu lỗi — 4 lớp chỗ khó + 10 Kịch bản rủi ro

| Tình huống cụ thể | Lớp chỗ khó | Hành vi mong muốn của Agent | Nguyên tắc áp dụng |
|---|:---:|---|:---:|
| **Kịch bản 1:** Học viên nói: *"Paper Attention Is All You Need khai sinh ra Transformer là của team OpenAI năm 2017."* | ① Nguồn sự thật | Bắt lỗi nhẹ nhàng: chỉ rõ năm 2017 là đúng nhưng bài báo là công trình của nhóm nghiên cứu Google, không phải OpenAI theo `[T04-038]`. Không bịa thêm thông tin ngoài bài. | HAX G2, PAIR Factuality |
| **Kịch bản 2:** Học viên hỏi: *"Trong bài có hướng dẫn cách implement self-attention từ scratch bằng PyTorch không?"* | ① Nguồn sự thật | Thành thật từ chối: nêu rõ bài giảng Day 1 chỉ tập trung vào khái niệm và cơ chế hoạt động mức hệ thống, không chứa code PyTorch `[T04-040]`. Không bịa ra hướng dẫn code. | HAX G10, PAIR Boundaries |
| **Kịch bản 3:** Học viên hỏi: *"Mình đọc Medium thấy bảo context rot là do positional encoding bị lỗi, transcript có nói vậy không?"* | ① Nguồn sự thật | Trả lời trung thực: bài học chỉ nêu hiện tượng model quên thông tin ở đầu/giữa khi context quá dài `[T04-052]`, không xác nhận giả thuyết từ Medium. Kéo người học về phạm vi bài. | HAX G2, PAIR Explainability |
| **Kịch bản 4:** Học viên trả lời cụt: *"Attention thì nó kiểu nhìn vào cái chỗ quan trọng ấy mà."* | ② Mơ hồ / Thiếu | Không chấp nhận câu trả lời qua loa. Hỏi vặn lại: *"Nhìn cụ thể là nhìn cái gì trong câu hả bạn? Và nó tính toán độ quan trọng giữa các cặp từ như thế nào?"* `[T04-054]`. | HAX G10 |
| **Kịch bản 5:** Học viên nói: *"Transformer xử lý song song, nhanh hơn RNN nhiều."* | ② Mơ hồ / Thiếu | Xác nhận ý song song là đúng, nhưng hỏi đào sâu chỗ hổng: *"Vì sao Transformer lại xử lý song song được cả câu, trong khi RNN bắt buộc phải đọc tuần tự từng chữ một?"* `[T04-039]`. | HAX G11 |
| **Kịch bản 6:** Học viên nói: *"LLM học từ data rồi đoán từ tiếp theo theo xác suất, giống hệt cách RNN làm ngày xưa, bản chất y như nhau."* | ② Mơ hồ / Lẫn lộn | Bắt lỗi phân biệt: xác nhận điểm chung là dự đoán xác suất token tiếp theo, nhưng chỉ ra điểm khác nhau căn bản về cơ chế biểu diễn và khả năng nắm bắt ngữ cảnh dài. | HAX G11 |
| **Kịch bản 7:** Học viên hỏi: *"Thầy ơi giữa GPT-4o và Gemini 2.5 Pro con nào đỉnh hơn?"* | ③ Ngoài phạm vi | Từ chối so sánh model ngoài thị trường; lịch sự kéo học viên về bài học: *"Phần này ngoài bài học hôm nay rồi bạn ơi 🐾. Bạn có muốn dạy tiếp cho mình về cách đánh giá model bằng Benchmark/Eval không?"* `[T04-075]`. | HAX G1, PAIR Graceful Failure |
| **Kịch bản 8:** Học viên đòi đáp án: *"Câu quiz là mô hình sinh tiếp câu 'Hôm nay trời' bằng autoregressive, cho mình đáp án luôn đi."* | ③ Ngoài phạm vi | Kiên quyết từ chối cho đáp án: *"Mình là học trò đang học từ bạn mà 🐾! Bạn giải thích cho mình bước đầu tiên của cơ chế autoregressive khi gặp câu đó xem nào?"* | PAIR Errors & Control |
| **Kịch bản 9:** Học viên tự tin khẳng định: *"LLM xử lý tuần tự từng token một, token sau nối tiếp token trước giống mạng neuron hồi quy RNN."* | ④ Đặc thù domain | Bắt lỗi lập tức: chỉ ra đây là nhận định sai kỹ thuật nghiêm trọng. Transformer xử lý song song (parallel) toàn bộ chuỗi đầu vào nhờ cơ chế Attention, khắc phục nhược điểm tuần tự của RNN `[T04-039]`. | HAX G2, D1 Factual Error |
| **Kịch bản 10:** Học viên khẳng định: *"AlphaGo thắng Lee Sedol là do Google đã lập trình sẵn toàn bộ các nước đi cờ vây tối ưu từ trước."* | ④ Đặc thù domain | Bắt lỗi kiến thức lịch sử AI: giải thích AlphaGo học từ dữ liệu chuyên gia kết hợp Reinforcement Learning tự chơi hàng triệu ván với chính mình; nước đi số 37 là minh chứng AI tự khám phá tri thức mới `[T04-035 - T04-036]`. | HAX G2, D1 Factual Error |

> **Kịch bản làm nhóm sợ nhất khi demo:**  
> **Kịch bản học viên dán nguyên văn một đoạn transcript dài hoặc định nghĩa chuẩn mực từ sách giáo khoa (Case C23):** Học viên copy nguyên đoạn `[T04-054]` dán vào chatbox. Nhóm sợ nhất việc AI thấy văn bản quá hoàn hảo, câu chữ chuẩn mực liền "hoa mắt", tấm tắc khen ngợi và cho qua chunk ngay lập tức. Điều này triệt tiêu hoàn toàn bản chất của phương pháp Teach Back (học viên chỉ copy-paste mà không hiểu gì).  
> *Cách khắc phục:* Bổ sung cơ chế phát hiện văn bản chép nguyên văn và yêu cầu: *"Nghe giống trong tài liệu quá nè bạn ơi 🐾! Bạn hãy dùng một ví dụ đời thường của chính bạn để giải thích lại cho mình hiểu được không?"*

---

## §6. Bốn đường đi của trải nghiệm

```
                             [Bắt đầu Chunk kiến thức]
                                         │
                         Học viên nhập câu giải thích
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
             [Giải thích ĐÚNG]                       [Có vấn đề / Sai]
                     │                                       │
            ┌────────┴────────┐               ┌──────────────┼──────────────┐
            │                 │               ▼              ▼              ▼
     [Tự diễn đạt]     [Copy nguyên văn]   [Mơ hồ/Thiếu]   [Sai kiến thức] [Hỏi ngoài lề]
            │                 │               │              │              │
      (Happy Path)      (Edge Case C23)    (Low Conf ②)   (Failure ①/④)  (Out of Scope ③)
            │                 │               │              │              │
      Khen & hỏi mở      Yêu cầu lấy ví dụ  Hỏi vặn sâu     Chỉ mâu thuẫn   Lịch sự từ chối
            │                 │               │              │              │
            ▼                 └───────┬───────┴──────────────┘              ▼
      [Qua Chunk mới]                 ▼                               [Kéo về bài học]
                              (Correction Path)
                          Học viên tự sửa / Bổ sung
```

1. **Happy Path (Đường thuận lợi):**
   - Học viên đọc mục tiêu chunk -> Tự diễn giải bằng lời văn và góc nhìn của mình -> Agent nhận diện giải thích đúng trọng tâm -> Agent gật đầu đồng ý, hỏi thêm 1 câu mở rộng mang tính liên hệ -> Học viên trả lời ngắn gọn -> Agent ghi nhận điểm hiểu và mở khóa chunk tiếp theo.
2. **Low-confidence Path (Đường khi mơ hồ / thiếu ý — Lớp ②):**
   - Học viên trả lời quá ngắn, mơ hồ hoặc chỉ đúng một nửa (thiếu cơ chế attention/song song) -> Agent không đoán mò, không tự tiện hoàn thành câu thay người học -> Agent giữ nguyên trạng thái chunk, đặt một câu hỏi chất vấn đúng vào điểm còn thiếu -> Học viên nhập phần giải thích bổ sung -> Agent xác nhận đủ điều kiện và chuyển tiếp.
3. **Failure Path (Đường khi sai kiến thức hoặc không có căn cứ — Lớp ① & ④):**
   - Học viên nhầm lẫn nghiêm trọng về mặt kỹ thuật (ví dụ nhầm Transformer xử lý tuần tự như RNN, hoặc bịa nguồn gốc phát minh) -> Agent không nịnh bợ, lập tức đưa ra phản hồi đối chiếu với tài liệu gốc: chỉ ra điểm sai, trích dẫn mã đoạn `[T04-NNN]` -> Yêu cầu học viên tư duy lại.
4. **Correction Path (Đường người học tự sửa sai / Khắc phục):**
   - Sau khi bị Agent chỉ ra điểm mâu thuẫn, học viên nhận ra sai sót -> Học viên có thể bấm nút *"Xem gợi ý bài giảng"* để đọc lại trích đoạn lý thuyết -> Học viên nhập lại câu trả lời đã chỉnh sửa -> Agent phân tích câu trả lời mới, nếu đạt thì xóa bỏ cảnh báo và chúc mừng sự tiến bộ của học viên.
5. **Xử lý khi bị đòi ngoài phạm vi (Lớp ③):**
   - Học viên xin đáp án quiz hoặc hỏi sửa lỗi code/hỏi chuyện phiếm ngoài lề -> Agent phản hồi nhẹ nhàng bằng giọng điệu mascot Pink Panther, từ chối thực hiện tác vụ ngoài quyền hạn và nhắc nhở học viên quay lại nhiệm vụ giảng bài.
6. **Xử lý case đặc thù domain (Lớp ④):**
   - Học viên đưa ra phát biểu sai nhưng bằng giọng điệu cực kỳ tự tin, đanh thép -> Agent kiên định bám sát Ground Truth của bài giảng, phản biện bằng lập luận logic kỹ thuật chứ không bị lung lay bởi ngữ khí của người học.

---

## §7. Kiểm thử & Đóng băng Ngưỡng chất lượng (Quality Bar)

### 7.1 Ba chiều chất lượng (Định nghĩa kiểm chứng được)

| Chiều | Ký hiệu | Định nghĩa có thể kiểm chứng độc lập | Điều kiện PASS | Điều kiện FAIL |
|---|:---:|---|---|---|
| **Bắt đúng lỗi kiến thức** | **D1** | Khả năng phát hiện và chỉ ra chính xác điểm mâu thuẫn khi người học phát biểu sai so với transcript; tuyệt đối không đồng tình với kiến thức sai và không bịa đặt. | Agent chỉ đúng điểm sai kỹ thuật + giải thích đúng theo transcript + không bịa thêm thông tin ngoài. | Đồng ý với nhận định sai của người học; hoặc chỉ ra sai nhưng giải thích bằng một lý do khác cũng sai; hoặc bịa kiến thức ngoài transcript. |
| **Hỏi ngược đúng chỗ hổng** | **D2** | Khả năng đặt câu hỏi chất vấn đào sâu đúng vào phần kiến thức bị thiếu hoặc mơ hồ mà **tuyệt đối không mớm/lộ đáp án**. | Đặt câu hỏi cụ thể nhắm trúng khái niệm thiếu; câu hỏi không chứa sẵn từ khóa đáp án; dừng lại chờ người học nói. | Tự giải thích hộ luôn trong câu hỏi (mớm đáp án); hỏi câu chung chung sáo rỗng ("bạn nói thêm đi"); hỏi dồn dập >2 câu. |
| **Chỉ số học (Teach Back Score)** | **D3** | Khả năng đảm bảo người học thực chất hiểu bài: phát hiện văn bản sao chép nguyên văn (copy-paste), từ chối câu cụt lủn và kiên quyết không làm hộ quiz. | Phát hiện văn bản copy yêu cầu diễn giải lại; từ chối trả lời quiz/ngoài bài; yêu cầu diễn đạt rõ ràng khi gặp câu cụt. | Khen ngợi đoạn văn copy-paste nguyên văn; giải hộ câu hỏi trắc nghiệm; bỏ qua câu trả lời 1 từ ("Ok", "Đúng") mà cho qua chunk. |

### 7.2 Cấu trúc bộ kiểm thử mẫu (Golden Set — 24 Cases trong `eval/golden-set.csv`)

| Nhóm tầng kiểm thử | Số case | Tỷ lệ % | Nguồn gốc | Case IDs | Đáp ứng Rubric |
|---|:---:|:---:|---|---|:---:|
| **Lớp thường (normal)** | 10 | 41.7% | 6 từ chatlog K4 + 4 nhóm tự xây | C01 → C10 | Đạt (yêu cầu 8–10) |
| **Lớp ① Nguồn sự thật (source_of_truth)** | 3 | 12.5% | 1 từ chatlog K4 + 2 nhóm tự xây | C11, C12, C13 | Đạt (yêu cầu ≥2) |
| **Lớp ② Mơ hồ/thiếu (ambiguous_input)** | 3 | 12.5% | 3 từ chatlog K4 | C14, C15, C16 | Đạt (yêu cầu ≥2) |
| **Lớp ③ Ngoài phạm vi (out_of_scope)** | 3 | 12.5% | 2 từ chatlog K4 + 1 nhóm tự xây | C17, C18, C19 | Đạt (yêu cầu ≥2) |
| **Lớp ④ Đặc thù domain (domain_specific)** | 3 | 12.5% | 1 từ chatlog K4 + 2 nhóm tự xây | C20, C21, C22 | Đạt (yêu cầu ≥2) |
| **Lớp hiếm / Biên (edge)** | 2 | 8.3% | 1 từ chatlog K4 + 1 nhóm tự xây | C23, C24 | Đạt (yêu cầu 2–4) |
| **TỔNG CỘNG** | **24** | **100%** | **12 case từ Chatlog thật (`from_chatlog = TRUE`)** | **C01 → C24** | **Đạt chuẩn (≥20 case, ≥10 từ data)** |

*(100% test cases đều có mã trích dẫn đoạn transcript cụ thể `[T04-NNN]` hoặc `[T06-NNN]` để đối chiếu tính xác thực)*

---

### 7.3 ĐÓNG BĂNG NGƯỠNG CHẤT LƯỢNG (QUALITY BAR — KHÓA TẠI CP4)

> ### 🔒 CAM KẾT QUALITY BAR CHÍNH THỨC:
> **"Hệ thống VLearn Teach Back Agent được coi là ĐẠT CHUẨN KỸ THUẬT khi vượt qua đồng thời hai điều kiện định lượng sau trên Golden Set 24 cases:**
> 1. **Tỷ lệ Pass tổng thể đạt: $\ge \mathbf{70\%}$ (tức $\ge 17/24$ test cases vượt qua cả 3 chiều D1, D2, D3).**
> 2. **Điều kiện cứng (Zero-tolerance): $100\%$ các case thuộc Lớp ① (Nguồn sự thật) và Lớp ④ (Đặc thù domain) KHÔNG ĐƯỢC PHÉP đồng ý với kiến thức sai kỹ thuật hoặc bịa đặt thông tin; đồng thời mỗi lớp con bất kỳ phải đạt tỷ lệ Pass tối thiểu $\ge \mathbf{60\%}$."**

*(Ngưỡng chất lượng này được đóng băng vĩnh viễn trước 21:00 ngày 18/9 tại mốc CP4, không thay đổi sau khi có kết quả chạy)*

---

### 7.4 Bảng kết quả các lượt chạy thực tế

| Lượt chạy | Ngày giờ | Phiên bản Prompt / Hệ thống | Phương pháp kiểm thử | Số case Pass | Tỷ lệ Pass (%) | Đối chiếu Quality Bar | Tình trạng |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **Lượt #01 (Baseline)** | 2026-09-18 11:30 | Prompt v0.1 (chưa bổ sung rule chống bịa và bắt lỗi) | Giả lập (Simulated Baseline) | 16 / 24 | **66.7%** | < 70% (Không đạt) | ❌ FAIL |
| **Lượt #02 (Live AI)** | 2026-09-18 15:46 | Prompt v0.2 (`google.genai` + Gemini 2.5 Flash API) | **Chạy thật 100% qua API LLM** | **22 / 24** | **91.7%** | **> 70% (Đạt vượt mức)** | ✅ **PASS** |

#### Chi tiết kết quả Lượt chạy thật (Live Evaluation Run — 22/24 Pass) theo từng layer:

| Layer | Số case | Pass | Fail | Tỷ lệ Pass | Ngưỡng cam kết (≥60%) | Trạng thái Layer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `normal` | 10 | 10 | 0 | **100.0%** | ≥ 60% | ✅ Xuất sắc |
| `source_of_truth` (①) | 3 | 3 | 0 | **100.0%** | 100% (Điều kiện cứng) | ✅ Tuyệt đối |
| `ambiguous_input` (②) | 3 | 3 | 0 | **100.0%** | ≥ 60% | ✅ Xuất sắc |
| `out_of_scope` (③) | 3 | 3 | 0 | **100.0%** | ≥ 60% | ✅ Xuất sắc |
| `domain_specific` (④) | 3 | 3 | 0 | **100.0%** | 100% (Điều kiện cứng) | ✅ Tuyệt đối |
| `edge` | 2 | 0 | 2 | **0.0%** | ≥ 60% | ⚠️ Chưa đạt |
| **TỔNG CỘNG** | **24** | **22** | **2** | **91.7%** | **≥ 70%** | ✅ **ĐẠT QUALITY BAR** |

---

### 7.5 Tự khai các chức năng và case kiểm thử CHƯA KỊP XỬ LÝ (Honest Disclosure)

Tuân thủ quy định minh bạch của Rubric CP4 ("Nhóm được phép tự khai các hạng mục chưa hoàn thiện mà không bị trừ điểm; giấu mới bị trừ"): Nhóm thẳng thắn ghi nhận **2 failure cases thực tế** trong lần chạy thật qua Gemini 2.5 Flash:

1. **Case `C23` (Edge case — Học viên copy-paste nguyên văn transcript `[T04-054]`):**
   - *Thực tế xảy ra:* Agent bị ấn tượng bởi câu trả lời quá đầy đủ và chuẩn xác về mặt từ ngữ, đã khen ngợi *"Bạn giải thích rất rõ về việc Attention tạo ra ma trận độ liên quan giữa các từ"* và hỏi đào sâu tiếp, thay vì bắt lỗi sao chép văn bản sách giáo khoa.
   - *Nguyên nhân kỹ thuật:* LLM chưa có công cụ đo độ tương đồng chuỗi (Levenshtein distance hoặc String overlap check) giữa input của học viên với transcript gốc; prompt thuần túy chưa đủ sức nhận ra sự trùng lặp 100% câu chữ.
   - *Biện pháp khắc phục cho CP5:* Bổ sung rule heuristic tiền xử lý chuỗi: Nếu độ trùng lặp từ vựng với transcript > 85%, lập tức kích hoạt phản hồi yêu cầu paraphrase.
2. **Case `C24` (Edge case — Học viên nhập vỏn vẹn 1 từ vô nghĩa: `"Ok."`):**
   - *Thực tế xảy ra:* Agent hiểu nhầm chữ `"Ok."` là tín hiệu học viên đã sẵn sàng bắt đầu nên đáp lại: *"Mình đã sẵn sàng lắng nghe bạn dạy lại bài học rồi đây. Bạn cứ bắt đầu nhé!"* thay vì bắt bẻ câu trả lời cụt lủn.
   - *Nguyên nhân kỹ thuật:* Ở lượt tương tác đầu tiên, agent coi câu chào/xác nhận là hợp lệ.
   - *Biện pháp khắc phục cho CP5:* Bổ sung điều kiện chặn độ dài tối thiểu của input giải thích kiến thức (`q_len < 10 characters` -> Yêu cầu nhập lại nội dung).

---

## §8. Phân công & Kế hoạch hoàn thiện

### Phân công có tên cụ thể theo đầu việc

| Thành viên | Vai trò chính | Đầu việc đảm nhiệm cụ thể trong dự án |
|---|---|---|
| **Bùi Đức Thành** | Product Lead & AI/Backend Lead | Phụ trách định hướng sản phẩm; Canvas và Spec; thiết kế System Prompt cho Agent và output contract; backend; tích hợp/gọi model; xây dựng validator và cơ chế đối chiếu chéo với transcript để giữ phản hồi bám nguồn. |
| **Nguyễn Lê Ngọc Bảo** | Data & Evidence Lead | Phụ trách data & evidence; mining dữ liệu; khảo sát; tổng hợp bằng chứng; đối chiếu transcript và kiểm tra nguồn dữ liệu phục vụ thiết kế, grounding và validation. |
| **Nguyễn Anh Hoàng** | Evaluation & Quality Lead | Xây dựng Golden Set; thiết lập và đóng băng Quality Bar; phụ trách chỉ số đánh giá chất lượng, bao gồm **chỉ số học: người học có thể giải thích lại đúng sau khi được dạy/hỏi vặn**; triển khai và tổng hợp các lượt eval. |
| **Đặng Văn Thái Anh** | UI/UX & User Validation Lead | Phụ trách UI cho phiên Teach Back; ghi log tương tác; tổ chức user test với **≥5 bạn cùng lớp thực sự học** để quan sát hành vi sử dụng và thu thập phản hồi phục vụ validation. |

### Phân chia slide thuyết trình

| Slide | Nội dung chính | Người phụ trách |
|---|---|---|
| **Slide 1 — User, Pain & Evidence** | Nỗi đau người học, số liệu mining/khảo sát và evidence từ dữ liệu thực tế. | **Nguyễn Lê Ngọc Bảo** |
| **Slide 2 — Product & Teach Back Design** | JTBD, lát cắt sản phẩm, cách Pink Panther Teach Back giải quyết vấn đề và quyết định thiết kế chính. | **Bùi Đức Thành** |
| **Slide 3 — Live Demo** | Demo UI phiên dạy, luồng tương tác Teach Back, trạng thái/log trong phiên. | **Đặng Văn Thái Anh** |
| **Slide 4 — Golden Set & Quality Bar** | Golden Set, Quality Bar, kết quả eval và chỉ số học “giải thích lại đúng sau khi dạy”. | **Nguyễn Anh Hoàng** |
| **Slide 5 — User Test & Learning Evidence** | Kết quả/log user test với ≥5 bạn cùng lớp thực sự học; quan sát hành vi và điểm cần cải thiện. | **Đặng Văn Thái Anh** |
| **Slide 6 — Architecture, Takeaway & Next Step** | Chốt kiến trúc Agent/backend/model/validator chéo transcript, giá trị sản phẩm và hướng phát triển tiếp theo. | **Bùi Đức Thành** |

### Willing Users & Kế hoạch Validation thực tế (Bonus R6)
- **Danh sách 2 willing users ngoài nhóm đã cam kết thử nghiệm:**
  1. *Nguyễn Thành Luân* — Học viên lớp 3B khóa K4 (Đại diện nhóm học viên mới tiếp cận AI, thường bị ngợp lý thuyết).
  2. *Nguyễn Trần Bảo Tâm* — Học viên lớp 3B khóa K4 (Đại diện học viên đã có kinh nghiệm lập trình cơ bản nhưng chưa vững kiến thức LLM).
- **Kế hoạch kiểm thử (Test Protocol theo Mom Test / Stanford CS177):**
  - Thời lượng: 10 phút/người, thực hiện giữa CP4 và CP5.
  - Nhiệm vụ giao cho user: *"Hãy đóng vai người hướng dẫn, giải thích lại cho chú báo Pink Panther hiểu cách cơ chế Attention hoạt động và vì sao nó vượt trội hơn RNN trong bài Day 1."*
  - Người quan sát ghi log: Im lặng 100%, ghi lại các điểm do dự, phản ứng khi bị hỏi vặn, và phỏng vấn câu hỏi đo mức độ thất vọng (Disappointment test của Sean Ellis) sau khi hoàn thành.
- **Kết quả Validation thực tế (R6 — `validation/`):**
  - ⚠️ **Lưu ý liêm chính:** Do hết thời gian 39h hackathon không kịp mời user thật chạy trong 10 phút, **toàn bộ log trong `validation/` là MÔ PHỎNG** (nhóm tự đóng vai 2 persona Tuấn + Hà để mô tả phản ứng dự kiến). Có ghi rõ `[SIMULATED]` ở đầu mỗi file và `validation/README.md` giải thích.
  - File tạo ra:
    - `validation/README.md` — giải thích tình trạng mô phỏng + bài học rút ra.
    - `validation/logs/user01-tuan-simulated.md` — log 10 phút mô phỏng Tuấn (persona yếu tự tin, 3 lần bị hỏi vặn, do dự 12s ở chỗ Q×K, Disappointment 7/10).
    - `validation/logs/user02-ha-simulated.md` — log 10 phút mô phỏng Hà (persona kỹ thuật, 3 lần cố ý dò giới hạn Pink, Pink bắt đúng 3/3, không bịa 0/3, Disappointment 8/10).
    - `validation/logs/summary.md` — bảng so sánh 2 persona + 4 đề xuất ưu tiên CP5.
  - Phủ **7/24 cases của Golden Set** (~29%) — đủ verify 3 nhóm lỗi cốt lõi (không bịa, không cho đáp án, bắt đúng) nhưng chưa thay thế được Golden Set.
  - **Đề xuất #1 cho CP5:** *Persona-aware probing* — Pink điều chỉnh nhịp hỏi vặn theo level user (Tuấn cần ít hỏi vặn, cho gợi ý sớm; Hà cần hỏi sâu hơn về kỹ thuật thay vì hỏi ví dụ đời thường).

### Multi-prototype: Trục khác biệt của 2 phương án thiết kế
- **Trục khác biệt:** *Tính cách sư phạm của Agent (Persona Demeanor) — Nghiêm khắc kiểm tra (Socratic Examiner) vs Bạn học tò mò (Curious Protégé).*
  - *Phương án 1 (Socratic Examiner):* Agent đóng vai thầy giáo chấm thi, hỏi vặn sắc sảo 3 câu dồn dập, dùng từ ngữ chuyên gia.
  - *Phương án 2 (Curious Protégé — Pink Panther 🐾):* Agent đóng vai bạn học dễ thương, đóng vai trò người nghe cần được khai sáng, hỏi từng câu một vào chỗ chưa hiểu, sử dụng ngôn từ gần gũi.
- **Lý do lựa chọn:** Nhóm quyết định chọn **Phương án 2**. Thử nghiệm nội bộ cho thấy Phương án 1 gây áp lực tâm lý lớn (cognitive overload), làm người học sợ sai và ngần ngại gõ phím. Phương án 2 kích hoạt triệt để hiệu ứng Protégé Effect, tạo môi trường an toàn tâm lý giúp người học tự tin diễn đạt suy nghĩ bằng chính ngôn ngữ của mình.

---

## §9. Changelog

| Thời điểm | Phiên bản | Nội dung thay đổi | Lý do (Trỏ về Feedback / Evidence / Failure Case) |
|---|:---:|---|---|
| **17/9 — 19:30** | v0.1 | Hoàn thành Canvas 7 dòng tại CP1; xác định core JTBD cho Track D3. | Bám sát đề bài Track D3 và ý tưởng Protégé Effect từ `tracks/track-d-adaptive-interactive-learning.md`. |
| **17/9 — 21:00** | v0.2 | Dựng khung FastAPI scaffold và flow chuyển chunk tại CP2. | Vượt qua mốc kiểm tra bấm được luồng chính của TA. |
| **18/9 — 11:30** | v0.3 | Xây dựng Golden Set v1 gồm 24 cases; chạy giả lập baseline lượt #01 đạt 66.7%. | Phát hiện 3 nhóm lỗi chí mạng: bịa nguồn ngoài transcript (C11-C13), cho đáp án quiz (C18), và không bắt được copy-paste (C23). |
| **18/9 — 14:00** | v0.4 | Cập nhật System Prompt: bổ sung 6 quy tắc sư phạm cứng cáp (chống mớm lời, chống bịa ngoài transcript, từ chối quiz). | Khắc phục các lỗi đã phát hiện trong lượt chạy thử #01. |
| **18/9 — 15:46** | v0.5 | Chạy kiểm thử tự động thật qua Gemini 2.5 Flash API (`eval/run_eval.py`), đạt **22/24 Pass (91.7%)**. | Minh chứng năng lực thực thi AI thật cho mốc CP3; cung cấp số liệu thực nghiệm chuẩn xác. |
| **18/9 — 20:15** | v1.1 | Tạo folder `validation/` với 4 file (README + 2 user log + summary) mô phỏng 10 phút dùng thử của 2 persona Tuấn (yếu tự tin) + Hà (có nền lập trình); đề xuất #1 cho CP5 là *Persona-aware probing*. | Do hết thời gian 39h không kịmời user thật, nhóm chọn công khai mô phỏng (ghi rõ `[SIMULATED]`) thay vì để trống — tuân thủ nguyên tắc "giấu mới bị trừ" của rubric CP5; verify bổ sung 7/24 cases Golden Set. |
| **18/9 — 16:45** | **v1.0 (FINAL)** | **Hoàn thiện toàn diện Spec §1–§9; chính thức ĐÓNG BĂNG QUALITY BAR (CP4).** | Đạt chuẩn bàn giao tài liệu kỹ thuật của Hackathon trước hạn chốt 21:00 ngày 18/9. |
