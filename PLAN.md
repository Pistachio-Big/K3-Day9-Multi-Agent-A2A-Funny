# KẾ HOẠCH THI ĐẤU — NHÓM FUNNY (K3 Day 9)

> Mục tiêu: đạt điểm cao nhất trên 50 case. Tài liệu này gồm (A) kiến trúc đề xuất
> khác README, (B) kế hoạch chi tiết từng người, (C) mốc thời gian.

---

## A. KIẾN TRÚC ĐỀ XUẤT — "Deterministic core + Dual-path Adjudication + Critic-Repair loop"

### A.1 Vì sao KHÔNG dùng y hệt pipeline tuyến tính trong README

Thang điểm mỗi case:

| Thành phần | Trọng số | Bản chất |
| --- | --: | --- |
| Affected entities | 20% | ID lấy từ CSV — phải **chính xác tuyệt đối** |
| Financial resolution | 20% | Số tiền tính từ CSV — **không được để LLM bịa** |
| Primary issue + confidence | 20% | Phân loại — hưởng lợi từ **ensemble** |
| Root cause + responsible parties | 15% | Suy ra xác định từ issue |
| Evidence IDs | 15% | Sai định dạng/không có thật = **false positive** |
| Resolution actions | 10% | Ánh xạ 1-1 từ issue |

→ **55% điểm (entities + financial + evidence) là dữ liệu xác định**, LLM chỉ làm hại nếu
để nó sinh số/ID. Chốt chặn hard-gate (0 điểm) nằm ở evidence sai và schema lỗi.

Vì vậy kiến trúc tối ưu điểm phải: (1) **khoá dữ liệu vào tool deterministic**, (2) dùng LLM
đúng chỗ nó mạnh (phân loại/hiệu chỉnh niềm tin), (3) có **vòng lặp tự sửa** để chặn hard-gate.

### A.2 Sơ đồ

```
                         ┌──────────────────────────────────────────┐
                         │  TOOL LAYER (deterministic, KHÔNG LLM)    │
                         │  data_tools.py  — nguồn sự thật duy nhất  │
                         └──────────────────────────────────────────┘
                                          ▲  (mọi số & ID lấy từ đây)
 input/EC_xxx.json                        │
        │                                 │
        ▼                                 │
   ┌─────────────┐   fan-out (SONG SONG)  │
   │ COORDINATOR │──────────────┬─────────┼─────────────┐
   │  (router)   │              │         │             │
   └─────────────┘              ▼         ▼             ▼
        ▲                 ┌──────────┐ ┌────────┐ ┌──────────┐
        │                 │Order/    │ │Delivery│ │ Payment  │   ← 3 specialist
        │                 │Seller    │ │ Agent  │ │  Agent   │     ghi vào BLACKBOARD
        │                 └────┬─────┘ └───┬────┘ └────┬─────┘
        │                      └───────────┼───────────┘
        │                                  ▼
        │                        ┌───────────────────┐
        │                        │ POLICY ADJUDICATOR │  DUAL-PATH:
        │                        │  Path A: rule engine (xác định)
        │                        │  Path B: LLM chọn issue (JSON, ràng buộc)
        │                        │  → so khớp → confidence theo mức đồng thuận
        │                        └─────────┬─────────┘
        │                                  ▼
        │                        ┌───────────────────┐   nếu phát hiện mâu thuẫn
        │                        │ VERIFIER-CRITIC    │──── REPAIR ───┐
        │                        │ validate evidence  │               │ (bounce back)
        │                        │ + cross-check tiền │◄──────────────┘
        │                        └─────────┬─────────┘
        └──────────── final ───────────────┘
                     │
                     ▼
              output/EC_xxx.json  +  logging/trace.jsonl (ghi mọi handoff & repair)
```

### A.3 Bốn điểm KHÁC README (nêu rõ trong `architecture.md` để ăn điểm thiết kế)

1. **Fan-out song song** 3 specialist thay vì chuỗi tuyến tính (orchestrator–workers /
   map-reduce). Các facts đơn/giao/thanh toán độc lập nên chạy song song, giảm phụ thuộc.
2. **Dual-path adjudication (ensemble)**: quyết định issue bằng CẢ rule engine xác định
   VÀ LLM trên cùng bộ facts, rồi so khớp. Đồng thuận → confidence cao; lệch → escalate.
   Hiệu chỉnh `confidence` có căn cứ thay vì gán cứng (ăn điểm phần 20%).
3. **Critic-Repair loop (handoff hai chiều)**: Verifier có quyền "trả ngược" khi phát hiện
   evidence không tồn tại / refund không khớp issue → agent liên quan sửa rồi chạy lại.
   Đây là cơ chế chống hard-gate, README chỉ có pipeline một chiều.
4. **Tách tầng Tool vs Reasoning**: tiền và ID luôn từ `data_tools`, LLM không bao giờ tự
   sinh con số → khoá chắc 55% điểm dữ liệu, tránh hallucination.

### A.4 Vì sao ăn điểm cao hơn

- Entities/Financial/Evidence (55%): khoá vào tool xác định → gần như tuyệt đối, không hard-gate.
- Primary issue (20%): ensemble rule+LLM giảm sai phân loại ở case biên.
- Confidence: suy từ mức đồng thuận A/B → hợp lý, không bịa.
- Repair loop: chặn schema/evidence lỗi trước khi ghi → tránh nhận 0 điểm.

> Ghi chú: baseline hiện tại (deterministic thuần) đã chạy đúng 50/50, không vi phạm ràng buộc.
> Kiến trúc trên là bản nâng cấp để chắc điểm ở case biên + ghi điểm thiết kế multi-agent.

---

## B. KẾ HOẠCH CHI TIẾT TỪNG NGƯỜI

Mỗi người: Mục tiêu → File sở hữu → Việc cụ thể (checklist) → Tiêu chí nghiệm thu → Lệnh kiểm chứng.

### B.1 — Nguyễn Văn Đại (Coordinator / Team Lead)

**Mục tiêu:** dựng orchestration song song + vòng lặp repair, chốt model, gom output, nộp bài.

**File:** `src/agents/coordinator.py`, `main.py`, `src/config.py`, `README_DEV.md`

**Việc:**
- [ ] Nâng router từ chuỗi tuyến tính → **fan-out song song** 3 specialist (gọi tuần tự cũng được
      nhưng đánh dấu độc lập; nếu có thời gian dùng `concurrent.futures`).
- [ ] Thêm cơ chế **repair loop**: khi Verifier trả message `intent="repair"`, định tuyến lại
      đến agent bị chỉ ra, giới hạn tối đa 2 vòng (chống lặp vô hạn).
- [ ] Chốt `AGENT_MODELS` trong `config.py` (đảm bảo ≤10B), provider Groq/OpenRouter.
- [ ] Kiểm tra `main.py` sinh đủ 50 output, gọi `tracer.flush()` + `write_metadata()`.
- [ ] Viết script `make_submission` (zip **chỉ** `output/`, đúng 50 JSON, không file lạ).
- [ ] Gộp code các thành viên, giải quyết xung đột, giữ contract `schemas.py` ổn định.

**Nghiệm thu:** `python main.py` sinh 50 file, trace ghi cả bước repair, zip đúng 50 JSON.

**Lệnh:**
```bash
python main.py
python -c "import glob; assert len(glob.glob('output/EC_*.json'))==50, 'thieu output'"
```

### B.2 — Phạm Trung Kiên (Tool Layer + Order/Seller Specialist)

**Mục tiêu:** tầng dữ liệu là "nguồn sự thật" chính xác; facts đơn/seller đầy đủ.

**File:** `src/data_tools.py`, `src/agents/order_seller_agent.py`

**Việc:**
- [ ] Rà `data_tools`: đảm bảo lookup order/item/payment/seller đúng, parse timestamp chuẩn,
      hàm evidence ID đúng định dạng README mục 5.
- [ ] Order/Seller: điền đủ status, mốc thời gian, danh sách item, seller_ids **duy nhất**.
- [ ] Tính chính xác `seller_handoff_late` per seller (`carrier_date > shipping_limit_date`).
- [ ] Xử lý **order không có item row** → items rỗng, seller rỗng (đã có baseline, cần test).
- [ ] Test lookup không tìm thấy order (không crash, đánh dấu `found=False`).

**Nghiệm thu:** với mọi order trong 50 case, facts khớp CSV; item_total/freight khớp thủ công.

**Lệnh (kiểm 1 order bất kỳ):**
```bash
python -c "from src import data_tools as dt; o='e2a03ccf5ea816036608b2d8c3ab8e60'; print(dt.STORE.get_order(o)['order_status']); print(dt.STORE.get_items(o))"
```

### B.3 — Nguyễn Huy Anh (Delivery + Payment Specialist)

**Mục tiêu:** facts giao hàng & đối soát thanh toán chính xác — nền của 20% financial.

**File:** `src/agents/delivery_agent.py`, `src/agents/payment_agent.py`

**Việc:**
- [ ] Delivery: `late_vs_estimate` = delivered_customer_date > estimated_delivery_date.
- [ ] Delivery: `carrier_after_limit` = OR các seller_handoff_late (đã có, cần đối chiếu).
- [ ] Xử lý đơn **chưa giao** (delivered rỗng): quyết định coi là không kết luận late được;
      thống nhất với Phái cách xử lý (tránh gán nhầm late).
- [ ] Payment: `payment_total`, `item_total`, `freight_total`, `num_payment_rows`,
      `reconciled` (sai số 0.10 BRL). Nhớ: payment_value theo row, KHÔNG theo installment.
- [ ] Test 5 case mỗi loại: số khớp tay.

**Nghiệm thu:** financial_resolution của 50 output khớp tính tay trên CSV.

**Lệnh:**
```bash
python main.py EC_009
python -c "import json;o=json.load(open('output/EC_009.json',encoding='utf-8'));print(o['financial_resolution'])"
```

### B.4 — Hoàng Văn Phái (Policy Adjudicator — dual-path)

**Mục tiêu:** phán quyết đúng issue + refund + party, hiệu chỉnh confidence có căn cứ.

**File:** `src/agents/policy_agent.py`

**Việc:**
- [ ] Giữ **Path A** rule engine 6 luật theo đúng thứ tự ưu tiên (đã có baseline).
- [ ] Rà kỹ ranh giới `valid_split_payment` vs `unsupported_late_claim` — đối chiếu ý đồ đề
      để không đảo nhầm case on-time (đây là rủi ro phân loại lớn nhất).
- [ ] (Nâng cấp) Thêm **Path B**: gọi `llm_client.chat_json` cho LLM chọn 1 trong 6 issue
      TRÊN CÙNG bộ facts (chỉ nhận facts đã tính, không cho LLM sinh số).
- [ ] So khớp A/B: đồng thuận → confidence 0.9–0.97; lệch → giữ Path A + hạ confidence + note.
- [ ] Ánh xạ chuẩn: issue → cause_code, responsible_party, action, refund (full=payment_total,
      freight=freight_total, no_action=0).
- [ ] Build evidence liên quan quyết định (order/item/payment/seller vi phạm/policy code).

**Nghiệm thu:** phân loại khớp kỳ vọng trên tập tự gán nhãn; refund đúng công thức theo issue.

**Lệnh:**
```bash
python -c "import json,glob,collections;c=collections.Counter(json.load(open(f,encoding='utf-8'))['assessment']['primary_issue'] for f in glob.glob('output/EC_*.json'));print(c)"
```

### B.5 — Hà Tấn Phong (Verifier-Critic + Observability + Docs)

**Mục tiêu:** chốt chặn chống hard-gate; trace/metadata chuẩn; `architecture.md`.

**File:** `src/agents/verifier_agent.py`, `src/tracing.py`, `architecture.md`

**Việc:**
- [ ] Validate mọi evidence ID **tồn tại thật** trong CSV + đúng định dạng (đã có baseline).
- [ ] Siết ràng buộc: ≤5 ID/entity, ≤10 evidence, ≤3 cause, ≤3 party, ≤5 action, confidence∈[0,1].
- [ ] (Nâng cấp) **Cross-check tài chính khớp issue**: full_refund ⇒ refund==payment_total;
      refund_freight ⇒ refund==freight_total; no_action ⇒ refund==0. Lệch → phát `intent="repair"`.
- [ ] Ghi cảnh báo vào `ctx.notes` + trace để audit.
- [ ] `tracing.py`: đảm bảo `trace.jsonl` **ghi đè**, `metadata.json` đủ trường (model/framework/runtime).
- [ ] Viết `architecture.md`: sơ đồ (mục A.2), vai trò, quyền truy cập dữ liệu, luồng handoff + repair.

**Nghiệm thu:** 0 evidence false-positive; 0 vi phạm ràng buộc; refund luôn khớp issue.

**Lệnh:**
```bash
python -c "import json,glob
bad=[]
for f in glob.glob('output/EC_*.json'):
    o=json.load(open(f,encoding='utf-8'));a=o['assessment'];fr=o['financial_resolution']
    if a['case_status']=='no_action' and fr['recommended_refund_brl']!=0: bad.append(f)
print('refund mismatch:',bad or 'NONE')"
```

### B.6 — Việc chung (mỗi người tự làm)

- [ ] Điền báo cáo cá nhân `individual_5SoCuoiMHV_HoVaTen.md` (đổi tên theo họ tên mình).
- [ ] Không commit `.env`; xác nhận model dùng ≤10B.

---

## C. MỐC THỜI GIAN (khớp checkpoint đề bài)

| Thời gian | Việc |
| --- | --- |
| 9h30–10h00 | Cả nhóm pull scaffold, cài `.venv`, chạy `python main.py` OK. Kiên chốt data layer. |
| 10h00–11h00 | Huy Anh (delivery/payment) + Phái (policy Path A rà ranh giới) + Phong (verifier cross-check). |
| 11h00–11h45 | Đại ráp repair loop; Phái thêm Path B (nếu kịp); test lại 50 case. |
| 11h45–12h15 | Phong hoàn thiện `architecture.md` + trace/metadata; mỗi người viết báo cáo cá nhân. |
| 12h15–12h30 | Đại: commit toàn bộ source → zip `output/` → nộp. Chốt leaderboard 12h30. |

**Nguyên tắc an toàn:** baseline deterministic đã đạt 50/50 hợp lệ — **commit baseline trước**,
rồi mới nâng cấp. Nếu Path B/LLM gây rủi ro, luôn có thể fallback về baseline để nộp.
