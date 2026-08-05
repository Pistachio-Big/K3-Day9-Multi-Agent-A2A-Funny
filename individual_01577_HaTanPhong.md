# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                       |
| --------------- | ---------------------------------------------- |
| Họ và tên       | Hà Tấn Phong                                   |
| MSSV            | [MSSV]                                         |
| Khóa/Lớp        | K3                                             |
| Vai trò chính   | Verifier-Critic, Observability & Documentation |
| Ngày hoàn thành | 2026-08-05                                     |


## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable            | File/hàm phụ trách                  | Input nhận vào                                                      | Output bàn giao                                                    | Trạng thái |
| ----------------------------- | ----------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------- |
| Verifier Agent                | `src/agents/verifier_agent.py`      | Kết quả tổng hợp từ Coordinator, CSV evidence, financial resolution | Assessment đã được kiểm tra hoặc intent=`repair` nếu phát hiện lỗi | Hoàn thành |
| Observability & Documentation | `src/tracing.py`, `architecture.md` | Metadata runtime và trace của toàn pipeline                         | `trace.jsonl`, `metadata.json`, tài liệu kiến trúc                 | Hoàn thành |


### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                  | Thành viên/module được hỗ trợ | Kết quả                                                                     |
| -------------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| Kiểm thử tích hợp pipeline | Coordinator                   | Xác minh output cuối cùng thỏa schema và financial rules trước khi ghi file |
| Hỗ trợ tài liệu hệ thống   | Toàn bộ project               | Hoàn thiện architecture.md mô tả luồng Agent A2A và repair flow             |


## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                          | File/hàm/artifact liên quan    | Kết quả bàn giao                                 | Cách xác minh                           |
| ---------------------------------------------- | ------------------------------ | ------------------------------------------------ | --------------------------------------- |
| Kiểm tra Evidence ID tồn tại và đúng định dạng | `src/agents/verifier_agent.py` | Không còn evidence false-positive                | Chạy verifier trên toàn bộ output       |
| Cross-check financial resolution               | `src/agents/verifier_agent.py` | Refund luôn khớp issue hoặc sinh intent=`repair` | Script kiểm tra refund mismatch         |
| Ghi trace và metadata                          | `src/tracing.py`               | `trace.jsonl`, `metadata.json`                   | Kiểm tra artifact sau khi chạy pipeline |
| Viết tài liệu kiến trúc                        | `architecture.md`              | Mô tả đầy đủ Agent Architecture                  | Review tài liệu                         |


Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Assessment đã được xác minh.
intent=repair khi phát hiện lỗi.
trace.jsonl
metadata.json
architecture.md
[Mô tả artifact, metric, report hoặc kết quả tích hợp.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline gồm nhiều agent nên kết quả tổng hợp có thể vi phạm schema hoặc sinh dữ liệu không nhất quán. Verifier Agent đóng vai trò lớp kiểm tra cuối nhằm ngăn các output sai được ghi xuống file.

### Cách triển khai

Verifier thực hiện nhiều bước kiểm tra trước khi pipeline kết thúc:

Kiểm tra mọi Evidence ID phải tồn tại trong CSV và đúng định dạng.
Kiểm tra số lượng entity, evidence, cause, party và action theo đúng giới hạn của schema.
Kiểm tra confidence luôn nằm trong khoảng [0,1].
Cross-check giữa issue và financial resolution:
full_refund ⇒ refund bằng payment_total.
refund_freight ⇒ refund bằng freight_total.
no_action ⇒ refund bằng 0.
Nếu phát hiện sai lệch thì không ghi kết quả ngay mà sinh intent="repair" để Coordinator thực hiện vòng sửa.
Mọi cảnh báo đều được ghi vào ctx.notes và trace nhằm phục vụ audit sau này.

Ngoài ra tôi xây dựng module tracing để lưu lại metadata của lần chạy (model, framework, runtime) và toàn bộ trace phục vụ kiểm thử cũng như tái hiện kết quả.

### Input, output và contract

| Thành phần              | Mô tả                                                                             |
| ----------------------- | --------------------------------------------------------------------------------- |
| Input                   | Assessment, Financial Resolution, Evidence CSV                                    |
| Output                  | Assessment đã verify hoặc intent=`repair`, trace.jsonl, metadata.json             |
| Module phụ thuộc        | Coordinator, schemas.py                                                           |
| Module sử dụng output   | Output writer, evaluation                                                         |
| Điều kiện lỗi cần xử lý | Evidence sai, schema sai, refund không khớp issue, confidence ngoài khoảng hợp lệ |

### Cách xác minh

```bash
python -c "import json,glob
bad=[]
for f in glob.glob('output/EC_*.json'):
    o=json.load(open(f,encoding='utf-8'))
    a=o['assessment']
    fr=o['financial_resolution']
    if a['case_status']=='no_action' and fr['recommended_refund_brl']!=0:
        bad.append(f)
print('refund mismatch:',bad or 'NONE')"```



## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Pipeline có thể sinh financial resolution không nhất quán với issue được dự đoán.]
- **Các phương án đã cân nhắc:** [Chỉ ghi warning vào log, Chặn pipeline và yêu cầu Coordinator thực hiện repair.]
- **Phương án đã chọn:** [Sinh intent="repair" khi phát hiện mismatch.]
- **Lý do:** [Đảm bảo output cuối cùng luôn nhất quán thay vì chỉ cảnh báo rồi vẫn ghi dữ liệu sai. Cách này tăng độ tin cậy của pipeline và tránh lỗi lan sang bước đánh giá.]
- **Bằng chứng quyết định phù hợp:** [Sau khi repair, script kiểm tra refund không còn phát hiện mismatch.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Financial resolution không khớp với assessment (ví dụ no_action nhưng refund khác 0).]
- **Lệnh hoặc bước tái hiện:** [Chạy verifier trên output của Coordinator.]
- **Nguyên nhân gốc:** [Agent chuyên môn trả về dữ liệu hợp lệ riêng lẻ nhưng chưa đảm bảo tính nhất quán giữa các trường.]
- **Cách xử lý:** [Bổ sung bước cross-check và sinh intent="repair" nếu phát hiện sai lệch.]
- **Cách xác minh sau khi sửa:** [Chạy script kiểm tra refund mismatch, kết quả trả về NONE.]
- **Điều học được:** [Ngoài kiểm tra schema cần có kiểm tra tính nhất quán nghiệp vụ giữa các trường dữ liệu.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?

Tài liệu được lấy từ Crossref, tiền xử lý và chia thành các đoạn nhỏ (chunk). Mỗi chunk được embedding thành vector rồi lưu trong vector database để phục vụ truy xuất ngữ nghĩa.

2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?

Evaluation set chứa các câu truy vấn chuẩn cùng ground-truth document IDs. Retrieval được đánh giá bằng việc so sánh tài liệu trả về với ground-truth, còn answer quality được đánh giá dựa trên việc câu trả lời có sử dụng đúng các tài liệu liên quan hay không.

3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?

Quality checks đánh giá chất lượng dữ liệu và kết quả hiện tại (schema, correctness, consistency). Freshness monitoring theo dõi dữ liệu có còn mới hay đã lỗi thời để quyết định cần cập nhật hay không.

4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?

Sử dụng cùng một tập kiểm thử giúp đảm bảo sự khác biệt về metric chỉ đến từ việc sửa hệ thống, tránh sai lệch do thay đổi dữ liệu kiểm thử.

5. Repair được xem là thành công dựa trên artifact và metric nào?

Repair thành công khi output không còn vi phạm các ràng buộc của verifier, không còn refund mismatch, trace ghi nhận pipeline hoàn tất và các artifact đầu ra hợp lệ.

**Câu trả lời:**

[Viết câu trả lời tại đây.]

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Hà Tấn Phong]
**Ngày xác nhận:** [2026-08-05]
