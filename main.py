"""
Entrypoint — NHÓM FUNNY, K3 Day 9 Multi-Agent A2A.

Chạy toàn bộ case trong input/, sinh output/<case>.json, ghi trace + metadata.

Cách chạy:
    python -m venv .venv && .venv\\Scripts\\activate   (Windows)
    pip install -r requirements.txt
    python main.py                 # chạy tất cả input
    python main.py EC_001          # chạy 1 case để debug

Scaffold chạy được khi USE_LLM=0 (không cần API key) để test pipeline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src import config
from src.agents.coordinator import Coordinator
from src.tracing import Tracer


def load_case(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str]) -> int:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    input_files = sorted(config.INPUT_DIR.glob("EC_*.json"))
    if argv:  # lọc theo case_id truyền vào
        wanted = set(argv)
        input_files = [p for p in input_files if p.stem in wanted]

    if not input_files:
        print(f"[!] Không thấy input EC_*.json trong {config.INPUT_DIR}")
        print("    Đưa các file EC_001.json..EC_050.json vào input/ rồi chạy lại.")
        return 1

    tracer = Tracer()
    coord = Coordinator(tracer)

    n = 0
    for path in input_files:
        case = load_case(path)
        output = coord.run_case(case)
        out_path = config.OUTPUT_DIR / f"{case['case_id']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        n += 1
        print(f"[ok] {case['case_id']:8} -> {output['assessment']['primary_issue']:24} "
              f"refund={output['financial_resolution']['recommended_refund_brl']}")

    tracer.flush()
    tracer.write_metadata(num_cases=n)
    print(f"\nXong {n} case. Output: {config.OUTPUT_DIR} | trace+metadata: {config.LOG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
