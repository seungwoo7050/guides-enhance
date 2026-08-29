# Session and Room Lifecycle

연결, 인증된 세션, 플레이어, 방과 경기의 수명을 분리해 처리하는 상태 기계 시뮬레이터입니다. 재접속 grace, `session_epoch`, drain과 shutdown을 논리 시각으로 실행하므로 실제 socket이나 timer 없이 같은 사건을 다시 재현할 수 있습니다.

## 제공 기능

- 연결과 세션 소유 관계 분리
- 인증되지 않은 연결의 방 작업 거절
- disconnect 뒤 제한된 재접속 grace
- 이전 `session_epoch`를 사용한 재접속 차단
- grace 만료 시 기권 처리와 방 owner 승계
- duplicate event와 duplicate join의 상태 보존
- 참가자 준비 상태와 경기 시작 조건 확인
- 경기 결과 한 번만 확정
- drain 중 새 방, 참가와 경기 시작 차단
- shutdown 시 연결, 세션, 플레이어, 방과 경기 정리

## 파일

- `src/session_room_lifecycle/model.py`: 연결, 세션, 플레이어, 방, 경기와 판정 Record
- `src/session_room_lifecycle/engine.py`: 사건 처리, 재접속, 경기와 자원 정리
- `src/session_room_lifecycle/serialization.py`: 상태 trace와 digest 계산
- `src/session_room_lifecycle/cli.py`: scenario 파일 실행
- `tests/test_lifecycle.py`: 재접속, 중복, drain과 cleanup 검사
- `examples/scenario.json`: 전체 수명 예제

## 요구 사항

- Python 3.11 이상
- 외부 package 없음

## 실행

```sh
PYTHONPATH=src python -m session_room_lifecycle examples/scenario.json --pretty
```

설치한 뒤에는 다음 명령을 사용할 수 있습니다.

```sh
python -m pip install .
session-room-lifecycle examples/scenario.json --pretty
```

각 event에는 `event_id`, `kind`, `logical_time`이 필요합니다. 지원하는 종류는 다음과 같습니다.

```text
CONNECT
AUTHENTICATE
CREATE_ROOM
JOIN_ROOM
READY
START_MATCH
DISCONNECT
RECONNECT
LEAVE_ROOM
END_MATCH
CLOSE_ROOM
BEGIN_DRAIN
ADVANCE_TIME
SHUTDOWN
```

## 검사

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 구현에서 지키는 조건

- 연결이 끊겨도 세션, 플레이어와 진행 중 경기의 참가 정보는 즉시 삭제하지 않습니다.
- 재접속은 현재 `epoch + 1`만 허용합니다. 이전 연결이 현재 세션을 다시 소유하지 못합니다.
- grace가 끝난 플레이어가 진행 중 경기에 속하면 참가 기록을 유지하고 `forfeited`로 표시합니다. 진행 중 경기가 없으면 방에서 제거합니다.
- 같은 `event_id`와 같은 내용은 `DUPLICATE_EVENT`로 무시합니다. 같은 ID에 다른 내용을 넣으면 `EVENT_ID_CONFLICT`로 거절하고 시각과 자원을 바꾸지 않습니다.
- 경기 중 owner가 만료되면 남은 참가자에게 owner를 넘깁니다. 모든 참가자가 기권하면 경기와 방을 정리합니다.
- `SHUTDOWN`은 모든 collection을 비우고 최종 snapshot에 남은 자원이 없게 합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Connection, session, player, room, and match records | `src/session_room_lifecycle/model.py` |
| 2 | Logical time and event deduplication | `src/session_room_lifecycle/engine.py` |
| 3 | Connection creation and session ownership | `src/session_room_lifecycle/engine.py` |
| 3-1 | Authentication binding | `src/session_room_lifecycle/engine.py` |
| 3-2 | Disconnect grace and expiry | `src/session_room_lifecycle/engine.py` |
| 3-3 | Epoch-checked reconnect | `src/session_room_lifecycle/engine.py` |
| 4 | Room creation and membership | `src/session_room_lifecycle/engine.py` |
| 4-1 | Duplicate-safe readiness updates | `src/session_room_lifecycle/engine.py` |
| 5 | Match start and phase transitions | `src/session_room_lifecycle/engine.py` |
| 5-1 | Result finalization and expired-player cleanup | `src/session_room_lifecycle/engine.py` |
| 6 | Drain admission checks | `src/session_room_lifecycle/engine.py` |
| 7 | Shutdown cleanup | `src/session_room_lifecycle/engine.py` |
| 8 | Stable lifecycle trace digest | `src/session_room_lifecycle/serialization.py` |
| 9 | Scenario file execution and exit status | `src/session_room_lifecycle/cli.py` |
| 10 | Lifecycle ownership and cleanup regression tests | `tests/test_lifecycle.py` |

## 범위와 제한

- 실제 authentication provider, socket과 process supervisor는 포함하지 않습니다.
- grace 만료 시 AI takeover 대신 기권을 선택합니다.
- process 장애 뒤 경기 migration은 보장하지 않습니다.
- event 목록의 `logical_time`은 감소할 수 없습니다.
