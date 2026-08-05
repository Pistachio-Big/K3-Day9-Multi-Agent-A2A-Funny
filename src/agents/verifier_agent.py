"""
Verifier-Critic Agent — chốt chặn cuối + vòng lặp repair.

Kiểm tra:
  - Mọi evidence ID có THẬT trong CSV & đúng định dạng (evidence sai = false positive).
  - Ràng buộc schema: <=5 ID/entity, <=10 evidence, <=3 cause, <=3 party, <=5 action.
  - confidence trong [0,1].
  - CROSS-CHECK tài chính khớp issue:
        full refund  -> refund == payment_total
        refund_freight -> refund == freight_total
        no_action    -> refund == 0
    Lệch -> phát intent="repair" (target=policy_agent), ép Policy chạy lại Path A xác định.
    Tối đa 2 vòng repair; hết vòng thì chốt best-effort.

Trả về Coordinator: intent="final" (đạt) hoặc "repair" (cần sửa).

Owner: Hà Tấn Phong.
"""
from __future__ import annotations

from typing import Optional

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt

MAX_REPAIR = 2


class VerifierAgent(BaseAgent):
    name = "verifier_agent"

    def process(self, ctx: CaseContext, inbox: Optional[A2AMessage] = None) -> A2AMessage:
        # 1) evidence phải tồn tại thật + bỏ trùng + cap 10
        ctx.evidence_ids = [e for e in ctx.evidence_ids if self._evidence_exists(e)]
        seen: set[str] = set()
        ctx.evidence_ids = [e for e in ctx.evidence_ids if e not in seen and not seen.add(e)][:10]

        # 2) siết ràng buộc schema
        dec = ctx.decision
        dec.confidence = max(0.0, min(1.0, float(dec.confidence or 0.0)))
        dec.ranked_causes = dec.ranked_causes[:3]
        dec.responsible_parties = dec.responsible_parties[:3]
        dec.resolution_actions = dec.resolution_actions[:5]

        # 3) cross-check tài chính khớp issue
        expected = self._expected_refund(ctx)
        mismatch = expected is not None and abs(round(dec.recommended_refund_brl, 2) - expected) > 0.001

        if mismatch and ctx.repair_count < MAX_REPAIR:
            ctx.repair_count += 1
            ctx.force_deterministic = True          # ép Policy dùng Path A xác định
            ctx.notes.append(
                f"repair#{ctx.repair_count}:refund={dec.recommended_refund_brl} != expected={expected}"
            )
            return self.result("policy_agent", "repair", ctx,
                               reason="refund_mismatch", expected=expected)

        if mismatch:
            ctx.notes.append("repair_exhausted_refund_mismatch")

        ctx.verified = True
        return self.result("coordinator", "final", ctx, evidence_count=len(ctx.evidence_ids))

    # ------------------------------------------------------------------ #
    def _expected_refund(self, ctx: CaseContext) -> Optional[float]:
        issue = ctx.decision.primary_issue
        pf = ctx.payment_facts
        if issue in ("canceled_order_paid", "unavailable_order_paid"):
            return round(pf.payment_total_brl, 2)
        if issue in ("late_delivery_seller", "late_delivery_logistics"):
            return round(pf.freight_total_brl, 2)
        if issue in ("valid_split_payment", "unsupported_late_claim"):
            return 0.0
        return None

    def _evidence_exists(self, ev: str) -> bool:
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
