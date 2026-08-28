# TCP 송신 창 모델

`rwnd`, `cwnd`, 전송 중인 바이트, RTT, Reno 상태를 결정적인 숫자로 계산하는 작은 Python 모델입니다. 실제 패킷을 전송하지 않으므로 같은 사건을 같은 순서로 적용하면 항상 같은 결과가 나옵니다.

## 계산하는 값

```text
in_flight = next_sequence - send_base
effective_window = min(rwnd, cwnd)
available = max(0, effective_window - in_flight)
```

- `rwnd`는 수신자가 현재 더 받을 수 있다고 광고한 바이트 수입니다.
- `cwnd`는 송신자가 경로의 혼잡 상태를 바탕으로 정한 바이트 수입니다.
- `available`은 두 제한과 이미 전송한 바이트를 반영한 추가 송신 가능량입니다.

## 실행

```sh
python3 window_model.py
python3 -m unittest -v
```

예제는 MSS 1000, `rwnd=4000`, `cwnd=3000`에서 세 세그먼트를 보낸 뒤 추가 전송이 막히는 과정을 출력합니다. 누적 ACK가 1500바이트를 새로 확인하면 그만큼 다시 전송할 수 있습니다.

## 검사 항목

- 유효 윈도가 `min(rwnd, cwnd)`인지 확인합니다.
- 전송 중인 바이트가 윈도를 채우면 새 데이터 전송을 멈추는지 확인합니다.
- 누적 ACK가 `send_base`를 이동시키고 추가 송신 가능량을 늘리는지 확인합니다.
- 보내지 않은 바이트까지 ACK하는 입력을 거부하는지 확인합니다.
- 첫 RTT 표본, RTO 하한·상한, 지수 백오프를 확인합니다.
- Reno 느린 시작, 혼잡 회피, 중복 ACK, 빠른 복구, 제한 시간 처리를 확인합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Sender window state | `window_model.py::WindowSender` |
| 1-1 | Derived send capacity | `window_model.py::WindowSender` properties |
| 1-2 | Send and cumulative ACK sequence updates | `window_model.py::WindowSender` methods |
| 2 | RTT estimator and RTO backoff | `window_model.py::RttEstimator` |
| 3 | Reno congestion state | `window_model.py::RenoController` |
| 3-1 | ACK-driven Reno transitions | `window_model.py::RenoController.acknowledge` |
| 3-2 | Timeout recovery | `window_model.py::RenoController.timeout` |
| 4 | Deterministic demonstration | `window_model.py::demo` |

## 범위와 제한

- 32비트 순서 번호 순환을 처리하지 않습니다.
- SACK scoreboard와 실제 패킷 전송을 구현하지 않습니다.
- Zero window는 새 데이터 전송만 막으며 TCP persist timer와 probe는 재현하지 않습니다.
- Reno의 핵심 계산만 포함하며 실제 운영체제의 혼잡 제어 구현을 대체하지 않습니다.
