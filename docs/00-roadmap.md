# 게임 서버 기초 로드맵

## 과정의 종료점

이 과정의 목표는 게임 서버 관련 용어를 많이 외우는 것이 아닙니다. 다음 문제를 독립적으로 구현하고 검사할 수 있으면 과정을 마친 것으로 봅니다.

1. 서버가 변경하는 정본 상태와 클라이언트가 요청하는 명령을 분리합니다.
2. 고정 tick에서 명령을 일정한 순서로 처리하고 중복, 오래된 입력과 처리 한도를 판정합니다.
3. 연결, 세션, 플레이어, 방과 경기의 수명을 구분하고 재접속과 종료를 처리합니다.
4. 스냅샷과 델타를 version과 `baseline`으로 연결하고 손실 뒤 다시 수렴시킵니다.
5. 서버의 상태와 남은 용량을 확인해 경기를 배치하거나 제한된 큐에 넣거나 거절합니다.
6. 세션, 참가 관계, 소유권과 수치 범위를 확인한 뒤 명령을 적용하고 감사 기록을 남깁니다.
7. 고정된 입력, 논리 시각과 digest로 실패를 다시 만들고 첫 잘못된 변경을 찾습니다.

## 학습 방식

이 저장소는 문서를 모두 읽은 뒤 구현하는 방식으로 사용하지 않습니다.

```text
필요한 개념을 읽습니다.
→ 바로 대응하는 프로젝트를 실행하고 코드를 추적합니다.
→ 실패 검사를 확인합니다.
→ 다음 개념으로 넘어갑니다.
```

각 프로젝트는 별도 저장소로 복사해도 실행할 수 있습니다. 외부 capstone이나 다른 프로젝트를 완료 조건으로 요구하지 않습니다.

## 1단계: 정본 상태와 tick

먼저 다음 두 문서를 읽습니다.

- `01-authoritative-state-and-trust.md`
- `02-tick-time-and-command-order.md`

다음 질문에 답할 수 있어야 합니다.

- 클라이언트가 직접 정할 수 없는 값은 무엇입니까?
- 명령이 거절될 때 바뀌면 안 되는 값은 무엇입니까?
- 한 tick에서 명령을 어떤 key로 정렬합니까?
- `sequence`가 중복되거나 비었을 때 어떤 결과를 반환합니까?
- 늦어진 tick을 몇 번까지 따라잡습니까?

이후 `exercises/tick-command-model/`을 실행합니다. 설정과 입력을 검증하는 위치, 정렬 key, 명령 적용 전후 상태, tick별 검사 한도와 pending 결과를 확인합니다.

## 2단계: 연결과 게임 참가의 수명

다음 문서를 읽습니다.

- `03-connection-session-room-and-match-lifecycle.md`

이후 `exercises/session-room-lifecycle/`을 실행합니다. 특히 다음 항목을 확인합니다.

- 연결이 끊겨도 즉시 삭제하지 않는 상태
- `session_epoch`가 이전 연결을 막는 방법
- 중복 join과 중복 event가 인원수를 바꾸지 않는 이유
- grace 만료, 경기 종료, drain과 shutdown에서 제거하는 자원

## 3단계: protocol과 상태 복제

다음 문서를 읽습니다.

- `04-transport-protocol-and-state-replication.md`

이후 `exercises/replication-reconnect/`을 실행합니다.

- message의 match, protocol, schema, version을 언제 확인하는지 찾습니다.
- 현재 `baseline`과 맞지 않는 델타가 상태를 바꾸지 않는지 확인합니다.
- 순서가 뒤바뀐 델타를 몇 개까지 보류하는지 확인합니다.
- 재접속 이력이 끊겼을 때 full snapshot으로 바꾸는 조건을 확인합니다.
- 느린 클라이언트의 송신 큐가 상한을 넘을 때 어떤 결과가 남는지 확인합니다.

process 장애 뒤 durable snapshot과 replay가 필요하다면 `05-reconnect-snapshot-replay-and-recovery.md`를 추가로 읽습니다. 이 문서는 필수 경로가 아닙니다.

## 4단계: 수용 한도와 서버 배치

다음 문서를 읽습니다.

- `07-load-backpressure-placement-and-handover.md`

이후 `exercises/load-placement/`을 실행합니다.

- 오래된 heartbeat, drain 상태와 protocol 불일치 서버를 제외하는 위치를 찾습니다.
- 배치 뒤 room, player, tick cost, outbound bytes와 memory 사용량을 계산합니다.
- hard limit과 남겨야 할 headroom을 구분합니다.
- 배치 결정을 반환하기 전에 reservation을 반영하는지 확인합니다.
- 큐의 최대 크기와 deadline을 확인합니다.

문서의 handover 절은 선택 심화입니다. 기초 완료를 위해 실행 중인 경기를 다른 process로 옮길 필요는 없습니다.

## 5단계: 신뢰하지 않는 입력과 abuse 제한

다음 문서를 읽습니다.

- `08-security-abuse-and-anticheat-boundaries.md`

이후 `exercises/trust-abuse/`를 실행합니다.

- 세션, 연결, 플레이어, 방, 경기와 entity 소유 관계를 확인합니다.
- NaN, infinity, 큰 payload와 client가 직접 제출한 position·score를 거절합니다.
- 요청 제한 key에서 connection ID를 제외한 이유를 확인합니다.
- 상태 변경이 끝난 뒤에만 `sequence`를 기록하는지 확인합니다.
- 감사 기록에 원문 token과 payload가 남지 않는지 확인합니다.

## 6단계: 전체 검증

마지막으로 다음 문서를 읽습니다.

- `09-testing-observability-and-release-evidence.md`

다섯 프로젝트에서 다음 근거를 다시 확인합니다.

- 고정 seed 또는 고정 사건 목록
- 동일 입력의 동일 결과와 digest
- 중복·오래된 입력·순서 역전·제한 초과 검사
- 거절 뒤 상태 보존
- 큐와 처리량 상한
- 종료 뒤 자원 정리
- 구현하지 않은 운영 범위

## 선택 문서

| 문서 | 사용하는 시점 |
|---|---|
| `05-reconnect-snapshot-replay-and-recovery.md` | process 장애 뒤 경기 상태를 복구하거나 replay를 보존해야 할 때 |
| `06-persistence-side-effects-and-service-boundaries.md` | 경기 결과, 보상, DB transaction과 outbox를 연결할 때 |
| `90-language-and-runtime-profiles.md` | C++ 또는 Java로 실제 서버를 구현하며 수명과 실행 환경 차이를 확인할 때 |

## 완료 판정

다음 질문에 코드 위치와 실제 검사 이름으로 답할 수 있어야 합니다.

- 명령을 적용하는 유일한 위치는 어디입니까?
- 실패한 명령이 부분 상태를 남기지 않는 이유는 무엇입니까?
- 입력 순서가 달라도 결과가 같은 이유는 무엇입니까?
- 재접속 전 연결의 명령을 무엇으로 거절합니까?
- 델타 gap과 느린 클라이언트 큐의 최대치는 얼마입니까?
- 배치할 수 없는 요청은 언제 큐에 들어가고 언제 만료됩니까?
- reconnect로 요청 제한을 우회하지 못하는 이유는 무엇입니까?
- shutdown 뒤 어떤 collection이 비어 있어야 합니까?

답을 설명하지 못한 항목만 해당 문서와 검사를 다시 확인합니다.
