# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung          |
| --------------- | ----------------- |
| Họ và tên       | Nguyễn Văn Đại    |
| MSSV            | 2A202601217       |
| Khóa/Lớp        | K3                |
| Vai trò chính   | Coordinator / Team Lead |
| Ngày hoàn thành | 2026-08-05        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Orchestration multi-agent | `src/agents/coordinator.py` (`Coordinator.run_case`) | 1 case JSON (`input/EC_xxx.json`) | dict output đúng schema + các dòng trace | Hoàn thành |
| Contract dùng chung | `src/schemas.py` (`CaseContext`, `build_output`), `src/a2a/base_agent.py`, `src/a2a/message.py` | facts từ các agent | blackboard + envelope handoff | Hoàn thành |
| Cấu hình model/provider | `src/config.py` (`AGENT_MODELS`, provider, `USE_LLM`) | `.env` (provider, key) | tên model ≤10B khai báo trong code | Hoàn thành |
| Entrypoint chạy 50 case | `main.py` | thư mục `input/` | `output/EC_*.json` + `logging/` | Hoàn thành |
| Script nộp bài | `make_submission.py` | `output/` | `submission.zip` (chỉ 50 JSON) | Hoàn thành |

Tôi chỉ nhận ownership phần điều phối + contract + đóng gói. Logic từng domain (order/seller, delivery, payment, policy, verifier) do các thành viên khác sở hữu; phần của tôi **tiêu thụ facts** họ ghi vào `CaseContext` và **định tuyến handoff** giữa họ.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Định nghĩa contract `CaseContext` + `A2AMessage` để cả nhóm bám theo | Cả 5 agent | Các agent ghép nối không lệch interface |
| Viết `COMMIT_GUIDE.md` phân công commit theo file | Cả nhóm | Mỗi người biết chính xác file + thay đổi cần commit |
| Thiết lập tuân thủ README mục 9 (model trong code, `.env` gitignore, zip chỉ output) | Cả nhóm | Tránh mất điểm hard-gate khi nộp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Điều phối fan-out song song Delivery ∥ Payment | `coordinator.py` (`ThreadPoolExecutor`) | 2 message `dispatch` mỗi case | đếm `dispatch` trong `trace.jsonl` |
| Critic-repair loop Policy↔Verifier (tối đa 2 vòng) | `coordinator.py` (vòng `MAX_ADJUDICATION_ROUNDS`) | verifier trả `final`/`repair` được định tuyến lại | trace có `verify`/`repair`/`final` |
| Sinh 50 output đúng schema | `main.py` + `build_output` | 50 file `output/EC_*.json` | `python main.py` |
| Trace + metadata lượt chạy mới nhất | `logging/trace.jsonl`, `logging/metadata.json` | 550 dòng trace, metadata model/runtime | mở 2 file |
| Đóng gói nộp bài đúng mục 9.2 | `make_submission.py` | `submission.zip` = đúng 50 JSON, không kèm source/.env | `python make_submission.py` |

**Output cụ thể phần tôi tạo/giúp xác minh:** khi chạy đầy đủ pipeline, `python main.py` sinh **50/50** file output hợp lệ, **0 vi phạm ràng buộc** schema (≤5 ID/entity, ≤10 evidence, ≤3 cause, confidence∈[0,1]), refund luôn khớp issue; `trace.jsonl` **550 dòng** (11 handoff/case) chứng minh handoff A2A thật giữa 6 agent.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đề chấm điểm cao cho **multi-agent có phân công + handoff + kiểm chứng thật**, không cho điểm nếu chỉ gọi 1 prompt. Phần của tôi phải: (1) ghép 6 agent rời rạc thành một luồng chạy được cho từng case, (2) đảm bảo có handoff hai chiều + tự sửa để chống hard-gate, (3) đóng gói đúng ràng buộc mục 9 để không bị 0 điểm khi nộp.

### Cách triển khai

Tôi dùng mô hình **blackboard + orchestrator**: một `CaseContext` (bảng đen) trôi qua toàn pipeline, mỗi agent đọc/ghi đúng slot của mình (`order_facts`, `delivery_facts`, `payment_facts`, `decision`). `Coordinator.run_case` điều phối theo 5 bước:

1. Gọi **Order & Seller** trước (lấy order/item/seller).
2. **Fan-out song song** Delivery ∥ Payment bằng `ThreadPoolExecutor` — hai agent chỉ đọc `order_facts` và ghi hai slot khác nhau nên an toàn, không tranh chấp.
3. Gọi **Policy** để phán quyết.
4. Gọi **Verifier**; nếu Verifier trả `intent="repair"` (refund/evidence mâu thuẫn) thì Coordinator quay lại Policy với cờ `force_deterministic`, tối đa 2 vòng — đây là **handoff hai chiều**, khác pipeline một chiều gợi ý trong README.
5. `build_output` ráp `CaseContext` thành JSON đúng schema, tự cắt theo giới hạn (≤5/≤10/≤3/≤5).

Mọi bước ghi 1 dòng vào `trace.jsonl` qua `Tracer` để có bằng chứng A2A. Tên model ≤10B khai báo trong `config.AGENT_MODELS` (không để trong `.env`) và được ghi lại vào `metadata.json`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | 1 case dict từ `input/EC_xxx.json` (`case_id`, `claimed_order_id`, `message`, `policy_version`) |
| Output | dict đúng schema README mục 6 (`assessment`, `affected_entities`, `root_cause_analysis`, `evidence_ids`, `financial_resolution`, `resolution_actions`) |
| Module phụ thuộc | 5 agent domain + `data_tools` (nguồn sự thật CSV) |
| Module sử dụng output | `main.py` ghi file; `make_submission.py` đóng gói |
| Điều kiện lỗi cần xử lý | order không tồn tại; đơn không có item row; verifier phát mâu thuẫn → repair; giới hạn số vòng để tránh lặp vô hạn (`MAX_ADJUDICATION_ROUNDS`) |

### Cách xác minh

```bash
python main.py
python -c "import glob; assert len(glob.glob('output/EC_*.json'))==50"
python make_submission.py
```

- **Kết quả mong đợi:** 50 file output hợp lệ, trace ghi đủ handoff, zip đúng 50 JSON.
- **Kết quả thực tế:** khi chạy đầy đủ 6 agent, sinh 50/50 output, 0 vi phạm ràng buộc, `trace.jsonl` 550 dòng (fan-out: 100 `dispatch`; adjudicate: 50), `submission.zip` đúng 50 JSON không kèm source/.env.
- **Artifact/log:** `output/`, `logging/trace.jsonl`, `logging/metadata.json` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** chọn topology cho hệ multi-agent để tối ưu thang điểm (55% điểm là entities + financial + evidence — dữ liệu xác định).
- **Các phương án đã cân nhắc:** (1) pipeline tuyến tính một chiều như gợi ý README; (2) blackboard + fan-out song song + critic-repair loop, tách hẳn tầng tool deterministic khỏi tầng suy luận LLM.
- **Phương án đã chọn:** phương án (2).
- **Lý do:** khoá mọi con số/ID vào `data_tools` (LLM không sinh số) → chống hallucination, bảo toàn 55% điểm dữ liệu; fan-out giảm phụ thuộc; repair loop chặn hard-gate (evidence/refund sai). Trade-off: phức tạp hơn một chút, nhưng đổi lại độ chính xác và khả năng tự sửa.
- **Bằng chứng quyết định phù hợp:** chạy 50 case cho phân bố đều 6 loại issue, 0 vi phạm ràng buộc, refund luôn khớp issue (cross-check của Verifier không kích hoạt repair với dữ liệu xác định).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: OrderSellerAgent.process() missing 1 required positional argument: 'ctx'`.
- **Lệnh tái hiện:** `python main.py EC_001`.
- **Nguyên nhân gốc:** đổi contract `BaseAgent.process` từ `(msg, ctx) -> list[A2AMessage]` sang `(ctx, inbox) -> A2AMessage` (bỏ `emit`, thêm `result`), nhưng một số agent chưa cập nhật theo contract mới → lệch chữ ký hàm khi Coordinator gọi.
- **Cách xử lý:** thống nhất contract mới trong `base_agent.py`, cập nhật Coordinator gọi `process(ctx)` và đọc 1 message trả về; ghi rõ thay đổi cho từng agent trong `COMMIT_GUIDE.md` để các thành viên đồng bộ.
- **Cách xác minh sau khi sửa:** khi tất cả agent theo contract mới, `python main.py` chạy hết 50 case không lỗi, trace 550 dòng.
- **Điều học được:** khi thay đổi interface dùng chung phải cập nhật đồng thời mọi bên hoặc khoá lại bằng lớp base + tài liệu; nếu để lệch, hệ multi-agent sẽ vỡ ở bước định tuyến.

## 7. Hiểu biết về luồng end-to-end

Câu hỏi (điều chỉnh cho đúng lab này):

1. Một case đi từ `input/EC_xxx.json` đến `output/EC_xxx.json` qua những agent nào?
2. `data_tools` đóng vai trò gì và vì sao mọi con số/ID phải lấy từ đó?
3. Handoff A2A được thể hiện và kiểm chứng ở đâu?
4. Cơ chế nào chống hard-gate (evidence sai / refund lệch)?
5. Vì sao ràng buộc model ≤10B vẫn thoả dù (hiện tại) chỉ Policy gọi LLM?

**Câu trả lời:**

1. Coordinator đọc case → Order&Seller lấy facts đơn/item/seller → fan-out Delivery ∥ Payment → Policy phán quyết (issue, refund, party, action, evidence) → Verifier validate + cross-check → `build_output` ráp JSON → `main.py` ghi ra `output/`.
2. `data_tools` là **nguồn sự thật duy nhất** đọc 9 CSV Olist và dựng evidence ID hợp lệ. Vì entities + financial + evidence chiếm 55% điểm và evidence sai bị tính false positive, nên chúng phải đến từ dữ liệu xác định chứ không để LLM sinh — tránh hallucination.
3. Mỗi bước điều phối tạo một `A2AMessage` và được `Tracer` ghi một dòng trong `logging/trace.jsonl` (`investigate → facts_ready → dispatch×2 → facts_ready×2 → adjudicate → decision_ready → verify → final → assembled`). Đây là bằng chứng có phân công + handoff thật.
4. Verifier kiểm tra evidence có thật trong CSV + siết ràng buộc schema; đồng thời cross-check refund khớp issue (full⇒payment_total, freight⇒freight_total, no_action⇒0). Lệch thì phát `repair` để Policy tính lại bằng đường deterministic, tối đa 2 vòng.
5. Đề ràng buộc **mỗi agent ≤10B**; nhóm khai báo model 8B (llama-3.1-8b) cho mọi agent trong `config.py`, đều thoả. Số liệu chạy deterministic để đảm bảo đúng, còn LLM là lớp trọng tài/hiệu chỉnh confidence — có thể mở rộng cho các agent khác mà vẫn giữ số liệu từ dữ liệu.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Đại
**Ngày xác nhận:** 2026-08-05
