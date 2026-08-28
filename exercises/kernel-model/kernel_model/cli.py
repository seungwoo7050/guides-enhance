"""JSON 입력을 각 운영체제 모델 호출로 변환합니다."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping

from .deadlock import detect_deadlocked, find_wait_cycle, safe_sequence
from .device_io import DeviceQueue
from .filesystem import FileSystemModel
from .journal import Journal
from .lifecycle import KernelState
from .paging import MemoryManager, simulate_replacement
from .scheduler import JobSpec, simulate
from .synchronization import ConditionChannel

Runner = Callable[[Mapping[str, Any]], dict[str, Any]]


# [Implementation 9] JSON 입력과 출력
def _load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Fixture root must be a JSON object")
    return data


def _dump(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


# [Implementation 9-1] JSON operation을 model 호출로 변환
def run_lifecycle(data: Mapping[str, Any]) -> dict[str, Any]:
    model = KernelState()
    for raw in _operation_objects(data):
        op = raw.get("op")
        if op == "add":
            model.add(str(raw["tid"]))
        elif op == "admit":
            model.admit(str(raw["tid"]))
        elif op == "dispatch":
            model.dispatch()
        elif op == "preempt":
            model.preempt()
        elif op == "yield":
            model.yield_cpu()
        elif op == "block":
            model.block(
                str(raw["channel"]),
                str(raw.get("reason", "unspecified")),
            )
        elif op == "wake-one":
            model.wake_one(str(raw["channel"]))
        elif op == "wake-all":
            model.wake_all(str(raw["channel"]))
        elif op == "exit":
            model.exit_running()
        else:
            raise ValueError(f"Unsupported lifecycle operation: {op}")
    return model.snapshot()


def run_schedule(data: Mapping[str, Any]) -> dict[str, Any]:
    raw_jobs = data.get("jobs", [])
    if not isinstance(raw_jobs, list):
        raise ValueError("jobs must be an array")
    jobs: list[JobSpec] = []
    for raw in raw_jobs:
        if not isinstance(raw, Mapping):
            raise ValueError("Each job must be an object")
        jobs.append(
            JobSpec(
                tid=str(raw["tid"]),
                arrival=int(raw.get("arrival", 0)),
                cpu_bursts=tuple(int(item) for item in raw["cpu_bursts"]),
                io_waits=tuple(int(item) for item in raw.get("io_waits", [])),
                priority=int(raw.get("priority", 0)),
            )
        )
    result = simulate(
        jobs,
        str(data.get("policy", "fcfs")),
        quantum=int(data.get("quantum", 2)),
    )
    return {
        "policy": result.policy.value,
        "timeline": [asdict(tick) for tick in result.timeline],
        "completion_order": list(result.completion_order),
        "metrics": {
            tid: asdict(metrics)
            for tid, metrics in sorted(result.metrics.items())
        },
        "makespan": result.makespan,
        "cpu_busy_ticks": result.cpu_busy_ticks,
    }


def run_deadlock(data: Mapping[str, Any]) -> dict[str, Any]:
    mode = str(data.get("mode", "detect"))
    if mode == "cycle":
        graph = data.get("graph", {})
        if not isinstance(graph, Mapping):
            raise ValueError("graph must be an object")
        normalized: dict[str, list[str]] = {}
        for key, value in graph.items():
            if not isinstance(value, list):
                raise ValueError("Each graph adjacency list must be an array")
            normalized[str(key)] = [str(item) for item in value]
        return {"cycle": find_wait_cycle(normalized)}

    available = [int(item) for item in data.get("available", [])]
    allocation = {
        str(key): [int(item) for item in value]
        for key, value in _mapping(data, "allocation").items()
    }
    if mode == "detect":
        outstanding = {
            str(key): [int(item) for item in value]
            for key, value in _mapping(data, "outstanding").items()
        }
        return {
            "deadlocked": sorted(
                detect_deadlocked(available, allocation, outstanding)
            )
        }
    if mode == "avoid":
        maximum = {
            str(key): [int(item) for item in value]
            for key, value in _mapping(data, "maximum").items()
        }
        sequence = safe_sequence(available, allocation, maximum)
        return {"safe": sequence is not None, "sequence": sequence}
    raise ValueError(f"Unsupported deadlock mode: {mode}")


def run_condition(data: Mapping[str, Any]) -> dict[str, Any]:
    channel = ConditionChannel(str(data.get("name", "event")))
    tokens: dict[str, Any] = {}
    outcomes: list[dict[str, Any]] = []
    for raw in _operation_objects(data):
        op = raw.get("op")
        tid = str(raw.get("tid", ""))
        if op == "prepare":
            tokens[tid] = channel.prepare_wait()
        elif op == "commit":
            outcomes.append(
                {"tid": tid, "slept": channel.commit_wait(tid, tokens[tid])}
            )
        elif op == "notify-one":
            outcomes.append({"awakened": channel.notify_one()})
        elif op == "notify-all":
            outcomes.append({"awakened": channel.notify_all()})
        else:
            raise ValueError(f"Unsupported condition operation: {op}")
    return {
        "generation": channel.generation,
        "waiters": sorted(channel.waiters),
        "outcomes": outcomes,
    }


def run_memory(data: Mapping[str, Any]) -> dict[str, Any]:
    model = MemoryManager(max_frames=int(data.get("max_frames", 64)))
    results: list[dict[str, Any]] = []
    for raw in _operation_objects(data):
        op = raw.get("op")
        if op == "create-process":
            model.create_process(str(raw["pid"]))
        elif op == "map-zero":
            model.map_demand_zero(
                str(raw["pid"]),
                int(raw["vpn"]),
                writable=bool(raw.get("writable", True)),
            )
        elif op == "map-value":
            model.map_value(
                str(raw["pid"]),
                int(raw["vpn"]),
                int(raw.get("value", 0)),
                writable=bool(raw.get("writable", True)),
            )
        elif op == "fork":
            model.fork(str(raw["parent"]), str(raw["child"]))
        elif op == "read":
            results.append(
                {"value": model.read(str(raw["pid"]), int(raw["vpn"]))}
            )
        elif op == "write":
            fault = model.write(
                str(raw["pid"]),
                int(raw["vpn"]),
                int(raw["value"]),
            )
            results.append({"fault": None if fault is None else fault.value})
        elif op == "unmap":
            model.unmap(str(raw["pid"]), int(raw["vpn"]))
        elif op == "destroy-process":
            model.destroy_process(str(raw["pid"]))
        else:
            raise ValueError(f"Unsupported memory operation: {op}")
    return {"results": results, "snapshot": model.snapshot()}


def run_replacement(data: Mapping[str, Any]) -> dict[str, Any]:
    result = simulate_replacement(
        [int(item) for item in data.get("references", [])],
        int(data.get("capacity", 3)),
        str(data.get("policy", "fifo")),
    )
    return asdict(result)


def run_filesystem(data: Mapping[str, Any]) -> dict[str, Any]:
    model = FileSystemModel()
    journal = Journal()
    applied: set[int] = set()
    for raw in _operation_objects(data):
        op = raw.get("op")
        if op == "begin":
            journal.begin()
        elif op == "journal":
            operation = raw["operation"]
            if not isinstance(operation, Mapping):
                raise ValueError("journal.operation must be an object")
            journal.append(int(raw["txid"]), operation)
        elif op == "commit":
            journal.commit(int(raw["txid"]))
        elif op == "recover":
            journal.recover(model.apply_operation, already_applied=applied)
        elif op == "crash":
            model.crash_recover()
        else:
            model.apply_operation(raw)
    return {
        "filesystem": model.snapshot(),
        "journal": journal.snapshot(),
        "applied": sorted(applied),
    }


def run_io(data: Mapping[str, Any]) -> dict[str, Any]:
    queue = DeviceQueue(queue_depth=int(data.get("queue_depth", 8)))
    aliases: dict[str, int] = {}
    reaped: list[dict[str, Any]] = []
    for raw in _operation_objects(data):
        op = raw.get("op")
        if op == "submit":
            request_id = queue.submit(
                str(raw["owner"]),
                tuple(int(item) for item in raw["buffer_pages"]),
                int(raw["length"]),
            )
            if "as" in raw:
                aliases[str(raw["as"])] = request_id
        elif op == "start":
            queue.start_next()
        elif op == "cancel":
            queue.cancel(
                str(raw["owner"]),
                _request_id(raw, aliases),
            )
        elif op == "complete":
            queue.interrupt_complete(
                _request_id(raw, aliases),
                bytes_transferred=int(raw.get("bytes_transferred", 0)),
                error=None if raw.get("error") is None else str(raw.get("error")),
            )
        elif op == "reap":
            request = queue.reap(str(raw["owner"]))
            reaped.append(
                {}
                if request is None
                else {
                    "request_id": request.request_id,
                    "state": request.state.value,
                    "bytes_transferred": request.bytes_transferred,
                    "error": request.error,
                }
            )
        else:
            raise ValueError(f"Unsupported I/O operation: {op}")
    return {"snapshot": queue.snapshot(), "reaped": reaped}


def _request_id(raw: Mapping[str, Any], aliases: Mapping[str, int]) -> int:
    if "request_id" in raw:
        return int(raw["request_id"])
    return aliases[str(raw["request"])]


def _operation_objects(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    operations = data.get("operations", [])
    if not isinstance(operations, list):
        raise ValueError("operations must be an array")
    result: list[Mapping[str, Any]] = []
    for raw in operations:
        if not isinstance(raw, Mapping):
            raise ValueError("Each operation must be an object")
        result.append(raw)
    return result


def _mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


RUNNERS: dict[str, Runner] = {
    "lifecycle": run_lifecycle,
    "schedule": run_schedule,
    "deadlock": run_deadlock,
    "condition": run_condition,
    "memory": run_memory,
    "replacement": run_replacement,
    "filesystem": run_filesystem,
    "io": run_io,
}


# [Implementation 9-2] model 선택과 종료 상태 반환
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic operating-system state models"
    )
    parser.add_argument("model", choices=sorted(RUNNERS))
    parser.add_argument("fixture", help="Path to a JSON scenario")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = _load(args.fixture)
        result = RUNNERS[args.model](data)
    except (
        json.JSONDecodeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        BufferError,
        PermissionError,
    ) as exc:
        print(f"Model execution failed: {exc}", file=sys.stderr)
        return 1
    _dump(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
