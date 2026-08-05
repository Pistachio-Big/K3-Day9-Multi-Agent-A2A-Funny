# DEV GUIDE — NHÓM FUNNY (K3 Day 9)

Hướng dẫn build tiếp trên bộ scaffold. Đọc `README.md` để nắm đề bài.

## 1. Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # điền GROQ_API_KEY hoặc OPENROUTER_API_KEY
```

## 2. Chạy

```bash
python main.py            # chạy tất cả input/EC_*.json -> output/
python main.py EC_001     # chạy 1 case để debug
```

Scaffold chạy được ngay cả khi `USE_LLM=0` (không cần API key) — dùng để test plumbing.
Bật LLM: đặt `USE_LLM=1` trong `.env`.

## 3. Kiến trúc & luồng handoff (A2A)

```
input/EC_xxx.json
        │
        ▼
   Coordinator ──investigate──► OrderSeller ──facts──► Delivery ──facts──► Payment
   (Nguyễn Văn Đại)             (Trung Kiên)          (Huy Anh)          (Huy Anh)
        ▲                                                                    │
        │                                                                  facts
        │                                                                    ▼
   output/EC_xxx.json ◄──final── Verifier ◄──decision── Policy ◄────────────┘
                                 (Tấn Phong)           (Văn Phái)
```

- Mỗi agent nhận `A2AMessage`, đọc/ghi bảng đen `CaseContext`, trả message cho agent kế.
- Coordinator định tuyến theo `recipient`; mọi bước được `Tracer` ghi vào `logging/trace.jsonl`.

## 4. Ai sửa file nào

| Người | File chính | Việc |
| --- | --- | --- |
| Nguyễn Văn Đại | `src/agents/coordinator.py`, `main.py`, `src/config.py` | orchestration, chốt model, gom output, zip |
| Phạm Trung Kiên | `src/data_tools.py`, `src/agents/order_seller_agent.py` | data layer + facts đơn/seller |
| Nguyễn Huy Anh | `src/agents/delivery_agent.py`, `src/agents/payment_agent.py` | facts giao hàng + đối soát payment |
| Hoàng Văn Phái | `src/agents/policy_agent.py` | rule engine EC_POLICY_V1, refund |
| Hà Tấn Phong | `src/agents/verifier_agent.py`, `src/tracing.py`, `architecture.md` | validate + observability + sơ đồ |

Contract dùng chung ở `src/schemas.py` — sửa phải báo cả nhóm.

## 5. Quy tắc bắt buộc (kẻo mất điểm)

- Mỗi agent model **≤10B**; tên model khai báo trong `src/config.py` (không để trong `.env`).
- `.env` **không commit** (đã có trong `.gitignore`).
- `logging/trace.jsonl` **ghi đè** mỗi lần chạy (chỉ lượt mới nhất).
- Zip nộp bài **chỉ** chứa `output/` (đúng 50 JSON, không kèm source/.env).

## 6. TODO còn lại (grep `TODO` trong `src/`)

- Policy: tinh chỉnh `confidence`, rà case biên nhiều seller.
- Verifier: cross-check refund khớp primary_issue.
- Delivery: xử lý đơn chưa giao nếu bộ case có.
- Cân nhắc bật LLM cho các bước cần suy luận ngôn ngữ.
