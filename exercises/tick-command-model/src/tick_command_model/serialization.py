from __future__ import annotations

import hashlib
import json
from typing import Any


# [Implementation 7]
# Stable JSON result digest
# key 순서와 공백 표현을 고정해 같은 결과가 항상 같은 digest를 만들게 합니다.
def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_result(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
