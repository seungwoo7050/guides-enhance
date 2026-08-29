# 게임 서버 독립 프로젝트

이 디렉터리에는 게임 서버의 핵심 문제를 각각 실행하고 검사할 수 있는 다섯 프로젝트가 있습니다. 각 디렉터리를 별도 저장소로 복사해도 설치, 실행과 자동 검사가 동작합니다.

## 프로젝트

| 프로젝트 | 확인하는 내용 |
|---|---|
| [`tick-command-model`](tick-command-model/) | 고정 tick, 명령 순서, `sequence`, 처리량과 catch-up 한도 |
| [`session-room-lifecycle`](session-room-lifecycle/) | 연결, 세션, 플레이어, 방, 경기의 수명과 재접속·종료 |
| [`replication-reconnect`](replication-reconnect/) | 스냅샷, 델타, gap 복구, 재동기화와 느린 클라이언트 큐 |
| [`load-placement`](load-placement/) | 서버 상태, protocol, 수용량, 대기열과 drain을 반영한 경기 배치 |
| [`trust-abuse`](trust-abuse/) | 정본 명령 검증, 요청 제한, 감사 기록과 alert 집계 |

## 공통 사항

- Python 3.11 이상을 사용합니다.
- 외부 package에 의존하지 않습니다.
- JSON scenario를 읽고 JSON 결과를 출력합니다.
- 실제 시각과 스레드 실행 순서 대신 논리 시각과 고정 입력을 사용합니다.
- 각 프로젝트가 source, tests, example과 package 설정을 직접 소유합니다.
- README의 `Implementation Order`와 source의 `[Implementation N]` 주석이 일치합니다.
- 같은 결과는 key 순서를 고정한 JSON으로 직렬화해 같은 SHA-256 digest를 만듭니다.

## 실행 예

```sh
cd tick-command-model
PYTHONPATH=src python -m tick_command_model examples/scenario.json --pretty
python -m unittest discover -s tests -v
```

나머지 프로젝트의 package 이름과 실행 명령은 각 README에 적혀 있습니다. 다른 exercise, 저장소 root script나 `docs/`를 실행 중에 참조하지 않습니다.
