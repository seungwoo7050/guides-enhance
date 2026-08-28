# 테스트·디버깅·도구

## 사용 시점

이 문서는 구현을 시작하기 전 전부 외울 내용이 아닙니다. 실패를 재현하기 어렵거나, 수명·동시성·성능 문제의 근거가 필요할 때 사용합니다.

## 테스트 전에 질문을 씁니다

함수 이름을 따라 테스트하지 말고 관찰 가능한 조건을 적습니다.

```text
이동 뒤 원본은 안전하게 소멸되는가
할당 실패 뒤 기존 값이 남는가
queue가 가득 찬 시점이 scheduling과 무관하게 재현되는가
stop 뒤 새 작업을 거부하는가
부분 send 뒤 다음 writable event에서 이어 쓰는가
```

이 질문이 명확해야 어떤 입력과 실패 주입이 필요한지 정할 수 있습니다.

## compile-time 검사

잘못된 사용 자체가 컴파일되지 않아야 한다면 `static_assert`나 compile-fail test를 사용합니다.

```cpp
static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
```

compiler 진단 문구 전체는 버전마다 달라질 수 있으므로, compile 성공·실패와 문제가 난 위치를 중심으로 확인합니다.

## 단위·통합·E2E 테스트

- 단위 테스트: 값 변환, 상태 변경, 오류 분기를 외부 process 없이 검사합니다.
- 통합 테스트: thread, filesystem, socket, 실제 build target을 함께 검사합니다.
- E2E 테스트: 실행 파일의 입력·출력·종료 상태를 확인합니다.

모든 것을 mock으로 바꾸면 실제 fd 정리나 thread join을 확인하지 못합니다. 반대로 모든 검사를 process 실행으로만 만들면 실패 위치를 찾기 어렵습니다.

## 결정적인 동시성 테스트

다음 검사는 실행 환경에 따라 달라집니다.

```cpp
std::this_thread::sleep_for(100ms);
assert(job_is_running());
```

느린 환경에서는 아직 시작하지 않았고 빠른 환경에서는 이미 끝났을 수 있습니다. 사건을 직접 동기화합니다.

```cpp
std::promise<void> started;
auto ready = started.get_future();
```

작업이 `started.set_value()`를 호출한 뒤에만 다음 제출을 진행하면 queue 상태를 반복해서 같은 방식으로 만들 수 있습니다.

## 실패 주입

정상 입력만으로는 rollback을 검사할 수 없습니다.

- 지정한 복사 횟수에서 예외를 던지는 값 타입
- 할당 횟수 제한
- 닫힌 file descriptor
- 읽기 전용 디렉터리
- timeout을 넘기는 callback
- 응답을 읽지 않는 socket client

실패 직후 값, 크기, 열린 fd 수, 살아 있는 객체 수를 함께 검사합니다.

## sanitizer

- AddressSanitizer: use-after-free, out-of-bounds, 일부 leak
- UndefinedBehaviorSanitizer: 정수·정렬·캐스트 등 정의되지 않은 동작
- ThreadSanitizer: data race

sanitizer가 테스트를 대신하지는 않습니다. 잘못된 결과를 내지만 메모리 오류가 없는 코드는 sanitizer를 통과할 수 있습니다. 서로 호환되지 않는 sanitizer는 별도 build에서 실행합니다.

## debugger

crash 위치만 확인하지 말고 잘못된 상태가 처음 생긴 시점을 찾습니다.

```sh
gdb --args ./app input.txt
break Store::put
run
print size_
next
```

watchpoint로 값 변경 지점을 찾거나, thread 목록과 backtrace로 deadlock 후보를 확인할 수 있습니다.

## CTest와 project-local test

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

테스트 이름은 실패한 영역을 찾을 수 있게 짓습니다. 각 테스트에는 timeout을 둬 무한 대기를 명확한 실패로 바꿉니다.

Make 기반 프로젝트도 `make test`, `make sanitize`, `make leak-check`처럼 프로젝트 안에서 실행 가능한 명령을 제공합니다.

## 성능 측정

Release build, compiler, CPU, 입력 크기와 반복 횟수를 기록합니다. parsing·I/O·출력을 알고리즘 측정에 섞지 않습니다.

한 번의 짧은 실행 결과로 성능을 단정하지 않습니다. warm-up, 반복 편차와 OS scheduling 영향을 확인합니다.

## 완료 기록

“테스트 완료”만 적지 않습니다.

```text
실행 명령
입력과 환경
통과한 조건
의도적으로 만든 실패
실행하지 못한 검사와 이유
```

## 완료 기준

- compile-time, 단위, 통합, E2E 검사를 구분합니다.
- 실패 조건을 먼저 문장으로 적고 테스트를 만듭니다.
- 동시성 테스트를 시간 지연이 아닌 사건으로 맞춥니다.
- rollback과 자원 정리를 실패 주입으로 확인합니다.
- sanitizer와 debugger가 각각 찾을 수 있는 문제를 구분합니다.
- 다른 디렉터리에서도 README 명령으로 같은 검사를 실행합니다.
