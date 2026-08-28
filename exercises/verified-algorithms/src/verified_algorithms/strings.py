"""String-search algorithms."""

from __future__ import annotations


# [Implementation 12]
# KMP prefix fallback
def kmp_find(text: str, pattern: str) -> int:
    """Return the first match position, or ``-1`` when no match exists."""
    if pattern == "":
        return 0

    prefix = [0] * len(pattern)
    matched = 0
    for index in range(1, len(pattern)):
        while matched > 0 and pattern[index] != pattern[matched]:
            matched = prefix[matched - 1]
        if pattern[index] == pattern[matched]:
            matched += 1
        prefix[index] = matched

    matched = 0
    for index, character in enumerate(text):
        # 이미 계산한 proper prefix 길이로 이동하므로 확인한 본문을 처음부터 다시 읽지 않습니다.
        while matched > 0 and character != pattern[matched]:
            matched = prefix[matched - 1]
        if character == pattern[matched]:
            matched += 1
        if matched == len(pattern):
            return index - len(pattern) + 1
    return -1
