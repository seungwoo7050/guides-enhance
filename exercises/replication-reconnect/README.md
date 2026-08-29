# Replication and Reconnect

서버의 정본 상태를 스냅샷과 version이 있는 델타로 클라이언트에 전달하고, 손실·중복·순서 역전·`baseline` 불일치 뒤 다시 수렴시키는 시뮬레이터입니다. 재접속 때 보존된 이력이 연속이면 델타를 이어서 적용하고, 그렇지 않으면 full snapshot으로 바꿉니다.

## 제공 기능

- match, protocol, schema와 state version 검사
- full snapshot 적용과 오래된 snapshot 거절
- 같은 version에 서로 다른 snapshot이 온 경우 충돌 판정
- 현재 `baseline`에 바로 이어지는 델타만 적용
- duplicate delta를 한 번만 반영
- future delta를 제한된 수만 보류
- 연속된 보류 델타 자동 적용
- gap 한도 초과 시 resync 요청
- reconnect token을 이용한 델타 resume
- resume 실패 시 full snapshot 사용
- 클라이언트별 송신 큐 byte 상한
- 큐 초과 시 최신 snapshot으로 압축하거나 연결 종료
- 송신 큐를 FIFO 순서로 flush

## 파일

- `src/replication_reconnect/model.py`: message, client replica와 송신 큐 Record
- `src/replication_reconnect/engine.py`: message 검증, 델타 적용, 재접속과 큐 처리
- `src/replication_reconnect/serialization.py`: JSON 크기와 digest 계산
- `src/replication_reconnect/cli.py`: scenario 파일 실행
- `tests/test_replication.py`: loss, reorder, duplicate, reconnect와 큐 검사
- `examples/scenario.json`: snapshot, 순서가 뒤바뀐 delta와 reconnect 예제

## 요구 사항

- Python 3.11 이상
- 외부 package 없음

## 실행

```sh
PYTHONPATH=src python -m replication_reconnect examples/scenario.json --pretty
```

설치한 뒤에는 다음 명령을 사용할 수 있습니다.

```sh
python -m pip install .
replication-reconnect examples/scenario.json --pretty
```

지원 event는 `DELIVER`, `DISCONNECT`, `RECONNECT`, `ENQUEUE`, `FLUSH`입니다. 델타 operation은 `SET`, `DELETE`, `INCREMENT`이며 object path를 문자열 배열로 지정합니다.

## 검사

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 구현에서 지키는 조건

- 델타는 `version == baseline_version + 1`이어야 하며 현재 client version과 `baseline_version`이 같을 때만 상태를 바꿉니다.
- future delta는 `max_pending_deltas`와 `max_gap` 안에서만 보류합니다. 한도를 넘으면 보류 목록을 비우고 resync를 요청합니다.
- 여러 operation을 복사본에 먼저 적용하고 모두 성공한 경우에만 client state를 바꿉니다. 잘못된 path나 범위 오류가 부분 상태를 남기지 않습니다.
- reconnect 이력도 복사본에 먼저 적용합니다. 연속 구간 전체가 성공한 경우에만 기존 replica를 교체합니다.
- 같은 state version에 다른 내용의 snapshot이 도착하거나 server current version보다 앞선 메시지가 오면 적용하지 않고 resync를 요청합니다.
- 송신 큐가 상한을 넘으면 델타 여러 개를 최신 snapshot 하나로 바꿉니다. snapshot도 상한 안에 들어오지 않으면 해당 클라이언트 연결을 종료합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Replication message, replica, and queue records | `src/replication_reconnect/model.py` |
| 2 | Message envelope validation | `src/replication_reconnect/engine.py` |
| 2-1 | Snapshot content and size validation | `src/replication_reconnect/engine.py` |
| 2-2 | Delta operation validation | `src/replication_reconnect/engine.py` |
| 3 | Contiguous buffered-delta replay | `src/replication_reconnect/engine.py` |
| 4 | Version and baseline validation | `src/replication_reconnect/engine.py` |
| 4-1 | Bounded future-delta buffering | `src/replication_reconnect/engine.py` |
| 5 | Snapshot replacement and resync | `src/replication_reconnect/engine.py` |
| 6 | Reconnect resume with snapshot fallback | `src/replication_reconnect/engine.py` |
| 7 | Per-client outbound queue limit | `src/replication_reconnect/engine.py` |
| 7-1 | Snapshot compaction or client disconnect | `src/replication_reconnect/engine.py` |
| 8 | Stable convergence digest | `src/replication_reconnect/serialization.py` |
| 9 | Scenario file execution and exit status | `src/replication_reconnect/cli.py` |
| 10 | Replication loss, reorder, and queue regression tests | `tests/test_replication.py` |

## 범위와 제한

- 실제 packet MTU, encryption, compression과 transport retry는 구현하지 않습니다.
- client prediction과 rendering interpolation 품질은 평가하지 않습니다.
- 델타 path는 JSON object만 순회하며 배열 index operation은 제공하지 않습니다.
- reconnect token의 암호학적 서명은 검사하지 않습니다.
