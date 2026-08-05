# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                |
| --------------- | ----------------------- |
| Họ và tên       | Phạm Trung Kiên         |
| MSSV            | 2A202601986              |
| Khóa/Lớp        | K3                       |
| Vai trò chính   | Viết và duy trì agent Order & Seller trong `src/agents/order_seller_agent.py` |
| Ngày hoàn thành | 2026/08/05               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Fact extraction cho đơn hàng và seller | `OrderSellerAgent.process()` trong `src/agents/order_seller_agent.py` | `CaseContext.claimed_order_id` và store dữ liệu order/item trong `src/data_tools.py` | `OrderFacts` đầy đủ: `order_id`, `customer_id`, `order_status`, timestamp, `items`, `seller_ids`, `seller_handoff_late` | Hoàn thành |
| Xử lý edge case không crash | Cùng file trên | `CaseContext` khi order không tồn tại hoặc thiếu trường dữ liệu | `ctx.notes` với `order_not_found`, `carrier_date_missing`, `order_has_no_item_row`; trả message `facts_ready` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Kiểm tra tích hợp handoff | `Coordinator` và `DeliveryAgent` | Agent của tôi đặt dữ liệu chuẩn lên `CaseContext`, rồi `DeliveryAgent` dùng `seller_handoff_late` để suy luận `carrier_after_limit`. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Trích xuất facts đơn hàng, item, seller từ `claimed_order_id` | `src/agents/order_seller_agent.py` | `OrderFacts` được điền vào `CaseContext` để các agent sau dùng | Dùng `CaseContext` trong luồng `Coordinator.run_case()` và check `logging/trace.jsonl` |
| Xây dựng logic phát hiện seller bàn giao trễ | `src/agents/order_seller_agent.py` + schema `src/schemas.py` | `seller_handoff_late[seller_id] = True` khi `order_delivered_carrier_date > shipping_limit_date` | Kiểm tra từ logic trong file và compile module |
| Bảo vệ pipeline không crash trên missing data | `src/agents/order_seller_agent.py` | Khi không tìm thấy order hoặc thiếu carrier date thì ghi note và trả `found=False` / `carrier_date_missing` | Chạy compile và kiểm tra branch logic trong code |

Output cụ thể mà phần việc của tôi tạo ra: `OrderFacts` trong `CaseContext` và note `carrier_date_missing` / `order_has_no_item_row` khi dữ liệu không đủ bằng chứng để kết luận seller trễ.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết việc chuẩn hóa dữ liệu đơn hàng từ kho dữ liệu Olist thành `facts` cho các agent sau, đồng thời tránh rơi vào các lỗi dạng crash khi `claimed_order_id` không tồn tại hoặc khi thiếu `order_delivered_carrier_date`, vì nếu không xử lý đúng sẽ dẫn tới sai kết luận seller muộn.

### Cách triển khai

Tôi triển khai agent bằng cách đọc `claimed_order_id` từ `CaseContext`, gọi `dt.STORE.get_order()` để lấy thông tin order gốc, rồi sao chép các trường thời gian quan trọng vào `OrderFacts`. Sau đó, agent đọc các item tương ứng của đơn bằng `get_items(order_id)`, chuyển mỗi item thành bản ghi có `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`, và loại bỏ seller trùng nhau nhưng giữ nguyên thứ tự xuất hiện. 

Về logic trễ seller, agent không gán seller trễ theo kiểu “đoán mò”. Nó chỉ gán `seller_handoff_late=True` khi có thể parse được ngày `order_delivered_carrier_date` và `shipping_limit_date`, đồng thời `carrier_dt > limit_dt`. Nếu thiếu `carrier_date`, agent ghi note `carrier_date_missing` và không kết luận seller trễ. Điều này giúp `DeliveryAgent` và `PolicyAgent` nhận được dữ liệu an toàn, không có false positive.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `CaseContext.claimed_order_id` và dữ liệu order/item từ `src/data_tools.py` |
| Output | `OrderFacts` trong `CaseContext`: `found`, `order_id`, `order_status`, timestamps, `items`, `seller_ids`, `seller_handoff_late` |
| Module phụ thuộc | `src/data_tools.py`, `src/schemas.py`, `src/a2a/base_agent.py` |
| Module sử dụng output | `src/agents/delivery_agent.py`, `src/agents/policy_agent.py`, `src/agents/verifier_agent.py` |
| Điều kiện lỗi cần xử lý | Order không tìm thấy, thiếu `carrier_date`, không có item row, date parse không hợp lệ |

### Cách xác minh

```bash
python -m compileall src/agents/order_seller_agent.py
```

- **Kết quả mong đợi:** Module được biên dịch sạch, không syntax error.
- **Kết quả thực tế:** Lệnh chạy không in ra lỗi, exit code thành công. Đây là bằng chứng trực tiếp rằng file agent đang hợp lệ về cú pháp trong môi trường hiện tại.
- **Artifact/log:** `logging/trace.jsonl` và `output/EC_*.json` từ flow chạy chính của pipeline.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Nhiều case có thể không có `order_delivered_carrier_date` hoặc đơn hàng không tồn tại; nếu gán seller trễ bằng suy đoán sẽ gây sai lệch policy và refund.
- **Các phương án đã cân nhắc:**
  1. Gán `seller_handoff_late=True` nếu seller có item trong đơn và debug check không thấy carrier date. 
  2. Chỉ kết luận trễ khi có đủ bằng chứng thời gian và không suy đoán thiếu thông tin.
- **Phương án đã chọn:** Chọn phương án 2.
- **Lý do:** Đây là trade-off đúng hơn về `correctness` và `data quality`: ưu tiên không báo sai “seller muộn” khi chưa đủ bằng chứng. 
- **Bằng chứng quyết định phù hợp:** Code ghi note `carrier_date_missing` và không bật cờ seller trễ nếu `carrier_dt` là `None`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi đơn không tìm thấy hoặc thiếu `carrier_date`, pipeline không nên crash hoặc khoét ra kết luận sai.
- **Lệnh hoặc bước tái hiện:** Đọc `CaseContext` với `claimed_order_id` không có trong store hoặc item không có mốc carrier date.
- **Nguyên nhân gốc:** Root cause nằm ở thiết kế dữ liệu: không phải mọi đơn đều có đầy đủ timestamp bắt buộc để suy ra seller bàn giao muộn.
- **Cách xử lý:** Agent trả về `found=False` nếu `get_order()` trả `None`, đồng thời append `order_not_found`; khi `carrier_date` thiếu, append `carrier_date_missing` và giữ `seller_handoff_late` ở giá trị mặc định `False`.
- **Cách xác minh sau khi sửa:** Chạy compile module và kiểm tra các branch trong `process()` qua logic code. Không có lời khẳng định “đã chạy thành công” ngoài phép kiểm chứng syntax hợp lệ.
- **Điều học được:** Với dữ liệu thực tế, việc “không kết luận quá mức” tốt hơn “đoán có không đủ chứng cứ”.

## 7. Hiểu biết về luồng end-to-end

1. Input case `EC_*.json` được `main.py` nạp vào `Coordinator`, rồi `Coordinator` khởi tạo `CaseContext` với `claimed_order_id`.
2. `OrderSellerAgent` đọc order và item tương ứng để điền `OrderFacts`, sau đó `DeliveryAgent` và `PaymentAgent` chạy song song đọc `CaseContext` để sinh `DeliveryFacts` và `PaymentFacts` riêng.
3. `PolicyAgent` dùng các facts đó để suy ra `primary_issue`, `case_status` và `recommended_refund_brl`; `VerifierAgent` kiểm tra tính nhất quán và có thể yêu cầu repair.
4. Output cuối được `build_output()` rút gọn theo schema danh mục và ghi ra `output/EC_xxx.json`.

**Câu trả lời:**

Luồng end-to-end thực tế trong repo không đi qua Crossref/vector index. Nó bắt đầu từ file `input/EC_*.json`, được `Coordinator` phân phối vào từng agent theo thứ tự `OrderSeller -> Delivery ∥ Payment -> Policy -> Verifier`, rồi đóng thành JSON trong `output/`. Vì vậy phần tôi phụ trách là đóng góp `OrderFacts` rõ ràng và an toàn cho các bước sau, không để agent kế nhận dữ liệu sai hoặc thiếu bằng chứng.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Trung Kiên
**Ngày xác nhận:** 2026-08-05
