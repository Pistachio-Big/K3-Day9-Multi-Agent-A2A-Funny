"""
Data layer — "tools" mà các agent gọi để tra cứu 9 CSV Olist.

Đây là nền dùng chung: load CSV (cache), lookup theo order_id/seller_id, và các
helper dựng evidence ID + parse timestamp.

Owner: Phạm Trung Kiên (Data & Order/Seller). Các agent khác CHỈ gọi hàm ở đây,
không tự đọc CSV để tránh lệch cách join.
"""
from __future__ import annotations

import functools
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Load CSV có cache. geolocation nặng (59MB) nên chỉ load khi cần.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _load(name: str) -> pd.DataFrame:
    path = config.DATA_DIR / name
    return pd.read_csv(path, dtype=str, keep_default_na=False)


class DataStore:
    """Bọc các bảng + index theo khoá để lookup O(1)."""

    def __init__(self) -> None:
        self._orders_by_id: Optional[dict[str, dict]] = None
        self._items_by_order: Optional[dict[str, list[dict]]] = None
        self._payments_by_order: Optional[dict[str, list[dict]]] = None
        self._sellers_by_id: Optional[dict[str, dict]] = None

    # ---- lazy indexes -----------------------------------------------------
    @property
    def orders_by_id(self) -> dict[str, dict]:
        if self._orders_by_id is None:
            df = _load("olist_orders_dataset.csv")
            self._orders_by_id = {r["order_id"]: r for r in df.to_dict("records")}
        return self._orders_by_id

    @property
    def items_by_order(self) -> dict[str, list[dict]]:
        if self._items_by_order is None:
            df = _load("olist_order_items_dataset.csv")
            idx: dict[str, list[dict]] = {}
            for r in df.to_dict("records"):
                idx.setdefault(r["order_id"], []).append(r)
            self._items_by_order = idx
        return self._items_by_order

    @property
    def payments_by_order(self) -> dict[str, list[dict]]:
        if self._payments_by_order is None:
            df = _load("olist_order_payments_dataset.csv")
            idx: dict[str, list[dict]] = {}
            for r in df.to_dict("records"):
                idx.setdefault(r["order_id"], []).append(r)
            self._payments_by_order = idx
        return self._payments_by_order

    @property
    def sellers_by_id(self) -> dict[str, dict]:
        if self._sellers_by_id is None:
            df = _load("olist_sellers_dataset.csv")
            self._sellers_by_id = {r["seller_id"]: r for r in df.to_dict("records")}
        return self._sellers_by_id

    # ---- lookup API -------------------------------------------------------
    def get_order(self, order_id: str) -> Optional[dict]:
        return self.orders_by_id.get(order_id)

    def get_items(self, order_id: str) -> list[dict]:
        return self.items_by_order.get(order_id, [])

    def get_payments(self, order_id: str) -> list[dict]:
        return self.payments_by_order.get(order_id, [])

    def get_seller(self, seller_id: str) -> Optional[dict]:
        return self.sellers_by_id.get(seller_id)


# instance dùng chung
STORE = DataStore()


# ---------------------------------------------------------------------------
# Helpers: tiền, thời gian
# ---------------------------------------------------------------------------
def to_float(x: Any) -> float:
    try:
        if x is None or x == "":
            return 0.0
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def parse_dt(x: Any) -> Optional[datetime]:
    """Parse timestamp Olist ('YYYY-MM-DD HH:MM:SS' hoặc 'YYYY-MM-DD'). Rỗng -> None."""
    if not x or str(x).strip() == "":
        return None
    s = str(x).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def item_total(items: list[dict]) -> float:
    return round(sum(to_float(it.get("price")) for it in items), 2)


def freight_total(items: list[dict]) -> float:
    return round(sum(to_float(it.get("freight_value")) for it in items), 2)


def payment_total(payments: list[dict]) -> float:
    return round(sum(to_float(p.get("payment_value")) for p in payments), 2)


# ---------------------------------------------------------------------------
# Evidence ID builders — CHỈ dựng ID có thật trong CSV (README mục 5)
# ---------------------------------------------------------------------------
def ev_order(order_id: str) -> str:
    return f"order:{order_id}"


def ev_item(order_id: str, order_item_id: str) -> str:
    return f"item:{order_id}:{order_item_id}"


def ev_payment(order_id: str, payment_sequential: str) -> str:
    return f"payment:{order_id}:{payment_sequential}"


def ev_seller(seller_id: str) -> str:
    return f"seller:{seller_id}"


def ev_policy(root_cause_code: str) -> str:
    return f"policy:{root_cause_code}"
