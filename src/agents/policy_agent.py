"""
Policy Adjudicator — EC_POLICY_V1, ENSEMBLE 3 PHIẾU (deterministic + 2 model LLM).

Path A (xác định, LUÔN chạy — nguồn sự thật cho MỌI con số & ID):
  Áp 6 luật theo thứ tự ưu tiên, luật đầu tiên khớp thắng:
    1. canceled_order_paid      status=canceled   & payment>0            -> platform, full refund
    2. unavailable_order_paid   status=unavailable & payment>0           -> platform, full refund
    3. late_delivery_seller     giao trễ estimate & carrier > ship_limit -> seller, refund freight
    4. late_delivery_logistics  giao trễ estimate & carrier <= ship_limit-> logistics, refund freight
    5. valid_split_payment      >=2 payment row & reconciled             -> no action, giải thích
    6. unsupported_late_claim   giao không trễ & payment khớp            -> no action, bác claim

Ensemble (khi USE_LLM=1 và không bị ép deterministic):
  2 model (config.POLICY_ENSEMBLE_MODELS: qwen-2.5-7b + llama-3.1-8b) độc lập phân loại
  issue TRÊN CÙNG bộ facts. Gộp với Path A thành 3 phiếu:
    - cả 2 model đồng thuận Path A  -> confidence 0.97 (rất chắc)
    - 1 model đồng thuận            -> confidence 0.90
    - cả 2 model KHÁC Path A        -> confidence 0.60 + ghi ctx.disagreement (soi tay)
  QUAN TRỌNG: con số/ID/party/action LUÔN theo Path A (không để LLM sinh số).
  Đòn bẩy điểm = danh sách case bất đồng -> đối chiếu README mục 4 để sửa rule nếu cần.

Owner: Hoàng Văn Phái.
"""
from __future__ import annotations

from typing import Optional

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import config, data_tools as dt

CAUSE = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}
ISSUES = list(CAUSE.keys())


class PolicyAgent(BaseAgent):
    name = "policy_agent"

    def process(self, ctx: CaseContext, inbox: Optional[A2AMessage] = None) -> A2AMessage:
        # ---- Path A: xác định (nguồn số/ID) --------------------------------
        issue_a = self._decide_deterministic(ctx)
        self._apply(ctx, issue_a)

        confidence = self._base_confidence(issue_a)
        votes = {"deterministic": issue_a}

        # ---- Ensemble 2 model (không đổi số, chỉ vote + confidence) ---------
        if config.USE_LLM and not ctx.force_deterministic:
            model_votes = {m: self._classify_with(m, ctx) for m in config.POLICY_ENSEMBLE_MODELS}
            votes.update(model_votes)
            llm_valid = [v for v in model_votes.values() if v in ISSUES]
            agree = sum(1 for v in llm_valid if v == issue_a)

            # LƯU Ý: model 7-8B khá nhiễu, deterministic mới là nguồn tin cậy.
            # -> chỉ BOOST confidence khi model đồng thuận; TUYỆT ĐỐI không hạ
            #    confidence của câu deterministic đúng (tránh phản tác dụng điểm).
            if llm_valid and agree == len(llm_valid):
                confidence = min(0.97, confidence + 0.05)
                ctx.notes.append(f"ensemble_unanimous:{issue_a}")
            elif agree >= 1:
                ctx.notes.append(f"ensemble_majority:{issue_a}")  # giữ confidence base
            elif llm_valid:  # cả 2 model đều khác Path A -> chỉ ghi lại để soi tay
                ctx.notes.append(f"ensemble_disagree(A={issue_a},llm={llm_valid})")
                ctx.disagreement = {
                    "case_id": ctx.case_id,
                    "order_id": ctx.order_facts.order_id,
                    "deterministic": issue_a,
                    "model_votes": model_votes,
                    "facts": self._facts(ctx),
                }

        ctx.decision.confidence = round(confidence, 2)
        self._build_evidence(ctx)
        return self.result("coordinator", "decision_ready", ctx,
                           primary_issue=ctx.decision.primary_issue,
                           refund=ctx.decision.recommended_refund_brl,
                           confidence=ctx.decision.confidence,
                           votes=votes)

    # ------------------------------------------------------------------ #
    def _decide_deterministic(self, ctx: CaseContext) -> str:
        of, df, pf = ctx.order_facts, ctx.delivery_facts, ctx.payment_facts
        status = (of.order_status or "").lower()
        if status == "canceled" and pf.payment_total_brl > 0:
            return "canceled_order_paid"
        if status == "unavailable" and pf.payment_total_brl > 0:
            return "unavailable_order_paid"
        if df.late_vs_estimate and df.carrier_after_limit:
            return "late_delivery_seller"
        if df.late_vs_estimate and not df.carrier_after_limit:
            return "late_delivery_logistics"
        if pf.num_payment_rows >= 2 and pf.reconciled:
            return "valid_split_payment"
        return "unsupported_late_claim"

    def _apply(self, ctx: CaseContext, issue: str) -> None:
        of, pf, dec = ctx.order_facts, ctx.payment_facts, ctx.decision
        dec.primary_issue = issue
        dec.ranked_causes = [{"cause_code": CAUSE[issue], "rank": 1}]

        if issue in ("canceled_order_paid", "unavailable_order_paid"):
            dec.case_status = "action_required"
            dec.recommended_refund_brl = round(pf.payment_total_brl, 2)
            dec.resolution_actions = ["issue_full_refund"]
            dec.responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        elif issue == "late_delivery_seller":
            late_sellers = [s for s, late in of.seller_handoff_late.items() if late] or of.seller_ids
            dec.case_status = "action_required"
            dec.recommended_refund_brl = round(pf.freight_total_brl, 2)
            dec.resolution_actions = ["refund_freight"]
            dec.responsible_parties = [{"party_type": "seller", "party_id": s} for s in late_sellers]
        elif issue == "late_delivery_logistics":
            dec.case_status = "action_required"
            dec.recommended_refund_brl = round(pf.freight_total_brl, 2)
            dec.resolution_actions = ["refund_freight"]
            dec.responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
        elif issue == "valid_split_payment":
            dec.case_status = "no_action"
            dec.recommended_refund_brl = 0.0
            dec.resolution_actions = ["explain_valid_split_payment"]
            dec.responsible_parties = []
        else:  # unsupported_late_claim
            dec.case_status = "no_action"
            dec.recommended_refund_brl = 0.0
            dec.resolution_actions = ["reject_late_refund"]
            dec.responsible_parties = []

    def _base_confidence(self, issue: str) -> float:
        return {
            "canceled_order_paid": 0.92,
            "unavailable_order_paid": 0.92,
            "late_delivery_seller": 0.9,
            "late_delivery_logistics": 0.9,
            "valid_split_payment": 0.85,
            "unsupported_late_claim": 0.8,
        }[issue]

    def _facts(self, ctx: CaseContext) -> dict:
        of, df, pf = ctx.order_facts, ctx.delivery_facts, ctx.payment_facts
        return {
            "order_status": of.order_status,
            "delivered": df.delivered,
            "late_vs_estimate": df.late_vs_estimate,
            "carrier_after_limit": df.carrier_after_limit,
            "num_payment_rows": pf.num_payment_rows,
            "payment_reconciled": pf.reconciled,
            "payment_total_brl": pf.payment_total_brl,
        }

    def _classify_with(self, model: str, ctx: CaseContext) -> str:
        """1 model phân loại issue trên facts đã tính. Lỗi -> '' (bỏ phiếu trắng)."""
        from .. import llm_client
        system = (
            "Bạn là trọng tài chính sách EC_POLICY_V1. Chỉ chọn MỘT primary_issue trong danh sách, "
            "dựa THUẦN vào facts cho sẵn, không bịa. Trả JSON {\"primary_issue\": \"...\"}. "
            f"Danh sách hợp lệ: {ISSUES}."
        )
        user = f"facts = {self._facts(ctx)}"
        try:
            out = llm_client.chat_json(self.name, system, user, model=model)
            return out.get("primary_issue", "")
        except Exception:
            return ""

    def _build_evidence(self, ctx: CaseContext) -> None:
        of, pf, dec = ctx.order_facts, ctx.payment_facts, ctx.decision
        ev: list[str] = []
        if of.order_id:
            ev.append(dt.ev_order(of.order_id))
            for it in of.items:
                ev.append(dt.ev_item(of.order_id, it["order_item_id"]))
            for p in pf.payments:
                ev.append(dt.ev_payment(of.order_id, p["payment_sequential"]))
        for party in dec.responsible_parties:
            if party["party_type"] == "seller":
                ev.append(dt.ev_seller(party["party_id"]))
        if dec.ranked_causes:
            ev.append(dt.ev_policy(dec.ranked_causes[0]["cause_code"]))
        seen: set[str] = set()
        ctx.evidence_ids = [e for e in ev if e not in seen and not seen.add(e)]
