"""
Policy Agent — trái tim quyết định (EC_POLICY_V1).

Áp 6 luật THEO THỨ TỰ ƯU TIÊN (README mục 4), luật đầu tiên khớp sẽ thắng:

  1. canceled_order_paid      status=canceled  & payment>0   -> platform, full refund
  2. unavailable_order_paid   status=unavailable & payment>0 -> platform, full refund
  3. late_delivery_seller     giao trễ estimate & carrier > shipping_limit -> seller, refund freight
  4. late_delivery_logistics  giao trễ estimate & carrier <= shipping_limit -> logistics, refund freight
  5. valid_split_payment      >=2 payment row & reconciled                 -> no action, giải thích
  6. unsupported_late_claim   giao không trễ & payment khớp                -> no action, bác claim

Sau đó handoff sang Verifier Agent.

Owner: Hoàng Văn Phái.

TODO(Phái):
  - [baseline đã có] cây quyết định 6 luật + dựng evidence + refund.
  - Tinh chỉnh `confidence` theo độ chắc chắn của bằng chứng.
  - Rà case biên (nhiều seller vi phạm, order thiếu item row).
  - Có thể dùng LLM để giải thích/ghi chú, nhưng CON SỐ phải từ dữ liệu.
"""
from __future__ import annotations

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt

# Root-cause code cho mỗi primary issue
CAUSE = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}


class PolicyAgent(BaseAgent):
    name = "policy_agent"

    def process(self, ctx: CaseContext) -> list[A2AMessage]:
        of, df, pf, dec = ctx.order_facts, ctx.delivery_facts, ctx.payment_facts, ctx.decision
        status = (of.order_status or "").lower()

        # ---- Cây quyết định theo thứ tự ưu tiên -----------------------------
        if status == "canceled" and pf.payment_total_brl > 0:
            self._set(dec, "canceled_order_paid", "action_required",
                      refund=pf.payment_total_brl, actions=["issue_full_refund"],
                      parties=[("platform", "OLIST_PLATFORM")], confidence=0.9)

        elif status == "unavailable" and pf.payment_total_brl > 0:
            self._set(dec, "unavailable_order_paid", "action_required",
                      refund=pf.payment_total_brl, actions=["issue_full_refund"],
                      parties=[("platform", "OLIST_PLATFORM")], confidence=0.9)

        elif df.late_vs_estimate and df.carrier_after_limit:
            late_sellers = [s for s, late in of.seller_handoff_late.items() if late] or of.seller_ids
            self._set(dec, "late_delivery_seller", "action_required",
                      refund=pf.freight_total_brl, actions=["refund_freight"],
                      parties=[("seller", s) for s in late_sellers], confidence=0.9)

        elif df.late_vs_estimate and not df.carrier_after_limit:
            self._set(dec, "late_delivery_logistics", "action_required",
                      refund=pf.freight_total_brl, actions=["refund_freight"],
                      parties=[("logistics_provider", "LOGISTICS_PROVIDER")], confidence=0.9)

        elif pf.num_payment_rows >= 2 and pf.reconciled:
            self._set(dec, "valid_split_payment", "no_action",
                      refund=0.0, actions=["explain_valid_split_payment"],
                      parties=[], confidence=0.85)

        else:
            # đơn giao không trễ & payment khớp -> bác claim
            self._set(dec, "unsupported_late_claim", "no_action",
                      refund=0.0, actions=["reject_late_refund"],
                      parties=[], confidence=0.8)

        self._build_evidence(ctx)

        return [self.emit("verifier_agent", "decision_ready", ctx,
                          primary_issue=dec.primary_issue,
                          refund=dec.recommended_refund_brl)]

    # ------------------------------------------------------------------ #
    def _set(self, dec, issue, case_status, *, refund, actions, parties, confidence):
        dec.primary_issue = issue
        dec.case_status = case_status
        dec.recommended_refund_brl = round(refund, 2)
        dec.resolution_actions = actions
        dec.responsible_parties = [{"party_type": t, "party_id": pid} for t, pid in parties]
        dec.ranked_causes = [{"cause_code": CAUSE[issue], "rank": 1}]
        dec.confidence = confidence

    def _build_evidence(self, ctx: CaseContext):
        of, pf, dec = ctx.order_facts, ctx.payment_facts, ctx.decision
        ev: list[str] = []
        if of.order_id:
            ev.append(dt.ev_order(of.order_id))
            for it in of.items:
                ev.append(dt.ev_item(of.order_id, it["order_item_id"]))
            for p in pf.payments:
                ev.append(dt.ev_payment(of.order_id, p["payment_sequential"]))
        # seller chịu trách nhiệm
        for party in dec.responsible_parties:
            if party["party_type"] == "seller":
                ev.append(dt.ev_seller(party["party_id"]))
        # policy code
        if dec.ranked_causes:
            ev.append(dt.ev_policy(dec.ranked_causes[0]["cause_code"]))
        # bỏ trùng, giữ thứ tự
        seen: set[str] = set()
        ctx.evidence_ids = [e for e in ev if e not in seen and not seen.add(e)]
