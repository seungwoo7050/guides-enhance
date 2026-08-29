# Tick Command Model

고정된 simulation tick에서 여러 플레이어의 명령을 일정한 순서로 처리하는 시뮬레이터입니다. 실제 socket, thread와 wall clock을 사용하지 않으므로 같은 JSON 입력에서 같은 상태 전이와 digest를 재현할 수 있습니다.

## 제공 기능

- `tick_rate_hz`를 포함한 simulation 설정 검증
- 플레이어별 `session_epoch`와 `sequence` 확인
- 같은 tick에 속한 명령의 안정된 정렬
- duplicate, stale sequence와 sequence gap 거절
- `MOVE`, `ADD_SCORE` payload와 설정 범위 검사
- tick마다 검사할 명령 수 제한
- 제한된 catch-up과 처리하지 못한 명령 반환
- 과부하 원인을 `overload_reasons`로 구분
- key 순서를 고정한 JSON 결과와 SHA-256 digest

## 파일

- `src/tick_command_model/model.py`: 설정, 명령, 플레이어 상태와 판정 Record
- `src/tick_command_model/engine.py`: 입력 검증, 정렬, 명령 적용과 tick 실행
- `src/tick_command_model/serialization.py`: JSON 정규화와 digest 계산
- `src/tick_command_model/cli.py`: scenario 파일 실행
- `tests/test_engine.py`: 결정성, 실패 시 상태 보존과 처리 한도 검사
- `examples/scenario.json`: 실행 예제

## 요구 사항

- Python 3.11 이상
- 외부 package 없음

## 실행

```sh
PYTHONPATH=src python -m tick_command_model examples/scenario.json --pretty
```

설치한 뒤에는 console command를 사용할 수 있습니다.

```sh
python -m pip install .
tick-command-model examples/scenario.json --pretty
```

입력 JSON은 `config`, `players`, `commands`를 포함합니다. 출력에는 tick별 판정, `reason_code`, 최종 플레이어 상태, 처리하지 못한 명령, 과부하 여부와 digest가 들어갑니다.

## 검사

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 구현에서 지키는 조건

- 명령 순서는 입력 배열 위치가 아니라 `received_order`, `player_id`, `session_epoch`, `sequence`, `command_id`로 정합니다.
- payload 검증과 다음 값 계산이 모두 성공한 뒤에만 `last_sequence`를 갱신합니다.
- payload 처리 중 실패하면 위치, 점수와 `last_sequence`를 변경 전 값으로 되돌립니다.
- `max_commands_per_tick`은 적용에 성공한 명령 수가 아니라 검사한 명령 수를 제한합니다. 잘못된 명령도 처리 비용을 사용하기 때문입니다.
- `max_catch_up_ticks`를 넘는 tick은 실행하지 않고 남은 명령을 `pending_commands`로 반환합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Simulation state, command, and result records | `src/tick_command_model/model.py` |
| 2 | Scenario input validation and normalization | `src/tick_command_model/engine.py` |
| 3 | Stable command ordering | `src/tick_command_model/engine.py` |
| 4 | Payload range and arithmetic checks | `src/tick_command_model/engine.py` |
| 5 | Authoritative command validation | `src/tick_command_model/engine.py` |
| 5-1 | Session epoch and sequence checks | `src/tick_command_model/engine.py` |
| 6 | Bounded tick execution | `src/tick_command_model/engine.py` |
| 6-1 | Catch-up limit and pending work | `src/tick_command_model/engine.py` |
| 6-2 | Per-tick inspection limit | `src/tick_command_model/engine.py` |
| 7 | Stable JSON result digest | `src/tick_command_model/serialization.py` |
| 8 | Scenario file execution and exit status | `src/tick_command_model/cli.py` |
| 9 | Command ordering and limit regression tests | `tests/test_engine.py` |

## 범위와 제한

- 실제 network 도착 순서, 전송 신뢰성, thread scheduling은 다루지 않습니다.
- sequence gap을 자동으로 채우지 않고 명시적으로 거절합니다.
- `MOVE`와 `ADD_SCORE`만 제공하며 전체 game rule을 구현하지 않습니다.
- `pending_commands`를 다음 실행에 넣는 작업은 호출자가 새 scenario로 명시해야 합니다.
