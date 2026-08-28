# WAL Recovery Simulator

Write-ahead logging과 crash recovery의 핵심 순서를 작은 Python 상태 모델로 구현한 프로젝트입니다. 각 `UPDATE` record에는 증가하는 LSN과 before/after 값이 있으며, data page는 자신의 `page_lsn`까지 WAL이 flush된 뒤에만 disk에 기록할 수 있습니다.

## 주요 기능

- 증가하는 LSN을 가진 immutable `UPDATE`, `COMMIT` record
- 뒤로 이동하지 않는 WAL flush 범위
- WAL보다 data page를 먼저 기록하는 오류 거부
- `page_lsn`을 이용한 반복 가능한 REDO
- 미완료 transaction의 역순 UNDO
- 이전 미완료 update 뒤에 적용된 committed 값 보존
- 순서가 잘못되었거나 필드가 빠진 log 거부

## 구성

`LogManager`가 LSN을 발급하고 `flushed_lsn`을 기록합니다. `Disk`는 `Page`의 복사본을 저장하므로 호출자가 원본 객체를 바꿔도 저장된 값은 달라지지 않습니다. `RecoveryManager`는 UPDATE를 순서대로 REDO한 뒤 COMMIT record가 없는 transaction을 역순으로 UNDO합니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from recovery import Disk, LogManager, RecoveryManager

log = LogManager()
log.update(1, page_id=0, before=0, after=10)
log.commit(1)
log.update(2, page_id=0, before=10, after=99)  # crash 전에 commit되지 않았습니다.

disk = Disk()
RecoveryManager().recover(disk, log.records)
assert disk.pages[0].value == 10
```

## 테스트

```bash
make test
```

테스트는 WAL 선행 쓰기, Page 복사 저장, committed REDO, 미완료 UNDO, transaction 교차, `page_lsn` 건너뛰기, 반복 recovery와 잘못된 log 거부를 확인합니다.

## 설계에서 확인할 점

- Recovery는 UPDATE 이력을 먼저 다시 적용한 뒤 미완료 transaction을 되돌립니다. Crash 직전 page 값을 재현해야 각 before/after 값이 어떤 순서로 이어지는지 판단할 수 있습니다.
- UNDO는 현재 page 값이 해당 record의 `after`와 같을 때만 적용합니다. 뒤의 committed update가 이미 값을 바꿨다면 이전 미완료 record가 그 값을 덮어쓰지 않습니다.
- UNDO 뒤에도 `page_lsn`은 줄이지 않습니다. 같은 log로 recovery를 다시 실행했을 때 이미 본 UPDATE를 REDO하지 않게 합니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | page 상태와 immutable log record | `src/recovery.py` · `Page`, `LogRecord` |
| 2 | 증가하는 LSN과 durable 범위 | `src/recovery.py` · `LogManager` |
| 3 | WAL보다 앞서 쓰지 않는 page 저장 | `src/recovery.py` · `Disk` |
| 4 | `page_lsn`을 이용한 반복 가능한 REDO | `src/recovery.py` · `RecoveryManager.recover` REDO 구간 |
| 5 | 뒤의 committed 값을 보존하는 역순 UNDO | `src/recovery.py` · `RecoveryManager.recover` UNDO 구간 |
| 6 | WAL 기록 순서와 복구 결과 검증 | `tests/test_recovery.py` · `WALRecoveryTests` |

## 범위와 제한

이 구현은 page 값 하나를 정수로 두고 전체 before/after 값을 기록하는 결정적 시뮬레이터입니다. Log의 값이 실제 변경 순서대로 이어진다고 가정합니다. Checkpoint, log truncation, compensation log record, transaction table, dirty-page table, physiological logging과 ARIES의 전체 restart 절차는 포함하지 않습니다.
