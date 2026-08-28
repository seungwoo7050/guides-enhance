"""`processor_model` 기능을 명령행에서 실행합니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from . import bits, cache, coherence, control, isa, perf, pipeline, vm


def _json_dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False))


def _pipeline_text(result: dict[str, Any]) -> None:
    print(
        "cycles={cycles} retired={retired} cpi={cpi:.3f} "
        "data_stalls={data_stalls} control_stalls={control_stalls} flushes={flushes}".format(
            **result
        )
    )
    rows = result["timeline"]
    if not rows:
        return
    cycles = result["cycles"]
    header = ["instruction"] + [str(index) for index in range(1, cycles + 1)]
    widths = {key: len(key) for key in header}
    for row in rows:
        for key in header:
            widths[key] = max(widths[key], len(str(row.get(key, "."))))
    print("  ".join(key.ljust(widths[key]) for key in header))
    for row in rows:
        print("  ".join(str(row.get(key, ".")).ljust(widths[key]) for key in header))


# [Implementation 11] CLI 명령 정의
# 공개 하위 명령과 옵션을 한 파서에서 정의합니다.
# 계산 모듈은 명령행 구문 분석 상태를 알 필요가 없습니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="processor-model",
        description=(
            "데이터 표현, ISA 실행, 파이프라인, 캐시와 "
            "주소 변환을 실행합니다."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bits_parser = subparsers.add_parser("bits", help="고정 폭 정수와 부동소수점 표현")
    bits_sub = bits_parser.add_subparsers(dest="bits_command", required=True)
    int_parser = bits_sub.add_parser("int", help="정수 비트 패턴")
    int_parser.add_argument("value", type=lambda text: int(text, 0))
    int_parser.add_argument("--width", type=int, default=32)
    add_parser = bits_sub.add_parser("add", help="고정 폭 덧셈 상태값")
    add_parser.add_argument("left", type=lambda text: int(text, 0))
    add_parser.add_argument("right", type=lambda text: int(text, 0))
    add_parser.add_argument("--width", type=int, default=32)
    float_parser = bits_sub.add_parser("float", help="IEEE 754 필드")
    float_parser.add_argument("value", type=float)
    float_parser.add_argument("--format", choices=("f32", "f64"), default="f32")

    perf_parser = subparsers.add_parser("perf", help="성능식")
    perf_sub = perf_parser.add_subparsers(dest="perf_command", required=True)
    cpu_parser = perf_sub.add_parser("cpu", help="CPU 실행 시간")
    cpu_parser.add_argument("--instructions", type=float, required=True)
    cpu_parser.add_argument("--cpi", type=float, required=True)
    cpu_parser.add_argument("--ghz", type=float, required=True)
    amdahl_parser = perf_sub.add_parser("amdahl", help="Amdahl의 법칙")
    amdahl_parser.add_argument("--fraction", type=float, required=True)
    amdahl_parser.add_argument("--speedup", type=float, required=True)
    amat_parser = perf_sub.add_parser("amat", help="평균 메모리 접근 시간")
    amat_parser.add_argument("--hit-time", type=float, required=True)
    amat_parser.add_argument("--miss-rate", type=float, required=True)
    amat_parser.add_argument("--miss-penalty", type=float, required=True)

    control_parser = subparsers.add_parser("control", help="데이터패스 제어 신호")
    control_parser.add_argument("opcode")

    isa_parser = subparsers.add_parser("isa", help="Tiny-RISC 프로그램 실행")
    isa_parser.add_argument("program", type=Path)
    isa_parser.add_argument("--memory-size", type=int, default=4096)
    isa_parser.add_argument("--max-steps", type=int, default=100_000)

    pipeline_parser = subparsers.add_parser("pipeline", help="5단계 파이프라인 추적")
    pipeline_parser.add_argument("trace", type=Path)
    pipeline_parser.add_argument("--forwarding", choices=("full", "none"), default="full")
    pipeline_parser.add_argument("--branch-penalty", type=int, default=2)
    pipeline_parser.add_argument("--json", action="store_true")

    cache_parser = subparsers.add_parser("cache", help="집합 연관 캐시 추적")
    cache_parser.add_argument("trace", type=Path)
    cache_parser.add_argument("--size", type=int, required=True, help="캐시 크기(바이트)")
    cache_parser.add_argument("--block", type=int, required=True, help="블록 크기(바이트)")
    cache_parser.add_argument("--ways", type=int, required=True)
    cache_parser.add_argument("--no-write-allocate", action="store_true")

    vm_parser = subparsers.add_parser("vm", help="TLB와 페이지 테이블 주소 변환")
    vm_parser.add_argument("config", type=Path)
    vm_parser.add_argument("trace", type=Path)

    coherence_parser = subparsers.add_parser("coherence", help="MESI 추적")
    coherence_parser.add_argument("trace", type=Path)
    coherence_parser.add_argument("--cores", type=int, default=2)
    coherence_parser.add_argument("--line-size", type=int, default=64)
    return parser


def _load_vm_config(path: Path) -> tuple[int, int, dict[int, vm.Mapping]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    page_size = int(raw["page_size"])
    tlb_entries = int(raw["tlb_entries"])
    mappings: dict[int, vm.Mapping] = {}
    for vpn_text, entry in raw.get("mappings", {}).items():
        permissions = set(str(entry["permissions"]).lower())
        mappings[int(vpn_text, 0)] = vm.Mapping(int(entry["pfn"]), permissions)
    return page_size, tlb_entries, mappings


# [Implementation 11-1] CLI 입력과 결과 연결
# 파일을 읽고 해당 계산 모듈을 호출한 뒤 결과를 출력합니다.
# 계산 중간 상태는 명령행 코드가 따로 보관하지 않습니다.
def run(args: argparse.Namespace) -> int:
    if args.command == "bits":
        if args.bits_command == "int":
            _json_dump(bits.represent_integer(args.value, args.width))
        elif args.bits_command == "add":
            _json_dump(bits.add_fixed(args.left, args.right, args.width))
        else:
            _json_dump(bits.represent_float(args.value, args.format))
        return 0

    if args.command == "perf":
        if args.perf_command == "cpu":
            _json_dump(perf.cpu_time(args.instructions, args.cpi, args.ghz))
        elif args.perf_command == "amdahl":
            _json_dump(perf.amdahl(args.fraction, args.speedup))
        else:
            _json_dump(perf.amat(args.hit_time, args.miss_rate, args.miss_penalty))
        return 0

    if args.command == "control":
        _json_dump(control.signals(args.opcode.lower()))
        return 0

    if args.command == "isa":
        _json_dump(isa.run_file(args.program, args.memory_size, args.max_steps))
        return 0

    if args.command == "pipeline":
        instructions = isa.parse_pipeline_trace(
            args.trace.read_text(encoding="utf-8").splitlines()
        )
        result = pipeline.simulate(
            instructions,
            forwarding=args.forwarding,
            branch_penalty=args.branch_penalty,
        ).as_dict()
        if args.json:
            _json_dump(result)
        else:
            _pipeline_text(result)
        return 0

    if args.command == "cache":
        accesses = cache.parse_trace(args.trace.read_text(encoding="utf-8").splitlines())
        simulator = cache.CacheSimulator(
            size_bytes=args.size,
            block_size=args.block,
            associativity=args.ways,
            write_allocate=not args.no_write_allocate,
        )
        _json_dump(simulator.run(accesses))
        return 0

    if args.command == "vm":
        page_size, tlb_entries, mappings = _load_vm_config(args.config)
        operations = vm.parse_operations(args.trace.read_text(encoding="utf-8").splitlines())
        simulator = vm.VirtualMemorySimulator(page_size, tlb_entries, mappings)
        _json_dump(simulator.run(operations))
        return 0

    if args.command == "coherence":
        accesses = coherence.parse_trace(
            args.trace.read_text(encoding="utf-8").splitlines()
        )
        simulator = coherence.MESISimulator(args.cores, args.line_size)
        _json_dump(simulator.run(accesses))
        return 0

    raise AssertionError("도달할 수 없는 명령 분기입니다")


# [Implementation 11-2] 오류 종료 상태
# 입력·파일·모델 오류는 stderr에 표시하고 종료 상태 2를 반환합니다.
# 예상하지 못한 내부 결함은 이 예외 목록에 포함하지 않습니다.
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return run(parser.parse_args(argv))
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"processor-model: {exc}", file=sys.stderr)
        return 2
