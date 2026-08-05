"""
Các schema dùng chung giữa các agent (contract handoff) và schema output cuối.

- *Facts: bằng chứng mỗi agent điền vào "bảng đen" (CaseContext).
- CaseContext: bảng đen dùng chung, các agent đọc/ghi rồi handoff.
- CaseOutput: đúng schema đề bài ở README mục 6.

Owner: cả nhóm cùng tuân theo. Sửa contract phải báo cả nhóm.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Bằng chứng từng domain (mỗi agent điền phần của mình)
# ---------------------------------------------------------------------------
@dataclass
class OrderFacts:
    """Do Order & Seller Agent (Phạm Trung Kiên) điền."""
    found: bool = False
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    order_status: Optional[str] = None
    order_purchase_timestamp: Optional[str] = None
    order_approved_at: Optional[str] = None
    order_delivered_carrier_date: Optional[str] = None
    order_delivered_customer_date: Optional[str] = None
    order_estimated_delivery_date: Optional[str] = None
    # mỗi item: {order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value}
    items: list[dict[str, Any]] = field(default_factory=list)
    seller_ids: list[str] = field(default_factory=list)
    # seller_id -> True nếu bàn giao carrier muộn hơn shipping_limit_date
    seller_handoff_late: dict[str, bool] = field(default_factory=dict)


@dataclass
class DeliveryFacts:
    """Do Delivery Agent (Nguyễn Huy Anh) điền."""
    delivered: bool = False
    delivered_customer_date: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    delivered_carrier_date: Optional[str] = None
    # Giao tới KHÁCH muộn hơn ngày dự kiến?
    late_vs_estimate: bool = False
    # Carrier nhận hàng muộn hơn shipping_limit_date (tổng hợp mọi seller)?
    carrier_after_limit: bool = False


@dataclass
class PaymentFacts:
    """Do Payment Agent (Nguyễn Huy Anh) điền."""
    payments: list[dict[str, Any]] = field(default_factory=list)  # {payment_sequential, payment_type, payment_value}
    num_payment_rows: int = 0
    payment_total_brl: float = 0.0
    item_total_brl: float = 0.0
    freight_total_brl: float = 0.0
    # |payment_total - (item_total + freight_total)| <= RECONCILE_TOLERANCE
    reconciled: bool = False


@dataclass
class PolicyDecision:
    """Do Policy Agent (Hoàng Văn Phái) điền."""
    primary_issue: Optional[str] = None
    case_status: Optional[str] = None            # action_required | no_action
    confidence: float = 0.0
    ranked_causes: list[dict[str, Any]] = field(default_factory=list)   # {cause_code, rank}
    responsible_parties: list[dict[str, Any]] = field(default_factory=list)  # {party_type, party_id}
    recommended_refund_brl: float = 0.0
    resolution_actions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Bảng đen dùng chung — trôi qua toàn bộ pipeline
# ---------------------------------------------------------------------------
@dataclass
class CaseContext:
    case_id: str
    claimed_order_id: str
    opened_at: Optional[str] = None
    customer_message: Optional[str] = None
    policy_version: Optional[str] = None

    order_facts: OrderFacts = field(default_factory=OrderFacts)
    delivery_facts: DeliveryFacts = field(default_factory=DeliveryFacts)
    payment_facts: PaymentFacts = field(default_factory=PaymentFacts)
    decision: PolicyDecision = field(default_factory=PolicyDecision)

    evidence_ids: list[str] = field(default_factory=list)
    # cờ để Verifier đánh dấu đã kiểm tra
    verified: bool = False
    notes: list[str] = field(default_factory=list)

    # --- điều khiển Critic-Repair loop (Coordinator/Verifier dùng) ---
    repair_count: int = 0            # số vòng repair đã chạy
    force_deterministic: bool = False  # Verifier bật khi phát hiện mâu thuẫn -> Policy chỉ dùng Path A

    # --- ensemble Policy: ghi lại khi 2 model LLM bất đồng với rule engine ---
    disagreement: Optional[dict] = None


# ---------------------------------------------------------------------------
# Output cuối (đúng README mục 6)
# ---------------------------------------------------------------------------
def build_output(ctx: CaseContext) -> dict[str, Any]:
    """Ráp CaseContext -> dict output đúng schema đề bài (đã cắt theo giới hạn)."""
    of, df, pf, dec = ctx.order_facts, ctx.delivery_facts, ctx.payment_facts, ctx.decision

    def _round(x: float) -> float:
        return round(float(x or 0.0), 2)

    item_ids = [f"{of.order_id}:{it['order_item_id']}" for it in of.items] if of.order_id else []
    payment_ids = [f"{of.order_id}:{p['payment_sequential']}" for p in pf.payments] if of.order_id else []

    return {
        "case_id": ctx.case_id,
        "assessment": {
            "primary_issue": dec.primary_issue,
            "case_status": dec.case_status,
            "confidence": round(float(dec.confidence or 0.0), 2),
        },
        "affected_entities": {
            "order_ids": ([of.order_id] if of.order_id else [])[:5],
            "item_ids": item_ids[:5],
            "seller_ids": of.seller_ids[:5],
            "payment_ids": payment_ids[:5],
        },
        "root_cause_analysis": {
            "ranked_causes": dec.ranked_causes[:3],
            "responsible_parties": dec.responsible_parties[:3],
        },
        "evidence_ids": ctx.evidence_ids[:10],
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": _round(pf.item_total_brl),
            "freight_total_brl": _round(pf.freight_total_brl),
            "payment_total_brl": _round(pf.payment_total_brl),
            "recommended_refund_brl": _round(dec.recommended_refund_brl),
        },
        "resolution_actions": dec.resolution_actions[:5],
    }
