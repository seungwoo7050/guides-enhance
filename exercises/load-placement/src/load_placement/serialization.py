from __future__ import annotations

import hashlib
import json
from typing import Any


# [Implementation 8]
# Stable placement result digest
# 같은 서버 snapshot과 요청 목록이 같은 배치 결과 digest를 만들게 합니다.
def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
