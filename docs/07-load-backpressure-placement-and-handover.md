# 부하, 처리량 제한, 배치와 인계

## 목적

평균 CPU 사용률 하나로 서버 수용량을 판단하지 않습니다. tick 시간, 방과 플레이어 수, 명령 큐, 송신 큐, 메모리와 network 사용량을 함께 보고 새 연결과 경기를 받을지 결정합니다.

## Capacity를 나타내는 값

게임 서버는 request per second만으로 수용량을 표현하기 어렵습니다. 다음 값을 함께 측정합니다.

- active room 수
- active player와 connection 수
- tick마다 검사·적용하는 명령 수
- tick p50, p95, p99 시간
- tick lag와 catch-up 횟수
- inbound queue 길이
- 클라이언트별 송신 큐 길이
- 송수신 byte 수
- snapshot과 delta 크기
- room과 player당 메모리
- GC pause 또는 allocation rate
- worker와 event loop 사용량

서버 배치 시 사용하는 값과 실제 운영에서 측정하는 단위를 일치시켜야 합니다.

## Admission control

새 연결, 방과 경기를 받을 조건을 정합니다.

- 현재 room과 player 수
- 최근 tick 시간 초과 여부
- 남은 memory
- 남은 network 처리량
- 각 큐 길이
- server의 `ACTIVE`, `DRAINING`, `UNAVAILABLE` 상태
- 마지막 heartbeat 시각
- protocol version 호환 여부

수용량을 넘으면 무한 대기시키지 않습니다. 재시도 가능한 거절, 제한된 큐 또는 다른 server 배치 중 하나를 반환합니다.

## Queue 상한

### Inbound

- connection별 명령 요청 제한
- 방 inbox 최대 길이
- 오래된 명령 폐기
- 비필수 명령 축소
- authentication과 join 큐 분리

### Outbound

- 클라이언트별 송신 큐 최대 byte 수
- 오래된 상태 update를 최신 snapshot으로 교체
- 반드시 전달해야 하는 메시지와 대체 가능한 delta 분리
- 느린 클라이언트 resync 또는 disconnect

### External service

- result와 telemetry 큐 최대 길이
- 제한된 retry 횟수와 deadline
- disk-backed outbox 필요 여부
- 비필수 telemetry sampling

각 큐에는 상한뿐 아니라 상한을 넘었을 때 반환할 결과가 있어야 합니다.

## Match placement

단순 round-robin이나 room 수 하나만으로 서버를 선택하지 않습니다. 다음 조건을 차례로 확인합니다.

1. server가 active이며 heartbeat가 오래되지 않았습니다.
2. protocol과 rule version이 맞습니다.
3. region 또는 latency group이 요청에 맞습니다.
4. 배치 뒤 room, player, tick, memory와 network hard limit을 넘지 않습니다.
5. 장애나 순간 부하에 대비해 정한 headroom을 남깁니다.
6. 같은 조건이면 항상 같은 tie-breaker로 결과를 고릅니다.

배치를 결정하면 응답하기 전에 reservation을 반영합니다. 그렇지 않으면 연속된 두 요청이 같은 남은 용량을 모두 사용했다고 판단할 수 있습니다.

`request_id`를 다시 받아도 두 번째 reservation을 만들지 않습니다.

## 제한된 대기열

바로 배치할 수 없는 요청을 큐에 넣을 수 있습니다. 다음 값을 정합니다.

- 최대 요청 수
- 요청 생성 시각
- deadline
- 재평가 시점
- 정렬 기준
- 큐가 가득 찼을 때 reason code

이미 deadline을 넘긴 요청은 다시 배치하지 않습니다. 새 heartbeat나 경기 종료로 용량이 생겼을 때 큐를 다시 확인합니다.

## Graceful drain

서버를 교체하거나 종료할 때 다음 순서를 사용합니다.

```text
새 match placement 중단
→ 새 join 제한
→ 진행 중 match 완료 대기
→ 제한 시간을 넘긴 match 처리
→ result와 outbox flush
→ room과 connection 정리
→ process 종료
```

장시간 경기를 무기한 기다리지 않습니다. 제품 요구에 따라 snapshot handover, 경기 중단 또는 별도 장기 server pool을 선택합니다.

## Handover

실행 중인 방을 다른 process로 옮기는 작업은 선택 심화입니다. 필요하다면 다음 값을 함께 옮깁니다.

- authoritative snapshot과 tick
- 명령 sequence와 `session_epoch`
- replication baseline
- timer와 cooldown 상태
- result와 outbox 진행 상태
- destination ownership epoch

source와 destination이 동시에 같은 방을 변경하지 못하도록 fencing이나 ownership epoch를 사용합니다.

## Synthetic load

실제 사용자를 기다리지 않고 bot과 고정 scenario로 부하를 만듭니다.

- idle connection
- 일정한 명령 빈도의 플레이어
- burst join과 leave
- slow receiver
- reconnect storm
- 큰 snapshot
- external result service timeout

결과에는 seed, bot version, server release, hardware와 runtime 설정, 실행 시간을 함께 기록합니다.

## 확인 질문

- 수용량을 room, player, tick budget 중 무엇으로 측정합니까?
- 새 경기를 처음 거절하는 조건은 무엇입니까?
- 각 큐의 최대 길이와 초과 결과는 무엇입니까?
- reservation을 어느 시점에 server usage에 반영합니까?
- 느린 클라이언트 하나가 방 전체를 막지 않는 이유는 무엇입니까?
- drain 중 새 join과 장기 match를 어떻게 처리합니까?
- handover를 구현한다면 writer가 하나임을 무엇으로 보장합니까?
