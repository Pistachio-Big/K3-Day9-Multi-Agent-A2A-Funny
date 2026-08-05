"""
Delivery Agent.

Nhiệm vụ: so sánh thời điểm giao thực tế với hạn giao.
  - late_vs_estimate: order_delivered_customer_date > order_estimated_delivery_date
  - carrier_after_limit: có seller nào carrier nhận hàng muộn hơn shipping_limit_date
    (tổng hợp từ order_facts.seller_handoff_late do Order&Seller Agent tính).
Sau đó handoff sang Payment Agent.

Owner: Nguyễn Huy Anh.

TODO(Huy Anh):
  - [baseline đã có] so sánh 2 mốc thời gian.
  - Bổ sung xử lý đơn chưa giao (delivered_customer_date rỗng) nếu bộ case có.
  - Có thể dùng LLM để tóm tắt lý do trễ vào ctx.notes.
"""
from __future__ import annotations

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt


class DeliveryAgent(BaseAgent):
    name = "delivery_agent"

    def process(self, msg: A2AMessage, ctx: CaseContext) -> list[A2AMessage]:
        of, df = ctx.order_facts, ctx.delivery_facts

        df.delivered_customer_date = of.order_delivered_customer_date
        df.estimated_delivery_date = of.order_estimated_delivery_date
        df.delivered_carrier_date = of.order_delivered_carrier_date

        delivered_dt = dt.parse_dt(of.order_delivered_customer_date)
        estimated_dt = dt.parse_dt(of.order_estimated_delivery_date)

        df.delivered = delivered_dt is not None
        df.late_vs_estimate = bool(delivered_dt and estimated_dt and delivered_dt > estimated_dt)

        # carrier nhận hàng muộn hơn shipping_limit_date (bất kỳ seller nào)
        df.carrier_after_limit = any(of.seller_handoff_late.values())

        return [self.emit("payment_agent", "facts_ready", ctx,
                          late_vs_estimate=df.late_vs_estimate,
                          carrier_after_limit=df.carrier_after_limit)]
