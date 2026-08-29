# 보안, abuse와 anti-cheat 범위

## 목적

클라이언트를 신뢰하지 않되 모든 잘못된 요청을 곧바로 cheat로 단정하지 않습니다. 서버가 허용한 명령과 빈도를 확인하고, 나중에 조사할 수 있는 감사 기록을 남깁니다. client kernel driver나 상용 anti-cheat SDK는 다루지 않습니다.

## 클라이언트가 정할 수 없는 값

서버는 다음 값을 클라이언트 입력 그대로 저장하지 않습니다.

- authoritative position, health와 score
- cooldown 완료 여부
- inventory와 currency 변경
- 경기 승패와 reward
- 다른 플레이어의 object 소유권
- server time과 명령 순서

클라이언트는 의도를 담은 명령을 보냅니다. 서버가 세션, 경기 단계, 이전 상태와 규칙을 확인해 다음 값을 계산합니다.

## Authentication과 session

- gameplay packet마다 login credential을 보내지 않습니다.
- 짧은 수명의 gameplay session이나 token을 사용합니다.
- session은 actor, player, client build, protocol version과 권한 범위를 식별합니다.
- reconnect token에는 별도 TTL과 revoke 기준을 둡니다.
- 이전 connection의 `session_epoch`는 current로 인정하지 않습니다.
- 한 connection ID가 동시에 두 active session에 연결되지 않게 합니다.

## 명령 검증

다음 값을 차례로 확인합니다.

- 알려진 message type과 version
- payload length와 field type
- NaN, infinity와 정수 범위
- session과 connection ID
- `session_epoch`
- player, room과 match 참가 관계
- target entity의 소유자와 visibility
- command sequence
- 현재 match phase
- resource, cooldown, distance와 movement limit
- command 종류별 요청 빈도

검증에 실패한 요청은 정본 상태와 `sequence`를 바꾸지 않습니다.

## 오류와 abuse 구분

같은 invalid command도 원인이 다를 수 있습니다.

- 오래된 client bug
- packet reorder
- reconnect 뒤 이전 connection
- 손상된 payload
- 자동화된 과도한 요청
- 의도적인 조작

한 번의 실패만으로 영구 제재하지 않습니다. 안정된 reason code, 빈도, actor, session, player, client build와 release를 기록하고 별도 운영 규칙이 판단하게 합니다.

## 요청 제한

명령 종류별로 제한을 나눕니다.

- connection handshake
- authentication
- join과 matchmaking
- gameplay command type
- chat과 social
- snapshot과 resync 요청

결과는 drop, retry-after, temporary mute, disconnect, 조사 대상 등록 중 하나로 정합니다.

요청 제한 key를 connection ID만으로 만들면 재접속으로 우회할 수 있습니다. gameplay 명령은 `session_id`, `player_id`, command kind처럼 재접속 뒤에도 유지되는 값을 사용하는 편이 안전합니다.

인증과 참가 관계를 확인한 요청은 최종적으로 거절되더라도 token을 소비하게 할 수 있습니다. 잘못된 payload를 반복해 비싼 검증을 무제한 실행하지 못하게 하기 위해서입니다.

## Server-side rule 검사

예시:

- 한 tick에 허용한 이동 거리
- skill cooldown과 resource
- target visibility와 team
- 현재 경기 단계에서 허용한 명령인지
- item 소유자와 version
- duplicate result와 reward operation

지연 보정이 필요한 게임에서는 정상 latency와 불가능한 상태 전이를 구분할 허용 범위를 별도로 정합니다.

## Audit event

최소한 다음 값을 기록합니다.

- event time과 server monotonic context
- 인증된 actor
- client가 주장한 actor가 다른 경우 해당 값
- player, session, connection, room과 match ID
- server release와 protocol version
- command type과 sequence
- 판정과 stable reason code
- payload 원문 대신 크기와 안전한 digest
- correlation ID

secret, raw credential, reconnect token과 불필요한 개인정보를 기본 log에 남기지 않습니다.

같은 `command_id`와 같은 내용은 최초 판정을 재사용합니다. 같은 ID에 다른 내용을 넣은 충돌 요청도 audit와 alert 수를 무한히 늘리지 못하게 별도 중복 처리를 둡니다.

## Alert 집계

alert는 단순 event count보다 고유 command ID 집합을 사용하는 편이 안정적입니다.

```text
(actor_id, match_id, reason_code)
→ unique command_id 집합
→ threshold 이상이면 alert 생성
```

입력 순서가 달라지거나 같은 event가 다시 들어와도 같은 alert 집합을 만들어야 합니다.

## Anti-cheat 범위

이 문서가 다루는 내용:

- server-authoritative rule
- 불가능한 상태 전이 거절
- rate, sequence, membership와 ownership 확인
- replay와 trace 기반 조사
- 안정된 audit event

다루지 않는 내용:

- client kernel driver
- memory scanning
- binary protection
- 상용 anti-cheat SDK
- hardware ban
- 제재와 개인정보 관련 법률 판단

## 확인 질문

- 클라이언트가 직접 정할 수 없는 상태는 무엇입니까?
- 세션이 인증됐다는 이유만으로 생략하면 안 되는 검사는 무엇입니까?
- 거절된 명령 뒤 상태와 `sequence`가 그대로인지 어디에서 확인합니까?
- reconnect로 요청 제한을 우회하지 못하는 이유는 무엇입니까?
- 감사 기록에 남겨야 하는 값과 남기면 안 되는 값은 무엇입니까?
- 같은 거절 event의 재전달이 alert 수를 늘리지 않는 이유는 무엇입니까?
