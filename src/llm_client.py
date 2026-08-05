"""
Client LLM dùng chung (OpenAI-compatible) cho cả Groq và OpenRouter.

- Bật/tắt bằng USE_LLM trong .env. Khi tắt (mặc định), pipeline vẫn chạy nhờ
  logic deterministic của mỗi agent -> test được plumbing mà không cần key.
- Model lấy từ config.AGENT_MODELS (khai báo trong code, <=10B).

Owner: Coordinator (Nguyễn Văn Đại). Các agent gọi `chat(...)` khi cần suy luận.
"""
from __future__ import annotations

import json
from typing import Optional

from . import config

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI  # import trễ để scaffold chạy khi chưa cài openai
        if not config.API_KEY:
            raise RuntimeError(
                "Thiếu API key. Điền GROQ_API_KEY/OPENROUTER_API_KEY vào .env "
                "hoặc đặt USE_LLM=0 để chạy deterministic."
            )
        _client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY)
    return _client


def chat(
    agent_name: str,
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    temperature: Optional[float] = None,
) -> str:
    """Gọi LLM cho 1 agent. Trả về text (hoặc JSON string nếu json_mode)."""
    model = config.AGENT_MODELS.get(agent_name, next(iter(config.AGENT_MODELS.values())))
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
        "max_tokens": config.LLM_MAX_TOKENS,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _get_client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(agent_name: str, system: str, user: str) -> dict:
    """Như chat() nhưng parse JSON, lỗi thì trả {}."""
    try:
        return json.loads(chat(agent_name, system, user, json_mode=True))
    except (json.JSONDecodeError, Exception):
        return {}
