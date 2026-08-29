# 게임 서버 기초

이 저장소는 실시간 게임 서버의 핵심 문제를 문서와 독립 실행형 프로젝트로 학습하는 과정입니다. 별도의 외부 프로젝트나 통합 과제를 완료 조건으로 요구하지 않습니다. 필수 문서를 읽고 다섯 프로젝트의 구현과 검사를 직접 설명할 수 있으면 과정을 마친 것으로 봅니다.

게임 서버를 일반 웹 API에 socket만 추가한 프로그램으로 보지 않습니다. 서버가 정본 상태를 계산하고, 고정된 tick에서 여러 플레이어의 명령을 일정한 순서로 처리하며, 중복·손실·재접속·과부하와 조작된 입력에서도 허용한 상태만 남기는 방법을 다룹니다.

## 완료 후 갖춰야 할 역량

과정을 마치면 다음 내용을 구체적인 상태, 식별자, 함수와 검사로 설명할 수 있어야 합니다.

1. 클라이언트가 보낸 의도와 서버의 정본 상태를 구분합니다.
2. 고정된 tick에서 명령 순서, `sequence`, `session_epoch`와 처리 한도를 적용합니다.
3. 연결, 세션, 플레이어, 방과 경기의 수명을 분리하고 재접속과 종료를 처리합니다.
4. 스냅샷과 델타의 `baseline`을 확인하고 손실·중복·순서 역전 뒤 다시 동기화합니다.
5. 서버의 상태와 남은 처리 여유를 기준으로 새 경기를 배치하거나 대기·거절합니다.
6. 세션, 방, 경기와 소유 관계를 확인한 뒤 명령을 적용하고 요청 제한과 감사 기록을 남깁니다.
7. 고정된 입력과 논리 시각으로 실패를 재현하고 첫 잘못된 상태 변경을 찾습니다.

## 선행 지식

다음 작업을 수행할 수 있어야 합니다.

- 선택한 언어로 여러 파일을 구성하고 자동 검사를 실행합니다.
- 자료형, 함수, 오류 처리와 상태 변경 순서를 설명합니다.
- 스레드, 큐, 취소와 정상 종료의 기본 동작을 이해합니다.
- TCP와 UDP의 차이, 부분 입출력, 순서, 손실과 재전송 주체를 구분합니다.
- 외부 입력을 검증하고 실패한 요청이 기존 상태를 바꾸지 않게 처리합니다.

분산 합의, Kubernetes, 다중 리전 운영 경험은 시작 조건이 아닙니다.

## 필수 문서

다음 문서를 필수 순서에 포함합니다.

1. [`docs/00-roadmap.md`](docs/00-roadmap.md)
2. [`docs/01-authoritative-state-and-trust.md`](docs/01-authoritative-state-and-trust.md)
3. [`docs/02-tick-time-and-command-order.md`](docs/02-tick-time-and-command-order.md)
4. [`docs/03-connection-session-room-and-match-lifecycle.md`](docs/03-connection-session-room-and-match-lifecycle.md)
5. [`docs/04-transport-protocol-and-state-replication.md`](docs/04-transport-protocol-and-state-replication.md)
6. [`docs/07-load-backpressure-placement-and-handover.md`](docs/07-load-backpressure-placement-and-handover.md)
7. [`docs/08-security-abuse-and-anticheat-boundaries.md`](docs/08-security-abuse-and-anticheat-boundaries.md)
8. [`docs/09-testing-observability-and-release-evidence.md`](docs/09-testing-observability-and-release-evidence.md)

다음 문서는 필요할 때 선택합니다.

- [`docs/05-reconnect-snapshot-replay-and-recovery.md`](docs/05-reconnect-snapshot-replay-and-recovery.md): process 장애 뒤 스냅샷과 replay로 상태를 복구해야 할 때
- [`docs/06-persistence-side-effects-and-service-boundaries.md`](docs/06-persistence-side-effects-and-service-boundaries.md): 경기 결과, 보상, DB transaction과 outbox를 연결할 때
- [`docs/90-language-and-runtime-profiles.md`](docs/90-language-and-runtime-profiles.md): C++ 또는 Java로 실제 서버를 옮길 때

## 프로젝트

`exercises/`의 각 디렉터리는 다른 파일에 의존하지 않는 완성 프로젝트입니다.

| 프로젝트 | 확인하는 내용 |
|---|---|
| [`tick-command-model`](exercises/tick-command-model/) | 고정 tick, 명령 순서, 중복·오래된 입력, 처리 한도 |
| [`session-room-lifecycle`](exercises/session-room-lifecycle/) | 연결·세션·방·경기 수명, 재접속, drain, shutdown |
| [`replication-reconnect`](exercises/replication-reconnect/) | 스냅샷·델타, baseline, 손실·순서 역전, 재동기화 |
| [`load-placement`](exercises/load-placement/) | 수용 여부, 서버 배치, 제한된 대기열, drain |
| [`trust-abuse`](exercises/trust-abuse/) | 명령 검증, 소유 관계, 요청 제한, 감사 기록과 alert |

## 권장 순서

문서를 모두 읽은 뒤 프로젝트를 한꺼번에 시작하지 않습니다. 필요한 용어를 익히면 바로 해당 프로젝트를 읽고 실행합니다.

```text
00 로드맵
→ 01 정본 상태 + 02 tick과 명령 순서
→ tick-command-model
→ 03 연결·세션·방·경기 수명
→ session-room-lifecycle
→ 04 protocol과 상태 복제
→ replication-reconnect
→ 07 수용 한도와 배치
→ load-placement
→ 08 신뢰와 abuse 입력
→ trust-abuse
→ 09 검사와 운영 근거
→ 다섯 프로젝트의 실패 검사 재확인
```

각 프로젝트에서는 다음 순서로 확인합니다.

1. README의 입력, 출력과 제한을 정리합니다.
2. `Implementation Order`를 따라 상태가 만들어지고 변경되는 위치를 찾습니다.
3. 예제 입력을 실행하고 결과의 `reason_code`와 digest를 확인합니다.
4. 검사를 실행하고 각 검사가 막는 잘못된 구현을 설명합니다.
5. 설정 한도, 실패 시 남는 상태와 구현하지 않은 범위를 기록합니다.

## 완료 기준

다음을 모두 만족해야 합니다.

- 다섯 프로젝트의 예제를 독립적으로 실행합니다.
- 모든 프로젝트의 자동 검사를 통과합니다.
- 같은 입력이 같은 결과를 만드는 이유를 설명합니다.
- 거절된 명령이 정본 상태나 `sequence`를 바꾸지 않는 위치를 찾습니다.
- 재접속에서 유지하는 상태와 새로 만드는 상태를 구분합니다.
- 델타 손실과 `baseline` 불일치 뒤 재동기화 절차를 설명합니다.
- 서버 배치, 큐와 요청 제한의 상한을 수치로 확인합니다.
- 종료 뒤 남아서는 안 되는 연결, 세션, 방, 경기와 큐를 설명합니다.
- 로컬 자동 검사가 실제 공용망, 장시간 운영, 다중 리전 장애를 증명하지 않는다고 명시합니다.

## 다루지 않는 범위

이 과정만으로 다음을 검증했다고 주장하지 않습니다.

- 실제 상용 게임의 성능과 지연 목표
- 공용망의 장시간 패킷 손실과 통신사별 품질
- production orchestration, autoscaling과 다중 리전 장애 조치
- 커널 수준 anti-cheat와 DDoS 대응
- durable 경기 복구와 외부 보상 시스템의 실제 운영

이 항목은 실제 요구가 생겼을 때 선택 문서와 별도 프로젝트로 확장합니다.
