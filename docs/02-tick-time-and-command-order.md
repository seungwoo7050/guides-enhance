# Tick, 시간과 명령 순서

## 목적

wall clock과 스레드 실행 순서에 의존하지 않고, 같은 초기 상태와 명령 목록에서 같은 정본 결과를 만드는 기준을 정합니다.

## 시간의 종류

- **monotonic time**: timeout과 경과 시간을 측정합니다. 시스템 시각 변경의 영향을 받지 않아야 합니다.
- **wall clock**: 사용자에게 표시할 시각과 운영 기록에 사용합니다.
- **tick index**: simulation의 진행 순서를 나타내는 정수입니다.
- **received time**: 서버가 명령을 받은 monotonic 시각입니다.
- **client time**: 지연 추정에 참고할 수 있지만 정본 순서의 유일한 기준으로 사용하지 않습니다.

서로 다른 용도의 시간을 하나의 timestamp로 처리하면 timeout, replay와 운영 기록의 의미가 섞입니다.

## Fixed tick

서버는 일정한 simulation step으로 상태를 진행합니다.

```text
network에서 명령 수신
→ 방별 inbox에 기록
→ tick 시작 시 처리할 명령 선택
→ 정해진 순서로 명령 검증과 적용
→ simulation 진행
→ event와 replication 상태 생성
→ tick 시간과 처리량 기록
```

실제 loop가 늦어져도 simulation step을 임의로 크게 만들지 않습니다. 한 번에 밀린 tick을 모두 처리하면 CPU 사용량이 더 늘 수 있으므로 최대 catch-up 횟수나 허용 lag를 둡니다.

## 명령 식별 정보

명령에는 최소한 다음 값이 필요합니다.

- `player_id`
- `session_id`
- `session_epoch`
- `room_id`
- `match_id`
- `sequence`
- `target_tick` 또는 적용 시점을 판단할 값
- `command_type`
- `payload`
- 서버가 기록한 수신 순서 또는 수신 시각

프로토콜에 따라 `client_tick`을 추가할 수 있습니다. 서버가 허용할 과거·미래 범위를 수치로 정해야 합니다.

## Sequence 판정

한 세션 안에서 `sequence`를 단조 증가시키는 방식이 일반적입니다.

- 이미 적용한 값 이하: duplicate 또는 stale로 거절합니다.
- 바로 다음 값: 적용 후보로 처리합니다.
- 값이 비어 있음: 제한된 buffer, 즉시 거절, resync 중 하나를 선택합니다.
- `session_epoch`가 다름: 이전 연결에서 늦게 도착한 명령으로 거절합니다.

검증에 실패한 명령은 `sequence`를 소비하지 않아야 합니다. 그렇지 않으면 잘못된 payload 하나가 뒤의 정상 명령을 모두 막을 수 있습니다.

## 같은 tick의 순서

여러 플레이어의 명령이 같은 tick에 들어오면 결과가 항상 같도록 비교 key를 정합니다. 예를 들면 다음과 같습니다.

```text
(target_tick, received_order, player_id, session_epoch, sequence, command_id)
```

어떤 key를 사용하든 충돌한 명령의 우선순위를 경기 규칙으로 설명할 수 있어야 합니다. 입력 JSON 배열의 순서나 스레드가 우연히 실행된 순서를 그대로 사용하지 않습니다.

## 처리 한도

다음 값을 함께 봅니다.

- tick 처리 시간
- tick lag
- inbox 길이
- 검사한 명령 수와 적용·거절 수
- catch-up 횟수
- 클라이언트별 송신 큐 길이

한 tick의 명령 한도는 적용 성공 수가 아니라 검사한 수를 기준으로 두는 편이 안전합니다. 잘못된 명령도 parsing, identity 확인과 payload 검증 비용을 사용하기 때문입니다.

처리량을 넘으면 다음과 같이 범위를 줄일 수 있습니다.

1. 새 join이나 비필수 명령을 제한합니다.
2. 너무 오래된 명령을 안정된 reason code로 거절합니다.
3. 비필수 replication 빈도를 낮춥니다.
4. 해당 방이나 server를 unhealthy로 표시하고 새 배치를 막습니다.
5. 제한된 drain 또는 종료 절차를 시작합니다.

큐를 무한히 늘리거나 catch-up을 끝낼 때까지 CPU를 계속 쓰는 방식은 피합니다.

## 결정적 검사

실제 timer와 `sleep` 대신 test clock과 고정된 명령 목록을 사용합니다.

```text
initial state
seed
commands grouped by arrival step
requested tick range
expected state digest
expected rejected commands
expected pending commands
```

같은 입력을 여러 번 실행해 상태 digest와 event 순서가 같아야 합니다. 명령 배열을 섞어도 정의한 정렬 기준에 따라 결과가 같아야 하는 경우라면 그 검사도 추가합니다.

## 확인 질문

- simulation tick과 실제 loop 지연을 어떻게 구분합니까?
- 같은 명령을 두 번 받으면 어느 값으로 중복을 판정합니까?
- `sequence` gap을 보류합니까, 거절합니까, resync합니까?
- 같은 tick에서 명령을 정렬하는 key는 무엇입니까?
- 한 tick에서 검사하는 명령 수와 catch-up 횟수의 상한은 얼마입니까?
- 실제 시간을 기다리지 않고 같은 실패를 어떻게 재현합니까?
