"""
Delivery Agent.

Nhiệm vụ: so sánh thời điểm giao thực tế với hạn giao.
  - late_vs_estimate: order_delivered_customer_date > order_estimated_delivery_date
  - carrier_after_limit: có seller nào carrier nhận hàng muộn hơn shipping_limit_date
    (tổng hợp từ order_facts.seller_handoff_late do Order&Seller Agent tính).
Trả kết quả về Coordinator.

Owner: Nguyễn Huy Anh.

Thay đổi so với baseline:
  - Đơn CHƯA giao (delivered_customer_date rỗng) -> delivered=False, late_vs_estimate=False
    (không thể kết luận trễ), ghi note 'not_delivered_yet'. Tránh gán nhầm late_delivery.
"""
from __future__ import annotations

from typing import Optional

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt


class DeliveryAgent(BaseAgent):
    name = "delivery_agent"

    def process(self, ctx: CaseContext, inbox: Optional[A2AMessage] = None) -> A2AMessage:
        of, df = ctx.order_facts, ctx.delivery_facts

        df.delivered_customer_date = of.order_delivered_customer_date
        df.estimated_delivery_date = of.order_estimated_delivery_date
        df.delivered_carrier_date = of.order_delivered_carrier_date

        delivered_dt = dt.parse_dt(of.order_delivered_customer_date)
        estimated_dt = dt.parse_dt(of.order_estimated_delivery_date)

        df.delivered = delivered_dt is not None
        if not df.delivered:
            ctx.notes.append("not_delivered_yet")

        # Chỉ kết luận trễ khi ĐÃ giao và có mốc dự kiến.
        df.late_vs_estimate = bool(delivered_dt and estimated_dt and delivered_dt > estimated_dt)

        # carrier nhận hàng muộn hơn shipping_limit_date (bất kỳ seller nào)
        df.carrier_after_limit = any(of.seller_handoff_late.values())

        return [self.emit("coordinator", "facts_ready", ctx,
                           delivered=df.delivered,
                           late_vs_estimate=df.late_vs_estimate,
                           carrier_after_limit=df.carrier_after_limit)]
