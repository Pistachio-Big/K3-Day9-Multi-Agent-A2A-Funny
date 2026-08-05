"""
Cấu hình chung của hệ thống.

QUY ĐỊNH ĐỀ BÀI:
  - Mỗi agent chỉ dùng model <= 10B tham số.
  - Tên model KHÔNG để trong .env; phải khai báo trong code (file này) và
    ghi lại vào logging/metadata.json.
  - API key / secret để trong .env, KHÔNG commit.

Owner: Coordinator (Nguyễn Văn Đại) — chốt model & provider cho cả nhóm.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Đường dẫn gốc
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logging"

load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# Provider (Groq / OpenRouter) — cả hai đều OpenAI-compatible
# ---------------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
USE_LLM = os.getenv("USE_LLM", "0") == "1"

_PROVIDER_BASE_URL = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
_PROVIDER_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

BASE_URL = _PROVIDER_BASE_URL.get(LLM_PROVIDER, _PROVIDER_BASE_URL["groq"])
API_KEY = os.getenv(_PROVIDER_KEY_ENV.get(LLM_PROVIDER, "GROQ_API_KEY"), "")

# ---------------------------------------------------------------------------
# Model cho từng agent (đều <= 10B). KHAI BÁO TRONG CODE (bắt buộc).
# Đổi tên model tuỳ provider:
#   Groq       : "llama-3.1-8b-instant"
#   OpenRouter : "meta-llama/llama-3.1-8b-instruct"
# ---------------------------------------------------------------------------
_DEFAULT_MODEL = {
    "groq": "llama-3.1-8b-instant",
    "openrouter": "meta-llama/llama-3.1-8b-instruct",
}[LLM_PROVIDER if LLM_PROVIDER in ("groq", "openrouter") else "groq"]

AGENT_MODELS = {
    "coordinator": _DEFAULT_MODEL,
    "order_seller_agent": _DEFAULT_MODEL,
    "delivery_agent": _DEFAULT_MODEL,
    "payment_agent": _DEFAULT_MODEL,
    "policy_agent": _DEFAULT_MODEL,
    "verifier_agent": _DEFAULT_MODEL,
}

# Tham số suy luận mặc định — muốn quyết định ổn định nên để nhiệt độ thấp.
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 1024

# ---------------------------------------------------------------------------
# Chính sách nghiệp vụ
# ---------------------------------------------------------------------------
POLICY_VERSION = "EC_POLICY_V1"
CURRENCY = "BRL"
RECONCILE_TOLERANCE = 0.10  # sai số cho phép khi đối soát payment vs item+freight (BRL)
