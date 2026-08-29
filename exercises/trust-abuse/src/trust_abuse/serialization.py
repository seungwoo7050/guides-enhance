from __future__ import annotations

import hashlib
import json
from typing import Any


# [Implementation 11]
# Stable authoritative-state digest
# audit와 상태 결과를 정규화한 JSON으로 직렬화해 digest를 계산합니다.
def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_size(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
