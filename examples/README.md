# 운영체제 관찰 예제

이 디렉터리의 C 프로그램은 운영체제 개념을 사용자 공간에서 관찰할 수 있는 작은 실행으로 나눕니다. 특정 kernel의 내부 자료구조를 재현하거나 증명하지 않습니다. API 반환값, thread 결과, address space의 의미와 fault 통계가 문서의 설명과 맞는지 확인합니다.

## 요구 환경

- C11 compiler
- POSIX thread
- `fork`, `waitpid`, `getrusage`를 제공하는 Unix 계열 환경
- `make`
- Python 3.10 이상: repository의 예제 검증 스크립트 실행 시 필요

Linux와 macOS에서 실행할 수 있습니다. Windows에서는 WSL과 같은 POSIX 환경이 필요합니다.

주소 값, 정확한 fault 수와 실행 순서는 환경에 따라 달라질 수 있습니다.

## 빌드와 검증

```sh
make -C examples check
make -C examples verify
make -C examples sanitizer-check
```

- `check`: 여섯 프로그램을 엄격한 warning 설정으로 빌드합니다.
- `verify`: 대표 입력을 실행하고 고정된 출력 항목을 검사합니다.
- `sanitizer-check`: AddressSanitizer와 UndefinedBehaviorSanitizer로 다시 빌드해 실행합니다.

생성한 실행 파일은 다음 명령으로 제거합니다.

```sh
make -C examples clean
```

## 실행 전에 적을 내용

각 프로그램을 실행하기 전에 다음을 한 줄씩 적습니다.

```text
예상 성공 조건:
의도한 실패 또는 차이:
확인할 출력 항목:
이 결과만으로 알 수 없는 kernel 내부 상태:
환경에 따라 달라질 수 있는 값:
```

## 예제

### `syscall-boundary`

```sh
./examples/build/syscall-boundary
```

`write` 성공과 존재하지 않는 path의 `open` 실패를 확인합니다. `open` 직후 `errno`를 저장하므로, 이후 `rmdir` 같은 cleanup이 `errno`를 바꾸더라도 원래 실패 이유를 보존합니다.

확인할 내용:

- `write`가 성공했는지
- `open`이 `-1`을 반환했는지
- 저장한 `errno`가 `ENOENT`인지
- 이 출력만으로 실제 system-call instruction과 kernel handler를 알 수 없는 이유

### `lost-update`

```sh
./examples/build/lost-update split 100
./examples/build/lost-update fetch-add 100
```

barrier로 두 worker가 같은 counter 값을 읽도록 실행 순서를 고정합니다.

- `split`: atomic load와 store를 따로 실행하여 증가 하나가 사라지는 경우를 만듭니다.
- `fetch-add`: read-modify-write를 하나의 atomic operation으로 실행합니다.

이 예제는 우연한 scheduler timing에 기대지 않고 복합 갱신이 깨지는 순서를 반복합니다.

### `bounded-buffer`

```sh
./examples/build/bounded-buffer 100
```

고정 크기 ring buffer에서 `head`, `tail`, `count`, 종료 여부와 생산·소비 통계를 하나의 mutex로 보호합니다.

- producer는 buffer가 가득 찼으면 `not_full`에서 기다립니다.
- consumer는 buffer가 비었고 생산이 끝나지 않았으면 `not_empty`에서 기다립니다.
- wakeup 뒤 predicate를 `while`로 다시 확인합니다.
- 생산과 소비 개수 및 합계가 같은지 검사합니다.

### `dining-cycle`

```sh
./examples/build/dining-cycle 100
```

모든 diner가 필요한 두 lock 중 번호가 작은 lock을 먼저 획득합니다. 전역 순서가 circular wait를 없애는지 확인합니다.

프로그램은 각 diner가 정한 횟수만큼 완료하는지 확인하지만, 공정한 대기 시간이나 starvation 부재까지 증명하지는 않습니다.

### `cow-observer`

```sh
./examples/build/cow-observer
```

`fork` 전후 같은 virtual address와 부모·자식의 분리된 값을 출력합니다. 자식이 값을 바꾼 뒤 부모 값이 유지되는지는 확인할 수 있습니다.

다음 내용은 이 프로그램만으로 알 수 없습니다.

- 실제 physical frame number
- 정확한 COW fault 시점
- kernel이 사용한 page-table 형식

### `page-fault-observer`

```sh
./examples/build/page-fault-observer 128
```

anonymous memory의 각 page 첫 byte를 쓰고 process 전체의 minor fault 증가량을 출력합니다.

- `volatile` 접근으로 page별 write가 최적화에서 제거되지 않게 합니다.
- checksum으로 실제 page를 읽고 썼다는 근거를 남깁니다.
- 정확한 minor fault 수는 고정 정답으로 사용하지 않습니다.

## 전체 Implementation Order

이 번호는 `examples/` 전체에서 한 번씩만 사용합니다. 파일마다 다시 시작하지 않습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 소유할 임시 디렉터리와 실패 확인용 path 생성 | `syscall-boundary.c:create_temp_directory` |
| 2 | `write` 성공과 임시 디렉터리 정리 | `syscall-boundary.c:main` |
| 3 | `open` 직후 `errno` 보존 | `syscall-boundary.c:main` |
| 4 | barrier와 worker 공유 상태 정의 | `lost-update.c:t_barrier` |
| 5 | generation 기반 반복 barrier 초기화 | `lost-update.c:barrier_init` |
| 6 | 분리된 load/store와 atomic RMW 비교 | `lost-update.c:worker_main` |
| 7 | 입력 검증, thread 회수와 결과 출력 | `lost-update.c:main` |
| 8 | ring 위치, 종료 여부와 통계 보호 | `bounded-buffer.c:t_buffer` |
| 9 | mutex와 condition의 부분 초기화 정리 | `bounded-buffer.c:buffer_init` |
| 10 | full predicate 확인과 enqueue | `bounded-buffer.c:buffer_push` |
| 11 | 생산 종료 공개와 waiter wakeup | `bounded-buffer.c:mark_producer_done` |
| 12 | empty-or-done 확인과 dequeue | `bounded-buffer.c:buffer_pop` |
| 13 | producer와 consumer 결과 검증 | `bounded-buffer.c:main` |
| 14 | 포크별 mutex와 시작 조건을 포함한 공유 table | `dining-cycle.c:t_table` |
| 15 | start 또는 abort 대기 | `dining-cycle.c:wait_for_start` |
| 16 | 번호가 작은 lock부터 획득 | `dining-cycle.c:diner_main` |
| 17 | 부분 초기화된 mutex 정리 | `dining-cycle.c:table_init` |
| 18 | thread 시작, 회수와 완료 횟수 검사 | `dining-cycle.c:main` |
| 19 | fork 전 heap 값과 stdout 정리 | `cow-observer.c:main` |
| 20 | 자식의 private write와 `_exit` | `cow-observer.c:main` |
| 21 | EINTR를 처리하는 `waitpid`와 부모 값 확인 | `cow-observer.c:main` |
| 22 | process 단위 minor fault 통계 읽기 | `page-fault-observer.c:minor_faults` |
| 23 | 입력, page 크기와 곱셈 overflow 검사 | `page-fault-observer.c:main` |
| 24 | page별 실제 접근과 checksum 계산 | `page-fault-observer.c:main` |

## 결과가 예상과 다를 때

1. 종료 상태와 stderr를 저장합니다.
2. compiler, C library, 운영체제와 architecture를 기록합니다.
3. 출력값이 고정된 성공 조건인지 환경 의존 측정값인지 구분합니다.
4. API 문서에서 반환값과 오류 조건을 확인합니다.
5. 같은 문제를 `exercises/kernel-model/`의 결정론적 상태로 표현할 수 있는지 검토합니다.

## 완료 기준

- 여섯 프로그램의 성공 조건과 환경 의존 값을 실행 전에 구분합니다.
- `split`과 `fetch-add` 결과 차이를 복합 연산의 atomicity로 설명합니다.
- bounded buffer에서 condition wait 뒤 predicate를 다시 확인하는 이유를 설명합니다.
- lock order가 deadlock은 막아도 starvation 부재를 보장하지 않는 이유를 설명합니다.
- COW와 minor fault 출력이 증명하지 못하는 kernel 내부 상태를 구분합니다.
- 일반 실행과 sanitizer 검사를 모두 통과합니다.
