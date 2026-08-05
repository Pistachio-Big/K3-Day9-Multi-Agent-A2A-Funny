"""
Coordinator Agent — điều phối & tổng hợp.

- Đăng ký các agent, khởi tạo bảng đen CaseContext từ input JSON.
- Chạy vòng lặp định tuyến A2A: message được chuyển giữa các agent theo `recipient`,
  mỗi bước được Tracer ghi lại (chứng minh handoff thật).
- Khi nhận message intent="final", ráp output bằng schemas.build_output.

Luồng: order_seller -> delivery -> payment -> policy -> verifier -> coordinator(final)

Owner: Nguyễn Văn Đại (Team Lead).

TODO(Đại):
  - [baseline đã có] routing loop + tổng hợp.
  - Có thể thêm bước Coordinator dùng LLM để rà soát chéo trước khi chốt.
"""
from __future__ import annotations

from typing import Any

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext, build_output
from ..tracing import Tracer

from .order_seller_agent import OrderSellerAgent
from .delivery_agent import DeliveryAgent
from .payment_agent import PaymentAgent
from .policy_agent import PolicyAgent
from .verifier_agent import VerifierAgent

MAX_HOPS = 50  # chặn vòng lặp vô hạn


class Coordinator:
    name = "coordinator"

    def __init__(self, tracer: Tracer) -> None:
        self.tracer = tracer
        agents: list[BaseAgent] = [
            OrderSellerAgent(),
            DeliveryAgent(),
            PaymentAgent(),
            PolicyAgent(),
            VerifierAgent(),
        ]
        self.registry: dict[str, BaseAgent] = {a.name: a for a in agents}

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        ctx = CaseContext(
            case_id=case["case_id"],
            claimed_order_id=case.get("customer_request", {}).get("claimed_order_id", ""),
            opened_at=case.get("opened_at"),
            customer_message=case.get("customer_request", {}).get("message"),
            policy_version=case.get("policy_version"),
        )

        # seed: Coordinator giao việc cho Order&Seller Agent
        queue: list[A2AMessage] = [
            A2AMessage(self.name, "order_seller_agent", "investigate", ctx.case_id,
                       {"claimed_order_id": ctx.claimed_order_id})
        ]

        hops = 0
        while queue and hops < MAX_HOPS:
            hops += 1
            msg = queue.pop(0)
            self.tracer.log(msg.case_id, msg.sender, msg.recipient, msg.intent, msg.payload)

            if msg.recipient == self.name:  # đã quay về coordinator -> kết thúc
                break

            agent = self.registry.get(msg.recipient)
            if agent is None:
                ctx.notes.append(f"unknown_recipient:{msg.recipient}")
                break
            queue.extend(agent.process(msg, ctx))

        output = build_output(ctx)
        self.tracer.log(ctx.case_id, self.name, "output", "assembled",
                        {"primary_issue": output["assessment"]["primary_issue"],
                         "case_status": output["assessment"]["case_status"],
                         "refund": output["financial_resolution"]["recommended_refund_brl"]})
        return output
