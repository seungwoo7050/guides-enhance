# Connection, session, room과 match 수명

## 목적

socket 연결과 플레이어의 경기 참가를 같은 상태로 취급하지 않습니다. 연결 종료, 재접속, 방 폐기와 process 종료에서 유지할 값과 제거할 값을 정합니다.

## 식별자와 수명

| 상태 | 시작 | 종료 | 재접속 뒤 유지 |
|---|---|---|---|
| connection | socket accept 또는 connect 완료 | close, timeout, protocol error | 유지하지 않음 |
| authenticated session | 인증과 session 검증 완료 | 만료, logout, revoke | 조건부 유지 |
| player presence | 방 참가 성공 | leave, kick, 경기 종료 | 설정한 grace 안에서 복원 가능 |
| room | 생성 승인 | task, member, queue 정리 완료 | 새 room ID를 사용하는 것이 일반적 |
| match | 시작 조건 충족 | terminal result 확정 | 결과 조회에 필요한 정보만 유지 |

`connection_id`를 `player_id`로 사용하지 않습니다. 재접속하면 새 연결이 기존 세션과 플레이어 참가 상태를 이어받습니다.

## 상태 예시

### Connection

```text
ACCEPTED
→ NEGOTIATING
→ AUTHENTICATED
→ ACTIVE
→ CLOSING
→ CLOSED
```

protocol version, 인증과 방 참가가 끝나기 전에는 gameplay 명령을 받지 않습니다.

### Room membership

```text
NOT_JOINED
→ JOINING
→ JOINED
→ DISCONNECTED_GRACE
→ JOINED 또는 LEFT
```

`DISCONNECTED_GRACE`의 최대 시간을 정합니다. 연결이 끊긴 플레이어를 무기한 보관하지 않습니다.

### Match

```text
CREATED
→ WAITING
→ STARTING
→ RUNNING
→ FINISHING
→ FINISHED 또는 ABORTED
```

각 단계에서 허용할 명령을 제한합니다. `FINISHING`은 gameplay는 끝났지만 결과가 아직 확정되지 않은 상태를 나타낼 수 있습니다.

## Join과 leave

- 같은 join 요청을 다시 받아도 플레이어가 두 번 추가되지 않습니다.
- 정원 확인과 참가자 추가를 한 이벤트 처리 안에서 수행합니다.
- join 성공 응답이 유실돼 재시도해도 기존 membership을 반환할 수 있어야 합니다.
- 정상 leave와 일시적인 disconnect를 구분합니다.
- kick, timeout, 정상 leave의 reason code를 구분합니다.
- 방을 닫는 중에는 새 join과 경기 시작을 명시적으로 거절합니다.

## Reconnect

재접속은 이전 socket을 되살리는 작업이 아닙니다.

1. 새 연결을 인증합니다.
2. reconnect token과 `session_epoch`를 확인합니다.
3. 이전 연결을 더 이상 current로 인정하지 않습니다.
4. 기존 플레이어와 방·경기 참가 상태가 남아 있는지 확인합니다.
5. full snapshot과 새 replication baseline을 보냅니다.
6. 클라이언트가 baseline을 확인하면 델타 전송을 다시 시작합니다.

이전 연결에서 늦게 도착한 명령은 `session_epoch`로 거절합니다. 새 연결을 만들 때 플레이어 객체나 참가자 목록을 다시 추가하지 않습니다.

## Grace 만료

재접속 grace가 끝났을 때 결과를 명시합니다.

- AI가 대신 진행합니다.
- 기권 처리합니다.
- 경기에서 제거합니다.
- 경기 자체를 중단합니다.

어떤 선택을 하든 room, match와 player의 상태를 함께 갱신하고, 이미 확정한 경기 결과를 다시 만들지 않아야 합니다.

## 방 종료

member count가 0이 됐다는 이유만으로 방 객체를 즉시 삭제하지 않습니다. 다음 항목을 먼저 확인합니다.

- tick task 중단
- network subscription 제거
- 송신 큐와 buffer 정리
- pending result와 outbox 확인
- snapshot이나 replay flush 여부
- terminal reason 기록
- registry에서 방 제거

종료 중 새 join을 받을지 거절할지 상태로 나타냅니다.

## Process 종료

권장 순서는 다음과 같습니다.

```text
새 connection과 room 생성 중단
→ active room에 drain 시작 알림
→ 제한 시간 동안 경기 완료 또는 snapshot 저장
→ result와 outbox flush
→ socket, timer, worker 종료
→ 끝나지 않은 방과 손실 가능한 상태 기록
```

`kill -9`에서도 보존해야 하는 값은 메모리 밖에 먼저 기록되어 있어야 합니다.

## 확인 질문

- `connection_id`, `session_id`, `player_id`는 각각 언제 만들어지고 사라집니까?
- 재접속할 때 유지하는 값과 새로 만드는 값은 무엇입니까?
- 중복 join이 참가자 수를 늘리지 않는 검사는 어디에 있습니까?
- grace가 끝난 플레이어가 진행 중 경기에서 어떻게 처리됩니까?
- drain 중 새 방, 새 참가와 새 경기 시작은 어떤 결과를 받습니까?
- shutdown이 끝난 뒤 어떤 collection과 timer가 비어 있어야 합니까?
