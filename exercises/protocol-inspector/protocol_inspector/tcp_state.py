"""핵심 TCP 연결 상태와 허용된 사건 전이를 명시적으로 모델링합니다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import InvalidTransition


class EndpointRole(str, Enum):
    CLIENT = "client"
    SERVER = "server"


class TCPState(str, Enum):
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN-SENT"
    SYN_RECEIVED = "SYN-RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT_1 = "FIN-WAIT-1"
    FIN_WAIT_2 = "FIN-WAIT-2"
    CLOSE_WAIT = "CLOSE-WAIT"
    CLOSING = "CLOSING"
    LAST_ACK = "LAST-ACK"
    TIME_WAIT = "TIME-WAIT"


class TCPEvent(str, Enum):
    PASSIVE_OPEN = "passive-open"
    ACTIVE_OPEN = "active-open"
    RECEIVE_SYN = "receive-syn"
    RECEIVE_SYN_ACK = "receive-syn-ack"
    RECEIVE_ACK = "receive-ack"
    APP_CLOSE = "app-close"
    RECEIVE_FIN = "receive-fin"
    RECEIVE_FIN_ACK = "receive-fin-ack"
    RECEIVE_RST = "receive-rst"
    TIMEOUT = "timeout"


# [Implementation 5] TCP transition table
# 클라이언트와 서버가 공유하는 정상 상태 전이를 한 표에 모읍니다.
_TRANSITIONS: dict[tuple[TCPState, TCPEvent], TCPState] = {
    (TCPState.LISTEN, TCPEvent.RECEIVE_SYN): TCPState.SYN_RECEIVED,
    (TCPState.LISTEN, TCPEvent.APP_CLOSE): TCPState.CLOSED,
    (TCPState.SYN_SENT, TCPEvent.RECEIVE_SYN_ACK): TCPState.ESTABLISHED,
    (TCPState.SYN_SENT, TCPEvent.RECEIVE_SYN): TCPState.SYN_RECEIVED,
    (TCPState.SYN_RECEIVED, TCPEvent.RECEIVE_ACK): TCPState.ESTABLISHED,
    (TCPState.ESTABLISHED, TCPEvent.APP_CLOSE): TCPState.FIN_WAIT_1,
    (TCPState.ESTABLISHED, TCPEvent.RECEIVE_FIN): TCPState.CLOSE_WAIT,
    (TCPState.FIN_WAIT_1, TCPEvent.RECEIVE_ACK): TCPState.FIN_WAIT_2,
    (TCPState.FIN_WAIT_1, TCPEvent.RECEIVE_FIN): TCPState.CLOSING,
    (TCPState.FIN_WAIT_1, TCPEvent.RECEIVE_FIN_ACK): TCPState.TIME_WAIT,
    (TCPState.FIN_WAIT_2, TCPEvent.RECEIVE_FIN): TCPState.TIME_WAIT,
    (TCPState.CLOSING, TCPEvent.RECEIVE_ACK): TCPState.TIME_WAIT,
    (TCPState.CLOSE_WAIT, TCPEvent.APP_CLOSE): TCPState.LAST_ACK,
    (TCPState.LAST_ACK, TCPEvent.RECEIVE_ACK): TCPState.CLOSED,
    (TCPState.TIME_WAIT, TCPEvent.TIMEOUT): TCPState.CLOSED,
}


# [Implementation 5-1] Endpoint state updates
# 허용되지 않은 사건은 상태를 바꾸지 않으며 RST 예외도 종단점 안에서 처리합니다.
@dataclass
class TCPEndpoint:
    role: EndpointRole
    state: TCPState = TCPState.CLOSED

    def apply(self, event: TCPEvent) -> TCPState:
        if event is TCPEvent.RECEIVE_RST:
            if self.state in {TCPState.CLOSED, TCPState.LISTEN}:
                return self.state
            if self.state is TCPState.SYN_RECEIVED and self.role is EndpointRole.SERVER:
                self.state = TCPState.LISTEN
                return self.state
            self.state = TCPState.CLOSED
            return self.state

        if self.state is TCPState.CLOSED:
            if self.role is EndpointRole.SERVER and event is TCPEvent.PASSIVE_OPEN:
                self.state = TCPState.LISTEN
                return self.state
            if self.role is EndpointRole.CLIENT and event is TCPEvent.ACTIVE_OPEN:
                self.state = TCPState.SYN_SENT
                return self.state

        next_state = _TRANSITIONS.get((self.state, event))
        if next_state is None:
            raise InvalidTransition(
                f"Event {event.value!r} is invalid for a {self.role.value} "
                f"endpoint in state {self.state.value}"
            )
        self.state = next_state
        return self.state
