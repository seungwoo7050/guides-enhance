# 테스트·디버깅·도구

## 사용 시점

이 문서는 구현을 시작하기 전에 전부 외워야 하는 고정 선행 범위가 아닙니다. 다음과 같은 상황에서 필요한 절을 찾아 적용합니다.

- 실패를 반복해서 재현하기 어렵습니다.
- 객체 수명이나 자원 정리가 올바른지 근거가 필요합니다.
- 동시성 문제가 실행할 때마다 다르게 나타납니다.
- 예외 발생 뒤 상태가 보존되는지 확인해야 합니다.
- 성능 저하가 실제로 어디에서 발생하는지 측정해야 합니다.
- sanitizer나 debugger가 알려 주는 결과를 어떻게 해석해야 할지 판단해야 합니다.

핵심은 도구를 많이 사용하는 것이 아니라 다음 질문에 답하는 것입니다.

```text
무엇을 관찰하면 요구사항을 만족했다고 말할 수 있는가?
실패를 어떻게 의도적으로 재현할 것인가?
실패 직후 어떤 상태가 유지되어야 하는가?
이 문제는 test, sanitizer, debugger 중 무엇으로 가장 잘 찾을 수 있는가?
실행 결과를 다른 환경에서도 재현할 수 있는가?
```

---

## 테스트 전에 질문을 먼저 씁니다

테스트를 함수 이름에 맞춰 기계적으로 만드는 것보다, **관찰 가능한 조건**을 먼저 문장으로 적습니다.

예:

```text
이동 뒤 원본은 안전하게 소멸되는가

할당 실패 뒤 기존 값이 남는가

queue가 가득 찬 시점이 scheduling과 무관하게 재현되는가

stop 뒤 새 작업을 거부하는가

부분 send 뒤 다음 writable event에서 이어 쓰는가
```

이 질문이 명확하면 다음을 결정하기 쉬워집니다.

- 어떤 입력이 필요한가
- 어떤 상태를 관찰할 것인가
- 실패를 어디에서 주입할 것인가
- 어떤 test level이 필요한가
- 어떤 assertion을 작성할 것인가

---

## 구현 세부사항보다 observable behavior를 검사합니다

좋은 테스트는 가능하면 caller가 실제로 관찰할 수 있는 결과를 확인합니다.

예를 들어 `Store::put()`이 내부적으로 `std::map`을 사용하는지 `std::unordered_map`을 사용하는지는 외부 계약이 아닐 수 있습니다.

대신 다음을 검사합니다.

```text
등록한 key를 다시 찾을 수 있는가
중복 key를 넣으면 어떤 결과가 나오는가
실패 뒤 기존 데이터가 유지되는가
```

내부 구현에 지나치게 의존하면 작은 refactoring만으로도 테스트가 깨질 수 있습니다.

---

## 테스트는 하나의 조건에 대한 증거입니다

테스트 하나가 너무 많은 조건을 동시에 확인하면 실패 원인을 찾기 어려워집니다.

예를 들어:

```text
parse
→ validation
→ database write
→ formatting
→ network send
```

를 한 테스트에서 모두 확인하면 실패했을 때 어느 단계가 문제인지 바로 알기 어렵습니다.

반대로 모든 것을 지나치게 작은 단위로 쪼개 실제 조합이 동작하는지 검사하지 않으면 integration 문제를 놓칠 수 있습니다.

따라서 서로 다른 test level을 조합합니다.

---

## compile-time 검사

잘못된 사용 자체가 컴파일되지 않아야 한다면 runtime test보다 compile-time 검사가 더 직접적입니다.

예:

```cpp
static_assert(
    !std::is_copy_constructible_v<UniqueFile>
);

static_assert(
    std::is_nothrow_move_constructible_v<UniqueFile>
);
```

이 코드는 다음 계약을 검사합니다.

```text
UniqueFile은 복사할 수 없다
UniqueFile의 이동 생성은 noexcept다
```

이런 성질은 프로그램을 실행할 필요 없이 compiler가 확인할 수 있습니다.

---

## type trait 기반 검사

표준 type trait를 사용하면 타입 성질을 compile time에 확인할 수 있습니다.

예:

```cpp
static_assert(std::is_move_constructible_v<Task>);
static_assert(std::is_copy_assignable_v<Task>);
static_assert(!std::is_default_constructible_v<Port>);
```

이런 검사는 다음과 같은 API 의도를 유지하는 데 유용합니다.

- 복사 금지
- 이동 허용
- 기본 생성 금지
- noexcept 이동 보장

특히 refactoring 중 compiler가 자동 생성하는 특수 멤버 함수의 성질이 달라졌는지 확인할 수 있습니다.

---

## concept도 compile-time 계약입니다

C++20 concept을 사용한다면 해당 concept이 의도한 타입만 받아들이는지도 검사할 수 있습니다.

예:

```cpp
static_assert(JobRange<std::vector<Job>>);
static_assert(!JobRange<std::vector<int>>);
```

이런 검사는 template 제약이 너무 약하거나 지나치게 강해지는 문제를 빠르게 찾을 수 있습니다.

---

## compile-fail test

어떤 코드는 **컴파일에 실패하는 것이 정상**입니다.

예:

```cpp
UniqueFile a;
UniqueFile b = a;
```

복사를 금지한 타입이라면 이 코드는 compile되지 않아야 합니다.

이런 경우 test harness가 다음을 확인하도록 만들 수 있습니다.

```text
해당 source를 compile
↓
compile 실패를 기대
↓
성공하면 test 실패
```

이를 흔히 compile-fail test라고 부릅니다.

---

## compiler 진단 문자열 전체에 의존하지 않습니다

compiler error message는 compiler 종류와 버전에 따라 달라질 수 있습니다.

예:

```text
use of deleted function
call to deleted constructor
attempting to reference a deleted function
```

처럼 같은 의미를 서로 다르게 표현할 수 있습니다.

따라서 compile-fail test는 가능하면 다음을 중심으로 확인합니다.

```text
컴파일이 실패했는가
문제가 예상한 코드 위치에서 발생했는가
필요하다면 핵심 diagnostic category가 존재하는가
```

진단 문자열 전체를 exact match하면 compiler 업데이트 때 테스트가 불필요하게 깨질 수 있습니다.

---

## 단위 테스트

단위 테스트는 가능한 한 작은 논리 단위를 외부 process나 실제 외부 환경 없이 검사합니다.

예:

```text
문자열 → Port 변환
Task 상태 변경
Store 중복 key 처리
오류 enum 반환
비교 함수 정렬 규칙
```

예:

```cpp
auto result = parse_port("8080");

assert(result);
assert(result->value() == 8080);
```

또 실패 분기도 직접 검사합니다.

```cpp
auto result = parse_port("70000");

assert(!result);
assert(result.error() == ParseError::out_of_range);
```

---

## 단위 테스트의 목적

단위 테스트가 유용한 이유는 실패 위치를 좁히기 쉽기 때문입니다.

다음 E2E 테스트가 실패했다고 가정합니다.

```text
입력
→ parser
→ service
→ store
→ formatter
→ stdout
```

어느 단계가 잘못되었는지 바로 알기 어렵습니다.

반면 parser와 store가 각각 단위 테스트를 갖고 있다면 문제 범위를 빠르게 줄일 수 있습니다.

---

## 통합 테스트

통합 테스트는 여러 실제 구성 요소가 함께 동작하는지 확인합니다.

예:

```text
thread + queue
filesystem + parser
socket + event loop
library target + executable target
```

단위 테스트에서는 각각 정상이어도 실제 결합 과정에서 문제가 생길 수 있습니다.

예:

- 잘못된 include/link 설정
- 실제 file permission 문제
- thread shutdown 순서 오류
- 실제 socket의 partial I/O 처리 누락
- 실제 filesystem rename 동작 차이

이런 문제는 통합 테스트에서 더 잘 드러납니다.

---

## E2E 테스트

E2E(end-to-end) 테스트는 사용자가 실제로 실행하는 프로그램의 외부 동작을 검사합니다.

예:

```text
실행 파일 실행
↓
stdin 또는 command-line argument 전달
↓
stdout/stderr 확인
↓
exit status 확인
```

예를 들어 CLI program이라면:

```text
입력:
add compile

출력:
OK 1

종료 상태:
0
```

같은 계약을 검사할 수 있습니다.

---

## 단위·통합·E2E의 역할을 구분합니다

간단히 정리하면 다음과 같습니다.

| 종류 | 주로 확인하는 것 |
|---|---|
| compile-time | 잘못된 사용이 compile되는지 여부 |
| 단위 | 작은 값 변환·상태 규칙·오류 분기 |
| 통합 | 여러 실제 component의 결합 |
| E2E | 실행 파일의 외부 observable behavior |

하나의 종류만으로 모든 문제를 잘 잡을 수는 없습니다.

---

## 모든 것을 mock으로 만들지 않습니다

mock은 외부 dependency를 통제하기 쉽게 만들지만, 실제 자원 의미를 제거합니다.

예를 들어 모든 filesystem 동작을 mock으로 바꾸면 다음 문제를 놓칠 수 있습니다.

```text
실제 fd close 누락
rename 동작
permission error
filesystem 경계
```

모든 thread를 fake executor로 바꾸면 실제:

```text
join
deadlock
data race
condition variable wakeup
```

을 확인하지 못할 수 있습니다.

따라서 mock은 특정 논리를 격리하는 데 사용하고, 실제 자원 동작은 별도 integration test로 확인합니다.

---

## 반대로 모든 검사를 E2E로 만들지 않습니다

모든 테스트를 process 실행으로만 만들면 작은 오류 하나를 찾기 위해 전체 프로그램을 실행해야 합니다.

예:

```text
잘못된 Port 범위 처리
```

를 검사하는 데 매번:

```text
process 생성
argument 전달
filesystem 준비
stdout parsing
```

까지 필요하다면 테스트가 느리고 실패 위치도 불분명해집니다.

핵심 로직은 library와 단위 테스트에서 직접 검사하고, process boundary 자체가 중요한 기능만 E2E로 확인합니다.

---

## 결정적인 동시성 테스트

동시성 테스트에서 가장 흔한 실수 중 하나는 시간 지연으로 상태를 추측하는 것입니다.

```cpp
std::this_thread::sleep_for(100ms);
assert(job_is_running());
```

이 코드는 다음을 보장하지 않습니다.

```text
100ms 뒤 worker가 반드시 시작했는가?
100ms 뒤 아직 끝나지 않았는가?
CI 환경에서도 같은가?
scheduler가 test thread를 언제 실행했는가?
```

즉 테스트가 실제 사건이 아니라 wall-clock timing에 의존합니다.

---

## 사건을 직접 동기화합니다

테스트에서 필요한 상태가:

```text
worker가 실제로 작업을 시작했다
```

라면 그 사건을 직접 signal합니다.

예:

```cpp
std::promise<void> started;
auto ready = started.get_future();

std::jthread worker([&] {
    started.set_value();

    // 실제 작업
});

ready.wait();
```

`ready.wait()`가 끝났다면 적어도 worker가 `set_value()` 위치까지 도달했다는 사실을 알 수 있습니다.

---

## queue full을 결정적으로 만듭니다

bounded queue의 `queue_full` 동작을 검사한다고 가정합니다.

단순히 여러 작업을 빠르게 제출하면 worker가 동시에 queue를 비우므로 테스트가 매번 같은 상태를 만들지 못할 수 있습니다.

더 결정적인 구조는 다음과 같습니다.

```text
1. 첫 번째 작업 제출
2. 첫 작업이 worker에서 실제로 시작했다는 signal 대기
3. 첫 작업을 test-controlled wait 지점에서 멈춤
4. queue capacity만큼 추가 작업을 넣음
5. 한 개 더 submit
6. queue_full 결과 확인
7. 첫 작업을 진행시켜 테스트 종료
```

이 구조는 "worker가 언제 실행될지"를 추측하지 않고 필요한 상태를 직접 만듭니다.

---

## `promise`/`future`

`std::promise`와 `std::future`는 한 thread가 다른 thread에 특정 사건이 발생했음을 알리는 데 사용할 수 있습니다.

예:

```cpp
std::promise<void> reached_point;
auto future = reached_point.get_future();

std::jthread worker([&] {
    prepare();
    reached_point.set_value();
    continue_work();
});

future.wait();
```

이제 test는 `prepare()` 이후 지점에 실제로 도달한 뒤 다음 검사를 수행할 수 있습니다.

---

## condition variable을 테스트 synchronization에 사용할 수 있습니다

여러 상태를 반복적으로 기다려야 한다면 condition variable을 사용할 수 있습니다.

예:

```cpp
std::unique_lock lock{mutex};

changed.wait(lock, [&] {
    return state == State::running;
});
```

핵심은 production 코드와 마찬가지로 test에서도 **predicate가 실제 상태를 표현하도록 하는 것**입니다.

---

## latch와 barrier

C++20의 `std::latch`와 `std::barrier`는 여러 thread의 진행 단계를 맞추는 데 유용합니다.

### latch

여러 작업이 특정 단계까지 모두 도달하기를 한 번 기다릴 때 사용할 수 있습니다.

개념적으로:

```text
worker A ─┐
worker B ─┼─> 모두 준비
worker C ─┘
             ↓
          test 진행
```

### barrier

여러 thread가 여러 phase에서 반복적으로 같은 지점에 모여야 할 때 사용할 수 있습니다.

경쟁 조건을 재현하거나 특정 interleaving을 만들 때 도움이 될 수 있습니다.

---

## 동시성 테스트에도 timeout을 둡니다

동기화 기반 테스트도 버그가 있으면 영원히 기다릴 수 있습니다.

따라서 test runner 수준이나 wait 자체에 timeout을 둡니다.

예:

```text
기대 사건이 2초 안에 발생하지 않음
→ 무한 대기 대신 명시적 test failure
```

timeout은 동작의 정확한 timing을 검사하기 위한 것이 아니라 **테스트 자체가 영원히 멈추지 않게 하는 안전장치**로 사용할 수 있습니다.

---

## 실패 주입

정상 입력만 실행해서는 실패 뒤 상태가 올바른지 확인할 수 없습니다.

예를 들어 strong exception guarantee를 제공한다고 주장하려면 실제로 중간 실패를 발생시켜야 합니다.

```text
호출 전 상태 A
↓
중간 실패 주입
↓
오류 발생
↓
상태가 A 그대로인지 확인
```

이런 기법을 실패 주입(failure injection)이라고 볼 수 있습니다.

---

## 복사 횟수에서 예외를 던지는 타입

container나 상태 변경 코드의 예외 안전성을 검사하기 위해 일정 횟수의 copy/move에서 예외를 던지는 테스트 타입을 만들 수 있습니다.

개념적으로:

```cpp
struct ThrowingValue {
    static int copies_before_throw;

    ThrowingValue(const ThrowingValue&) {
        if (--copies_before_throw == 0)
            throw TestError{};
    }
};
```

그 뒤 여러 실패 위치를 반복해서 만들 수 있습니다.

```text
첫 번째 복사에서 실패
두 번째 복사에서 실패
세 번째 복사에서 실패
...
```

이런 테스트는 특정 중간 단계에서 자원과 상태가 누수되지 않는지 확인하는 데 유용합니다.

---

## 실패 주입 타입은 테스트 전용 도구입니다

실패 주입 타입의 목적은 production behavior를 흉내 내는 것이 아니라 **평소 발생하기 어려운 실패 위치를 반복 가능하게 만드는 것**입니다.

예:

- N번째 copy에서 throw
- N번째 allocation에서 실패
- N번째 write에서 short write
- close 시 오류 반환

이렇게 하면 특정 error path를 항상 같은 방식으로 실행할 수 있습니다.

---

## allocation 실패

메모리 부족은 실제 환경에서 재현하기 어렵습니다.

테스트에서는 allocator를 주입하거나 제한된 test allocator를 사용해 특정 allocation에서 실패시키는 방법을 사용할 수 있습니다.

핵심은 다음을 검사하는 것입니다.

```text
allocation 실패
↓
현재 object invariant 유지?
기존 값 보존?
resource leak 없음?
```

모든 프로젝트에서 custom allocator가 필요한 것은 아니지만, strong exception guarantee처럼 allocation 실패가 중요한 계약이라면 고려할 수 있습니다.

---

## filesystem 실패 주입

실제 filesystem 조건을 이용해 오류를 만들 수도 있습니다.

예:

```text
존재하지 않는 파일
읽기 전용 경로
존재하지 않는 parent directory
이미 닫힌 fd
잘못된 path
```

단, permission 관련 테스트는 실행 사용자와 OS 환경에 따라 결과가 달라질 수 있습니다.

예를 들어 관리자 권한으로 실행하면 "읽기 전용이라고 생각한 디렉터리"에서도 쓰기가 성공할 수 있습니다.

따라서 환경 의존 실패를 테스트할 때는 테스트 전제 조건 자체도 확인해야 합니다.

---

## socket 실패 주입

network code에서는 다음 상황을 의도적으로 만들 수 있습니다.

```text
응답을 읽지 않는 peer
연결 직후 종료하는 peer
부분 write만 허용되는 상황
timeout
connection reset
```

중요한 것은 정상적인 작은 message 한 번만 보내고 "socket 코드가 동작한다"고 결론내리지 않는 것입니다.

non-blocking I/O에서는 partial read/write가 정상적인 상황일 수 있으므로 해당 분기를 직접 테스트해야 합니다.

---

## 실패 직후 무엇을 검사할지 정합니다

실패를 발생시키는 것만으로 테스트가 끝나지 않습니다.

예를 들어 실패 직후 다음을 검사할 수 있습니다.

```text
값
container 크기
객체 invariant
열린 fd 수
살아 있는 객체 수
lock 상태
queue 상태
thread 종료 여부
temporary file 존재 여부
```

어떤 값을 검사할지는 함수가 약속한 실패 보장에 따라 달라집니다.

---

## rollback 검사

함수가 strong guarantee를 제공한다면 실패 전후 상태를 비교할 수 있습니다.

```cpp
State before = state;

auto result = apply(state, invalid_patch);

assert(!result);
assert(state == before);
```

예외를 사용하는 코드라면:

```cpp
State before = state;

try {
    apply(state, invalid_patch);
    assert(false);
} catch (const ValidationError&) {
}

assert(state == before);
```

이렇게 해야 "실패하면 기존 상태를 유지한다"는 계약을 실제로 확인할 수 있습니다.

---

## 자원 정리 검사

RAII 타입이라면 실패 경로에서 자원이 정확히 한 번 해제되는지 확인합니다.

테스트용 resource counter를 만들 수 있습니다.

개념적으로:

```text
resource acquire → live_count + 1
resource release → live_count - 1
```

테스트 전후에:

```text
live_count == 0
```

인지 확인하면 leak이나 double release 문제를 찾는 데 도움이 됩니다.

실제 파일 descriptor나 OS handle은 platform-specific 방법으로 개수를 관찰할 수도 있지만, 테스트 전용 wrapper가 더 결정적일 수 있습니다.

---

## sanitizer

sanitizer는 특정 종류의 잘못된 동작을 runtime에 계측해서 발견하도록 도와주는 도구입니다.

주요 sanitizer는 다음과 같습니다.

### AddressSanitizer

주로 다음 문제를 찾는 데 사용합니다.

```text
heap use-after-free
stack use-after-scope의 일부
heap/stack buffer overflow
일부 memory leak 환경
```

보통 compiler option으로 활성화합니다.

예:

```sh
-fsanitize=address
```

정확한 option과 지원 범위는 compiler와 platform에 따라 다를 수 있습니다.

---

## UndefinedBehaviorSanitizer

UndefinedBehaviorSanitizer는 여러 종류의 undefined behavior를 찾는 데 도움을 줍니다.

예:

```text
signed integer overflow의 일부
잘못된 shift
잘못된 alignment
일부 invalid cast
null 관련 오류
```

예:

```sh
-fsanitize=undefined
```

UBSan이 모든 undefined behavior를 검출하는 것은 아니며, 활성화한 검사 항목과 compiler 구현에 따라 범위가 달라집니다.

---

## ThreadSanitizer

ThreadSanitizer는 실행 중 발생하는 data race를 탐지하는 데 사용합니다.

예:

```sh
-fsanitize=thread
```

여러 thread가 같은 memory location에 잘못 접근하면 실제 실행에서 race를 보고할 수 있습니다.

하지만 ThreadSanitizer가 통과했다고 다음이 보장되는 것은 아닙니다.

```text
deadlock 없음
starvation 없음
논리적 invariant 유지
shutdown 순서 정확
```

TSan은 주로 **data race** 검출 도구입니다.

---

## LeakSanitizer

일부 환경에서는 LeakSanitizer를 별도로 사용하거나 AddressSanitizer와 함께 leak detection을 사용할 수 있습니다.

찾으려는 것은 다음과 같은 문제입니다.

```text
할당된 memory가 종료 시점까지 해제되지 않음
```

하지만 프로그램 종료 시 의도적으로 유지되는 전역 cache나 library 내부 allocation 등도 보고될 수 있으므로 결과를 해석해야 합니다.

---

## sanitizer가 테스트를 대신하지 않습니다

다음 코드가 잘못된 결과를 내지만 memory error는 없다고 가정합니다.

```cpp
int add(int a, int b) {
    return a - b;
}
```

sanitizer는 이 논리 오류를 알려 주지 않습니다.

즉:

```text
test
    → 결과가 요구사항과 같은가?

sanitizer
    → 실행 중 특정 저수준 오류가 발생했는가?
```

를 각각 검사합니다.

둘은 역할이 다릅니다.

---

## sanitizer는 실행된 경로만 검사합니다

sanitizer가 활성화되어 있어도 테스트가 특정 실패 경로를 실행하지 않으면 그 경로의 문제를 발견할 수 없습니다.

예:

```text
use-after-free 버그 존재
↓
해당 branch를 test가 실행하지 않음
↓
sanitizer도 관찰하지 못함
```

따라서 좋은 test coverage와 sanitizer 실행을 함께 사용해야 합니다.

---

## sanitizer 조합은 항상 가능한 것이 아닙니다

일부 sanitizer는 서로 동시에 사용할 수 없거나 지원 조합이 제한됩니다.

대표적으로 AddressSanitizer와 ThreadSanitizer는 일반적으로 별도 build로 실행합니다.

예:

```text
build/asan
build/ubsan
build/tsan
```

처럼 분리하면 configuration 충돌을 줄일 수 있습니다.

---

## Debug와 Release 계열 sanitizer build를 구분합니다

sanitizer를 켠 build가 반드시 순수 Debug build일 필요는 없습니다.

최적화 수준이 너무 낮으면 production에서만 발생하는 behavior와 차이가 커질 수 있고, 너무 높은 최적화에서는 debugging이 어려워질 수 있습니다.

프로젝트에서는 예를 들어:

```text
RelWithDebInfo + ASan
RelWithDebInfo + UBSan
RelWithDebInfo + TSan
```

같은 별도 configuration을 둘 수 있습니다.

중요한 것은 사용한 compiler, optimization, sanitizer option을 기록하는 것입니다.

---

## debugger

debugger의 목적은 단순히 crash 난 줄을 보는 것에 그치지 않습니다.

더 중요한 질문은:

```text
잘못된 상태가 처음 생긴 시점은 어디인가?
```

입니다.

crash 위치는 잘못된 상태가 만들어진 위치와 멀리 떨어져 있을 수 있습니다.

---

## crash 위치와 원인 위치는 다를 수 있습니다

예를 들어 dangling pointer가 만들어졌다고 가정합니다.

```text
함수 A
→ 객체 파괴
→ dangling pointer 남음

여러 함수 실행

함수 Z
→ dangling pointer 역참조
→ crash
```

debugger가 처음 멈추는 위치는 함수 Z일 수 있습니다.

하지만 실제 원인은 함수 A에서 객체 수명을 잘못 관리한 것입니다.

따라서 crash 지점에서 변수 상태를 확인한 뒤, 그 값이 언제 잘못되었는지 역으로 추적합니다.

---

## breakpoint

특정 함수나 source line에서 실행을 멈출 수 있습니다.

예:

```sh
gdb --args ./app input.txt
break Store::put
run
```

`Store::put`에 들어올 때마다 실행이 멈추므로 다음을 확인할 수 있습니다.

```text
어떤 argument가 들어왔는가?
현재 object 상태는 무엇인가?
어떤 호출 경로에서 들어왔는가?
```

---

## step과 next

debugger에서 일반적으로:

```text
step
    → 호출한 함수 내부로 들어감

next
    → 현재 줄을 실행하지만 함수 호출 내부는 건너뜀
```

처럼 사용합니다.

예:

```sh
print size_
next
print size_
```

로 특정 문장 전후 상태가 어떻게 바뀌는지 관찰할 수 있습니다.

---

## backtrace

현재 함수가 어떤 호출 경로를 통해 실행되었는지 확인할 수 있습니다.

gdb에서는 일반적으로:

```sh
backtrace
```

또는:

```sh
bt
```

를 사용합니다.

예:

```text
main
→ Service::execute
→ Store::put
→ std::vector::...
→ crash
```

같은 호출 흐름을 확인할 수 있습니다.

---

## watchpoint

특정 메모리 값이 바뀌는 순간을 찾고 싶다면 watchpoint를 사용할 수 있습니다.

예:

```sh
watch size_
continue
```

`size_`가 변경되는 시점에 debugger가 멈출 수 있습니다.

"언제 값이 잘못되었는지 모른다"는 문제에서 매우 유용합니다.

다만 hardware watchpoint 수나 지원 범위에는 제한이 있을 수 있습니다.

---

## 조건부 breakpoint

특정 값에서만 멈추고 싶다면 조건을 걸 수 있습니다.

개념적으로:

```text
id == 42일 때만 중단
queue.size() > capacity일 때만 중단
```

반복 loop에서 모든 iteration마다 멈추는 대신 문제 상황만 관찰할 수 있습니다.

---

## thread 목록과 thread별 backtrace

deadlock이나 동시성 문제에서는 모든 thread가 어디에 멈춰 있는지 확인합니다.

예:

```text
thread A
→ mutex X 기다림

thread B
→ mutex Y 기다림

thread C
→ condition variable wait
```

gdb에서는 thread 목록과 thread별 stack을 확인할 수 있습니다.

정확한 명령은 debugger에 따라 다르지만 핵심은 **한 thread의 stack만 보지 않는 것**입니다.

---

## deadlock 후보를 볼 때

deadlock을 의심한다면 다음을 확인합니다.

```text
각 thread는 어떤 lock을 기다리는가?
그 lock을 누가 보유하고 있는가?
다른 lock을 가진 채 기다리고 있는가?
모든 worker가 condition variable에서 기다리는데 notify가 가능한 thread가 남아 있는가?
```

debugger는 현재 멈춘 상태의 snapshot을 제공하므로 lock ordering 문제를 추적하는 근거가 됩니다.

---

## optimized build의 debugging

Release optimization이 켜지면 다음 현상이 있을 수 있습니다.

```text
변수가 optimized out
source line과 실제 instruction 순서가 다름
inline 때문에 stack frame이 달라짐
```

그래서 debugger 사용이 어려워질 수 있습니다.

성능 관련 문제나 Release에서만 재현되는 문제라면 debug symbol을 유지한 최적화 build를 사용할 수 있습니다.

예:

```text
RelWithDebInfo
```

같은 configuration이 도움이 될 수 있습니다.

---

## core dump

프로그램이 crash한 순간의 process 상태를 core dump로 남길 수 있는 환경도 있습니다.

core dump를 debugger로 열면 실행 당시 다음 정보를 조사할 수 있습니다.

```text
call stack
register
memory
thread 상태
```

항상 재현하기 어려운 production crash를 분석할 때 유용할 수 있습니다.

다만 core dump에는 메모리 안의 민감 정보가 포함될 수 있으므로 보관과 공유에 주의해야 합니다.

---

## CTest

CMake 프로젝트에서는 CTest를 사용해 test executable을 일관된 방식으로 실행할 수 있습니다.

기본 흐름:

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

`--output-on-failure`를 사용하면 실패한 test의 출력이 표시되어 원인을 확인하기 쉽습니다.

---

## CTest에 test를 등록합니다

CMake에서 test executable을 만든 뒤:

```cmake
add_executable(task_tests
    tests/task_tests.cpp
)

target_link_libraries(task_tests
    PRIVATE
        task_core
)
```

CTest에 등록합니다.

```cmake
enable_testing()

add_test(
    NAME task.core
    COMMAND task_tests
)
```

`add_executable()`은 build target을 만들고, `add_test()`는 그 실행 방법을 CTest에 등록합니다.

---

## 테스트 이름은 실패 위치를 알려 줘야 합니다

다음 이름은 정보가 적습니다.

```text
test1
test2
all_tests
```

대신 영역과 조건을 알 수 있는 이름을 사용합니다.

예:

```text
task.parse.invalid_port
store.put.duplicate_key
queue.submit.full
worker.stop.rejects_new_jobs
filesystem.replace.preserves_old_file_on_failure
```

테스트 이름만 보고도 어느 영역의 어떤 계약이 실패했는지 알 수 있습니다.

---

## test timeout

동시성 bug나 deadlock이 있으면 test process가 영원히 끝나지 않을 수 있습니다.

CTest에서는 test property로 timeout을 설정할 수 있습니다.

예:

```cmake
set_tests_properties(
    task.core
    PROPERTIES
        TIMEOUT 10
)
```

이 timeout은 "정상 실행이 정확히 10초 안에 끝나야 한다"는 성능 요구와는 다릅니다.

주 목적은 무한 대기를 명확한 test failure로 바꾸는 것입니다.

---

## test fixture와 임시 파일

filesystem test는 production 파일을 직접 수정하지 않고 test마다 독립된 temporary directory를 사용하는 것이 좋습니다.

예:

```text
test 시작
↓
temporary directory 생성
↓
입력 파일 준비
↓
test 실행
↓
결과 확인
↓
temporary directory 정리
```

각 테스트가 같은 파일 경로를 공유하면 병렬 실행 시 서로 영향을 줄 수 있습니다.

---

## 테스트 독립성

좋은 테스트는 가능한 한 다른 테스트의 실행 순서에 의존하지 않습니다.

나쁜 예:

```text
test A가 파일 생성
↓
test B가 그 파일 사용
```

test B만 따로 실행하면 실패할 수 있습니다.

각 test가 자신에게 필요한 상태를 준비하고 정리하면:

```text
단독 실행
순서 변경
병렬 실행
```

이 쉬워집니다.

---

## project-local test 명령

사용자가 compiler option, sanitizer 명령, test target 이름을 모두 기억하게 하지 않습니다.

프로젝트 안에서 반복 가능한 명령을 제공합니다.

CMake 기반이라면 preset이나 script를 사용할 수 있고, Make 기반 프로젝트라면 예를 들어:

```sh
make test
make sanitize
make leak-check
```

같은 target을 제공할 수 있습니다.

중요한 것은 명령 이름 자체가 아니라 **새 checkout에서도 같은 검사를 재현할 수 있어야 한다**는 점입니다.

---

## sanitizer build도 프로젝트 명령으로 제공합니다

예:

```text
cmake --preset asan
cmake --build --preset asan
ctest --preset asan
```

처럼 구성할 수 있습니다.

또는 project script:

```sh
./scripts/test-asan.sh
```

을 사용할 수 있습니다.

이렇게 하면 개인 shell history에만 존재하는 옵션 조합을 프로젝트의 재현 가능한 검사로 바꿀 수 있습니다.

---

## performance 측정

성능 측정에서는 먼저 무엇을 측정하려는지 정합니다.

예:

```text
정렬 시간
parser 처리량
queue submit latency
filesystem write throughput
```

한 번에 모든 것을 포함하면 어느 부분이 병목인지 알기 어렵습니다.

---

## parsing·I/O·출력을 알고리즘 측정에 섞지 않습니다

정렬 성능을 측정한다고 가정합니다.

다음 전체 시간을 측정하면:

```text
파일 읽기
↓
parse
↓
sort
↓
stdout 출력
```

sort 자체의 성능을 알기 어렵습니다.

가능하면 정렬 대상 데이터를 미리 준비하고 다음 구간만 측정합니다.

```text
start
↓
sort
↓
end
```

---

## Release build에서 측정합니다

Debug build는 optimization이 꺼져 있거나 assertion·debug iterator 등 추가 비용이 있을 수 있습니다.

따라서 실제 성능 비교에서는 최소한 다음 정보를 기록합니다.

```text
compiler
compiler version
optimization level
Debug/Release configuration
CPU
입력 크기
반복 횟수
```

다른 환경의 숫자를 비교할 때 이 정보가 없으면 의미가 크게 줄어듭니다.

---

## 한 번의 실행으로 성능을 단정하지 않습니다

짧은 benchmark는 다음 영향을 받을 수 있습니다.

```text
OS scheduling
CPU frequency 변화
cache 상태
background process
memory allocation 상태
filesystem cache
```

따라서 여러 번 반복하고 분포를 봅니다.

최소한:

```text
여러 번 반복
최솟값
중앙값 또는 평균
편차
```

중 필요한 값을 기록합니다.

어떤 통계가 적합한지는 benchmark 성격에 따라 달라질 수 있습니다.

---

## warm-up

JIT가 없는 일반적인 C++ native code에서도 첫 실행은 다음 때문에 후속 실행과 다를 수 있습니다.

```text
page fault
filesystem cache
dynamic linking
CPU cache
allocator 초기화
```

따라서 매우 짧은 benchmark라면 warm-up iteration을 별도로 두고 측정값에서 제외할 수 있습니다.

---

## benchmark 자체가 최적화로 사라지지 않게 합니다

compiler는 사용되지 않는 계산을 제거할 수 있습니다.

예:

```cpp
for (...) {
    expensive_computation();
}
```

결과를 전혀 사용하지 않으면 optimizer가 계산 일부나 전체를 제거할 수 있습니다.

따라서 benchmark에서는 결과가 실제로 관찰되는 방식으로 사용되도록 해야 합니다.

전문 benchmark library는 이런 문제를 처리하는 도구를 제공하기도 합니다.

---

## 성능 측정과 profiling은 다릅니다

benchmark는 보통:

```text
이 작업이 얼마나 걸리는가?
```

를 측정합니다.

profiler는:

```text
전체 실행 시간 중 어디에서 시간이 소비되는가?
```

를 찾는 데 사용합니다.

예를 들어 프로그램 전체가 느린데 어디가 병목인지 모른다면 먼저 profiler로 hot path를 찾고, 그 뒤 작은 benchmark로 개선 전후를 비교하는 흐름이 자연스러울 수 있습니다.

---

## 성능 수치를 요구사항과 연결합니다

단순히:

```text
10% 빨라졌다
```

만 기록하기보다 실제 요구와 연결합니다.

예:

```text
10만 개 task 정렬
기존: 38ms
변경 후: 24ms
목표: 50ms 이하
```

이렇게 하면 최적화가 실제로 필요한지 판단하기 쉽습니다.

---

## 완료 기록

"테스트 완료", "문제 없음"처럼 결과만 적으면 나중에 무엇을 검사했는지 알기 어렵습니다.

다음 정보를 남깁니다.

```text
실행 명령
입력
환경
통과한 조건
의도적으로 만든 실패
사용한 sanitizer
실행하지 못한 검사
실행하지 못한 이유
```

예:

```text
Command:
ctest --test-dir build/asan --output-on-failure

Environment:
Clang 18
Linux x86_64
ASan enabled

Checked:
- parse success/failure
- duplicate insertion rollback
- UniqueFile move cleanup
- queue shutdown

Not checked:
- ThreadSanitizer
Reason:
- ASan과 별도 build 필요
```

이런 기록은 "무엇이 검증되었고 무엇이 아직 검증되지 않았는가"를 구분하게 합니다.

---

## 재현 명령을 남깁니다

bug를 고쳤다면 수정 내용뿐 아니라 재현 가능한 test command를 함께 남기는 것이 좋습니다.

예:

```text
Before:
ctest -R queue.submit.full
→ intermittent failure

After:
ctest -R queue.submit.full --repeat until-fail:100
→ 100회 통과
```

동시성 문제라면 한 번 통과했다는 사실보다 반복 실행 결과가 더 유용할 수 있습니다.

---

## 실패한 테스트의 최소 재현

큰 E2E test에서 문제가 발견되면 가능한 한 더 작은 재현으로 줄입니다.

예:

```text
전체 application 실행에서 crash
↓
특정 command sequence로 축소
↓
특정 Store 호출로 축소
↓
두 함수 호출만으로 재현
```

최소 재현은 다음에 도움이 됩니다.

- 원인 분석
- debugger 사용
- regression test 작성
- 관계없는 subsystem 제거

---

## regression test

버그를 수정했다면 가능하면 그 버그를 다시 재현하는 테스트를 남깁니다.

흐름:

```text
1. 버그를 재현하는 test 작성
2. 수정 전 test 실패 확인
3. 코드 수정
4. test 통과 확인
5. 이후에도 test 유지
```

이렇게 하면 같은 종류의 버그가 나중 refactoring에서 다시 생기는 것을 막을 수 있습니다.

---

## debugger와 sanitizer를 함께 사용할 수 있습니다

예를 들어 ASan이 다음을 보고했다고 가정합니다.

```text
heap-use-after-free
```

ASan report에는 allocation, free, invalid access 위치가 포함될 수 있습니다.

그 정보를 바탕으로 debugger breakpoint를 설정해:

```text
객체가 언제 free되는가?
왜 observer가 남아 있는가?
```

를 더 자세히 조사할 수 있습니다.

즉:

```text
sanitizer
    → 문제 종류와 발생 위치 탐지

debugger
    → 상태 변화 과정 조사
```

처럼 함께 사용할 수 있습니다.

---

## assertion

프로그램 내부에서 "이 조건은 반드시 참이어야 한다"는 invariant를 검사할 때 assertion을 사용할 수 있습니다.

예:

```cpp
assert(queue_.size() <= capacity_);
```

assertion failure는 정상적인 사용자 오류를 처리하는 방식이 아닙니다.

예를 들어 사용자가 잘못된 입력을 줬다는 이유로:

```cpp
assert(valid_user_input);
```

를 사용하는 것은 적절하지 않습니다.

사용자 입력은 정상적인 오류 처리 경로로 처리해야 합니다.

---

## assertion은 build 설정에 따라 사라질 수 있습니다

표준 `assert()`는 `NDEBUG`가 정의된 build에서 비활성화될 수 있습니다.

따라서 다음과 같이 사용하면 안 됩니다.

```cpp
assert(do_required_side_effect());
```

Release build에서 expression 자체가 실행되지 않을 수 있기 때문입니다.

assert에는 side effect가 없는 조건 검사를 넣습니다.

```cpp
do_required_side_effect();
assert(condition);
```

---

## 로그도 진단 도구입니다

동시성·I/O 문제에서는 debugger를 붙이기 어려운 환경이 있을 수 있습니다.

이때 구조화된 로그가 도움이 됩니다.

예:

```text
timestamp
thread id
job id
state transition
error category
```

하지만 로그가 synchronization 자체를 대신하지는 않습니다.

또 민감한 값이나 내부 credential을 그대로 기록하지 않도록 주의해야 합니다.

---

## 테스트가 실패했을 때의 조사 순서

문제가 발생하면 다음 순서로 범위를 좁힐 수 있습니다.

```text
1. 실패를 반복 재현할 수 있는가?
2. 어떤 observable condition이 깨졌는가?
3. 더 작은 test로 축소할 수 있는가?
4. compile/runtime/concurrency/resource 문제 중 어느 종류인가?
5. sanitizer가 해당 문제 종류를 찾을 수 있는가?
6. debugger에서 잘못된 상태가 처음 생기는 시점을 찾을 수 있는가?
7. 수정 후 regression test를 남겼는가?
```

---

## 도구 선택 기준

### compile-time 오류 계약

사용:

```text
static_assert
type trait
concept check
compile-fail test
```

### 값·상태 규칙

사용:

```text
unit test
property-style 반복 test
failure injection
```

### 실제 component 결합

사용:

```text
integration test
temporary filesystem
실제 thread/socket
```

### 외부 프로그램 동작

사용:

```text
E2E test
stdout/stderr
exit status
```

### memory lifetime 문제

사용:

```text
AddressSanitizer
debugger
```

### undefined behavior

사용:

```text
UndefinedBehaviorSanitizer
```

### data race

사용:

```text
ThreadSanitizer
결정적인 concurrency test
```

### 잘못된 상태가 생기는 순간 추적

사용:

```text
breakpoint
watchpoint
backtrace
```

### 성능 병목

사용:

```text
profiler
분리된 benchmark
Release build
```

---

## 자주 놓치는 문제

### 함수 이름만 따라 테스트를 만듭니다

무엇을 보장해야 하는지보다 public function 하나당 test 하나를 만드는 데 집중하면 실제 요구사항이 빠질 수 있습니다.

---

### 성공 경로만 검사합니다

예외 안전성, rollback, resource cleanup은 실패를 실제로 만들어야 검사할 수 있습니다.

---

### 동시성 테스트에서 `sleep()`으로 상태를 추측합니다

scheduler와 머신 속도에 따라 flaky test가 됩니다.

사건을 직접 synchronization합니다.

---

### compile-fail test가 compiler 오류 문자열 전체에 의존합니다

compiler 버전이 바뀌면 의미는 같은데 문자열 차이로 실패할 수 있습니다.

---

### 모든 dependency를 mock으로 바꿉니다

실제 fd, socket, thread, filesystem의 정리와 결합 문제를 놓칠 수 있습니다.

---

### 모든 테스트를 E2E로 만듭니다

느리고 실패 위치가 불분명해집니다.

핵심 규칙은 unit test로 직접 검사합니다.

---

### sanitizer가 통과하면 코드가 올바르다고 생각합니다

sanitizer는 특정 저수준 오류만 탐지합니다.

논리 오류, deadlock, 요구사항 위반은 별도 테스트가 필요합니다.

---

### sanitizer를 한 configuration에 모두 켭니다

서로 호환되지 않는 sanitizer가 있을 수 있으므로 별도 build를 사용합니다.

---

### crash line만 보고 원인이라고 판단합니다

잘못된 상태는 훨씬 이전에 만들어졌을 수 있습니다.

watchpoint, backtrace, sanitizer report를 이용해 최초 원인을 찾습니다.

---

### Debug build 성능을 production 성능으로 해석합니다

optimization 수준이 달라 의미 있는 비교가 되지 않을 수 있습니다.

---

### 한 번의 짧은 benchmark를 확정적인 결과로 기록합니다

scheduler, cache, background load의 영향을 받을 수 있습니다.

반복과 환경 정보를 함께 기록합니다.

---

### assertion에 필요한 side effect를 넣습니다

`NDEBUG` build에서 expression이 사라질 수 있습니다.

---

### 테스트가 다른 테스트가 만든 상태에 의존합니다

단독 실행, 순서 변경, 병렬 실행에서 실패할 수 있습니다.

---

## 실전 확인 순서

새 기능이나 버그 수정 후 다음 순서로 확인할 수 있습니다.

```text
1. 요구사항을 observable condition으로 문장화
2. 가장 작은 단위 test 작성
3. 실패 경로가 있다면 failure injection 추가
4. 실제 resource 결합이 있다면 integration test 추가
5. 사용자-visible behavior라면 E2E test 추가
6. memory/thread 문제 가능성이 있으면 sanitizer build 실행
7. 재현되지 않는 상태 문제면 debugger로 변화 시점 추적
8. 성능 요구가 있다면 Release benchmark 실행
9. 실행 명령과 환경, 미실행 항목을 기록
```

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 수행할 수 있어야 합니다.

- 구현 함수 이름보다 관찰 가능한 실패·성공 조건을 먼저 작성합니다.
- compile-time, 단위, 통합, E2E 검사를 각각 어떤 문제에 사용하는지 구분합니다.
- `static_assert`, type trait, concept, compile-fail test로 타입 계약을 확인합니다.
- compiler diagnostic 문자열 전체보다 compile 성공·실패와 핵심 위치를 중심으로 검사합니다.
- 모든 것을 mock으로 바꾸거나 모든 검사를 E2E로 만드는 문제를 설명합니다.
- 동시성 테스트를 시간 지연이 아니라 `promise`/`future`, condition variable, latch/barrier 같은 사건으로 맞춥니다.
- 동시성 test 자체에 timeout을 두어 무한 대기를 명확한 실패로 바꿉니다.
- rollback과 resource cleanup을 failure injection으로 확인합니다.
- allocation, filesystem, socket 등 평소 발생하기 어려운 오류 경로를 의도적으로 재현합니다.
- 실패 직후 값·크기·resource 수·thread 상태 등 함수 계약에 맞는 상태를 검사합니다.
- AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer가 각각 주로 어떤 문제를 찾는지 설명합니다.
- sanitizer가 실행된 경로의 특정 오류만 찾으며 일반적인 correctness test를 대신하지 못한다는 점을 설명합니다.
- 서로 호환되지 않는 sanitizer를 별도 build로 실행합니다.
- debugger에서 crash 위치뿐 아니라 잘못된 상태가 처음 생기는 시점을 추적합니다.
- breakpoint, watchpoint, backtrace, thread stack을 문제 유형에 맞게 사용합니다.
- CTest에 test를 등록하고 test 이름과 timeout을 실패 위치를 찾기 쉽게 구성합니다.
- filesystem test를 독립된 temporary directory에서 실행합니다.
- test가 다른 test의 실행 순서나 남은 상태에 의존하지 않게 만듭니다.
- README나 project-local 명령으로 새 checkout에서도 같은 검사를 실행할 수 있게 합니다.
- Release 계열 build에서 성능을 측정하고 compiler, CPU, 입력 크기, 반복 횟수를 기록합니다.
- parsing·I/O·출력 시간을 알고리즘 benchmark에 섞지 않습니다.
- 한 번의 실행보다 반복 편차와 환경 차이를 확인합니다.
- bug 수정 뒤 최소 재현과 regression test를 남깁니다.
- "테스트 완료"가 아니라 실행 명령, 조건, 실패 주입, 미실행 항목과 이유를 기록합니다.
