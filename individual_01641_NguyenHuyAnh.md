# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                       |
| --------------- | ------------------------------ |
| Họ và tên       | Nguyễn Huy Anh                 |
| MSSV            | 2A202601641                    |
| Khóa/Lớp        | K3                             |
| Vai trò chính   | Delivery Agent & Payment Agent |
| Ngày hoàn thành | 2026-08-05                     |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách             | Input nhận vào                                                | Output bàn giao              | Trạng thái |
| ------------------ | ------------------------------ | ------------------------------------------------------------- | ---------------------------- | ---------- |
| Delivery Agent     | `src/agents/delivery_agent.py` | `CaseContext.order_facts` (từ OrderSellerAgent), Olist CSV    | `CaseContext.delivery_facts` | Hoàn thành |
| Payment Agent      | `src/agents/payment_agent.py`  | `CaseContext.order_facts`, `olist_order_payments_dataset.csv` | `CaseContext.payment_facts`  | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                            | Thành viên/module được hỗ trợ      | Kết quả                                                                        |
| ------------------------------------ | ---------------------------------- | ------------------------------------------------------------------------------ |
| Thống nhất logic xử lý đơn chưa giao | Hoàng Văn Phái (`policy_agent.py`) | Không gán nhầm `late_delivery` cho các đơn có `delivered_customer_date` rỗng   |
| Kiểm tra tài chính 50 case           | Cả nhóm                            | Khớp 100% `financial_resolution` giữa kết quả tính tay trên CSV và output JSON |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan    | Kết quả bàn giao                                                            | Cách xác minh                                                            |
| --------------------- | ------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Xử lý facts Delivery  | `src/agents/delivery_agent.py` | Trích xuất `delivered`, `late_vs_estimate`, `carrier_after_limit` chuẩn xác | Run 50 case, kiểm tra `late_delivery_seller` & `late_delivery_logistics` |
| Xử lý facts Payment   | `src/agents/payment_agent.py`  | Trích xuất `payment_total`, `item_total`, `freight_total`, `reconciled`     | Run `python main.py EC_009` & check `financial_resolution`               |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Output `EC_009.json` có `financial_resolution`:

```json
{
  "currency": "BRL",
  "item_total_brl": 39.9,
  "freight_total_brl": 12.36,
  "payment_total_brl": 52.26,
  "recommended_refund_brl": 12.36
}
```

Khớp hoàn toàn với tổng tiền tính tay từ `olist_order_items_dataset.csv` và `olist_order_payments_dataset.csv`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

- **Delivery**: Xác định đơn hàng có bị giao muộn so với dự kiến hay không (`late_vs_estimate`), và nếu muộn thì trách nhiệm thuộc về Seller (carrier nhận hàng muộn hơn `shipping_limit_date`) hay đơn vị logistics. Xử lý chính xác các đơn chưa giao (`delivered_customer_date` rỗng).
- **Payment**: Tính toán tổng tiền thanh toán của khách (`payment_total_brl`), tổng giá trị tiền hàng (`item_total_brl`) và tiền vận chuyển (`freight_total_brl`), thực hiện đối soát (`reconciled`) với sai số cho phép $\le 0.10$ BRL.

### Cách triển khai

- **Delivery Agent**:
  1. Parse timestamp `order_delivered_customer_date` và `order_estimated_delivery_date` thông qua helper `dt.parse_dt`.
  2. Nếu `order_delivered_customer_date` rỗng: set `df.delivered = False`, `df.late_vs_estimate = False` và ghi note `not_delivered_yet` để tránh kết luận sai.
  3. Nếu đã giao: `df.late_vs_estimate = (delivered_dt > estimated_dt)`.
  4. Đánh giá `carrier_after_limit = any(of.seller_handoff_late.values())` dựa trên dữ liệu do OrderSellerAgent cung cấp.

- **Payment Agent**:
  1. Tra cứu các dòng thanh toán của order từ `dt.STORE.get_payments(order_id)`.
  2. Đọc trực tiếp `payment_value` từng dòng (lưu ý `payment_value` là tổng giá trị dòng payment row, KHÔNG nhân/chia theo `payment_installments`).
  3. Tính `payment_total_brl`, `item_total_brl = sum(price)`, `freight_total_brl = sum(freight_value)`.
  4. Xác định `reconciled = abs(payment_total - (item_total + freight_total)) <= 0.10`.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `CaseContext` chứa `order_facts` (order_id, dates, items, seller_handoff_late)                                                                                                                                      |
| Output                  | `CaseContext.delivery_facts` (`delivered`, `late_vs_estimate`, `carrier_after_limit`) và `payment_facts` (`payments`, `num_payment_rows`, `payment_total_brl`, `item_total_brl`, `freight_total_brl`, `reconciled`) |
| Module phụ thuộc        | `src/data_tools.py`, `src/agents/order_seller_agent.py`                                                                                                                                                             |
| Module sử dụng output   | `src/agents/policy_agent.py`, `src/agents/verifier_agent.py`                                                                                                                                                        |
| Điều kiện lỗi cần xử lý | `order_delivered_customer_date` rỗng, order không có item row, lệch làm tròn thanh toán                                                                                                                             |

### Cách xác minh

```bash
python main.py EC_009
python -c "import json;o=json.load(open('output/EC_009.json',encoding='utf-8'));print(o['financial_resolution'])"
```

- **Kết quả mong đợi:** In ra `financial_resolution` với `item_total_brl: 39.9`, `freight_total_brl: 12.36`, `payment_total_brl: 52.26`, `recommended_refund_brl: 12.36`.
- **Kết quả thực tế:** Kết quả khớp 100%.
- **Artifact/log:** File `output/EC_009.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý trường hợp các đơn hàng chưa có ngày giao khách (`order_delivered_customer_date` bị rỗng/None).
- **Các phương án đã cân nhắc:**
  - _Phương án 1:_ So sánh `order_estimated_delivery_date` với ngày mở case (`opened_at`), nếu `opened_at > estimated_date` thì coi là trễ.
  - _Phương án 2:_ Đánh dấu `delivered = False`, `late_vs_estimate = False` (không kết luận trễ khi đơn chưa giao thực tế), ghi note `not_delivered_yet`.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Olist dataset có nhiều đơn bị hủy (`canceled`) hoặc chưa hoàn thành (`unavailable`, `shipped`). Việc so sánh với `opened_at` có thể gây sai lệch nghiêm trọng, làm gán nhầm lỗi `late_delivery_seller` hoặc `late_delivery_logistics`. Việc set `late_vs_estimate = False` giúp luồng ưu tiên xử lý các luật chính như `canceled_order_paid` hoặc `unavailable_order_paid`.
- **Bằng chứng quyết định phù hợp:** 100% các đơn canceled/unavailable trong 50 case đều được phân loại đúng vào `canceled_order_paid` hoặc `unavailable_order_paid` thay vì bị gán nhầm trễ giao hàng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lệch tổng tiền thanh toán khi order có cột `payment_installments > 1`.
- **Lệnh hoặc bước tái hiện:** Chạy test case `EC_004` (order có thanh toán nhiều đợt).
- **Nguyên nhân gốc:** Hiểu nhầm `payment_value` trong `olist_order_payments_dataset.csv` là số tiền của 1 installment thay vì tổng tiền của payment row.
- **Cách xử lý:** Đọc trực tiếp `payment_value` từ CSV cho mỗi payment row, không thực hiện nhân với `payment_installments`.
- **Cách xác minh sau khi sửa:** Chạy `python main.py EC_004`, kết quả `payment_total_brl` khớp chính xác với `item_total_brl + freight_total_brl`, đưa ra `valid_split_payment` chuẩn xác.
- **Điều học được:** Đọc kỹ mô tả dataset trước khi tính toán dữ liệu tài chính (README mục 2 chốt rõ: `payment_value` là số tiền của từng payment row, không phải của từng installment).

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ các CSV Olist được đọc và đánh index O(1) thông qua `DataStore` trong `src/data_tools.py`.
2. Pipeline A2A khởi chạy từ Coordinator, gọi `OrderSellerAgent` để lấy thông tin đơn và seller.
3. `DeliveryAgent` nhận `order_facts`, tính toán các chỉ số giao hàng (`delivered`, `late_vs_estimate`, `carrier_after_limit`).
4. `PaymentAgent` đối soát tài chính (`payment_total_brl`, `item_total_brl`, `freight_total_brl`, `reconciled`).
5. `PolicyAgent` tổng hợp bằng chứng từ tất cả các agent, áp dụng 6 quy tắc ưu tiên `EC_POLICY_V1` để ra quyết định và mức hoàn tiền.
6. `VerifierAgent` thẩm định các Evidence ID và giới hạn schema trước khi Coordinator lưu output JSON.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Huy Anh  
**Ngày xác nhận:** 2026-08-05
