"""
BaseAgent — lớp cha cho mọi agent.

Contract (kiến trúc mới, Coordinator điều phối):
  - name: định danh agent (khớp key trong config.AGENT_MODELS).
  - process(ctx, inbox) -> A2AMessage: đọc/ghi bảng đen `ctx`, làm phần việc của mình,
    trả về 1 A2AMessage kết quả (để Coordinator ghi trace & định tuyến bước kế).

Coordinator là bên định tuyến (fan-out song song + repair loop), agent chỉ báo kết quả
qua `result(...)`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..schemas import CaseContext
from .message import A2AMessage


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def process(self, ctx: CaseContext) -> list[A2AMessage]:
        ...

    def emit(self, recipient: str, intent: str, ctx: CaseContext, **payload) -> A2AMessage:
        """Tạo message kết quả gửi về Coordinator (hoặc gợi ý bước kế)."""
        return A2AMessage(
            sender=self.name,
            recipient=recipient,
            intent=intent,
            case_id=ctx.case_id,
            payload=payload,
        )
