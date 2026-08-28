from __future__ import annotations

import unittest

from protocol_inspector import (
    EndpointRole,
    InvalidTransition,
    TCPEndpoint,
    TCPEvent,
    TCPState,
)


class TCPStateTests(unittest.TestCase):
    def test_client_active_open_and_active_close(self) -> None:
        endpoint = TCPEndpoint(EndpointRole.CLIENT)
        events = [
            TCPEvent.ACTIVE_OPEN,
            TCPEvent.RECEIVE_SYN_ACK,
            TCPEvent.APP_CLOSE,
            TCPEvent.RECEIVE_ACK,
            TCPEvent.RECEIVE_FIN,
            TCPEvent.TIMEOUT,
        ]
        states = [endpoint.apply(event) for event in events]
        self.assertEqual(
            states,
            [
                TCPState.SYN_SENT,
                TCPState.ESTABLISHED,
                TCPState.FIN_WAIT_1,
                TCPState.FIN_WAIT_2,
                TCPState.TIME_WAIT,
                TCPState.CLOSED,
            ],
        )

    def test_server_passive_open_and_passive_close(self) -> None:
        endpoint = TCPEndpoint(EndpointRole.SERVER)
        events = [
            TCPEvent.PASSIVE_OPEN,
            TCPEvent.RECEIVE_SYN,
            TCPEvent.RECEIVE_ACK,
            TCPEvent.RECEIVE_FIN,
            TCPEvent.APP_CLOSE,
            TCPEvent.RECEIVE_ACK,
        ]
        states = [endpoint.apply(event) for event in events]
        self.assertEqual(states[-1], TCPState.CLOSED)
        self.assertEqual(states[0], TCPState.LISTEN)
        self.assertEqual(states[2], TCPState.ESTABLISHED)
        self.assertEqual(states[3], TCPState.CLOSE_WAIT)

    def test_listen_does_not_jump_to_syn_sent(self) -> None:
        # 수동 열기와 능동 열기를 같은 전이로 합친 상태 기계를 거부합니다.
        endpoint = TCPEndpoint(EndpointRole.SERVER)
        endpoint.apply(TCPEvent.PASSIVE_OPEN)
        with self.assertRaises(InvalidTransition):
            endpoint.apply(TCPEvent.ACTIVE_OPEN)

    def test_reset_processing_depends_on_the_current_state(self) -> None:
        closed = TCPEndpoint(EndpointRole.CLIENT)
        self.assertEqual(closed.apply(TCPEvent.RECEIVE_RST), TCPState.CLOSED)

        listener = TCPEndpoint(EndpointRole.SERVER)
        listener.apply(TCPEvent.PASSIVE_OPEN)
        self.assertEqual(listener.apply(TCPEvent.RECEIVE_RST), TCPState.LISTEN)
        listener.apply(TCPEvent.RECEIVE_SYN)
        self.assertEqual(listener.apply(TCPEvent.RECEIVE_RST), TCPState.LISTEN)

        active = TCPEndpoint(EndpointRole.CLIENT)
        active.apply(TCPEvent.ACTIVE_OPEN)
        self.assertEqual(active.apply(TCPEvent.RECEIVE_RST), TCPState.CLOSED)

        established = TCPEndpoint(EndpointRole.CLIENT)
        established.apply(TCPEvent.ACTIVE_OPEN)
        established.apply(TCPEvent.RECEIVE_SYN_ACK)
        self.assertEqual(established.apply(TCPEvent.RECEIVE_RST), TCPState.CLOSED)


if __name__ == "__main__":
    unittest.main()
