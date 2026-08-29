from __future__ import annotations

import hashlib
import json
from typing import Any


# [Implementation 8]
# Stable convergence digest
# key 순서와 숫자 표현을 고정해 같은 replica 상태가 같은 digest를 만들게 합니다.
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
