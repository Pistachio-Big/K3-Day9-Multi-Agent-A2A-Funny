"""
Coordinator Agent — điều phối theo kiến trúc "fan-out + critic-repair".

Luồng:
  1. order_seller_agent      : lấy facts đơn/item/seller (phải chạy trước).
  2. delivery ∥ payment      : FAN-OUT song song (đọc order_facts, ghi slot riêng -> an toàn).
  3. policy_agent            : dual-path adjudication.
  4. verifier_agent          : validate + cross-check; nếu 'repair' -> quay lại policy (tối đa 2 vòng).
  5. assemble output.

Mọi bước handoff (kể cả repair) được Tracer ghi vào logging/trace.jsonl -> chứng minh A2A thật.

Owner: Nguyễn Văn Đại (Team Lead).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..a2a.message import A2AMessage
from ..schemas import CaseContext, build_output
from ..tracing import Tracer

from .order_seller_agent import OrderSellerAgent
from .delivery_agent import DeliveryAgent
from .payment_agent import PaymentAgent
from .policy_agent import PolicyAgent
from .verifier_agent import VerifierAgent

MAX_ADJUDICATION_ROUNDS = 3  # 1 lần đầu + tối đa 2 vòng repair


class Coordinator:
    name = "coordinator"

    def __init__(self, tracer: Tracer) -> None:
        self.tracer = tracer
        self.order_seller = OrderSellerAgent()
        self.delivery = DeliveryAgent()
        self.payment = PaymentAgent()
        self.policy = PolicyAgent()
        self.verifier = VerifierAgent()

    def _log(self, ctx: CaseContext, sender: str, recipient: str, intent: str,
             payload: dict[str, Any] | None = None) -> None:
        self.tracer.log(ctx.case_id, sender, recipient, intent, payload or {})

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        ctx = CaseContext(
            case_id=case["case_id"],
            claimed_order_id=case.get("customer_request", {}).get("claimed_order_id", ""),
            opened_at=case.get("opened_at"),
            customer_message=case.get("customer_request", {}).get("message"),
            policy_version=case.get("policy_version"),
        )

        # 1) Order & Seller ---------------------------------------------------
        self._log(ctx, self.name, "order_seller_agent", "investigate",
                  {"claimed_order_id": ctx.claimed_order_id})
        msgs = self.order_seller.process(ctx)
        for m in msgs:
            self._log(ctx, m.sender, m.recipient, m.intent, m.payload)

        # 2) FAN-OUT song song: Delivery ∥ Payment ----------------------------
        self._log(ctx, self.name, "delivery_agent", "dispatch")
        self._log(ctx, self.name, "payment_agent", "dispatch")
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_del = ex.submit(self.delivery.process, ctx)
            f_pay = ex.submit(self.payment.process, ctx)
            msgs_del = f_del.result()
            msgs_pay = f_pay.result()
        for m in msgs_del:
            self._log(ctx, m.sender, m.recipient, m.intent, m.payload)
        for m in msgs_pay:
            self._log(ctx, m.sender, m.recipient, m.intent, m.payload)

        # 3-4) Policy adjudication + Critic-Repair loop ------------------------
        for _ in range(MAX_ADJUDICATION_ROUNDS):
            self._log(ctx, self.name, "policy_agent", "adjudicate")
            msgs_pol = self.policy.process(ctx)
            for m in msgs_pol:
                self._log(ctx, m.sender, m.recipient, m.intent, m.payload)

            self._log(ctx, self.name, "verifier_agent", "verify")
            msgs_ver = self.verifier.process(ctx)
            for m in msgs_ver:
                self._log(ctx, m.sender, m.recipient, m.intent, m.payload)

            # Lấy intent từ message đầu tiên của verifier
            if msgs_ver and msgs_ver[0].intent == "final":
                break
            # intent == "repair": quay lại policy (đã bật force_deterministic trong ctx)

        # 5) Assemble ---------------------------------------------------------
        output = build_output(ctx)
        self._log(ctx, self.name, "output", "assembled",
                  {"primary_issue": output["assessment"]["primary_issue"],
                   "case_status": output["assessment"]["case_status"],
                   "refund": output["financial_resolution"]["recommended_refund_brl"]})
        return output
