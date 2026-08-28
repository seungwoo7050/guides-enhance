"""Tiny-RISC 명령을 단순한 단일 사이클 제어 신호로 변환합니다."""

from __future__ import annotations

from typing import Any


# [Implementation 4] 명령별 제어 신호표
# 레지스터·메모리 쓰기, ALU 연산과 다음 PC 선택이
# ISA 실행 결과와 어긋나지 않도록 표로 정의합니다.
CONTROL: dict[str, dict[str, Any]] = {
    "li": {
        "reg_write": 1,
        "alu_src": "immediate",
        "alu_op": "pass-b",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "add": {
        "reg_write": 1,
        "alu_src": "register",
        "alu_op": "add",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "addi": {
        "reg_write": 1,
        "alu_src": "immediate",
        "alu_op": "add",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "sub": {
        "reg_write": 1,
        "alu_src": "register",
        "alu_op": "sub",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "and": {
        "reg_write": 1,
        "alu_src": "register",
        "alu_op": "and",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "or": {
        "reg_write": 1,
        "alu_src": "register",
        "alu_op": "or",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "xor": {
        "reg_write": 1,
        "alu_src": "register",
        "alu_op": "xor",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "alu",
        "branch": "none",
        "jump": 0,
    },
    "lw": {
        "reg_write": 1,
        "alu_src": "immediate",
        "alu_op": "add",
        "mem_read": 1,
        "mem_write": 0,
        "writeback": "memory",
        "branch": "none",
        "jump": 0,
    },
    "sw": {
        "reg_write": 0,
        "alu_src": "immediate",
        "alu_op": "add",
        "mem_read": 0,
        "mem_write": 1,
        "writeback": "none",
        "branch": "none",
        "jump": 0,
    },
    "beq": {
        "reg_write": 0,
        "alu_src": "register",
        "alu_op": "sub",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "none",
        "branch": "equal",
        "jump": 0,
    },
    "bne": {
        "reg_write": 0,
        "alu_src": "register",
        "alu_op": "sub",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "none",
        "branch": "not-equal",
        "jump": 0,
    },
    "j": {
        "reg_write": 0,
        "alu_src": "none",
        "alu_op": "none",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "none",
        "branch": "none",
        "jump": 1,
    },
    "halt": {
        "reg_write": 0,
        "alu_src": "none",
        "alu_op": "none",
        "mem_read": 0,
        "mem_write": 0,
        "writeback": "none",
        "branch": "none",
        "jump": 0,
    },
}


def signals(opcode: str) -> dict[str, Any]:
    try:
        return {"opcode": opcode, **CONTROL[opcode]}
    except KeyError as exc:
        raise ValueError(f"지원하지 않는 연산 코드입니다: {opcode}") from exc
