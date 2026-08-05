"""
BaseAgent — lớp cha cho mọi agent.

Contract:
  - name: định danh agent (khớp key trong config.AGENT_MODELS).
  - process(msg, ctx) -> list[A2AMessage]: đọc bảng đen `ctx`, làm phần việc của
    mình, ghi bằng chứng vào `ctx`, rồi trả về message handoff cho agent kế.

Mỗi agent con override `process`. Dùng self.emit(...) để tạo message handoff.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import CaseContext
from .message import A2AMessage


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def process(self, msg: A2AMessage, ctx: CaseContext) -> list[A2AMessage]:
        ...

    def emit(self, recipient: str, intent: str, ctx: CaseContext, **payload) -> A2AMessage:
        return A2AMessage(
            sender=self.name,
            recipient=recipient,
            intent=intent,
            case_id=ctx.case_id,
            payload=payload,
        )
