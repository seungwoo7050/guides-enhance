# 전송, protocol과 상태 복제

## 목적

UDP와 TCP를 단순히 속도만 비교해 선택하지 않습니다. 메시지의 손실, 순서, 중복, 지연과 재전송을 누가 처리할지 정한 뒤 전송 방식을 선택합니다. 또한 전체 상태를 매번 보내지 않고도 클라이언트가 서버 상태에 다시 수렴하도록 스냅샷과 델타의 적용 조건을 정합니다.

## TCP가 맞는 경우

- 메시지를 빠짐없이 순서대로 받아야 합니다.
- head-of-line blocking을 감수할 수 있는 제어, lobby, chat 경로입니다.
- 구현 복잡도를 줄이는 것이 지연 분산보다 중요합니다.

TCP는 message boundary를 제공하지 않습니다. length prefix, delimiter 또는 고정 header로 framing을 구현해야 합니다. 한 번의 `read`가 메시지 하나를 정확히 반환한다고 가정하지 않습니다. partial read와 여러 메시지가 한 번에 들어오는 경우를 모두 처리합니다.

## UDP가 맞는 경우

- 오래된 상태보다 최신 상태가 중요합니다.
- 일부 packet loss를 application이 처리할 수 있습니다.
- 순서, duplicate, 선택적 재전송과 최대 크기를 protocol에서 정할 수 있습니다.

UDP를 선택했다고 모든 메시지를 비신뢰로 처리하지는 않습니다. join, inventory 변경, 경기 결과처럼 반드시 도달해야 하는 메시지는 별도 재전송 규칙이나 다른 전송 방식을 사용합니다.

## Message envelope

payload를 해석하기 전에 다음 값을 확인합니다.

- protocol version
- schema version
- message type
- payload length
- connection 또는 session epoch
- sequence
- room 또는 match ID
- state version과 baseline version
- correlation ID가 필요한 경우 해당 값

알 수 없는 version, type과 length는 allocation과 payload parsing 전에 거절합니다. 최대 메시지 크기를 수치로 정합니다.

## Version 구분

다음 값은 서로 다른 의미를 갖습니다.

- wire format version
- state schema version
- gameplay rule version
- server release
- client build

wire format이 같아도 경기 규칙이나 상태 schema가 다를 수 있습니다. 경기 시작 뒤 rule version을 바꾸지 않습니다. 지원하지 않는 client에는 upgrade 또는 incompatibility reason을 반환합니다.

## 메시지별 전달 조건

| 종류 | 손실 허용 | 순서 확인 | 중복 처리 |
|---|---|---|---|
| 이동·시점 명령 | 제한적으로 허용 가능 | session sequence | stale·duplicate 거절 |
| join·leave | 허용하지 않음 | lifecycle state | 같은 요청을 다시 받아도 한 번만 반영 |
| snapshot | 최신 full state 하나면 됨 | state version | 오래된 snapshot 폐기 |
| delta | baseline 이후 순서 필요 | baseline + version | duplicate 무시 |
| chat·notification | 제품 요구에 따라 결정 | channel sequence | message ID |
| match result | 허용하지 않음 | operation ID | 업무 효과 한 번만 반영 |

## Full snapshot

다음 경우 full snapshot을 사용합니다.

- 최초 방 참가
- 재접속
- baseline 불일치
- 델타 gap을 복구할 수 없음
- state schema 전환

스냅샷에는 match 또는 room ID, state version, authoritative tick과 schema version을 포함합니다. 크기 상한을 넘으면 보내기 전에 거절하거나 여러 메시지로 나누는 규칙을 둡니다.

## Delta

클라이언트가 확인한 baseline 이후 바뀐 값만 보냅니다. 델타는 다음 조건을 만족해야 합니다.

- 어느 baseline에 적용하는지 식별합니다.
- `version`이 현재 상태에서 바로 이어지는지 확인합니다.
- 같은 델타를 다시 받아도 상태를 두 번 바꾸지 않습니다.
- gap이 있으면 제한된 수만 보류하거나 즉시 resync를 요청합니다.
- 잘못된 operation 하나가 앞선 operation의 부분 변경을 남기지 않게 합니다.
- entity 삭제와 재생성이 같은 ID에 섞일 수 있다면 generation을 둡니다.

스냅샷을 적용하면 이전 baseline에 속한 보류 델타를 정리합니다.

## Interest management

모든 플레이어에게 world 전체를 보내지 않아도 됩니다. 다음 기준을 조합할 수 있습니다.

- 공간 영역
- team, party, visibility
- entity 종류와 중요도
- update 빈도
- client bandwidth budget

interest set이 바뀔 때 create, update와 remove 메시지의 순서를 정합니다. 제거한 entity의 늦은 update가 다시 나타나지 않게 version이나 generation을 확인합니다.

## 느린 클라이언트

클라이언트별 송신 큐에 상한을 둡니다.

- 오래된 비필수 델타를 최신 스냅샷 하나로 바꿉니다.
- 반드시 전달해야 하는 메시지와 대체 가능한 상태 update를 다른 큐로 나눕니다.
- 상한을 넘으면 품질 저하, resync 또는 disconnect 중 하나를 선택합니다.
- 한 클라이언트의 큐가 방 tick과 다른 클라이언트의 전송을 막지 않게 합니다.

큐를 압축할 때도 최신 스냅샷 하나가 상한 안에 들어오는지 확인합니다. 들어오지 않으면 연결을 종료하는 편이 무제한 메모리 사용보다 안전합니다.

## MTU와 fragmentation

UDP 메시지가 경로 MTU를 넘지 않도록 크기 예산을 둡니다. application fragmentation을 구현한다면 fragment ID, 개수, timeout, duplicate와 메모리 상한을 함께 정합니다. 가능하면 상태를 작은 메시지로 나누고 오래된 fragment를 폐기합니다.

## 확인 질문

- 각 메시지의 손실, 순서와 중복 처리는 어느 코드가 담당합니까?
- TCP partial read와 여러 메시지 동시 수신을 어떻게 처리합니까?
- 델타가 어느 스냅샷에 적용되는지 어떤 값으로 확인합니까?
- future delta를 몇 개까지 보류하며 언제 resync합니까?
- 느린 클라이언트의 송신 큐 상한과 초과 결과는 무엇입니까?
- 지원하는 protocol, schema, rule과 client build 조합은 무엇입니까?
