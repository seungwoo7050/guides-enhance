"""교육용 Tiny-RISC 어셈블리 파서와 실행기입니다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

REGISTER_RE = re.compile(r"r([0-7])$")
MEMORY_RE = re.compile(r"(-?(?:0x[0-9a-fA-F]+|\d+))\((r[0-7])\)$")


# [Implementation 2] Tiny-RISC 명령 표현
# 파서, 레이블 해석, 실행기와 파이프라인 추적기가
# 같은 불변 명령 객체를 사용합니다.
@dataclass(frozen=True)
class Instruction:
    op: str
    args: tuple[str, ...]
    source_line: int
    text: str
    taken: bool = False
    target_index: int | None = None


def parse_int(text: str) -> int:
    return int(text, 0)


def register_index(token: str) -> int:
    match = REGISTER_RE.fullmatch(token.strip())
    if not match:
        raise ValueError(f"잘못된 레지스터입니다: {token}")
    return int(match.group(1))


def _strip_comment(raw: str) -> str:
    return raw.split("#", 1)[0].strip()


def parse_program(lines: Iterable[str]) -> tuple[list[Instruction], dict[str, int]]:
    labels: dict[str, int] = {}
    pending: list[tuple[int, str]] = []
    pc = 0
    for number, raw in enumerate(lines, 1):
        text = _strip_comment(raw)
        if not text:
            continue
        while ":" in text:
            label, rest = text.split(":", 1)
            label = label.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
                raise ValueError(f"{number}행: 잘못된 레이블입니다: {label}")
            if label in labels:
                raise ValueError(f"{number}행: 중복 레이블입니다: {label}")
            labels[label] = pc
            text = rest.strip()
            if not text:
                break
        if text:
            pending.append((number, text))
            pc += 1

    program: list[Instruction] = []
    for number, text in pending:
        normalized = text.replace(",", " ")
        tokens = tuple(part for part in normalized.split() if part)
        if not tokens:
            continue
        op = tokens[0].lower()
        args = tokens[1:]
        _validate_instruction(op, args, labels, number)
        program.append(Instruction(op, args, number, text))
    return program, labels


def parse_pipeline_trace(lines: Iterable[str]) -> list[Instruction]:
    """정적 추적 입력을 읽고 실행된 분기의 목적지 인덱스를 정합니다."""

    cleaned: list[str] = []
    taken_lines: set[int] = set()
    for number, raw in enumerate(lines, 1):
        text = _strip_comment(raw)
        taken = text.endswith("@taken")
        if taken:
            text = text[: -len("@taken")].rstrip()
            taken_lines.add(number)
        cleaned.append(text)

    program, labels = parse_program(cleaned)
    result: list[Instruction] = []
    for instruction in program:
        taken = instruction.source_line in taken_lines
        if taken and instruction.op not in {"beq", "bne", "j"}:
            raise ValueError(
                f"{instruction.source_line}행: @taken은 "
                "분기 또는 점프 명령에만 사용할 수 있습니다"
            )
        target_index: int | None = None
        if taken:
            label = instruction.args[0] if instruction.op == "j" else instruction.args[2]
            target_index = labels[label]
        result.append(
            Instruction(
                instruction.op,
                instruction.args,
                instruction.source_line,
                instruction.text,
                taken=taken,
                target_index=target_index,
            )
        )
    return result


def _validate_instruction(
    op: str,
    args: tuple[str, ...],
    labels: dict[str, int],
    line: int,
    allow_unknown_label: bool = False,
) -> None:
    arity = {
        "li": 2,
        "add": 3,
        "addi": 3,
        "sub": 3,
        "and": 3,
        "or": 3,
        "xor": 3,
        "lw": 2,
        "sw": 2,
        "beq": 3,
        "bne": 3,
        "j": 1,
        "halt": 0,
    }
    if op not in arity:
        raise ValueError(f"{line}행: 지원하지 않는 연산 코드입니다: {op}")
    if len(args) != arity[op]:
        raise ValueError(f"{line}행: {op}에는 인자 {arity[op]}개가 필요합니다")

    if op == "li":
        register_index(args[0])
        parse_int(args[1])
    elif op in {"add", "sub", "and", "or", "xor"}:
        for token in args:
            register_index(token)
    elif op == "addi":
        register_index(args[0])
        register_index(args[1])
        parse_int(args[2])
    elif op in {"lw", "sw"}:
        register_index(args[0])
        match = MEMORY_RE.fullmatch(args[1])
        if not match:
            raise ValueError(f"{line}행: 메모리 피연산자는 offset(base) 형식이어야 합니다")
        parse_int(match.group(1))
        register_index(match.group(2))
    elif op in {"beq", "bne"}:
        register_index(args[0])
        register_index(args[1])
        if not allow_unknown_label and args[2] not in labels:
            raise ValueError(f"{line}행: 존재하지 않는 레이블입니다: {args[2]}")
    elif op == "j" and not allow_unknown_label and args[0] not in labels:
        raise ValueError(f"{line}행: 존재하지 않는 레이블입니다: {args[0]}")


def wrap32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


# [Implementation 2-1] 데이터 의존 정보
# 피연산자를 소스·목적지 레지스터와 적재 명령 여부로
# 한 번만 변환해 데이터 위험 판정에 사용합니다.
def sources_and_destination(instruction: Instruction) -> tuple[set[int], int | None, bool]:
    op, args = instruction.op, instruction.args
    if op == "li":
        return set(), register_index(args[0]), False
    if op in {"add", "sub", "and", "or", "xor"}:
        return {register_index(args[1]), register_index(args[2])}, register_index(args[0]), False
    if op == "addi":
        return {register_index(args[1])}, register_index(args[0]), False
    if op == "lw":
        match = MEMORY_RE.fullmatch(args[1])
        assert match
        return {register_index(match.group(2))}, register_index(args[0]), True
    if op == "sw":
        match = MEMORY_RE.fullmatch(args[1])
        assert match
        return {register_index(args[0]), register_index(match.group(2))}, None, False
    if op in {"beq", "bne"}:
        return {register_index(args[0]), register_index(args[1])}, None, False
    return set(), None, False


# [Implementation 2-2] 레지스터·메모리·PC 갱신
# Machine이 레지스터, 메모리와 PC를 함께 갱신합니다.
# r0, 32비트 순환, 주소 범위와 정렬 조건도 여기서 검사합니다.
class Machine:
    def __init__(self, memory_size: int = 4096) -> None:
        if memory_size <= 0 or memory_size % 4:
            raise ValueError("메모리 크기는 양수이며 4의 배수여야 합니다")
        self.registers = [0] * 8
        self.memory = bytearray(memory_size)
        self.pc = 0
        self.steps = 0
        self.halted = False

    def _read_reg(self, token: str) -> int:
        return self.registers[register_index(token)]

    def _write_reg(self, token: str, value: int) -> None:
        index = register_index(token)
        if index != 0:
            self.registers[index] = wrap32(value)

    def _address(self, operand: str) -> int:
        match = MEMORY_RE.fullmatch(operand)
        assert match
        address = self._read_reg(match.group(2)) + parse_int(match.group(1))
        if address % 4:
            raise RuntimeError(f"정렬되지 않은 워드 주소입니다: {address}")
        if address < 0 or address + 4 > len(self.memory):
            raise RuntimeError(f"메모리 범위를 벗어난 주소입니다: {address}")
        return address

    def _load_word(self, address: int) -> int:
        raw = int.from_bytes(self.memory[address : address + 4], "little", signed=False)
        return wrap32(raw)

    def _store_word(self, address: int, value: int) -> None:
        raw = value & 0xFFFFFFFF
        self.memory[address : address + 4] = raw.to_bytes(4, "little", signed=False)

    def run(
        self,
        program: list[Instruction],
        labels: dict[str, int],
        max_steps: int = 100_000,
    ) -> dict[str, Any]:
        while not self.halted:
            if self.steps >= max_steps:
                raise RuntimeError(f"최대 실행 횟수를 넘었습니다: {max_steps}")
            if self.pc < 0 or self.pc >= len(program):
                raise RuntimeError(f"PC가 프로그램 범위를 벗어났습니다: {self.pc}")
            instruction = program[self.pc]
            self._execute(instruction, labels)
            self.registers[0] = 0
            self.steps += 1
        words = {
            str(address): self._load_word(address)
            for address in range(0, len(self.memory), 4)
            if any(self.memory[address : address + 4])
        }
        return {
            "halted": self.halted,
            "steps": self.steps,
            "pc": self.pc,
            "registers": {f"r{index}": value for index, value in enumerate(self.registers)},
            "nonzero_memory_words": words,
        }

    def _execute(self, instruction: Instruction, labels: dict[str, int]) -> None:
        op, args = instruction.op, instruction.args
        next_pc = self.pc + 1
        if op == "li":
            self._write_reg(args[0], parse_int(args[1]))
        elif op == "add":
            self._write_reg(args[0], self._read_reg(args[1]) + self._read_reg(args[2]))
        elif op == "addi":
            self._write_reg(args[0], self._read_reg(args[1]) + parse_int(args[2]))
        elif op == "sub":
            self._write_reg(args[0], self._read_reg(args[1]) - self._read_reg(args[2]))
        elif op == "and":
            self._write_reg(args[0], self._read_reg(args[1]) & self._read_reg(args[2]))
        elif op == "or":
            self._write_reg(args[0], self._read_reg(args[1]) | self._read_reg(args[2]))
        elif op == "xor":
            self._write_reg(args[0], self._read_reg(args[1]) ^ self._read_reg(args[2]))
        elif op == "lw":
            self._write_reg(args[0], self._load_word(self._address(args[1])))
        elif op == "sw":
            self._store_word(self._address(args[1]), self._read_reg(args[0]))
        elif op == "beq":
            if self._read_reg(args[0]) == self._read_reg(args[1]):
                next_pc = labels[args[2]]
        elif op == "bne":
            if self._read_reg(args[0]) != self._read_reg(args[1]):
                next_pc = labels[args[2]]
        elif op == "j":
            next_pc = labels[args[0]]
        elif op == "halt":
            self.halted = True
        else:  # pragma: no cover - parse_program rejects unsupported opcodes.
            raise RuntimeError(f"지원하지 않는 연산 코드입니다: {op}")
        self.pc = next_pc


def run_file(path: Path, memory_size: int, max_steps: int) -> dict[str, Any]:
    program, labels = parse_program(path.read_text(encoding="utf-8").splitlines())
    return Machine(memory_size=memory_size).run(program, labels, max_steps=max_steps)
