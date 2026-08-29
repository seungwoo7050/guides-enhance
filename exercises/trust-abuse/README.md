# Trust and Abuse

클라이언트가 보낸 position, score와 ownership을 정본 값으로 저장하지 않고, 세션·플레이어·방·경기 관계와 명령 규칙을 확인한 뒤 허용한 요청만 반영하는 시뮬레이터입니다. 논리 시각으로 동작하는 token bucket, 비밀값을 제거한 감사 기록과 입력 순서에 영향을 받지 않는 alert 집계를 제공합니다.

## 제공 기능

- actor, session, connection, `session_epoch`와 player 연결 검사
- room과 running match 참가 관계 확인
- 다른 player, room, match와 entity 조작 차단
- payload byte 수, NaN, infinity와 정수 범위 검사
- 서버가 계산하는 상대 이동 명령
- `SET_POSITION`, `SET_SCORE`, `CLAIM_OWNERSHIP` 거절
- 명령 종류별 token bucket 요청 제한
- 재접속 뒤에도 유지되는 session/player 기반 제한 key
- 상태와 `sequence`를 성공 뒤에만 반영
- duplicate `command_id`와 ID 충돌 요청의 반복 효과 차단
- 인증된 actor와 client가 주장한 actor를 구분한 감사 기록
- token과 원문 payload를 남기지 않는 audit
- 입력 순서와 중복에 영향을 받지 않는 alert 집합

## 파일

- `src/trust_abuse/model.py`: identity, 정본 상태, 요청 제한과 판정 Record
- `src/trust_abuse/engine.py`: 입력 검증, 명령 적용, 요청 제한, audit와 alert 처리
- `src/trust_abuse/serialization.py`: JSON 크기와 digest 계산
- `src/trust_abuse/cli.py`: scenario 파일 실행
- `tests/test_trust.py`: 소유 관계, 범위, 요청 제한, 비밀값 제거와 alert 검사
- `examples/scenario.json`: 정상 이동, entity 사용과 위조 score 거절 예제

## 요구 사항

- Python 3.11 이상
- 외부 package 없음

## 실행

```sh
PYTHONPATH=src python -m trust_abuse examples/scenario.json --pretty
```

설치한 뒤에는 다음 명령을 사용할 수 있습니다.

```sh
python -m pip install .
trust-abuse examples/scenario.json --pretty
```

지원 event는 `COMMAND`와 `RECONNECT`입니다. 구현된 명령은 `MOVE`, `USE_OWNED_ENTITY`입니다. 클라이언트가 정본 값을 직접 정하려는 명령은 stable `reason_code`로 거절합니다.

## 검사

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 구현에서 지키는 조건

- 요청 제한 key는 `session_id`, `player_id`, command kind로 구성합니다. connection ID를 바꿔도 기존 bucket을 우회할 수 없습니다.
- 인증과 참가 관계를 통과한 명령은 최종 허용 여부와 관계없이 token을 소비합니다. 잘못된 요청으로 비싼 검증을 무제한 반복하지 못하게 하기 위해서입니다.
- payload, `sequence`와 적용할 다음 값을 모두 확인한 뒤에만 정본 상태와 `last_sequence`를 바꿉니다.
- 같은 `command_id`와 같은 내용은 `DUPLICATE_COMMAND`로 무시합니다. 같은 ID에 다른 내용을 넣으면 `COMMAND_ID_CONFLICT`로 거절하고 최초 판정 cache는 유지합니다.
- 같은 충돌 요청을 다시 보내도 audit와 alert 수를 늘리지 않습니다.
- audit에는 인증된 세션에서 확인한 actor와 클라이언트가 주장한 actor를 구분해 기록합니다. payload는 byte 수와 digest만 남기며 인증 token과 원문을 저장하지 않습니다.
- 재접속이 다른 active session의 connection ID를 가져가려 하면 `CONNECTION_ALREADY_BOUND`로 거절합니다.
- alert는 actor, match, reason별 고유 command ID 집합으로 계산합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Identity, authoritative state, rate-limit, and decision records | `src/trust_abuse/model.py` |
| 2 | Initial identity and membership consistency | `src/trust_abuse/engine.py` |
| 3 | Payload size and finite-number checks | `src/trust_abuse/engine.py` |
| 4 | Command envelope normalization | `src/trust_abuse/engine.py` |
| 5 | Session epoch and connection validation | `src/trust_abuse/engine.py` |
| 5-1 | Room, match, and ownership validation | `src/trust_abuse/engine.py` |
| 6 | Logical-time token bucket | `src/trust_abuse/engine.py` |
| 6-1 | Reconnect-stable rate-limit keys | `src/trust_abuse/engine.py` |
| 7 | Validate and prepare authoritative changes | `src/trust_abuse/engine.py` |
| 7-1 | Commit sequence after state change | `src/trust_abuse/engine.py` |
| 8 | Redacted audit records | `src/trust_abuse/engine.py` |
| 9 | Duplicate command decision reuse | `src/trust_abuse/engine.py` |
| 10 | Order-stable alert aggregation | `src/trust_abuse/engine.py` |
| 11 | Stable authoritative-state digest | `src/trust_abuse/serialization.py` |
| 12 | Scenario file execution and exit status | `src/trust_abuse/cli.py` |
| 13 | Trust, rate-limit, audit, and alert regression tests | `tests/test_trust.py` |

## 범위와 제한

- kernel driver, client anti-cheat와 intrusion testing은 포함하지 않습니다.
- token signature와 authentication provider 검증은 scenario의 initial identity가 완료했다고 가정합니다.
- `MOVE`는 전체 물리 simulation이 아니라 제한된 상대 이동만 계산합니다.
- alert는 결정적인 집계 예제이며 실제 운영 탐지 정확도를 주장하지 않습니다.
