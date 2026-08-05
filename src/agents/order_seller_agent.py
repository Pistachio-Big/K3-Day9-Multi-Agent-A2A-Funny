"""
Order & Seller Agent.

Nhiệm vụ: từ claimed_order_id, tra order + item + seller, xác định:
  - order_status, các mốc thời gian của đơn
  - danh sách item (order_item_id, product_id, seller_id, shipping_limit_date, price, freight)
  - seller nào bàn giao carrier MUỘN hơn shipping_limit_date của item thuộc seller đó
Trả kết quả về Coordinator (Coordinator fan-out tiếp Delivery ∥ Payment).

Owner: Phạm Trung Kiên.

Thay đổi so với baseline:
  - Nếu order không có -> found=False, ghi note, pipeline vẫn hoàn tất (không crash).
  - Nếu THIẾU order_delivered_carrier_date -> KHÔNG kết luận seller trễ (seller_handoff_late=False)
    và ghi note 'carrier_date_missing' (không đủ bằng chứng để đổ lỗi seller).
  - seller_ids duy nhất, giữ thứ tự xuất hiện.
"""
from __future__ import annotations

from typing import Optional

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt


class OrderSellerAgent(BaseAgent):
    name = "order_seller_agent"

    def process(self, ctx: CaseContext, inbox: Optional[A2AMessage] = None) -> A2AMessage:
        of = ctx.order_facts
        order = dt.STORE.get_order(ctx.claimed_order_id)

        if order is None:
            of.found = False
            ctx.notes.append("order_not_found")
            return self.result("coordinator", "facts_ready", ctx, found=False)

        of.found = True
        of.order_id = order["order_id"]
        of.customer_id = order.get("customer_id")
        of.order_status = order.get("order_status")
        of.order_purchase_timestamp = order.get("order_purchase_timestamp")
        of.order_approved_at = order.get("order_approved_at")
        of.order_delivered_carrier_date = order.get("order_delivered_carrier_date")
        of.order_delivered_customer_date = order.get("order_delivered_customer_date")
        of.order_estimated_delivery_date = order.get("order_estimated_delivery_date")

        items = dt.STORE.get_items(of.order_id)
        of.items = [
            {
                "order_item_id": it["order_item_id"],
                "product_id": it["product_id"],
                "seller_id": it["seller_id"],
                "shipping_limit_date": it["shipping_limit_date"],
                "price": dt.to_float(it["price"]),
                "freight_value": dt.to_float(it["freight_value"]),
            }
            for it in items
        ]
        # seller_ids duy nhất, giữ thứ tự
        seen: set[str] = set()
        of.seller_ids = [s for it in of.items if (s := it["seller_id"]) not in seen and not seen.add(s)]

        # seller bàn giao muộn? carrier_date > shipping_limit_date của item seller đó.
        # Thiếu carrier_date -> không đủ bằng chứng -> KHÔNG đổ lỗi seller.
        carrier_dt = dt.parse_dt(of.order_delivered_carrier_date)
        if carrier_dt is None and of.items:
            ctx.notes.append("carrier_date_missing")
        for it in of.items:
            limit_dt = dt.parse_dt(it["shipping_limit_date"])
            late = bool(carrier_dt and limit_dt and carrier_dt > limit_dt)
            of.seller_handoff_late[it["seller_id"]] = of.seller_handoff_late.get(it["seller_id"], False) or late

        if not of.items:
            ctx.notes.append("order_has_no_item_row")

        return self.result("coordinator", "facts_ready", ctx,
                           found=True, order_status=of.order_status, num_items=len(of.items))
