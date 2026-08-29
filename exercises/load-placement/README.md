# Load and Placement

여러 게임 서버 process의 방, 플레이어, tick cost, 송신 큐와 메모리 사용량을 함께 계산해 새 경기를 배치하는 시뮬레이터입니다. hard limit과 남겨야 할 headroom을 구분하고, 배치할 수 없는 요청은 제한된 큐에 넣거나 명시적으로 거절합니다.

## 제공 기능

- `ACTIVE`, `DRAINING`, `UNAVAILABLE` 서버 구분
- 오래된 heartbeat 서버 제외
- protocol version 호환성 검사
- room, player, tick, outbound bytes와 memory hard limit 검사
- 배치 뒤에도 정한 headroom 유지
- region preference와 배치 후 사용률을 이용한 안정된 점수 계산
- `created_at` 이전 요청 거절
- 배치 결정과 동시에 reservation 반영
- 같은 `request_id`의 중복 배치 방지
- 최대 크기와 deadline이 있는 대기열
- heartbeat와 경기 종료 뒤 큐 재평가
- drain 중 새 경기 배치 차단
- 기존 경기 완료 시 capacity 반환과 drain 완료 판정

## 파일

- `src/load_placement/model.py`: server, request, reservation과 decision Record
- `src/load_placement/engine.py`: 입력 검증, 후보 선택, 배치, 큐와 drain 처리
- `src/load_placement/serialization.py`: 배치 결과 digest 계산
- `src/load_placement/cli.py`: scenario 파일 실행
- `tests/test_placement.py`: capacity, stale heartbeat, queue, duplicate와 drain 검사
- `examples/scenario.json`: 두 region의 배치와 drain 예제

## 요구 사항

- Python 3.11 이상
- 외부 package 없음

## 실행

```sh
PYTHONPATH=src python -m load_placement examples/scenario.json --pretty
```

설치한 뒤에는 다음 명령을 사용할 수 있습니다.

```sh
python -m pip install .
load-placement examples/scenario.json --pretty
```

지원 event는 `REQUEST`, `ADVANCE_TIME`, `BEGIN_DRAIN`, `COMPLETE_MATCH`, `HEARTBEAT`입니다. 모든 event의 `logical_time`은 감소할 수 없습니다.

## 검사

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 구현에서 지키는 조건

- heartbeat가 오래됐거나 drain 중이거나 protocol이 다른 서버는 capacity 계산 전에 후보에서 제외합니다.
- hard limit은 room 수뿐 아니라 player, tick cost, outbound bytes와 memory를 함께 확인합니다.
- region preference를 먼저 적용하고, 같은 순위에서는 배치 후 최대 사용률과 평균 사용률이 낮은 서버를 고릅니다. 마지막 tie-breaker는 `server_id`입니다.
- 배치 결정을 반환하기 전에 reservation을 server usage에 반영합니다. 연속된 두 요청이 같은 남은 용량을 함께 사용하지 못합니다.
- event 시각이 `created_at`보다 이르면 `REQUEST_NOT_CREATED`로 거절하며 해당 request ID를 저장하지 않습니다.
- 같은 `request_id`는 기존 결정을 반환하고 두 번째 room이나 reservation을 만들지 않습니다.
- 큐는 `created_at`, `request_id` 순으로 처리하고 deadline을 넘긴 요청을 `DEADLINE_EXPIRED`로 종료합니다.
- drain은 진행 중 경기를 이동하지 않습니다. 새 배치만 막고 기존 reservation이 모두 반환되면 `DRAIN_COMPLETE`를 기록합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Server, request, reservation, and decision records | `src/load_placement/model.py` |
| 2 | Scenario server and request validation | `src/load_placement/engine.py` |
| 3 | Health, drain, and protocol filtering | `src/load_placement/engine.py` |
| 3-1 | Hard and soft capacity checks | `src/load_placement/engine.py` |
| 3-2 | Headroom-aware stable scoring | `src/load_placement/engine.py` |
| 4 | Candidate server selection | `src/load_placement/engine.py` |
| 5 | Immediate reservation and duplicate request handling | `src/load_placement/engine.py` |
| 6 | Bounded placement queue | `src/load_placement/engine.py` |
| 6-1 | Queue deadline expiry and retry | `src/load_placement/engine.py` |
| 7 | Drain tracking and capacity release | `src/load_placement/engine.py` |
| 8 | Stable placement result digest | `src/load_placement/serialization.py` |
| 9 | Scenario file execution and exit status | `src/load_placement/cli.py` |
| 10 | Capacity, queue, and drain regression tests | `tests/test_placement.py` |

## 범위와 제한

- 실제 orchestration, process restart와 autoscaling API는 포함하지 않습니다.
- process 장애 뒤 진행 중인 경기를 다른 서버로 옮기지 않습니다.
- region은 실제 latency 측정값이 아니라 요청에 적힌 preference 순서로 평가합니다.
- resource 값은 scenario에서 정한 정수 단위입니다. 실제 CPU 사용률이나 byte sampling을 수집하지 않습니다.
