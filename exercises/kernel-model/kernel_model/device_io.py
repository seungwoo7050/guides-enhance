"""device request, DMA pin, interrupt, cancellation과 completion을 관리합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


# [Implementation 8] device request 상태 정의
class RequestState(str, Enum):
    QUEUED = "queued"
    IN_FLIGHT = "in-flight"
    COMPLETED = "completed"
    CANCEL_PENDING = "cancel-pending"
    CANCELLED = "cancelled"
    REAPED = "reaped"


class DeviceStateError(ValueError):
    """request 위치와 DMA pin 상태가 맞지 않을 때 발생합니다."""


@dataclass
class IORequest:
    request_id: int
    owner: str
    buffer_pages: tuple[int, ...]
    length: int
    state: RequestState = RequestState.QUEUED
    pinned: bool = False
    bytes_transferred: int = 0
    error: str | None = None


@dataclass
class DeviceQueue:
    """request 제출부터 owner의 결과 회수까지 상태를 관리합니다."""

    queue_depth: int = 8
    requests: dict[int, IORequest] = field(default_factory=dict)
    pending: deque[int] = field(default_factory=deque)
    in_flight: set[int] = field(default_factory=set)
    completions: dict[str, deque[int]] = field(default_factory=dict)
    _next_id: int = 1

    def __post_init__(self) -> None:
        if self.queue_depth <= 0:
            raise ValueError("Device queue depth must be positive")

    # [Implementation 8-1] queue 용량 확인과 DMA 시작
    def submit(self, owner: str, buffer_pages: tuple[int, ...], length: int) -> int:
        if not owner:
            raise ValueError("Request owner cannot be empty")
        if length <= 0:
            raise ValueError("Request length must be positive")
        if not buffer_pages or any(page < 0 for page in buffer_pages):
            raise ValueError("DMA buffer pages are invalid")
        active = sum(
            request.state not in {RequestState.REAPED, RequestState.CANCELLED}
            for request in self.requests.values()
        )
        if active >= self.queue_depth:
            raise BufferError("Device queue is full")

        request_id = self._next_id
        self._next_id += 1
        self.requests[request_id] = IORequest(
            request_id,
            owner,
            tuple(buffer_pages),
            length,
        )
        self.pending.append(request_id)
        self.assert_invariants()
        return request_id

    def start_next(self) -> IORequest | None:
        if not self.pending:
            self.assert_invariants()
            return None
        request_id = self.pending.popleft()
        request = self.requests[request_id]
        if request.state is not RequestState.QUEUED:
            raise DeviceStateError(
                f"A pending request is not QUEUED: {request_id}"
            )
        request.state = RequestState.IN_FLIGHT
        request.pinned = True
        self.in_flight.add(request_id)
        self.assert_invariants()
        return request

    # [Implementation 8-2] cancel과 interrupt completion 경쟁
    def cancel(self, owner: str, request_id: int) -> RequestState:
        request = self._request_for_owner(owner, request_id)
        if request.state is RequestState.QUEUED:
            self.pending.remove(request_id)
            request.state = RequestState.CANCELLED
            self.completions.setdefault(request.owner, deque()).append(request_id)
        elif request.state is RequestState.IN_FLIGHT:
            # device가 아직 buffer를 사용할 수 있으므로
            # interrupt completion 전까지 pin을 유지합니다.
            request.state = RequestState.CANCEL_PENDING
        elif request.state in {
            RequestState.COMPLETED,
            RequestState.CANCELLED,
            RequestState.REAPED,
        }:
            return request.state
        elif request.state is RequestState.CANCEL_PENDING:
            return request.state
        self.assert_invariants()
        return request.state

    def interrupt_complete(
        self,
        request_id: int,
        *,
        bytes_transferred: int,
        error: str | None = None,
    ) -> None:
        request = self._require(request_id)
        if request.state not in {
            RequestState.IN_FLIGHT,
            RequestState.CANCEL_PENDING,
        }:
            raise DeviceStateError(
                f"Cannot complete a request that is not in flight: {request_id}"
            )
        if bytes_transferred < 0 or bytes_transferred > request.length:
            raise DeviceStateError(
                f"Transferred byte count exceeds request bounds: {request_id}"
            )
        self.in_flight.remove(request_id)
        request.pinned = False
        request.bytes_transferred = bytes_transferred
        request.error = error
        request.state = (
            RequestState.CANCELLED
            if request.state is RequestState.CANCEL_PENDING
            else RequestState.COMPLETED
        )
        self.completions.setdefault(request.owner, deque()).append(request_id)
        self.assert_invariants()

    # [Implementation 8-3] completion 결과 한 번만 전달
    def reap(self, owner: str) -> IORequest | None:
        queue = self.completions.get(owner)
        if not queue:
            self.assert_invariants()
            return None
        request_id = queue.popleft()
        if not queue:
            self.completions.pop(owner, None)
        request = self._request_for_owner(owner, request_id)
        if request.state not in {RequestState.COMPLETED, RequestState.CANCELLED}:
            raise DeviceStateError(
                f"Completion queue contains a non-terminal request: {request_id}"
            )
        # owner가 결과를 받은 시점에만 request의 마지막 수명을 닫습니다.
        request.state = RequestState.REAPED
        self.assert_invariants()
        return request

    # [Implementation 8-4] request 위치와 DMA pin 검사
    def assert_invariants(self) -> None:
        pending = list(self.pending)
        if len(set(pending)) != len(pending):
            raise DeviceStateError("Pending queue contains duplicate requests")

        completion_locations: dict[int, str] = {}
        for owner, queue in self.completions.items():
            for request_id in queue:
                if request_id in completion_locations:
                    raise DeviceStateError(
                        f"A request appears in multiple completion queues: {request_id}"
                    )
                completion_locations[request_id] = owner

        active = sum(
            request.state not in {RequestState.REAPED, RequestState.CANCELLED}
            for request in self.requests.values()
        )
        if active > self.queue_depth:
            raise DeviceStateError(
                "Active request count exceeds queue depth: "
                f"active={active} depth={self.queue_depth}"
            )

        for request_id, request in self.requests.items():
            if not request.owner:
                raise DeviceStateError(f"Request owner is empty: {request_id}")
            if request.length <= 0:
                raise DeviceStateError(f"Request length is invalid: {request_id}")
            if not request.buffer_pages or any(page < 0 for page in request.buffer_pages):
                raise DeviceStateError(f"DMA buffer pages are invalid: {request_id}")
            if request.bytes_transferred < 0 or request.bytes_transferred > request.length:
                raise DeviceStateError(
                    f"Transfer result exceeds request bounds: {request_id}"
                )

            in_pending = request_id in pending
            in_flight = request_id in self.in_flight
            completion_owner = completion_locations.get(request_id)
            if request.pinned != in_flight:
                raise DeviceStateError(
                    f"DMA pin state disagrees with in-flight ownership: {request_id}"
                )
            if request.state is RequestState.QUEUED:
                if not in_pending or in_flight or completion_owner is not None:
                    raise DeviceStateError(
                        f"A QUEUED request has an invalid location: {request_id}"
                    )
            elif request.state in {
                RequestState.IN_FLIGHT,
                RequestState.CANCEL_PENDING,
            }:
                if in_pending or not in_flight or completion_owner is not None:
                    raise DeviceStateError(
                        f"An in-flight request has an invalid location: {request_id}"
                    )
            elif request.state in {
                RequestState.COMPLETED,
                RequestState.CANCELLED,
            }:
                if in_pending or in_flight or completion_owner != request.owner:
                    raise DeviceStateError(
                        f"A terminal request has an invalid location: {request_id}"
                    )
            elif request.state is RequestState.REAPED:
                if in_pending or in_flight or completion_owner is not None or request.pinned:
                    raise DeviceStateError(
                        f"A reaped request remains in a queue: {request_id}"
                    )

        for request_id in pending + list(self.in_flight) + list(completion_locations):
            if request_id not in self.requests:
                raise DeviceStateError(
                    f"A queue references a request that does not exist: {request_id}"
                )

    def snapshot(self) -> dict[str, Any]:
        return {
            "queue_depth": self.queue_depth,
            "pending": list(self.pending),
            "in_flight": sorted(self.in_flight),
            "completions": {
                owner: list(queue)
                for owner, queue in sorted(self.completions.items())
            },
            "requests": {
                str(request_id): {
                    "owner": request.owner,
                    "buffer_pages": list(request.buffer_pages),
                    "length": request.length,
                    "state": request.state.value,
                    "pinned": request.pinned,
                    "bytes_transferred": request.bytes_transferred,
                    "error": request.error,
                }
                for request_id, request in sorted(self.requests.items())
            },
        }

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        queue = cls(queue_depth=int(snapshot.get("queue_depth", 8)))
        raw_requests = snapshot.get("requests")
        raw_pending = snapshot.get("pending", [])
        raw_in_flight = snapshot.get("in_flight", [])
        raw_completions = snapshot.get("completions", {})
        if (
            not isinstance(raw_requests, Mapping)
            or not isinstance(raw_pending, list)
            or not isinstance(raw_in_flight, list)
            or not isinstance(raw_completions, Mapping)
        ):
            raise DeviceStateError("Device snapshot has an invalid shape")

        queue.requests = {}
        for raw_id, raw in raw_requests.items():
            if not isinstance(raw, Mapping):
                raise DeviceStateError("A request entry has an invalid shape")
            request_id = int(raw_id)
            queue.requests[request_id] = IORequest(
                request_id=request_id,
                owner=str(raw.get("owner", "")),
                buffer_pages=tuple(int(item) for item in raw.get("buffer_pages", [])),
                length=int(raw.get("length", 0)),
                state=RequestState(str(raw.get("state"))),
                pinned=bool(raw.get("pinned", False)),
                bytes_transferred=int(raw.get("bytes_transferred", 0)),
                error=None if raw.get("error") is None else str(raw.get("error")),
            )

        queue.pending = deque(int(item) for item in raw_pending)
        queue.in_flight = {int(item) for item in raw_in_flight}
        queue.completions = {
            str(owner): deque(int(item) for item in items)
            for owner, items in raw_completions.items()
            if isinstance(items, list)
        }
        if len(queue.completions) != len(raw_completions):
            raise DeviceStateError("Each completion queue must be an array")
        queue._next_id = max(queue.requests, default=0) + 1
        queue.assert_invariants()

    def _request_for_owner(self, owner: str, request_id: int) -> IORequest:
        request = self._require(request_id)
        if request.owner != owner:
            raise PermissionError(f"Request belongs to another owner: {request_id}")
        return request

    def _require(self, request_id: int) -> IORequest:
        try:
            return self.requests[request_id]
        except KeyError as exc:
            raise KeyError(f"I/O request not found: {request_id}") from exc
