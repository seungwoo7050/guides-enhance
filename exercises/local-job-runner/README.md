# Local Job Runner

## 개요

`local_job_runner`는 하나의 worker thread가 제한된 대기열에서 작업을 꺼내 실행하는 C++20 라이브러리입니다. 작업 제출, 상태 조회, 대기, 취소, 종료와 상태 변경 기록을 제공합니다.

작업 취소는 협력 방식입니다. 실행 중인 callback은 전달받은 `std::stop_token`을 확인해야 멈출 수 있습니다. 임의의 thread를 강제로 종료하지 않습니다.

## 제공 기능

- 정수에서 암묵적으로 만들어지지 않는 `JobId`
- `queued`, `running`, `succeeded`, `failed`, `cancelled` 상태
- 제출 실패를 값으로 돌려주는 `Result<JobId, SubmitError>`
- 최대 대기 작업 수 제한
- 작업별 `stop_source`
- thread-safe `snapshot()`과 terminal 상태 대기
- callback 예외를 `failed` 상태로 저장
- 상태 변경을 TSV 파일에 기록
- 여러 thread가 동시에 호출해도 한 번만 join하는 `stop()`

## 상태 변화

```text
submit
  ├─ rejected: empty_name | empty_work | queue_full | stopped
  └─ accepted: queued → running → succeeded | failed | cancelled
```

terminal 상태에 들어간 작업은 다시 바뀌지 않습니다. 대기 중인 작업은 즉시 `cancelled`로 바꿀 수 있습니다. 실행 중인 작업은 stop 요청만 전달하며 callback이 반환한 뒤 최종 상태를 기록합니다.

## 빌드와 실행

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/local_job_runner_app /tmp/local-jobs.tsv
```

`local_job_runner` library target을 애플리케이션과 테스트가 함께 사용합니다. thread 의존성도 library target에 연결되어 사용자가 별도로 link option을 복사하지 않아도 됩니다.

## 테스트

테스트는 `sleep`으로 실행 순서를 추측하지 않습니다. `promise`, `future`, condition variable을 사용해 다음 사건을 직접 기다립니다.

- 첫 작업이 실제로 시작했는지
- 다음 작업이 대기열에 들어갔는지
- 대기열이 가득 찬 시점의 제출이 거부되는지
- 실행 중 callback이 stop 요청을 받는지
- callback 예외 뒤 worker가 계속 동작하는지
- `stop()` 반복 호출이 중복 join이나 deadlock을 만들지 않는지
- journal 내용과 최종 snapshot이 같은 상태를 가리키는지

## journal

각 상태 변화는 다음 형식으로 한 줄씩 기록합니다.

```text
<id>\t<status>\t<name>\t<message>\n
```

작업 이름과 메시지의 tab·줄바꿈은 공백으로 바꿉니다. 생성 시 journal을 열 수 없으면 `JobRunner` 생성이 실패합니다. 실행 중 기록이 실패하면 작업은 계속 처리하고 `journal_healthy()`가 `false`를 반환합니다. 한 번 `false`가 된 값은 자동으로 복구하지 않습니다.

이 파일은 상태 확인용 기록일 뿐, 재시작 뒤 작업을 복구하는 durable queue는 아닙니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 0 | Build one reusable library for the app and tests | `CMakeLists.txt` |
| 1 | Store either a value or an error | `include/result.hpp` |
| 2 | Job identifiers, states, snapshots, and work callbacks | `include/job_runner.hpp` |
| 3 | Own queued work, records, cancellation sources, and worker state | `include/job_runner.hpp` |
| 4 | Validate capacity and journal before starting the worker | `src/job_runner.cpp` |
| 5 | Insert the record and queue entry as one operation | `src/job_runner.cpp` |
| 6 | Cancel queued work or request cooperative stop | `src/job_runner.cpp` |
| 7 | Move jobs from queued to a terminal state in the worker | `src/job_runner.cpp` |
| 8 | Keep journal failure separate from job completion | `src/job_runner.cpp` |
| 9 | Stop submissions, request cancellation, and join safely | `src/job_runner.cpp` |
| 10 | Run sample jobs and map failures to exit status | `app/main.cpp` |

## 범위

worker는 하나뿐이며 우선순위를 지원하지 않습니다. 재시작 복구, 여러 프로세스의 공유, `fsync`를 이용한 내구성 보장, 완료 기록 자동 삭제, `JobId` 소진 처리는 구현하지 않습니다. callback이 stop 요청을 무시하고 영원히 반환하지 않으면 `stop()`도 종료를 기다립니다.
