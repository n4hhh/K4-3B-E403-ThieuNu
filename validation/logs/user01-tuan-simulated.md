# 📋  Validation Log — Nguyễn Minh Tuấn


---

## 1. THÔNG TIN CHUNG

| Mục | Giá trị |
|---|---|
| **User** | Nguyễn Minh Tuấn |
| **Persona** | HV lớp 3B K4, **mới tiếp cận AI**, thường bị ngợp lý thuyết Transformer/Attention |
| **Ngày giờ** | Mô phỏng — 2026-09-18 ~19:00 (sau CP4) |
| **Thời lượng** | 10 phút |
| **Người quan sát** | Mô phỏng bởi Nguyễn Thanh (UI Lead) |
| **Nhiệm vụ** | *"Hãy đóng vai người hướng dẫn, giải thích lại cho chú báo Pink Panther hiểu cách cơ chế Attention hoạt động và vì sao nó vượt trội hơn RNN trong bài Day 1."* |
| **Mục tiêu đo** | (1) Điểm do dự khi bị Pink hỏi vặn · (2) Phản ứng khi bị từ chối qua chunk · (3) Mức độ hài lòng sau 10p (Sean Ellis Disappointment Test) |

---

## 2. TIMELINE QUAN SÁT 

| Thời điểm | Hành động user| Phản hồi Pink Panther | Quan sát / cảm xúc |
|:---:|---|---|---|
| **T+0:00** | Đọc mục tiêu chunk 1, im lặng 8s rồi gõ | Pink chào + nói rõ vai | Rõ ràng bất ngờ vì "AI đóng vai học trò" — dừng đọc mục tiêu 2 lần |
| **T+0:35** | *"Attention là cái cơ chế giúp mô hình biết từ nào quan trọng khi đọc câu."* | Pink: *"Bạn giỏi quá! Bạn nói thêm giúp mình vì sao điều này giúp Transformer không phải đọc tuần tự như RNN được không?"* | Dừng 5s — thấy mình chưa nghĩ tới điểm "song song" |
| **T+1:45** | *"Ờm... vì Transformer nó đọc hết cả câu một lúc ấy, nó biết được từ nào với từ nào liên quan."* | Pink: *"Đúng rồi 🐾 Bạn nói cho mình nghe 'liên quan' được tính bằng cái gì trong bài không?"* | Lần đầu tiên bị hỏi vặn — lúng túng, gõ rồi xóa 2 lần |
| **T+2:50** | *"Được tính bằng... độ tương đồng? Em không nhớ rõ."* | Pink: *"Bạn gần đúng rồi, mình nghĩ bài dùng từ 'trọng số'. Bạn thử giải thích 'trọng số' là gì xem?"* | Thở phào — Pink "mớm" keyword nhưng vẫn ép giải thích tiếp. Đây là điểm hay |
| **T+4:10** | *"Trọng số là số nói mức quan trọng giữa 2 từ. Mỗi từ có 3 ma trận Q K V."* | Pink: *"Xuất sắc! Bạn nhớ kỹ ghê. Bạn cho mình biết Q K V làm gì khác nhau?"* | Tự tin hẳn lên — bắt đầu dùng từ chuyên môn |
| **T+5:30** | *"Q hỏi, K trả lời, V là giá trị thật."* | Pink: *"Hmm bạn ơi 🐾, bạn nói K 'trả lời' Q nghĩa là sao? Mình hơi mơ hồ chỗ này."* | Lại bị hỏi vặn — lần này **do dự 12s** (dài nhất session) |
| **T+7:20** | *"Ờ... thật ra em không chắc lắm, em chỉ nhớ là Q nhân với K."* | Pink: *"Ok bạn! Mình hiểu ý bạn rồi. Nếu sau này bạn muốn đào sâu thêm, bạn có thể bấm 'Xem gợi ý bài giảng' nhé."* — qua chunk | **Nhẹ người** — nhận ra mình chưa hiểu kỹ Q×K nhưng không bị phạt |
| **T+8:00** | Chuyển chunk 2 (vì sao Transformer > RNN). Bắt đầu tự nói trước khi đọc mục tiêu. | Pink lắng nghe | **Behavioral shift rõ rệt** — bắt đầu chủ động cấu trúc câu trả lời thay vì chờ đọc |
| **T+9:30** | Hoàn thành 2/3 chunks. Tự đánh giá "Đoạn Q×K mình chưa hiểu lắm" | Pink cảm ơn + hiện nút "Xem gợi ý" | Tự nhận lỗ hổng — đây là thành công lớn nhất của session |
| **T+10:00** | Kết thúc. Trả lời Disappointment Test | — | Xem §3 bên dưới |

---

## 3. PHỎNG VẤN SAU SESSION 

**Câu hỏi:** *"Nếu tuần sau bài Day 1 có Pink Panther nhưng không có sẵn — bạn sẽ thất vọng đến mức nào?"*

> **Tuấn (mô phỏng):** *"Mức 7/10. Lúc đầu mình hơi khó chịu vì bị hỏi vặn liên tục, nhưng về sau mình nhận ra mấy chỗ mình nói bậy mà không biết. Đặc biệt là chỗ Q×K — mình tưởng mình hiểu mà thật ra chỉ nhớ keyword. Pink bắt được chỗ đó."*

**Câu hỏi mở (Mom Test):** *"Bạn nhớ lại lúc nào trong 10 phút vừa rồi mà bạn thấy... khó chịu nhất?"*

> **Tuấn (mô phỏng):** *"Lúc Pink hỏi 'Q K V làm gì khác nhau' — mình bị bí và tự dưng thấy mình học bài cũng chỉ chăm chăm nhớ công thức chứ không hiểu bản chất. Hơi sốc."*

**Câu hỏi mở:** *"Nếu có 1 thứ để sửa, bạn muốn sửa gì?"*

> **Tuấn (mô phỏng):** *"Lúc mình bị bí mà Pink gợi ý keyword 'trọng số' thì dễ chịu, nhưng sau đó Pink lại hỏi tiếp 'trọng số là gì' — hơi dồn. Nếu cho mình nút 'Xem gợi ý bài giảng' ngay từ đầu thì mình tự bấm, đỡ bị áp lực hơn."*

---

## 4. ĐIỂM ĐO LƯỜNG 

| Chỉ số | Kết quả | Đạt mục tiêu? |
|---|---|---|
| Số chunks hoàn thành / tổng | 2 / 3 | ⚠️ Trung bình (do dừng ở chunk khó) |
| Số lần bị Pink hỏi vặn | 3 | ✅ (đúng thiết kế — bắt lỗ hổng) |
| Số lần user tự điều chỉnh câu trả lời | 2 | ✅ (đang dần làm chủ) |
| Số lần user tự nhận lỗ hổng bằng lời | 1 | ✅ (chuyển từ thụ động → chủ động) |
| Disappointment Score | 7 / 10 | ✅ (≥40% theo Sean Ellis = sản phẩm có giá trị) |
| Thời gian dừng trung bình khi bị hỏi vặn | 7.3s | ⚠️ Có 1 lần 12s (Q×K) — cần cho "Xem gợi ý" sớm hơn |

---

## 5. ĐỀ XUẤT CẢI TIẾN (feedback → spec)

| # | Feedback | Hành động đề xuất cho CP5 | Nguyên tắc |
|:---:|---|---|---|
| 1 | "Cho nút 'Xem gợi ý' xuất hiện sớm hơn sau 1 lần hỏi vặn, không phải 2 lần" | Giảm `MAX_PROBE_BEFORE_HINT` từ 2 xuống 1 | HAX G10 |
| 2 | "Lúc Pink 'mớm' keyword 'trọng số' rồi vẫn hỏi tiếp — hơi dồn" | Refactor: sau khi mớm keyword, Pink hỏi **1** câu đơn giản hơn thay vì câu cùng độ khó | PAIR Feedback & Control |
| 3 | "Tự dưng nhận ra mình chỉ nhớ keyword chứ không hiểu bản chất" | **GIỮ NGUYÊN** — đây là thành công cốt lõi của Teach Back | (đã đạt mục tiêu) |
| 4 | "Behavioral shift rõ rệt ở chunk 2 — chủ động hơn" | **GIỮ NGUYÊN** — Protégé Effect hoạt động | (đã đạt mục tiêu) |

---

## 6. ĐÁNH GIÁ TỔNG HỢP

> **Tuấn — Persona "mới tiếp cận AI" đã được verify:** Pink Panther thực hiện đúng vai "bạn học cầu thị" gây áp lực vừa đủ để user tự phát hiện lỗ hổng, không gây sợ hãi. Tuy nhiên cần giảm tần suất hỏi vặn (1 lần thay vì 2 lần trước khi cho gợi ý) cho persona yếu tự tin.
