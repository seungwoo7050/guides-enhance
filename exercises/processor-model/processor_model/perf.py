"""CPU 실행 시간, Amdahl의 법칙과 AMAT를 계산합니다."""

from __future__ import annotations

from typing import Any


# [Implementation 3] 성능식 계산
# CPU 시간, Amdahl과 AMAT는 입력 범위를 먼저 검사합니다.
# 반환값에는 계산에 사용한 입력과 결과를 함께 넣습니다.
def cpu_time(instructions: float, cpi: float, frequency_ghz: float) -> dict[str, Any]:
    if instructions < 0:
        raise ValueError("명령 수는 음수일 수 없습니다")
    if cpi <= 0:
        raise ValueError("CPI는 0보다 커야 합니다")
    if frequency_ghz <= 0:
        raise ValueError("주파수는 0GHz보다 커야 합니다")
    cycles = instructions * cpi
    seconds = cycles / (frequency_ghz * 1_000_000_000.0)
    return {
        "instructions": instructions,
        "cpi": cpi,
        "frequency_ghz": frequency_ghz,
        "cycles": cycles,
        "seconds": seconds,
    }


def amdahl(fraction: float, enhanced_speedup: float) -> dict[str, Any]:
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("개선 비율은 0 이상 1 이하여야 합니다")
    if enhanced_speedup <= 0:
        raise ValueError("개선 구간의 속도 향상률은 0보다 커야 합니다")
    total = (1.0 - fraction) + fraction / enhanced_speedup
    speedup = 1.0 / total
    limit = None if fraction == 1.0 else 1.0 / (1.0 - fraction)
    return {
        "enhanced_fraction": fraction,
        "enhanced_part_speedup": enhanced_speedup,
        "normalized_time": total,
        "overall_speedup": speedup,
        "infinite_enhancement_limit": limit,
    }


def amat(hit_time: float, miss_rate: float, miss_penalty: float) -> dict[str, Any]:
    if hit_time < 0 or miss_penalty < 0:
        raise ValueError("시간 값은 음수일 수 없습니다")
    if not 0.0 <= miss_rate <= 1.0:
        raise ValueError("실패율은 0 이상 1 이하여야 합니다")
    value = hit_time + miss_rate * miss_penalty
    return {
        "hit_time": hit_time,
        "miss_rate": miss_rate,
        "miss_penalty": miss_penalty,
        "amat": value,
    }
