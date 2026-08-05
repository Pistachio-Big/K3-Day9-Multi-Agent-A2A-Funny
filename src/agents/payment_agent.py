"""
Payment Agent.

Nhiệm vụ: đối soát thanh toán.
  - payment_total = tổng payment_value các row
  - item_total = tổng price các item; freight_total = tổng freight_value
  - reconciled = |payment_total - (item_total + freight_total)| <= 0.10 BRL
  - num_payment_rows: >= 2 dùng cho luật valid_split_payment
Sau đó handoff sang Policy Agent.

Owner: Nguyễn Huy Anh.

TODO(Huy Anh):
  - [baseline đã có] tính tổng + reconcile.
  - Lưu ý: payment_value là số tiền mỗi payment row, KHÔNG phải từng installment.
"""
from __future__ import annotations

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import config, data_tools as dt


class PaymentAgent(BaseAgent):
    name = "payment_agent"

    def process(self, msg: A2AMessage, ctx: CaseContext) -> list[A2AMessage]:
        of, pf = ctx.order_facts, ctx.payment_facts

        payments = dt.STORE.get_payments(of.order_id) if of.order_id else []
        pf.payments = [
            {
                "payment_sequential": p["payment_sequential"],
                "payment_type": p.get("payment_type"),
                "payment_value": dt.to_float(p.get("payment_value")),
            }
            for p in payments
        ]
        pf.num_payment_rows = len(pf.payments)
        pf.payment_total_brl = round(sum(p["payment_value"] for p in pf.payments), 2)
        pf.item_total_brl = dt.item_total(of.items)
        pf.freight_total_brl = dt.freight_total(of.items)

        expected = round(pf.item_total_brl + pf.freight_total_brl, 2)
        pf.reconciled = abs(pf.payment_total_brl - expected) <= config.RECONCILE_TOLERANCE

        return [self.emit("policy_agent", "facts_ready", ctx,
                          payment_total=pf.payment_total_brl,
                          reconciled=pf.reconciled,
                          num_payment_rows=pf.num_payment_rows)]
