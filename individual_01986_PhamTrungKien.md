# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                              |
| --------------- | ----------------------------------------------------- |
| Họ và tên       | Phạm Trung Kiên                                       |
| MSSV            | 2A202601986                                            |
| Khóa/Lớp        | K3                                                     |
| Vai trò chính   | Viết file `src/agents/order_seller_agent.py`          |
| Ngày hoàn thành | 2026-08-05                                             |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Extract facts cho order, item và seller | `OrderSellerAgent.process()` trong `src/agents/order_seller_agent.py` | `CaseContext.claimed_order_id` và store dữ liệu `orders/items` | `OrderFacts` đã được điền vào `CaseContext`: `order_status`, timestamps, `items`, `seller_ids`, `seller_handoff_late` | Hoàn thành |
| Edge-case handling không làm vỡ pipeline | Cùng file trên | `CaseContext` khi order không tồn tại hoặc thiếu date | `ctx.notes` với `order_not_found`, `carrier_date_missing`, `order_has_no_item_row`; message trả về `facts_ready` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Handoff dữ liệu cho các agent sau | `Coordinator`, `DeliveryAgent`, `PolicyAgent` | Agent của tôi đặt dữ liệu chuẩn lên `CaseContext` để các module sau có thể đọc và suy luận tiếp. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Trích xuất facts đơn hàng + item + seller | `src/agents/order_seller_agent.py` | `OrderFacts` đầy đủ cho toàn bộ pipeline | Dòng flow trong `Coordinator.run_case()` và `CaseContext` handoff |
| Xác định seller bàn giao carrier muộn hơn `shipping_limit_date` | `src/agents/order_seller_agent.py` + `src/schemas.py` | `seller_handoff_late` map theo từng `seller_id` | Logic trong file + kiểm tra cú pháp bằng compile |
| Bảo vệ pipeline khi dữ liệu thiếu | `src/agents/order_seller_agent.py` | Append note thay vì crash: `order_not_found`, `carrier_date_missing`, `order_has_no_item_row` | Kiểm tra branch logic trong code |

Output cụ thể mà phần việc của tôi tạo ra: `OrderFacts` trong `CaseContext` và các note cảnh báo để tránh kết luận seller trễ thiếu bằng chứng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết việc chuẩn hóa thông tin đơn hàng từ bộ dữ liệu Olist vào `CaseContext` và chuyển thành các facts dùng cho mô hình multi-agent. Cụ thể, tôi cần làm rõ: trạng thái order, thời điểm lịch sử của đơn, danh sách item và seller, đồng thời không được gán “seller trễ” khi thiếu `order_delivered_carrier_date` để tránh false positive.

### Cách triển khai

Tôi triển khai agent bằng cách lấy `claimed_order_id` từ `CaseContext`, gọi `dt.STORE.get_order()` để nạp order ban đầu, rồi điền các trường thời gian và thông tin của đơn vào `OrderFacts`. Sau đó, agent đọc item của order bằng `get_items(order_id)`, chuyển mỗi item thành cấu trúc chuẩn gồm `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price` và `freight_value`, rồi tạo `seller_ids` duy nhất nhưng giữ nguyên thứ tự xuất hiện. 

Về logic kết luận seller trễ, agent chỉ đánh dấu `seller_handoff_late=True` khi `carrier_dt > limit_dt` đồng thời cả hai mốc đều parse được. Nếu `carrier_date` thiếu, agent không suy luận sai; nó ghi `carrier_date_missing` và giữ giá trị `False`. Đây là quyết định kỹ thuật quan trọng để tránh đổ lỗi cho seller khi bằng chứng còn thiếu.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `CaseContext.claimed_order_id` và store order/items từ `src/data_tools.py` |
| Output | `OrderFacts`: `found`, `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`, `items`, `seller_ids`, `seller_handoff_late` |
| Module phụ thuộc | `src/data_tools.py`, `src/schemas.py`, `src/a2a/base_agent.py` |
| Module sử dụng output | `src/agents/delivery_agent.py`, `src/agents/policy_agent.py`, `src/agents/verifier_agent.py` |
| Điều kiện lỗi cần xử lý | Order không tồn tại, `carrier_date` thiếu, order không có item row, parse date không hợp lệ |

### Cách xác minh

```bash
python -m compileall src/agents/order_seller_agent.py
```

- **Kết quả mong đợi:** File agent được biên dịch mà không có syntax error.
- **Kết quả thực tế:** Lệnh chạy với output rỗng và exit code thành công. Đây là bằng chứng thực tế rằng module hiện tại đang hợp lệ về cú pháp trong môi trường workspace này.
- **Artifact/log:** `logging/trace.jsonl` và `output/EC_*.json` từ luồng chính chạy pipeline.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Không phải mọi đơn hàng đều có đầy đủ thời điểm giao carrier; nếu agent “đoán” seller trễ thì policy và refund sẽ bị sai.
- **Các phương án đã cân nhắc:**
  1. Gán `seller_handoff_late=True` dựa trên item seller mà không cần kiểm tra carrier date.
  2. Chỉ ghi `True` khi có đủ bằng chứng `carrier_dt > shipping_limit_date`.
- **Phương án đã chọn:** Chọn phương án 2.
- **Lý do:** Đây là lựa chọn tối ưu hơn về `correctness` và `data quality`: tránh false positive và tránh báo cáo sai về trách nhiệm seller.
- **Bằng chứng quyết định phù hợp:** Branch logic trong file đã thêm `carrier_date_missing` và chỉ set `seller_handoff_late` khi cả mốc đều có thể parse được.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Nếu order không tồn tại hoặc thiếu `carrier_date`, pipeline có thể đi sai và phát sinh kết luận seller trễ không đáng có.
- **Lệnh hoặc bước tái hiện:** Truy cập case có `claimed_order_id` không có trong store hoặc dữ liệu thiếu `order_delivered_carrier_date`.
- **Nguyên nhân gốc:** Root cause nằm ở việc dữ liệu thực tế không đồng nhất; không phải mọi order đều có đầy đủ ngày để suy ra `seller_handoff_late`.
- **Cách xử lý:** Agent return `found=False` nếu order không có, đồng thời append `order_not_found`. Nếu `carrier_dt` thiếu nhưng có items, append `carrier_date_missing` và không suy ra `True` cho seller trễ.
- **Cách xác minh sau khi sửa:** Chạy compile module và kiểm tra logic hỗ trợ. Kết quả xác thực là syntax file hợp lệ và code cẩn thận với branch lỗi.
- **Điều học được:** Với dữ liệu nghiệp vụ thật, “không kết luận quá mức” là một quyết định tốt hơn “đoán” khi thiếu chứng cứ.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu case đầu vào đến từ `input/EC_*.json`, được `main.py` nạp và gửi cho `Coordinator`.
2. `Coordinator` tạo `CaseContext`, rồi `OrderSellerAgent` đọc order/item/store để điền `OrderFacts`.
3. `DeliveryAgent` và `PaymentAgent` chạy song song dựa trên cùng `CaseContext`, mỗi agent ghi vào slot riêng (`DeliveryFacts` và `PaymentFacts`).
4. `PolicyAgent` rút ra quyết định và `VerifierAgent` kiểm tra tính nhất quán; nếu cần, `Coordinator` quay lại `PolicyAgent` trong vòng repair.
5. Output cuối được gói với `build_output()` và lưu ra `output/EC_*.json`.

**Câu trả lời:**

Trong repo này, luồng end-to-end không đi qua Crossref hay vector index. Nó chạy theo pipeline A2A nội bộ: `input/EC_*.json` → `Coordinator` → `OrderSellerAgent` → `DeliveryAgent` ∥ `PaymentAgent` → `PolicyAgent` → `VerifierAgent` → `output/EC_*.json`. Vai trò của phần tôi phụ trách là chuẩn hóa dữ liệu order/item/seller và đưa ra các signal an toàn để các agent sau đó không phát sinh false positive trong quyết định chính sách và refund.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Trung Kiên
**Ngày xác nhận:** 2026-08-05
