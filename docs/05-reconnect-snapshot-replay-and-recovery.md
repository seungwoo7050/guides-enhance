# 재접속, snapshot, replay와 복구

## 역할

이 문서는 선택 과정입니다. 연결이 끊긴 클라이언트를 다시 동기화하는 수준을 넘어, process 장애 뒤 경기 상태를 어느 지점까지 복구할지 정할 때 사용합니다.

## 상태 분류

| 상태 | 예시 | 보존 기준 |
|---|---|---|
| transient connection | socket, 송신 큐, handshake | 재접속 때 새로 생성 |
| session continuity | `session_epoch`, reconnect token | 짧은 기간 보존 |
| authoritative room state | entity, 점수, 경기 단계, tick | 재접속과 필요 시 장애 복구 |
| command trace | 검증을 통과한 gameplay 명령 | replay와 조사에 필요할 때 보존 |
| external result | reward, rating, match record | 별도 service나 DB에 저장 |
| presentation state | animation, camera | 서버 복구 대상이 아님 |

무엇을 복구할지 정하기 전에 상태별 소유자, 보존 시간과 손실 허용량을 적습니다.

## Reconnect 절차

```text
새 connection 인증
→ reconnect token과 session epoch 확인
→ 이전 connection 무효화
→ player, room, match 존재 확인
→ full snapshot과 새 baseline 전송
→ client의 baseline 확인
→ delta 전송 재개
```

재접속은 process 장애 복구와 다릅니다. 재접속에서는 서버의 정본 상태가 살아 있다고 가정합니다. process 장애 복구는 정본 상태 자체를 다시 만들어야 합니다.

## Snapshot

스냅샷은 특정 tick의 정본 상태를 다시 만들 수 있는 자료입니다. 최소한 다음 metadata가 필요합니다.

- match와 room ID
- gameplay rule version
- state schema version
- authoritative tick
- random seed 또는 RNG state
- entity generation
- checksum 또는 hash
- 스냅샷을 만든 server release

파일로 저장한다면 부분 파일이 정상 파일처럼 보이지 않게 임시 파일과 atomic rename을 사용하거나 transaction으로 저장합니다. 스냅샷을 기록한 뒤 ACK가 유실돼도 같은 식별자로 다시 확인할 수 있어야 합니다.

## Replay

replay는 화면 녹화가 아니라 초기 상태와 명령·이벤트의 적용 순서를 다시 실행하는 자료입니다.

필수 항목:

- 초기 상태 또는 시작 스냅샷
- 각 명령이 적용된 tick
- 같은 tick에서의 정렬 순서
- gameplay rule, protocol, schema와 release version
- random seed와 외부 결정 입력
- 중간 state hash

모든 platform에서 bit 단위로 같은 결과가 나온다고 가정하지 않습니다. 필요한 재현 수준을 다음 중 하나로 정합니다.

- 같은 build와 platform에서 같은 state hash
- 정한 오차 범위 안에서 같은 결과
- 중요한 gameplay invariant가 같음

## Crash recovery 수준

### 복구하지 않음

짧은 casual match라면 process 장애 시 경기를 중단하고 보상하지 않을 수 있습니다. 이 선택도 명시적인 제품 결정입니다.

### 마지막 snapshot으로 복구

가장 최근 스냅샷으로 돌아갑니다. 스냅샷 이후 명령을 저장하지 않았다면 그 구간은 잃습니다. 허용할 최대 손실량, 즉 RPO를 수치로 정합니다.

### snapshot과 지속 command log로 복구

마지막 스냅샷 뒤의 검증된 명령이나 이벤트를 durable log에 기록하고 다시 적용합니다. 복구 범위는 넓어지지만 저장 지연, 비용과 오류 처리가 늘어납니다.

## 결과 처리와 구분

경기 상태를 복구할 수 있다고 reward를 안전하게 다시 지급할 수 있는 것은 아닙니다. 경기 결과는 별도 `operation_id`와 외부 저장소의 중복 처리 방지로 관리합니다. room state replay가 보상 지급을 자동으로 다시 실행하게 두지 않습니다.

## 보존과 삭제

- reconnect token은 짧은 TTL 뒤 삭제합니다.
- snapshot과 replay의 보존 기간과 최대 용량을 정합니다.
- account 삭제 요청이 replay, log와 export에 어떻게 반영되는지 구분합니다.
- debug 파일에 secret과 불필요한 개인정보를 넣지 않습니다.
- 오래된 schema를 언제까지 읽을지 명시합니다.

## 확인할 실패

- 스냅샷 파일을 쓰는 중 process 종료
- 스냅샷 저장 성공 뒤 ACK 유실
- 재접속 중 이전 연결의 명령 도착
- 델타 gap 뒤 full resync
- replay 중간 checkpoint에서 state hash 불일치
- 다른 rule version으로 replay 시도
- 경기 결과 전송 성공 뒤 room process 종료

## 확인 질문

- 재접속 때 유지하는 값과 새로 만드는 값은 무엇입니까?
- 스냅샷 하나로 어느 tick까지 복구합니까?
- process 장애 뒤 잃을 수 있는 최대 명령 수는 얼마입니까?
- replay 결과가 같다고 판단하는 기준은 무엇입니까?
- 오래된 token, snapshot과 replay를 언제 삭제합니까?
