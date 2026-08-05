"""
Observability: ghi trace A2A và metadata.

- trace.jsonl: mỗi dòng 1 message/handoff/decision. GHI ĐÈ mỗi lần chạy
  (đề bài: "không append, chỉ cần lượt chạy mới nhất").
- metadata.json: model, param size, framework, runtime.

Owner: Hà Tấn Phong (Verifier & Observability).
"""
from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from typing import Any

from . import config


class Tracer:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self._t0 = time.time()

    def log(self, case_id: str, sender: str, recipient: str, msg_type: str, payload: dict) -> None:
        self.records.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "sender": sender,
            "recipient": recipient,
            "type": msg_type,
            "payload": payload,
        })

    def flush(self) -> None:
        """Ghi đè trace.jsonl bằng toàn bộ record của lượt chạy hiện tại."""
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = config.LOG_DIR / "trace.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def write_metadata(self, num_cases: int, framework: str = "custom-a2a") -> None:
        meta = {
            "team": "FUNNY",
            "framework": framework,
            "provider": config.LLM_PROVIDER,
            "use_llm": config.USE_LLM,
            "agent_models": config.AGENT_MODELS,
            "parameter_size_constraint": "<=10B per agent",
            "policy_version": config.POLICY_VERSION,
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "num_cases": num_cases,
            "elapsed_seconds": round(time.time() - self._t0, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.LOG_DIR / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
