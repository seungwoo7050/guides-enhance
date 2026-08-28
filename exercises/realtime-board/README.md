# Realtime Board

Fastify와 WebSocket으로 만든 메모리 기반 실시간 보드 서버입니다. 연결과 보드 참가를 구분하고, 서버가 항목 버전과 방별 시퀀스를 관리합니다. 드래그 미리보기는 저장하지 않으며 최종 이동만 확정 패치로 전송합니다.

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

## 설치와 실행

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm dev
```

기본 주소는 `ws://localhost:4000/ws`입니다. `PORT` 환경 변수로 포트를 바꿀 수 있습니다.

## 메시지 순서

```text
연결
→ board.join
→ board.snapshot
→ item.create / item.update / item.move
→ board.patch 또는 item.preview
```

방에 참가하기 전에는 스냅샷 요청과 변경 요청을 거부합니다.

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

## 범위와 제한

보드 상태는 메모리에만 저장되어 서버를 재시작하면 사라집니다. 사용자 인증, 데이터베이스, 여러 서버 인스턴스 사이의 방 전송, 패치 보관과 자동 재연결 클라이언트는 포함하지 않습니다.
