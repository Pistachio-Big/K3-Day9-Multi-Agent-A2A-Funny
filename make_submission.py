"""
Tạo file zip nộp bài — CHỈ chứa output/ (đúng 50 JSON EC_001..EC_050).

Tuân thủ README mục 9:
  - 9.2: zip chỉ chứa folder output/, KHÔNG kèm source code, .env, file audit.
  - Không đưa logging/, src/, data/, .env vào zip.

Cách chạy:
    python make_submission.py            # -> submission.zip
    python make_submission.py my.zip     # đặt tên khác
"""
from __future__ import annotations

import sys
import zipfile

from src import config


def main(argv: list[str]) -> int:
    zip_name = argv[0] if argv else "submission.zip"

    files = sorted(config.OUTPUT_DIR.glob("EC_*.json"))
    expected = {f"EC_{i:03d}.json" for i in range(1, 51)}
    have = {f.name for f in files}

    missing = sorted(expected - have)
    extra = sorted(have - expected)
    if missing:
        print(f"[X] Thiếu {len(missing)} file: {missing[:5]}{'...' if len(missing) > 5 else ''}")
        return 1
    if extra:
        print(f"[X] Có file lạ ngoài EC_001..EC_050: {extra}")
        return 1

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            # arcname không kèm đường dẫn tuyệt đối; đặt phẳng theo yêu cầu chấm
            zf.write(f, arcname=f.name)

    print(f"[OK] {zip_name}: {len(files)} file JSON (EC_001..EC_050). Không kèm source/.env/log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
