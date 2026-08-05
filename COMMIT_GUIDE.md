# COMMIT GUIDE — Bản nâng cấp kiến trúc (NHÓM FUNNY)

Tài liệu để **gửi từng thành viên commit đúng phần của mình**. Tất cả thay đổi đã có sẵn
trong working tree; mỗi người chỉ `git add` file của mình + commit theo message gợi ý.

> Kiến trúc mới: **Deterministic core + Dual-path Adjudication + Critic-Repair loop**
> (chi tiết trong `architecture.md`). Baseline vẫn chạy khi `USE_LLM=0`.
> Đã verify: 50/50 output hợp lệ, 0 vi phạm ràng buộc, refund luôn khớp issue.

---

## 0. Contract dùng chung (Đại commit TRƯỚC — cả nhóm phụ thuộc)

| File | Thay đổi |
| --- | --- |
| `src/schemas.py` | Thêm 2 field điều khiển repair vào `CaseContext`: `repair_count`, `force_deterministic`. |
| `src/a2a/base_agent.py` | Đổi contract: `process(ctx, inbox=None) -> A2AMessage` (trả 1 message kết quả); thêm helper `result(...)`. Coordinator là bên định tuyến. |

```bash
git add src/schemas.py src/a2a/base_agent.py
git commit -m "refactor(a2a): agent contract tra 1 message + them co repair vao CaseContext"
```

---

## 1. Nguyễn Văn Đại — Coordinator / Lead

| File | Thay đổi |
| --- | --- |
| `src/agents/coordinator.py` | Viết lại orchestration: (1) fan-out **song song** Delivery ∥ Payment bằng `ThreadPoolExecutor`; (2) **critic-repair loop** Policy↔Verifier tối đa 2 vòng; (3) ghi trace mọi handoff (`dispatch`, `adjudicate`, `verify`, `repair`, `final`). |
| `make_submission.py` (mới) | Script zip **chỉ** `output/` (đúng 50 JSON EC_001..EC_050), chặn file lạ — tuân thủ README **mục 9.2**. |

```bash
git add src/agents/coordinator.py make_submission.py
git commit -m "feat(coordinator): fan-out song song + critic-repair loop; them make_submission"
```

## 2. Phạm Trung Kiên — Tool Layer + Order/Seller

| File | Thay đổi |
| --- | --- |
| `src/agents/order_seller_agent.py` | Đổi sang contract mới. Thêm: order not found → `found=False` không crash; **thiếu `order_delivered_carrier_date` → không kết luận seller trễ** (ghi note `carrier_date_missing`); note `order_has_no_item_row`; seller_ids duy nhất giữ thứ tự. |

> `src/data_tools.py` (Kiên sở hữu) đợt này **không đổi** — vẫn là nguồn sự thật đọc CSV.

```bash
git add src/agents/order_seller_agent.py
git commit -m "feat(order-seller): xu ly thieu carrier_date & order khong item; contract moi"
```

## 3. Nguyễn Huy Anh — Delivery + Payment

| File | Thay đổi |
| --- | --- |
| `src/agents/delivery_agent.py` | Contract mới. Đơn **chưa giao** (delivered rỗng) → `late_vs_estimate=False`, note `not_delivered_yet` (tránh gán nhầm late). |
| `src/agents/payment_agent.py` | Contract mới. Ghi note `payment_not_reconciled(diff=...)` khi lệch > 0.10 BRL để Policy/Verifier tham chiếu. |

```bash
git add src/agents/delivery_agent.py src/agents/payment_agent.py
git commit -m "feat(delivery,payment): xu ly don chua giao + note reconcile"
```

## 4. Hoàng Văn Phái — Policy Adjudicator (dual-path)

| File | Thay đổi |
| --- | --- |
| `src/agents/policy_agent.py` | Tách **Path A** (6 luật xác định — nguồn mọi số/ID) và **Path B** (LLM chọn issue, chỉ khi `USE_LLM=1` & không bị ép deterministic). So khớp A/B → hiệu chỉnh `confidence` (đồng thuận cao / lệch hạ + note). Tôn trọng `ctx.force_deterministic` do Verifier bật khi repair. |

```bash
git add src/agents/policy_agent.py
git commit -m "feat(policy): dual-path adjudication (rule + LLM) + confidence theo dong thuan"
```

## 5. Hà Tấn Phong — Verifier-Critic + Docs

| File | Thay đổi |
| --- | --- |
| `src/agents/verifier_agent.py` | Contract mới. Thêm **cross-check tài chính ↔ issue** (full⇒payment_total, freight⇒freight_total, no_action⇒0). Lệch → phát `intent="repair"` (ép Policy Path A), tối đa 2 vòng. Giữ validate evidence tồn tại + siết ràng buộc schema. |
| `architecture.md` | Viết mới: sơ đồ kiến trúc, vai trò & quyền truy cập dữ liệu, luồng handoff + repair, tuân thủ mục 9. |

> `logging/trace.jsonl`, `logging/metadata.json` là **sinh tự động** khi chạy `main.py` — không sửa tay.

```bash
git add src/agents/verifier_agent.py architecture.md
git commit -m "feat(verifier): cross-check refund<->issue + repair loop; viet architecture.md"
```

---

## 6. Sau khi mọi người commit code — chạy & commit output (Đại)

```bash
python main.py                 # sinh lại output/ + logging/trace.jsonl + metadata.json
git add output/ logging/metadata.json logging/trace.jsonl
git commit -m "chore: regenerate 50 output + trace/metadata (kien truc moi)"
```

## 7. Checklist tuân thủ README mục 9 (BẮT BUỘC trước khi nộp)

- [ ] **9.1** Mỗi agent model ≤10B — khai báo trong `src/config.py` (`AGENT_MODELS`), KHÔNG trong `.env`.
- [ ] **9.2** Zip nộp bài **chỉ** `output/` (dùng `python make_submission.py`), không kèm source/.env/log.
- [ ] **9.3** Commit toàn bộ source code lên repo **trước** khi nộp zip output.
- [ ] **9.4** `.env` không commit (đã có trong `.gitignore`); model name có trong code + `logging/metadata.json`.
- [ ] Mỗi người điền báo cáo cá nhân `individual_5SoCuoiMHV_HoVaTen.md` (đổi tên theo họ tên).

## 8. Kiểm chứng nhanh (bất kỳ ai)

```bash
python main.py
python -c "import glob;assert len(glob.glob('output/EC_*.json'))==50"   # đủ 50 output
python make_submission.py   # tạo submission.zip đúng 50 JSON
```
