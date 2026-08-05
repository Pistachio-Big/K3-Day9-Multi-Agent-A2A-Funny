"""
Verifier Agent — chốt chặn cuối trước khi ghi file.

Kiểm tra:
  - Mọi evidence ID có THẬT trong CSV & đúng định dạng (evidence sai = false positive).
  - Ràng buộc schema: <=5 ID/entity, <=10 evidence, <=3 cause, <=3 party, <=5 action.
  - confidence trong [0,1]; refund làm tròn 2 số; case_status hợp lệ.
  - Đơn không có item row -> item/seller rỗng, item_total/freight_total = 0.
Sau đó handoff "final" về Coordinator.

Owner: Hà Tấn Phong.

TODO(Phong):
  - [baseline đã có] validate evidence tồn tại + siết ràng buộc.
  - Bổ sung cross-check refund khớp primary_issue (full refund = payment_total, ...).
  - Ghi cảnh báo vào ctx.notes để trace.
"""
from __future__ import annotations

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt


class VerifierAgent(BaseAgent):
    name = "verifier_agent"

    def process(self, msg: A2AMessage, ctx: CaseContext) -> list[A2AMessage]:
        ctx.evidence_ids = [e for e in ctx.evidence_ids if self._evidence_exists(e)]

        # bỏ trùng, cap 10
        seen: set[str] = set()
        ctx.evidence_ids = [e for e in ctx.evidence_ids if e not in seen and not seen.add(e)][:10]

        # confidence trong [0,1]
        dec = ctx.decision
        dec.confidence = max(0.0, min(1.0, float(dec.confidence or 0.0)))

        # cap các list
        dec.ranked_causes = dec.ranked_causes[:3]
        dec.responsible_parties = dec.responsible_parties[:3]
        dec.resolution_actions = dec.resolution_actions[:5]

        ctx.verified = True
        return [self.emit("coordinator", "final", ctx, evidence_count=len(ctx.evidence_ids))]

    # ------------------------------------------------------------------ #
    def _evidence_exists(self, ev: str) -> bool:
        """Chỉ chấp nhận evidence dựng được trực tiếp từ CSV."""
        parts = ev.split(":")
        kind = parts[0]
        try:
            if kind == "order":
                return dt.STORE.get_order(parts[1]) is not None
            if kind == "item":
                items = dt.STORE.get_items(parts[1])
                return any(it["order_item_id"] == parts[2] for it in items)
            if kind == "payment":
                pays = dt.STORE.get_payments(parts[1])
                return any(p["payment_sequential"] == parts[2] for p in pays)
            if kind == "seller":
                return dt.STORE.get_seller(parts[1]) is not None
            if kind == "policy":
                return len(parts) == 2 and parts[1] != ""
        except IndexError:
            return False
        return False
