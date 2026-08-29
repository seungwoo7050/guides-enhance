# 저장, 부수 효과와 service 분리

## 역할

이 문서는 선택 심화입니다. 실시간 방 상태와 account, inventory, rating, reward처럼 오래 저장할 값을 연결할 때 사용합니다.

## 상태를 변경하는 주체

| 상태 | 일반적인 변경 주체 |
|---|---|
| 현재 위치, 체력, cooldown | room server |
| connection과 replication 상태 | room server |
| account와 entitlement | account service 또는 DB |
| inventory와 currency | inventory·economy service |
| matchmaking ticket | matchmaking service |
| match result 원본 | result service 또는 transaction DB |
| leaderboard projection | 조회용 저장소 |

room server가 모든 업무 데이터를 직접 수정하면 process 재시작, retry와 scale-out에서 중복 효과를 제어하기 어렵습니다.

## 경기 시작 전에 읽는 값

방이 외부 상태를 읽을 때 다음을 정합니다.

- 읽은 값의 version
- 경기 중 변경을 반영할지 여부
- 경기 중 바뀌면 안 되는 값
- 읽기 실패와 timeout 처리
- 시작 요청의 `operation_id`

예를 들어 loadout을 경기 시작 시 고정하고 경기 중 inventory 변경은 반영하지 않을 수 있습니다.

## 경기 결과

결과에는 최소한 다음 식별자를 포함합니다.

- match ID
- result operation ID
- rule version
- 참가자와 결과
- 결과를 만든 room, server와 release
- terminal tick 또는 종료 reason
- 필요하다면 state hash와 replay hash

같은 결과를 여러 번 보내도 업무 상태와 reward는 한 번만 바뀌어야 합니다.

## Transaction과 outbox

결과 저장과 후속 event 발행을 한 DB에서 처리한다면 다음 순서를 사용할 수 있습니다.

```text
result operation ID 중복 확인
→ 업무 상태 변경
→ outbox record 저장
→ 같은 DB transaction commit
→ 별도 dispatcher가 event 발행
→ 중단 뒤 미전송 outbox 재처리
```

업무 상태 commit과 message publish를 서로 독립적인 성공으로 처리하면 한쪽만 남는 구간이 생깁니다. outbox는 그 구간을 DB transaction 안으로 옮깁니다.

## 결과를 알 수 없는 경우

room server가 결과를 보낸 뒤 timeout이 발생하면 성공이나 실패로 단정하지 않습니다.

- 같은 `operation_id`로 다시 요청합니다.
- result service에서 현재 상태를 조회합니다.
- `PENDING`, `ACCEPTED`, `REJECTED`, `UNKNOWN`을 구분합니다.
- 방 종료 전에 확정할지, 별도 reconciliation 작업으로 넘길지 정합니다.

## Database 사용 기준

실시간 위치를 매 tick 관계형 DB에 저장하지 않습니다. DB는 다음 값에 더 적합합니다.

- account와 entitlement
- 경기 metadata와 최종 결과
- inventory와 currency transaction
- reconnect와 replay metadata
- operation과 outbox

schema 제약, transaction, index와 migration은 database 학습 자료에서 별도로 확인합니다.

## Cache와 임시 상태

cache에만 있는 값은 cache 유실 뒤 결과를 정해야 합니다.

- 다시 계산할 수 있습니다.
- 원본 저장소에서 다시 읽을 수 있습니다.
- 복구할 수 없어 경기를 중단해야 합니다.

cache hit 여부가 경기 결과나 reward를 바꾸지 않게 합니다.

## Service를 나누는 기준

다음 이유만으로 process나 service를 나누지 않습니다.

- class가 많습니다.
- 팀이 언젠가 커질 수 있습니다.
- 특정 framework를 사용하고 싶습니다.

상태를 변경하는 주체, 수명, 확장 단위, 보안 요구와 복구 방법이 실제로 다를 때 분리를 검토합니다.

## 확인할 실패

- result 저장 성공 뒤 response 유실
- outbox 저장 전 process 종료
- outbox 저장 뒤 publish 전 종료
- 같은 match result 두 번 수신
- reward 적용 뒤 leaderboard 갱신 실패
- 경기 시작용 loadout version 불일치
- cache 유실 뒤 room 복구

## 확인 질문

- 현재 방 상태와 장기 저장 상태를 각각 누가 바꿉니까?
- 경기 결과 중복을 어떤 key로 막습니까?
- timeout 뒤 결과 상태를 어떻게 확인합니까?
- outbox 처리의 각 중단 지점에 무엇이 남습니까?
- cache가 사라지면 어떤 값을 다시 만들 수 있습니까?
