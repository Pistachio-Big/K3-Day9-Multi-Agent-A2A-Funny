"""
A2A message envelope — đơn vị "handoff" giữa các agent.

Mỗi agent nhận 1 A2AMessage, xử lý, rồi trả về danh sách A2AMessage gửi cho
agent kế tiếp. Coordinator định tuyến theo `recipient`. Toàn bộ message được
Tracer ghi lại -> chứng minh có handoff thật (không nhồi 1 prompt).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class A2AMessage:
    sender: str          # tên agent gửi
    recipient: str       # tên agent nhận
    intent: str          # vd: "investigate", "facts_ready", "decision_ready", "final"
    case_id: str
    payload: dict[str, Any] = field(default_factory=dict)
