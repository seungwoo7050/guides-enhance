"""고정 폭 정수와 IEEE 754 표현을 계산합니다."""

from __future__ import annotations

import math
import struct
from typing import Any


# [Implementation 1] 고정 폭 비트 해석
# 모든 변환이 같은 하위 비트를 사용하도록 폭을 먼저 검증합니다.
def _validate_width(width: int) -> None:
    if width < 1 or width > 64:
        raise ValueError("비트 폭은 1 이상 64 이하여야 합니다")


def mask(width: int) -> int:
    _validate_width(width)
    return (1 << width) - 1


def to_unsigned(value: int, width: int) -> int:
    """지정한 폭의 하위 비트만 남기고 부호 없는 정수로 해석합니다."""

    return value & mask(width)


def to_signed(value: int, width: int) -> int:
    """지정한 폭의 하위 비트를 2의 보수 정수로 해석합니다."""

    unsigned = to_unsigned(value, width)
    sign_bit = 1 << (width - 1)
    return unsigned - (1 << width) if unsigned & sign_bit else unsigned


def represent_integer(value: int, width: int) -> dict[str, Any]:
    _validate_width(width)
    unsigned = to_unsigned(value, width)
    byte_count = (width + 7) // 8
    raw = unsigned.to_bytes(byte_count, byteorder="big", signed=False)
    return {
        "input": value,
        "width": width,
        "unsigned": unsigned,
        "signed": to_signed(unsigned, width),
        "binary": format(unsigned, f"0{width}b"),
        "hex": f"0x{unsigned:0{(width + 3) // 4}x}",
        "big_endian_bytes": [f"0x{byte:02x}" for byte in raw],
        "little_endian_bytes": [f"0x{byte:02x}" for byte in reversed(raw)],
        "truncated": value != unsigned and value != to_signed(unsigned, width),
    }


# [Implementation 1-1] 고정 폭 덧셈의 상태값
# 자리올림과 부호 없는·부호 있는 오버플로는
# 판정 조건이 다르므로 따로 계산합니다.
def add_fixed(left: int, right: int, width: int) -> dict[str, Any]:
    """고정 폭 덧셈 결과와 각 오버플로 판정값을 반환합니다."""

    _validate_width(width)
    left_u = to_unsigned(left, width)
    right_u = to_unsigned(right, width)
    full = left_u + right_u
    result_u = to_unsigned(full, width)
    left_s = to_signed(left_u, width)
    right_s = to_signed(right_u, width)
    result_s = to_signed(result_u, width)
    signed_overflow = (
        (left_s >= 0 and right_s >= 0 and result_s < 0)
        or (left_s < 0 and right_s < 0 and result_s >= 0)
    )
    return {
        "width": width,
        "left_unsigned": left_u,
        "right_unsigned": right_u,
        "result_unsigned": result_u,
        "left_signed": left_s,
        "right_signed": right_s,
        "result_signed": result_s,
        "carry_out": full > mask(width),
        "unsigned_overflow": full > mask(width),
        "signed_overflow": signed_overflow,
        "binary": format(result_u, f"0{width}b"),
    }


# [Implementation 1-2] IEEE 754 필드 분해
# f32 또는 f64로 반올림한 비트 패턴을 분해한 뒤 특수 지숫값을 분류합니다.
def _float_fields(raw: int, exponent_bits: int, fraction_bits: int) -> dict[str, Any]:
    sign = raw >> (exponent_bits + fraction_bits)
    exponent_mask = (1 << exponent_bits) - 1
    exponent = (raw >> fraction_bits) & exponent_mask
    fraction = raw & ((1 << fraction_bits) - 1)
    bias = (1 << (exponent_bits - 1)) - 1
    if exponent == 0:
        classification = "zero" if fraction == 0 else "subnormal"
        unbiased_exponent: int | None = 1 - bias
    elif exponent == exponent_mask:
        classification = "infinity" if fraction == 0 else "nan"
        unbiased_exponent = None
    else:
        classification = "normal"
        unbiased_exponent = exponent - bias
    return {
        "sign": sign,
        "exponent_raw": exponent,
        "exponent_unbiased": unbiased_exponent,
        "fraction_raw": fraction,
        "classification": classification,
    }


def represent_float(value: float, format_name: str) -> dict[str, Any]:
    """Python의 `float`를 f32 또는 f64로 반올림하고 필드를 반환합니다."""

    if format_name == "f32":
        packed = struct.pack(">f", value)
        raw = int.from_bytes(packed, "big")
        rounded = struct.unpack(">f", packed)[0]
        fields = _float_fields(raw, 8, 23)
        width = 32
    elif format_name == "f64":
        packed = struct.pack(">d", value)
        raw = int.from_bytes(packed, "big")
        rounded = struct.unpack(">d", packed)[0]
        fields = _float_fields(raw, 11, 52)
        width = 64
    else:
        raise ValueError("형식은 f32 또는 f64여야 합니다")

    absolute_error: float | None
    if math.isfinite(value) and math.isfinite(rounded):
        absolute_error = abs(value - rounded)
    else:
        absolute_error = None
    return {
        "format": format_name,
        "input": value,
        "rounded_value": rounded,
        "hex": f"0x{raw:0{width // 4}x}",
        "binary": format(raw, f"0{width}b"),
        "absolute_error": absolute_error,
        **fields,
    }
