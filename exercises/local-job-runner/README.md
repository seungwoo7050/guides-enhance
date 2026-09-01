# Local Job Runner

## 개요

`local_job_runner`는 하나의 worker thread가 제한된 대기열에서 작업을 꺼내 실행하는 C++20 라이브러리입니다.

제공 기능은 다음과 같습니다.

```text
작업 제출
작업 상태 조회
terminal 상태 대기
취소
정상 종료
상태 변경 journal 기록
```

핵심은 thread를 단순히 생성하는 것이 아니라 **작업 상태 머신과 공유 상태의 수명, 동기화, 종료 순서**를 일관되게 유지하는 것입니다.

작업 취소는 **협력적 취소(cooperative cancellation)** 방식입니다.

실행 중 callback을 외부에서 강제로 종료하지 않습니다.

대신 callback에 `std::stop_token`을 전달하고:

```text
취소 요청
→ stop_source가 stop 요청 전달
→ callback이 stop_token 확인
→ callback이 스스로 반환
```

하는 구조를 사용합니다.

따라서 callback이 stop 요청을 무시하고 영원히 반환하지 않으면 worker도 끝나지 않으며 `stop()`도 join에서 계속 기다립니다.

## 제공 기능

- 정수에서 암묵적으로 만들어지지 않는 `JobId`
- `queued`, `running`, `succeeded`, `failed`, `cancelled` 상태
- 제출 실패를 값으로 돌려주는 `Result<JobId, SubmitError>`
- 최대 대기 작업 수 제한
- 작업별 `stop_source`
- thread-safe `snapshot()`
- terminal 상태 대기
- callback exception을 `failed` 상태로 저장
- 상태 변경을 TSV 파일에 기록
- 여러 thread가 동시에 호출해도 한 번만 join하는 `stop()`

## `JobId`

`JobId`는 단순 정수 대신 별도 타입으로 둡니다.

목표는 다른 정수와 job identifier가 실수로 섞이는 것을 줄이는 것입니다.

예를 들어 다음과 같은 암묵적 사용을 막습니다.

```cpp
cancel(42);
```

대신 명시적인 `JobId`를 사용하도록 API를 설계합니다.

즉 강한 타입은 runtime 기능보다 **잘못된 호출을 compile 단계에서 줄이는 역할**을 합니다.

## 상태 변화

작업 상태는 다음 state machine을 따릅니다.

```text
submit
  ├─ rejected: empty_name | empty_work | queue_full | stopped
  └─ accepted: queued → running → succeeded | failed | cancelled
```

중요한 invariant:

```text
terminal 상태
= succeeded | failed | cancelled
```

한 번 terminal 상태가 되면 다시 다른 상태로 바뀌지 않습니다.

예:

```text
succeeded → running
failed    → succeeded
cancelled → running
```

같은 전이는 허용하지 않습니다.

## submit 실패

작업이 queue에 들어가기 전에 다음 조건을 검사합니다.

예:

```text
이름이 비어 있음
callback이 비어 있음
queue가 가득 참
runner가 이미 stop됨
```

이런 실패는 exception보다 `Result<JobId, SubmitError>` 값으로 표현합니다.

즉 정상적으로 예상 가능한 제출 거부와 시스템 내부 예외를 구분합니다.

```text
예상 가능한 제출 실패
→ SubmitError

예상하지 못한 내부 실패
→ exception 또는 별도 실패 처리
```

## queue capacity

capacity는 worker가 현재 실행 중인 작업을 포함하는 전체 job 수가 아니라 **대기 중인 작업 수 제한**입니다.

따라서 worker 하나가 작업을 실행 중이고 queue capacity가 `2`라면 보통 추가로 최대 두 작업이 queued 상태로 존재할 수 있습니다.

정확한 의미는 구현과 test에서 일치해야 합니다.

중요한 것은 capacity 검사가 enqueue와 race 없이 하나의 critical section 안에서 이루어지는 것입니다.

잘못된 구조:

```text
thread A: queue size 확인 → 1
thread B: queue size 확인 → 1
thread A: enqueue
thread B: enqueue
```

capacity가 2인데 기존 size가 1이었다면 두 thread가 동시에 통과하여 제한을 넘길 수 있습니다.

따라서:

```text
lock
→ stopped 확인
→ capacity 확인
→ record 생성
→ queue 삽입
→ unlock
```

처럼 원자적으로 보이는 critical section이 필요합니다.

## queued 작업 취소

아직 worker가 시작하지 않은 queued 작업은 즉시 `cancelled` 상태로 바꿀 수 있습니다.

```text
queued
→ cancel 요청
→ cancelled
```

이 경우 worker가 나중에 해당 작업을 실행하면 안 됩니다.

queue에서 제거하거나, dequeue 시 cancelled 상태를 확인하여 건너뛰는 방식 중 하나를 사용할 수 있습니다.

어느 방식이든 다음 invariant가 필요합니다.

```text
cancelled job callback은 새로 실행되지 않음
```

## running 작업 취소

이미 실행 중인 작업은 외부에서 강제로 중단하지 않습니다.

```text
running
→ cancel 요청
→ stop_source.request_stop()
```

그 뒤 callback이 `stop_token`을 확인해야 합니다.

예:

```cpp
void work(std::stop_token token)
{
    while (!token.stop_requested()) {
        // 작은 단위의 작업 수행
    }
}
```

callback이 stop 요청을 확인하지 않으면 cancellation은 즉시 완료되지 않습니다.

따라서 running job에서 `cancel()`의 의미는:

```text
"작업이 이미 멈췄다"
```

가 아니라:

```text
"작업에 중단 요청을 전달했다"
```

입니다.

최종 상태는 callback이 반환한 뒤 worker가 결정합니다.

## callback exception

callback이 exception을 던지더라도 worker thread가 종료되어서는 안 됩니다.

worker entry point까지 exception이 빠져나가면 `std::terminate()`로 process가 끝날 수 있습니다.

따라서 worker는 job callback을 exception boundary 안에서 호출합니다.

개념적으로:

```text
running
→ callback 실행

정상 반환
→ succeeded 또는 cancelled 판정

exception 발생
→ failed 기록
→ 다음 job 처리 계속
```

즉 하나의 job 실패가 worker 전체의 생명주기를 끝내지 않아야 합니다.

## snapshot

`snapshot()`은 현재 job 상태를 읽는 함수입니다.

thread-safe하다는 것은 단순히 crash하지 않는다는 뜻이 아니라, 동시 상태 변경 중에도 내부 data race 없이 **일관된 한 시점의 복사본**을 반환해야 한다는 뜻입니다.

일반적으로:

```text
mutex lock
→ 내부 record 읽기/복사
→ mutex unlock
→ snapshot 반환
```

구조를 사용합니다.

반환된 snapshot은 내부 mutable record의 reference가 아니라 독립된 값으로 만드는 편이 수명 관리에 유리합니다.

## terminal 상태 대기

호출자는 특정 job이 완료될 때까지 기다릴 수 있습니다.

busy waiting:

```cpp
while (!snapshot(id).is_terminal()) {
}
```

은 CPU를 낭비합니다.

대신 condition variable을 사용해 상태 변경 사건을 기다립니다.

개념적으로:

```text
lock
→ predicate 확인
→ terminal 아니면 condition_variable wait
→ 깨어나면 predicate 다시 확인
```

condition variable은 spurious wake-up이 가능하므로 "한 번 깨어났으니 조건이 참"이라고 가정하지 않습니다.

predicate를 반복 검사합니다.

## `stop()`의 의미

`stop()`은 다음 순서의 종료를 담당합니다.

```text
새 submit 거부
→ queued/running job에 필요한 취소 요청
→ worker 깨움
→ worker 종료 대기
→ join
```

중요한 점은 여러 thread가 동시에 `stop()`을 호출해도 thread object에 `join()`이 여러 번 수행되지 않게 하는 것입니다.

`std::jthread::join()` 계열 동작은 한 thread에 대해 한 번만 안전하게 수행해야 하므로 종료 상태를 동기화해야 합니다.

개념적으로:

```text
running
→ stopping
→ joined
```

같은 lifecycle state를 두고 하나의 caller만 실제 join을 담당하도록 만들 수 있습니다.

다른 caller는 이미 진행 중인 stop 결과를 기다립니다.

## destructor와 stop

`JobRunner` destructor가 worker보다 먼저 내부 공유 상태를 파괴하면 worker가 dangling reference를 사용할 수 있습니다.

따라서 destructor는 worker가 모두 끝난 뒤 멤버가 파괴되는 순서를 보장해야 합니다.

일반적인 관계:

```text
stop 요청
→ worker 깨움
→ worker loop 종료
→ join 완료
→ queue/records/mutex/journal 등 멤버 파괴
```

RAII 관점에서 `JobRunner`의 destructor는 worker thread lifetime을 자신의 lifetime 안에 완전히 포함시켜야 합니다.

## 빌드와 실행

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/local_job_runner_app /tmp/local-jobs.tsv
```

`local_job_runner` library target을 애플리케이션과 테스트가 함께 사용합니다.

즉 implementation source를 app과 test에 각각 따로 복사해 compile하지 않습니다.

```text
local_job_runner library
        ├─ app
        └─ tests
```

thread dependency도 library target에 연결하여 사용하는 target이 별도로 link option을 반복 작성하지 않게 합니다.

## 테스트

테스트는 `sleep`으로 timing을 추측하지 않습니다.

예를 들어:

```cpp
std::this_thread::sleep_for(...);
```

뒤 "아마 worker가 시작했을 것"이라고 가정하면 느린 CI나 scheduler 차이 때문에 flaky test가 됩니다.

대신 다음 동기화 primitive를 사용해 **사건 자체**를 기다립니다.

```text
promise / future
condition variable
explicit test barrier
```

확인할 사건:

- 첫 작업이 실제로 시작했는지
- 다음 작업이 queue에 들어갔는지
- queue가 가득 찬 정확한 시점에 submit이 거부되는지
- running callback이 stop 요청을 실제로 받는지
- callback exception 뒤 worker가 계속 동작하는지
- `stop()` 반복/동시 호출이 duplicate join이나 deadlock을 만들지 않는지
- journal 내용과 최종 snapshot이 같은 상태를 가리키는지

이런 test는 시간 지연이 아니라 state transition에 동기화하므로 더 결정적입니다.

## journal

각 상태 변화는 한 줄의 TSV 형식으로 기록합니다.

```text
<id>\t<status>\t<name>\t<message>\n
```

예:

```text
17	running	import	
17	succeeded	import	done
```

작업 이름과 메시지에 실제 tab이나 newline이 들어 있으면 record 경계가 깨질 수 있습니다.

따라서 해당 문자를 공백으로 바꿉니다.

```text
'\t' → ' '
'\n' → ' '
```

필요하다면 `'\r'` 같은 line separator도 동일 정책으로 처리할 수 있지만, 실제 범위는 구현 계약과 맞춰야 합니다.

## journal open 실패

`JobRunner` 생성 시 journal file을 열 수 없으면 객체 생성 자체가 실패합니다.

이유는 journal이 이 객체의 필수 초기화 조건이기 때문입니다.

```text
journal open 실패
→ worker 시작하지 않음
→ JobRunner 생성 실패
```

worker를 먼저 시작한 뒤 journal open에 실패하면 부분 생성 상태와 thread 정리가 복잡해집니다.

따라서 필수 resource를 먼저 준비한 뒤 worker를 시작하는 순서가 안전합니다.

## 실행 중 journal write 실패

실행 도중 journal write가 실패하면 job 실행 자체를 중단하지 않습니다.

```text
journal write 실패
→ job 처리 계속
→ journal_healthy() = false
```

즉 job completion과 observability failure를 분리합니다.

한 번 `false`가 된 상태는 자동으로 `true`로 복구하지 않습니다.

이를 sticky failure 상태라고 볼 수 있습니다.

```text
true
→ write 실패
→ false
→ 이후 성공해도 false 유지
```

이렇게 하면 호출자는 "과거 어느 시점에 기록 손실이 있었는가"를 알 수 있습니다.

## journal은 durable queue가 아닙니다

journal은 상태 확인용 기록입니다.

다음 기능을 제공하지 않습니다.

```text
재시작 뒤 job 복구
정확히 한 번 실행 보장
fsync 기반 내구성
crash recovery
distributed coordination
```

즉 process가 재시작되었을 때 journal을 읽어 queue를 복원하는 시스템이 아닙니다.

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

이 순서는 먼저 result/state model을 만들고, 그 위에 공유 상태와 worker lifecycle을 구성하도록 되어 있습니다.

## 범위

이 프로젝트는 다음 범위로 제한합니다.

```text
worker: 1개
priority: 없음
restart recovery: 없음
multi-process sharing: 없음
fsync durability: 없음
completed record auto deletion: 없음
JobId exhaustion 처리: 없음
```

callback이 stop 요청을 무시하고 영원히 반환하지 않으면 `stop()`도 join을 끝낼 수 없습니다.

이는 cooperative cancellation 모델의 의도된 한계입니다.