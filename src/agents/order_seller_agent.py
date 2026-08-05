"""
Order & Seller Agent.

Nhiệm vụ: từ claimed_order_id, tra order + item + seller, xác định:
  - order_status, các mốc thời gian của đơn
  - danh sách item (order_item_id, product_id, seller_id, shipping_limit_date, price, freight)
  - seller nào bàn giao carrier MUỘN hơn shipping_limit_date của item thuộc seller đó
Sau đó handoff sang Delivery Agent.

Owner: Phạm Trung Kiên.

TODO(Kiên):
  - [baseline đã có] lookup + tính seller_handoff_late.
  - Cân nhắc dùng LLM (llm_client.chat) để diễn giải trường hợp nhiều seller/biên.
  - Xử lý order không có item row (items rỗng) — đã để nhánh cơ bản.
"""
from __future__ import annotations

from ..a2a.base_agent import BaseAgent
from ..a2a.message import A2AMessage
from ..schemas import CaseContext
from .. import data_tools as dt


class OrderSellerAgent(BaseAgent):
    name = "order_seller_agent"

    def process(self, msg: A2AMessage, ctx: CaseContext) -> list[A2AMessage]:
        of = ctx.order_facts
        order = dt.STORE.get_order(ctx.claimed_order_id)

        if order is None:
            of.found = False
            ctx.notes.append("order_not_found")
            # vẫn handoff để pipeline hoàn tất, các agent sau xử lý rỗng
            return [self.emit("delivery_agent", "facts_ready", ctx, found=False)]

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

        # seller bàn giao muộn? carrier_date > shipping_limit_date của item seller đó
        carrier_dt = dt.parse_dt(of.order_delivered_carrier_date)
        for it in of.items:
            limit_dt = dt.parse_dt(it["shipping_limit_date"])
            late = bool(carrier_dt and limit_dt and carrier_dt > limit_dt)
            if late:
                of.seller_handoff_late[it["seller_id"]] = True
            else:
                of.seller_handoff_late.setdefault(it["seller_id"], False)

        return [self.emit("delivery_agent", "facts_ready", ctx, found=True,
                          order_status=of.order_status, num_items=len(of.items))]
