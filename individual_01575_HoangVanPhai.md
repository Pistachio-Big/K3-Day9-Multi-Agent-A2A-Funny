# Báo cáo cá nhân — Hoàng Văn Phái

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                  |
| --------------- | ------------------------- |
| Họ và tên       | Hoàng Văn Phái            |
| Khóa/Lớp        | K3                        |
| Vai trò chính   | Policy Adjudicator         |
| Ngày hoàn thành | 2026-08-05                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái      |
| ------------------ | ------------------ | -------------- | ----------------- | --------------- |
| Policy Agent       | src/agents/policy_agent.py | CaseContext (order_facts, delivery_facts, payment_facts) | PolicyDecision + evidence_ids | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                          |
| ------------------------- | ----------------------------- | -------------------------------- |
| Sửa lỗi signature mismatch | Coordinator, BaseAgent        | Align process() về (ctx) -> list |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | --------------- |
| Implement 6 luật EC_POLICY_V1 | policy_agent.py `_set()` | PolicyDecision đúng schema | Chạy 50 case |
| Build evidence IDs | policy_agent.py `_build_evidence()` | evidence_ids: order/item/payment/seller/policy | Output JSON |
| Ánh xạ cause + party | policy_agent.py CAUSE dict | ranked_causes + responsible_parties | Output JSON |
| Align signature agent | base_agent.py, policy_agent.py | process(ctx) -> list[A2AMessage] | main.py chạy OK |

**Output cụ thể:** 50 file output/EC_*.json với assessment.primary_issue và financial_resolution.recommended_refund_brl.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Policy Agent là "trái tim" của hệ thống — phải phân loại chính xác mỗi case thuộc issue nào trong 6 loại, tính đúng refund, xác định bên chịu trách nhiệm. 55% điểm đến từ dữ liệu xác định (entities, financial, evidence), nên Policy Agent phải đảm bảo mọi con số từ CSV, không để LLM hallucinate.

### Cách triển khai

**Cây quyết định 6 luật theo thứ tự ưu tiên tuyệt đối:**

```
1. status == "canceled" AND payment > 0
   → canceled_order_paid | platform | full refund (payment_total)

2. status == "unavailable" AND payment > 0
   → unavailable_order_paid | platform | full refund (payment_total)

3. late_vs_estimate AND carrier_after_limit
   → late_delivery_seller | seller(s) | freight refund (freight_total)

4. late_vs_estimate AND NOT carrier_after_limit
   → late_delivery_logistics | logistics | freight refund (freight_total)

5. num_payment_rows >= 2 AND reconciled
   → valid_split_payment | none | 0 (giải thích)

6. ELSE (giao không trễ, payment khớp)
   → unsupported_late_claim | none | 0 (bác claim)
```

**Evidence building:** Với mỗi decision, dựng evidence IDs:
- order:<order_id>
- item:<order_id>:<order_item_id>
- payment:<order_id>:<payment_sequential>
- seller:<seller_id> (nếu có seller chịu trách nhiệm)
- policy:<root_cause_code>

### Input, output và contract

| Thành phần              | Mô tả                                      |
| ----------------------- | ------------------------------------------ |
| Input                   | CaseContext: order_facts, delivery_facts, payment_facts |
| Output                  | PolicyDecision: primary_issue, case_status, confidence, ranked_causes, responsible_parties, recommended_refund_brl, resolution_actions |
| Module phụ thuộc        | data_tools.py (ev_* helpers), schemas.py   |
| Module sử dụng output   | verifier_agent.py (validate + cross-check)  |
| Điều kiện lỗi cần xử lý | Order không tìm thấy → found=False; order không có item → items=[] |

### Cách xác minh

```bash
.venv/bin/python main.py EC_001
```

- **Kết quả mong đợi:** EC_001 phân loại đúng issue, refund đúng công thức
- **Kết quả thực tế:** late_delivery_seller, refund=12.04 (freight_total)
- **Artifact/log:** output/EC_001.json, logging/trace.jsonl

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Ranh giới giữa `valid_split_payment` (luật 5) và `unsupported_late_claim` (luật 6) rất dễ đảo nhầm.
- **Các phương án đã cân nhắc:**
  1. Đặt `unsupported_late_claim` lên trước → split payment bị misclassify thành bác claim
  2. Đặt `valid_split_payment` lên trước → đúng thứ tự ưu tiên đề bài yêu cầu
- **Phương án đã chọn:** Đặt `valid_split_payment` trước, kiểm tra `num_payment_rows >= 2 AND reconciled`
- **Lý do:** Theo đề bài, luật 5 phải ưu tiên hơn luật 6. Điều kiện cụ thể (>=2 rows + reconciled) an toàn hơn điều kiện catch-all.
- **Bằng chứng:** Chạy 50 case cho phân bố đều: mỗi issue ~8-9 case.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  TypeError: PolicyAgent.process() missing 1 required positional argument: 'ctx'
  AttributeError: 'PolicyAgent' object has no attribute 'emit'
  TypeError: 'A2AMessage' object is not iterable
  ```
- **Lệnh hoặc bước tái hiện:** `.venv/bin/python main.py EC_001`
- **Nguyên nhân gốc:** Kiến trúc coordinator mới dùng signature `process(ctx)` trả về `list[A2AMessage]`, nhưng PolicyAgent cũ dùng `process(msg, ctx)` trả về `A2AMessage`. BaseAgent đổi tên `result()` → `emit()` nhưng agents chưa update.
- **Cách xử lý:**
  1. Sửa `base_agent.py`: đổi signature về `process(ctx) -> list[A2AMessage]`, đổi `result()` → `emit()`
  2. Sửa `policy_agent.py`: bỏ tham số `msg`, đổi `return self.emit(...)` → `return [self.emit(...)]`
  3. Sửa tất cả agents: `self.result` → `self.emit`, thêm `[]` bao quanh return
- **Cách xác minh sau khi sửa:** `.venv/bin/python main.py` → 50/50 case chạy thành công
- **Điều học được:** Khi refactor architecture, phải align tất cả agents cùng lúc. Thay đổi base class ảnh hưởng toàn bộ subclasses.

## 7. Hiểu biết về luồn end-to-end

1. **Dữ liệu đi từ input đến output như thế nào?**
   Input (EC_xxx.json) → Coordinator khởi tạo CaseContext → OrderSeller tra CSV → Delivery/Payment fan-out song song → PolicyAgent phân loại issue + tính refund → Verifier validate → Coordinator ghi output.

2. **Evidence IDs dùng để làm gì?**
   Bằng chứng xác nhận quyết định. Mỗi ID phải tồn tại trong CSV. Evidence sai = false positive = 0 điểm phần Evidence (15%).

3. **Tại sao tách Tool vs Reasoning?**
   55% điểm đến từ dữ liệu xác định. LLM sinh số/ID = hallucination = false positive. Tool layer là ground truth, LLM chỉ phân loại.

4. **Repair loop hoạt động thế nào?**
   Verifier phát hiện refund không khớp issue → gửi `intent="repair"` → Coordinator định tuyến lại Policy Agent → chạy lại với evidence đã sửa. Tối đa 2 vòng.

5. **Policy Agent đóng vai trò gì trong kiến trúc?**
   "Trái tim" — nhận tất cả facts đã tính, áp dụng 6 luật theo thứ tự ưu tiên, đưa ra quyết định cuối cùng (issue, refund, party, cause, evidence).

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồn end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Văn Phái
**Ngày xác nhận:** 2026-08-05
