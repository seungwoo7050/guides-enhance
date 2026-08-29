# Test, 관측과 release 근거

## 목적

실행할 때마다 결과가 달라지는 통합 검사 하나로 게임 서버를 검증하지 않습니다. 상태 계산, room 수명, protocol, process 종료, 부하와 release 호환성을 서로 다른 검사로 나눕니다.

## 검사 구분

### 1. 결정적 상태 계산

- test clock
- 고정 random seed
- 고정 command trace
- tick별 예상 상태 또는 hash
- 거절한 명령과 reason code

실제 socket과 thread 없이 경기 규칙, 명령 순서와 상태 변경을 검사합니다.

### 2. Room 통합

- 실제 room object와 queue
- connection adapter의 fake 또는 loopback 구현
- join, tick, disconnect, reconnect와 경기 종료
- shutdown과 자원 정리

연결이 끊긴 뒤 플레이어를 즉시 지우거나 재접속에서 참가자를 두 번 추가하는 오류를 찾습니다.

### 3. Protocol 검사

- framing, 최대 길이와 알 수 없는 version
- partial read와 partial write
- duplicate, loss와 reorder
- snapshot과 delta baseline
- 이전 `session_epoch`
- 지원 version별 fixture

전달 순서가 바뀌어도 허용된 경우 같은 최종 상태에 도달하는지 확인합니다.

### 4. Process 통합

- server process 시작과 readiness
- bot client 연결
- signal과 graceful shutdown
- restart 뒤 snapshot과 result 상태
- port와 file descriptor 정리

process 종료 상태와 stderr를 확인해 설정 오류와 runtime 오류를 구분합니다.

### 5. 부하와 fault

- bot 수와 명령 빈도
- slow receiver
- reconnect storm
- external service timeout
- queue limit과 load shedding
- tick 시간 회귀

평균값 하나만 보지 않고 p50, p95, p99와 오류·큐 길이를 함께 기록합니다.

## 실패했을 때 남길 값

다음을 함께 기록합니다.

- seed
- command 또는 packet trace
- server release
- protocol, schema와 rule version
- 첫 실패 tick
- 예상 상태 hash와 실제 상태 hash
- 관련 metric과 reason code

긴 log만 남기지 않고 실패를 재현하는 최소 입력으로 줄입니다.

## Log

구조화된 event에는 다음 식별자를 사용합니다.

- server instance와 release
- room과 match
- player, session과 connection
- command, operation과 event
- protocol과 rule version
- tick
- decision과 reason code

모든 tick의 모든 entity를 일반 log에 남기지 않습니다. 자세한 trace는 필요할 때만 활성화하고 보존 기간을 제한합니다.

secret, raw credential, reconnect token과 원문 payload는 기록하지 않습니다.

## Metric

필수 후보:

- active connection, room과 match 수
- tick duration, lag와 catch-up 횟수
- reason code별 command 허용·거절 수
- inbound와 outbound queue 길이
- 송수신 byte와 message 수
- snapshot과 delta 크기
- reconnect 성공·실패 수
- result의 pending, accepted, unknown 수
- process memory, allocation, GC와 thread 사용량

player ID와 match ID처럼 값의 종류가 계속 늘어나는 식별자를 metric label에 직접 넣지 않습니다.

## Trace와 correlation

network request, match placement, room 생성, result operation과 outbox를 연결할 correlation ID를 정합니다. 모든 gameplay packet을 분산 trace span으로 만들 필요는 없습니다. 중요 event와 sampling 기준을 정합니다.

## Release 호환성

release 전에 필요한 조합을 검사합니다.

- current server + current client
- new server + 현재 지원 중인 client
- 필요한 경우 current server + new client
- 이전 rule version의 replay fixture
- snapshot schema migration
- rolling restart 또는 drain 절차

protocol version과 server release를 같은 값으로 사용하지 않습니다.

## Smoke test

최소 실행 경로는 다음과 같습니다.

```text
server 시작
→ readiness 확인
→ bot 두 개 연결
→ join
→ 명령 처리
→ snapshot 수신
→ disconnect와 reconnect
→ 경기 종료
→ result 확인
→ graceful shutdown
```

로컬 smoke test가 공용망, cloud load balancer와 장시간 운영을 검증하지는 않습니다.

## 성능 결과에 함께 기록할 값

- hardware와 OS
- runtime 또는 compiler version
- build type과 option
- bot scenario와 seed
- 실행 시간과 warm-up
- room, player와 command 수
- tick p50, p95, p99
- queue 길이와 error rate
- test tool version

측정 조건 없이 단일 평균값만 제시하지 않습니다.

## 완료 근거

- 결정적 상태 검사
- protocol compatibility fixture
- loss, duplicate와 reorder fixture
- process smoke test
- queue와 처리량 상한 검사
- 자원 정리 결과
- 지원 version 표
- 자동 검사로 확인하지 못한 범위

## 확인 질문

- 같은 seed와 trace로 실패를 다시 만들 수 있습니까?
- 첫 잘못된 tick과 command를 찾을 수 있습니까?
- 거절 뒤 상태가 보존되는지 어떤 검사가 확인합니까?
- queue와 catch-up이 정한 상한을 넘지 않는지 확인합니까?
- metric label의 종류가 무제한 늘어나지 않습니까?
- release가 지원하는 client, protocol과 snapshot version은 무엇입니까?
- 로컬 검사가 실제 운영에서 보장하지 않는 항목은 무엇입니까?
