# Architecture — NHÓM FUNNY (K3 Day 9, Multi-Agent A2A)

Hệ thống multi-agent điều tra 50 khiếu nại TMĐT trên dữ liệu Olist, kiến trúc
**"Deterministic core + Dual-path Adjudication + Critic-Repair loop"**.

## 1. Sơ đồ tổng thể

```
                         ┌──────────────────────────────────────────┐
                         │  TOOL LAYER (deterministic, KHÔNG LLM)    │
                         │  src/data_tools.py — nguồn sự thật duy nhất│
                         │  đọc 9 CSV, lookup, dựng evidence ID       │
                         └──────────────────────────────────────────┘
                                          ▲  (mọi số & ID lấy từ đây)
 input/EC_xxx.json                        │
        │                                 │
        ▼                                 │
   ┌─────────────┐  1. investigate        │
   │ COORDINATOR │───────────────► Order/Seller Agent ──facts──► blackboard (CaseContext)
   │  (router)   │
   │             │  2. FAN-OUT song song
   │             │────────┬──────────► Delivery Agent ──facts──► blackboard
   │             │        └──────────► Payment  Agent ──facts──► blackboard
   │             │
   │             │  3. adjudicate
   │             │───────────────► Policy Adjudicator (Path A xác định ∥ Path B LLM)
   │             │                        │ decision
   │             │  4. verify             ▼
   │             │───────────────► Verifier-Critic ──┐
   │             │                        │           │ intent="repair" (refund/evidence sai)
   │             │◄──── final ────────────┘           │ -> quay lại Policy (force deterministic)
   └─────┬───────┘◄──────────────── repair loop ──────┘   (tối đa 2 vòng)
         │ 5. assemble
         ▼
   output/EC_xxx.json   +   logging/trace.jsonl (ghi mọi handoff & repair)
```

## 2. Vai trò & quyền truy cập dữ liệu

| Agent | Owner | Đọc | Ghi (blackboard) | Quyền LLM |
| --- | --- | --- | --- | --- |
| Coordinator | Nguyễn Văn Đại | input JSON | điều phối, không ghi facts | không |
| Order & Seller | Phạm Trung Kiên | orders, order_items, sellers | `order_facts` | không (thuần tool) |
| Delivery | Nguyễn Huy Anh | order_facts | `delivery_facts` | không |
| Payment | Nguyễn Huy Anh | order_facts, order_payments | `payment_facts` | không |
| Policy Adjudicator | Hoàng Văn Phái | *_facts | `decision`, `evidence_ids` | **có** (Path B, tuỳ chọn) |
| Verifier-Critic | Hà Tấn Phong | decision, evidence, CSV | siết ràng buộc, cờ repair | không |

**Nguyên tắc:** chỉ Tool Layer chạm CSV thô. Tiền & ID luôn từ tool → không hallucination.
LLM (nếu bật) chỉ **phân loại issue** trên facts đã tính, không sinh số.

## 3. Luồng handoff (A2A)

- Đơn vị handoff: `A2AMessage(sender, recipient, intent, case_id, payload)` (`src/a2a/message.py`).
- Coordinator định tuyến; mỗi bước ghi 1 dòng `logging/trace.jsonl` → bằng chứng handoff thật.
- Thứ tự 1 case: `investigate → facts_ready → dispatch×2 → facts_ready×2 → adjudicate →
  decision_ready → verify → (repair→adjudicate…)* → final → assembled` (11 dòng/case khi không repair).

## 4. Dual-path Adjudication

- **Path A (luôn chạy):** cây quyết định 6 luật EC_POLICY_V1 theo thứ tự ưu tiên. Nguồn của
  mọi con số, ID, party, action, refund.
- **Path B (khi `USE_LLM=1`):** LLM chọn 1 trong 6 issue trên cùng bộ facts. So khớp Path A:
  đồng thuận → confidence cao; lệch → giữ Path A, hạ confidence, ghi note.

## 5. Critic-Repair loop

Verifier cross-check: `full_refund ⇒ refund==payment_total`, `refund_freight ⇒ refund==freight_total`,
`no_action ⇒ refund==0`. Lệch → phát `repair` (ép Policy dùng Path A xác định), tối đa 2 vòng.
Đây là handoff **hai chiều**, chống hard-gate — khác pipeline một chiều gợi ý trong README.

## 6. Ràng buộc tuân thủ (README mục 9)

- Model mỗi agent ≤10B, khai báo trong `src/config.py` (`AGENT_MODELS`), ghi lại `logging/metadata.json`.
- API key trong `.env` (không commit); tên model KHÔNG để trong `.env`.
- `logging/trace.jsonl` ghi đè mỗi lần chạy; zip nộp bài chỉ chứa `output/`.

## 7. Model & runtime

Xem `logging/metadata.json` (sinh tự động): provider, `agent_models`, framework `custom-a2a`,
Python/OS runtime, số case, thời gian chạy.

```
python main.py            # chạy 50 case -> output/ + trace + metadata
python make_submission.py # zip chỉ output/ (đúng 50 JSON)
```
