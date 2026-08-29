from __future__ import annotations

import hashlib
import json
from typing import Any


# [Implementation 8]
# Stable lifecycle trace digest
# 같은 이벤트 목록이 같은 상태 trace와 digest를 만들도록 JSON 표현을 고정합니다.
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
