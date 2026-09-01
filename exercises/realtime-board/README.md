# Realtime Board

Fastify와 WebSocket으로 만든 메모리 기반 실시간 보드 서버입니다. **WebSocket 연결**, **보드 참가**, **임시 미리보기**, **서버가 확정한 변경**을 서로 다른 상태로 구분합니다.

서버는 항목별 `version`과 보드별 `sequence`를 관리하며, 드래그 중 좌표는 미리보기로만 전달하고 최종 이동만 확정 상태에 반영합니다.

## 주요 기능

- Zod로 검사하는 클라이언트 메시지
- 연결별 ID, 역할과 참가 보드 관리
- 참가 직후 전체 스냅샷 전송
- 방에 참가한 연결에만 메시지 전송
- `viewer`의 영속 변경 거부
- 항목 버전으로 오래된 수정 감지
- 미리보기와 확정 패치 분리
- 방별 시퀀스와 보드 버전 증가
- ping/pong 하트비트
- Fastify 종료 때 타이머와 소켓 정리

## 연결과 참가

WebSocket 연결이 열렸다고 해서 특정 보드의 메시지를 받을 수 있는 것은 아닙니다.

```text
WebSocket 연결
→ 아직 어떤 보드에도 참가하지 않음
→ board.join
→ 참가 상태 저장
→ board.snapshot
→ 이후 해당 보드 메시지 처리
```

이 구분이 필요한 이유는 다음 요청을 막기 위해서입니다.

```text
연결만 열기
→ board.join 없이 item.move 전송
```

서버는 참가하지 않은 연결의 보드 작업을 거부합니다.

## 설치와 실행

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm dev
```

기본 주소는 `ws://localhost:4000/ws`입니다. `PORT` 환경 변수로 포트를 바꿀 수 있습니다.

개발 환경의 로컬 예제이므로 `ws://`를 사용합니다. 실제 인터넷 환경에서 인증 정보나 민감한 데이터를 전송하는 서비스라면 보통 TLS가 적용된 `wss://` 연결이 필요합니다.

## 메시지 순서

기본 흐름은 다음과 같습니다.

```text
연결
→ board.join
→ board.snapshot
→ item.create / item.update / item.move
→ board.patch 또는 item.preview
```

방에 참가하기 전에는 스냅샷 요청과 변경 요청을 거부합니다.

### 스냅샷

스냅샷은 특정 시점의 보드 전체 확정 상태입니다.

```text
board.snapshot
→ 현재 items
→ 현재 sequence
→ 현재 board version
```

재연결이나 오래된 쓰기 충돌 뒤 클라이언트가 서버 기준 상태를 다시 얻는 데 사용합니다.

### 미리보기

`item.move(final=false)`는 드래그 중인 임시 위치입니다.

```text
item.move(final=false)
→ 좌표 검증
→ item.preview 전송
→ 저장 상태 변경 없음
→ sequence 증가 없음
```

중간 이동은 최신 값만 중요하므로 영속 상태에 기록하지 않습니다.

### 확정 패치

최종 변경은 서버 상태를 수정한 뒤 `board.patch`로 전달합니다.

```text
item.move(final=true)
→ 권한 확인
→ baseVersion 확인
→ 서버 상태 수정
→ item version 증가
→ board sequence 증가
→ board.patch 전송
```

## `sequence`와 `version`

두 숫자는 서로 다른 문제를 해결합니다.

```text
sequence
→ 보드 전체 확정 변경의 순서

item version
→ 특정 항목의 현재 버전
```

예:

```text
sequence=10  item A version=2
sequence=11  item B version=5
sequence=12  item A version=3
```

`sequence`는 방 전체에서 증가하지만, item A의 버전은 item A가 실제로 바뀔 때만 증가합니다.

클라이언트가 오래된 `baseVersion`으로 수정하면 일부 값도 반영하지 않고 최신 상태를 다시 받습니다.

## 역할과 쓰기 권한

연결에는 역할이 있고 `viewer`는 영속 변경을 수행할 수 없습니다.

다음은 서로 다른 상태입니다.

```text
연결됨
참가함
쓰기 권한 있음
```

즉 참가했다고 해서 자동으로 수정 권한이 생기는 것은 아닙니다.

`viewer`가 영속 변경을 시도하면 테스트 기준으로 정책 위반 close code `1008`로 연결을 종료합니다.

## 좌표 검증

브라우저가 계산한 좌표는 신뢰할 수 있는 서버 데이터가 아닙니다.

따라서 최종 좌표와 미리보기 좌표 모두 서버에서 허용 범위를 검사합니다.

```text
클라이언트 좌표
→ 숫자와 범위 검증
→ 유효할 때만 상태 변경 또는 preview
```

보드 범위 밖 좌표는 상태를 바꾸지 않습니다.

## 하트비트

연결이 비정상적으로 끊겨도 TCP 상태가 즉시 사라지지 않을 수 있으므로 서버는 ping/pong으로 연결 생존 여부를 확인합니다.

개념적인 흐름:

```text
주기적 ping
→ pong 수신
→ 연결 생존으로 표시

다음 검사까지 pong 없음
→ 끊긴 연결로 판단
→ 종료와 정리
```

하트비트 타이머는 서버 종료 때 반드시 해제합니다.

## 종료 정리

Fastify의 `onClose`에서 다음 자원을 정리합니다.

```text
heartbeat timer
열린 WebSocket
방 참가 상태
연결 상태
```

서버가 종료되는데 timer나 socket이 남아 있으면 테스트 프로세스가 끝나지 않거나 메모리 상태가 남을 수 있습니다.

## 테스트

테스트는 실제 WebSocket 연결을 사용해 다음을 확인합니다.

- 두 연결이 같은 확정 패치를 받음
- 스냅샷 요청으로 현재 시퀀스와 항목 복구
- `viewer`가 영속 변경을 시도하면 1008로 종료
- 잘못된 JSON은 1008로 종료
- 참가하지 않은 연결의 요청은 1008로 종료
- 드래그 미리보기는 스냅샷과 시퀀스를 바꾸지 않음
- 오래된 버전의 쓰기는 현재 스냅샷을 반환함
- 보드 범위 밖 좌표는 상태를 바꾸지 않음

테스트에서 WebSocket의 첫 수신 메시지가 항상 원하는 종류라고 가정하면 heartbeat나 다른 이벤트가 추가될 때 취약해질 수 있습니다. 실제 테스트 helper는 필요한 메시지 종류와 조건을 기다리는 방식으로 이해하는 것이 좋습니다.

## 코드 구성

- `src/protocol.ts`: 입력 메시지 스키마와 서버 이벤트 타입
- `src/state.ts`: 항목, 보드 버전과 시퀀스 변경
- `src/hub.ts`: 연결 등록, 방 참가와 방별 전송
- `src/app.ts`: WebSocket 라우트, 역할 검사, 하트비트와 종료
- `src/server.ts`: 포트 검사와 실제 서버 시작

## 주요 선택

- 연결이 열렸다는 이유만으로 보드에 참가한 것으로 보지 않습니다. `board.join`을 받은 뒤 참가 상태를 저장합니다.
- `BoardStore.snapshot()`은 복사본을 반환합니다. 호출자가 내부 배열과 항목을 직접 바꿀 수 없습니다.
- `baseVersion`이 현재 항목 버전과 다르면 일부 값도 수정하지 않고 최신 스냅샷을 반환합니다.
- `final=false` 이동은 미리보기로만 전송하고 시퀀스와 영속 상태를 바꾸지 않습니다.
- 하트비트 타이머와 모든 소켓은 Fastify `onClose`에서 정리합니다.
- 방 전체 변경 순서와 항목별 충돌 검사는 각각 `sequence`와 `version`으로 분리합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Validated client message types | `src/protocol.ts` |
| 2 | Mutable board snapshots and defensive copies | `src/state.ts` |
| 3 | Version-checked board mutation | `src/state.ts` |
| 4 | Socket membership and room delivery | `src/hub.ts` |
| 5 | Per-app realtime state | `src/app.ts` |
| 6 | Message parsing and join requirement | `src/app.ts` |
| 7 | Viewer write rejection | `src/app.ts` |
| 8 | Snapshot, preview, and patch dispatch | `src/app.ts` |
| 9 | Heartbeat and shutdown cleanup | `src/app.ts` |
| 10 | Network entry point | `src/server.ts` |

먼저 프로토콜과 상태 규칙을 정하고, 그 위에 연결·방 전송을 올린 뒤 마지막에 네트워크 서버를 엽니다. 이 순서로 구현하면 실시간 연결 코드와 상태 변경 규칙을 분리해서 테스트하기 쉽습니다.

## 범위와 제한

보드 상태는 메모리에만 저장되어 서버를 재시작하면 사라집니다. 사용자 인증, 데이터베이스, 여러 서버 인스턴스 사이의 방 전송, 패치 보관과 자동 재연결 클라이언트는 포함하지 않습니다.

따라서 이 exercise의 `sequence`와 `version`은 단일 애플리케이션 인스턴스 안에서 실시간 상태 관리 원리를 익히기 위한 구현입니다. 여러 서버에 걸친 전역 순서나 영속 이벤트 로그 문제까지 해결하지 않습니다.