# 동시성·시간·filesystem

## 사용 시점

이 문서는 모든 C++ 프로그램이 처음부터 반드시 적용해야 하는 고정 선행 범위가 아닙니다. 실제 프로젝트에서 다음 문제가 나타날 때 필요한 절을 찾아 적용합니다.

- 여러 thread가 같은 상태를 읽고 변경합니다.
- 작업 취소나 종료 순서를 정의해야 합니다.
- timeout이나 경과 시간을 정확히 측정해야 합니다.
- 파일을 갱신하다 실패해도 이전 내용을 보존해야 합니다.
- 동시성 테스트가 `sleep()` 시간에 따라 불안정하게 성공하거나 실패합니다.

핵심은 thread, mutex, clock, filesystem API를 각각 외우는 것이 아니라 다음 질문에 답하는 것입니다.

```text
공유 상태의 불변식은 무엇인가?
누가 그 상태를 어떤 synchronization으로 보호하는가?
어느 시점부터 새 작업을 받지 않는가?
대기 중인 thread는 종료 사실을 어떻게 알게 되는가?
timeout은 어떤 clock을 기준으로 측정하는가?
파일 갱신 중 실패하면 이전 상태가 보존되는가?
```

---

## data race와 논리 오류는 다릅니다

C++에서 **data race**는 단순히 "두 thread가 같은 변수를 사용한다"는 뜻이 아닙니다.

대략 다음 조건이 겹칠 때 문제가 됩니다.

- 두 실행이 동시에 일어날 수 있습니다.
- 같은 memory location에 접근합니다.
- 적어도 하나는 쓰기입니다.
- 적절한 synchronization 관계가 없습니다.
- 해당 접근이 모두 atomic으로 처리되는 것도 아닙니다.

이런 data race가 발생하면 프로그램 동작은 정의되지 않습니다.

예:

```cpp
int counter = 0;

void worker() {
    ++counter;
}
```

여러 thread가 synchronization 없이 `counter`를 동시에 증가시키면 읽기와 쓰기가 서로 충돌할 수 있습니다.

단순히 값 하나만 원자적으로 처리하면 되는 경우에는 `std::atomic`이 적합할 수 있습니다.

```cpp
std::atomic<int> counter{0};

void worker() {
    ++counter;
}
```

하지만 atomic을 사용한다고 여러 상태 사이의 **논리적 관계**까지 자동으로 보호되는 것은 아닙니다.

---

## data race가 없어도 프로그램은 틀릴 수 있습니다

다음 코드를 생각합니다.

```cpp
if (queue.size() < capacity)
    queue.push(job);
```

`size()`와 `push()` 각각이 내부적으로 안전하다고 가정하더라도, 두 연산 사이에 다른 thread가 끼어들 수 있다면 전체 규칙은 깨질 수 있습니다.

예를 들어 capacity가 1이고 queue가 비어 있다고 가정합니다.

```text
producer A: size() == 0 확인
producer B: size() == 0 확인
producer A: push(jobA)
producer B: push(jobB)
```

두 producer 모두 자신의 검사 시점에는 빈자리가 있다고 판단했습니다.

결과:

```text
queue.size() == 2
capacity == 1
```

가 될 수 있습니다.

즉 문제는 단일 변수의 접근이 아니라:

```text
"capacity를 확인하고 그 결과에 따라 삽입한다"
```

라는 **check-then-act 전체가 하나의 논리 연산**이라는 점입니다.

---

## mutex는 변수 하나가 아니라 불변식을 보호합니다

mutex를 다음처럼 생각하면 설계가 더 명확합니다.

```text
mutex가 queue_를 보호한다
```

보다:

```text
mutex가 queue_와 관련 상태가 만족해야 하는 불변식을 보호한다
```

가 더 정확합니다.

예를 들어 작업 queue가 다음 규칙을 가진다고 가정합니다.

```text
queue_.size() <= capacity_

queued 상태인 JobId는 queue_에 정확히 한 번 존재

terminal 상태인 job은 queue_에 존재하지 않음
```

그렇다면 이 규칙을 함께 바꾸는 상태들은 같은 synchronization 정책 아래 있어야 합니다.

예:

```cpp
bool Queue::try_push(Job job) {
    std::lock_guard lock{mutex_};

    if (queue_.size() >= capacity_)
        return false;

    queue_.push(std::move(job));
    return true;
}
```

capacity 확인과 삽입이 같은 critical section 안에 있으므로 다른 producer가 그 중간 상태를 볼 수 없습니다.

---

## critical section

mutex를 획득한 뒤 해제하기 전까지 공유 상태를 보호하는 구간을 흔히 **critical section**이라고 합니다.

```cpp
{
    std::lock_guard lock{mutex_};

    // critical section
    // mutex_가 보호하는 공유 상태 접근
}
```

좋은 critical section은 다음 두 요구를 동시에 만족해야 합니다.

```text
너무 짧지 않아야 함
    → 하나의 논리적 상태 변경이 중간에 노출되지 않음

불필요하게 길지 않아야 함
    → 다른 thread를 오래 막지 않음
```

따라서 "lock 범위는 항상 최대한 짧게"라는 규칙만으로는 부족합니다.

정확한 기준은:

> 공유 상태의 불변식을 깨뜨리지 않는 범위에서 불필요한 작업을 lock 밖으로 옮깁니다.

---

## lock 범위를 줄이되 상태 변경은 끝냅니다

다음 형태는 mutex 안에서 필요한 공유 상태만 꺼내고 실제 작업은 lock 밖에서 수행합니다.

```cpp
Work work;

{
    std::lock_guard lock{mutex_};
    work = take_next_locked();
}

work();
```

이 구조가 유용한 이유는 `work()`가 다음과 같은 동작을 할 수 있기 때문입니다.

- 오래 걸립니다.
- I/O를 수행합니다.
- 다른 mutex를 획득합니다.
- 다시 현재 객체를 호출합니다.
- 예외를 던집니다.
- 사용자 callback을 실행합니다.

이 모든 작업 동안 현재 mutex를 계속 잡고 있을 필요가 없다면 다른 thread의 진행을 불필요하게 막게 됩니다.

---

## 외부 callback을 lock 안에서 호출하지 않도록 주의합니다

다음 코드는 위험할 수 있습니다.

```cpp
void Service::notify() {
    std::lock_guard lock{mutex_};

    callback_();
}
```

`callback_()`의 구현을 현재 클래스가 통제하지 못한다면 다음 문제가 생길 수 있습니다.

### 재진입으로 인한 deadlock

callback이 다시 `Service`의 mutex가 필요한 함수를 호출할 수 있습니다.

```text
Service가 mutex 획득
↓
callback 호출
↓
callback이 Service::query() 호출
↓
query()가 같은 mutex 획득 시도
↓
진행 불가
```

### lock 장기 점유

callback이 파일 I/O나 network I/O를 수행하면 다른 thread가 오랫동안 기다릴 수 있습니다.

### lock ordering 문제

callback이 다른 mutex를 획득하고 다른 thread가 반대 순서로 mutex를 획득하면 deadlock 가능성이 생깁니다.

가능하다면 callback 실행에 필요한 데이터를 lock 안에서 준비하고 lock을 해제한 뒤 호출합니다.

```cpp
Callback callback;
Data data;

{
    std::lock_guard lock{mutex_};
    callback = callback_;
    data = make_snapshot_locked();
}

callback(data);
```

---

## 상태 변경을 여러 lock 구간으로 나누지 않습니다

lock 범위를 줄인다는 이유로 하나의 논리 상태 변경을 임의로 나누면 다른 thread가 중간 상태를 관찰할 수 있습니다.

예:

```cpp
{
    std::lock_guard lock{mutex_};
    jobs_[id].state = State::queued;
}

{
    std::lock_guard lock{mutex_};
    queue_.push(id);
}
```

이 두 변경이 항상 함께 성립해야 한다면 첫 번째 lock이 풀린 직후 다음 상태가 외부에 보일 수 있습니다.

```text
job은 queued 상태
하지만 queue에는 아직 없음
```

불변식이:

```text
queued 상태인 JobId는 queue에 정확히 한 번 존재
```

라면 잘못된 중간 상태입니다.

이 경우 두 변경을 같은 critical section에서 수행해야 합니다.

```cpp
{
    std::lock_guard lock{mutex_};

    jobs_[id].state = State::queued;
    queue_.push(id);
}
```

---

## 여러 mutex를 사용할 때는 lock 순서를 정합니다

두 개 이상의 mutex를 서로 다른 순서로 잡으면 deadlock이 발생할 수 있습니다.

예:

```text
thread A
mutex A 획득
↓
mutex B 기다림

thread B
mutex B 획득
↓
mutex A 기다림
```

둘 모두 상대가 가진 mutex를 기다리므로 진행할 수 없습니다.

가능하면 하나의 불변식을 하나의 mutex로 보호해 구조를 단순하게 합니다.

여러 mutex를 동시에 획득해야 한다면 `std::scoped_lock` 같은 도구를 사용할 수 있습니다.

```cpp
std::scoped_lock lock{mutex_a, mutex_b};
```

직접 순서를 관리해야 한다면 프로젝트 전체에서 일관된 lock ordering을 정해야 합니다.

---

## `volatile`은 thread synchronization이 아닙니다

C++의 `volatile`을 공유 변수에 붙인다고 data race가 해결되는 것은 아닙니다.

```cpp
volatile bool stopped = false;
```

이것은 mutex나 `std::atomic`을 대신하지 않습니다.

thread 사이에 값을 안전하게 전달해야 한다면 해당 상태의 성격에 따라:

```text
std::mutex
std::atomic
condition variable
```

등 적절한 synchronization을 사용해야 합니다.

---

## atomic과 mutex의 역할을 구분합니다

독립적인 단일 상태를 원자적으로 읽고 쓰는 정도라면 atomic이 잘 맞을 수 있습니다.

```cpp
std::atomic<bool> stopped_{false};
```

하지만 여러 값이 함께 하나의 불변식을 이룬다면 mutex가 더 자연스러운 경우가 많습니다.

예:

```text
queue 내용
queue 크기 제한
job 상태
```

이 세 가지를 서로 일관되게 바꿔야 한다면 각 값을 별도 atomic으로 만드는 것만으로 전체 규칙이 자동으로 원자적이 되지 않습니다.

즉:

```text
atomic operation
≠
여러 연산으로 구성된 transaction
```

입니다.

---

## condition variable은 "상태 변화 알림" 도구입니다

thread가 어떤 조건이 될 때까지 기다려야 한다고 가정합니다.

예:

```text
queue에 작업이 들어옴
또는
서비스가 종료됨
```

이를 반복적으로 polling할 수 있습니다.

```cpp
while (true) {
    {
        std::lock_guard lock{mutex_};
        if (stopped_ || !queue_.empty())
            break;
    }

    // 다시 확인
}
```

하지만 이렇게 계속 확인하면 CPU를 불필요하게 사용할 수 있습니다.

condition variable을 사용하면 조건이 바뀔 가능성이 있을 때 thread를 잠들게 하고 필요한 시점에 깨울 수 있습니다.

---

## condition variable은 predicate와 함께 사용합니다

대표적인 패턴은 다음과 같습니다.

```cpp
std::unique_lock lock{mutex_};

changed_.wait(lock, [this] {
    return stopped_ || !queue_.empty();
});
```

여기서 실제로 중요한 것은 `changed_` 자체가 아니라 predicate입니다.

```cpp
stopped_ || !queue_.empty()
```

즉 기다리는 대상은:

```text
"notify가 왔다"
```

가 아니라:

```text
"현재 상태가 내가 진행할 수 있는 조건을 만족한다"
```

입니다.

---

## `wait()`가 하는 일

개념적으로 predicate 기반 `wait()`는 다음 동작을 반복합니다.

```text
mutex를 가진 상태에서 predicate 확인
↓
false이면
mutex를 놓고 sleep
↓
깨움
↓
mutex를 다시 획득
↓
predicate 다시 확인
```

이를 직접 쓰면 대략 다음 형태입니다.

```cpp
std::unique_lock lock{mutex_};

while (!stopped_ && queue_.empty()) {
    changed_.wait(lock);
}
```

predicate overload는 이 패턴을 더 안전하고 간결하게 표현합니다.

---

## spurious wakeup

condition variable은 실제 상태 변화와 직접 대응하지 않는 wakeup을 허용합니다.

즉 `wait()`에서 돌아왔다고 다음이 자동으로 참이라는 뜻은 아닙니다.

```text
queue에 작업이 반드시 존재한다
```

따라서 다음 코드는 안전하지 않습니다.

```cpp
changed_.wait(lock);

// 작업이 있다고 가정
auto job = queue_.front();
```

대신 predicate를 다시 검사합니다.

```cpp
changed_.wait(lock, [this] {
    return stopped_ || !queue_.empty();
});
```

이 패턴은 spurious wakeup뿐 아니라 여러 waiter가 같은 알림 뒤 경쟁하는 경우에도 중요합니다.

---

## notify는 상태 자체를 저장하지 않습니다

condition variable을 event queue처럼 생각하면 안 됩니다.

다음 순서를 생각합니다.

```text
notify 발생
↓
아직 waiter 없음
↓
나중에 waiter가 wait 시작
```

이전 `notify`가 "한 개 저장되어 있다가" 나중 waiter를 자동으로 통과시키는 것이 아닙니다.

그래서 condition variable에서는 실제 상태를 별도 변수에 저장합니다.

예:

```cpp
bool stopped_{false};
std::queue<Job> queue_;
```

waiter는 이 상태를 predicate로 검사합니다.

---

## 상태를 먼저 변경하고 알립니다

일반적인 구조는 다음과 같습니다.

```cpp
{
    std::lock_guard lock{mutex_};
    queue_.push(std::move(job));
}

changed_.notify_one();
```

중요한 것은 waiter가 깨어났을 때 확인할 실제 상태가 이미 변경되어 있어야 한다는 것입니다.

즉 논리적으로:

```text
상태 변경
→ notify
```

순서를 사용합니다.

실제 `notify_one()`을 mutex를 잡은 상태에서 호출할지, 풀고 호출할지는 설계와 성능 특성에 따라 달라질 수 있습니다. 핵심은 predicate를 구성하는 공유 상태 변경 자체가 올바른 synchronization 아래 이루어져야 한다는 점입니다.

---

## `notify_one()`과 `notify_all()`

대기 중인 thread 중 하나만 진행하면 충분한 경우:

```cpp
changed_.notify_one();
```

모든 waiter가 조건을 다시 확인해야 하는 상태 변화라면:

```cpp
changed_.notify_all();
```

을 사용할 수 있습니다.

예를 들어 서비스 종료 시 모든 worker가 `stopped_`를 확인해야 한다면 `notify_all()`이 자연스러울 수 있습니다.

```cpp
{
    std::lock_guard lock{mutex_};
    stopped_ = true;
}

changed_.notify_all();
```

---

## timeout이 있는 wait에도 predicate가 필요합니다

시간 제한을 두고 기다릴 때도 wakeup과 조건을 구분해야 합니다.

예:

```cpp
std::unique_lock lock{mutex_};

const bool ready = changed_.wait_for(
    lock,
    timeout,
    [this] {
        return stopped_ || !queue_.empty();
    }
);
```

`ready == false`라면 주어진 시간 안에 predicate가 참이 되지 않았음을 의미합니다.

단순히 wakeup이 있었는지만 보는 것이 아니라 **조건 충족 여부**를 확인합니다.

---

## `std::jthread`와 thread 수명

C++20의 `std::jthread`는 `std::thread`보다 수명 관리가 편리한 경우가 많습니다.

`std::jthread`가 파괴될 때 joinable 상태라면 일반적으로:

```text
stop 요청
↓
join
```

을 수행합니다.

따라서 단순히 `std::thread`를 소멸시키면서 `join()`이나 `detach()`를 빠뜨리는 문제를 줄일 수 있습니다.

하지만 이것이 worker를 강제로 즉시 종료한다는 뜻은 아닙니다.

---

## stop request는 협력적 취소입니다

worker 함수가 stop request를 확인해야 실제로 종료할 수 있습니다.

```cpp
void work(std::stop_token token) {
    while (!token.stop_requested()) {
        run_one_step();
    }
}
```

`request_stop()`은 다음 명령이 아닙니다.

```text
지금 즉시 이 thread를 강제 종료하라
```

대신 다음 의미입니다.

```text
가능한 안전한 지점에서 종료해 달라는 요청
```

worker가 요청을 확인하지 않으면 계속 실행할 수 있습니다.

---

## 왜 강제 종료가 위험한가

임의의 시점에 thread를 중단하면 그 thread가 다음 상태일 수 있습니다.

```text
mutex를 획득한 상태
파일을 갱신하는 중
객체 불변식을 갱신하는 중
메모리를 할당한 직후
외부 자원을 보유한 상태
```

이 시점에 강제로 종료하면 cleanup과 불변식 복구가 수행되지 않을 수 있습니다.

협력적 취소는 worker가 자신이 안전하게 멈출 수 있는 지점에서 종료하도록 합니다.

---

## stop 확인 주기를 정합니다

다음 worker는 한 단계가 매우 오래 걸린다면 stop 요청에 늦게 반응할 수 있습니다.

```cpp
while (!token.stop_requested()) {
    run_one_step(); // 10분 동안 block될 수도 있음
}
```

따라서 cancellation latency는 `stop_requested()` 호출의 존재만이 아니라 실제 작업 구조에 달려 있습니다.

긴 작업은 가능하다면 더 작은 단계로 나누거나, 사용하는 blocking API가 취소 가능한지 확인합니다.

---

## blocking wait와 stop

worker가 condition variable이나 I/O에서 block되어 있으면 단순히 stop을 요청하는 것만으로 깨어나지 않을 수 있습니다.

예를 들어 일반적인 `std::condition_variable`에서:

```cpp
changed_.wait(lock, predicate);
```

로 무기한 기다리고 있다면 종료 상태를 변경한 뒤 `notify_all()`로 깨워야 할 수 있습니다.

```cpp
{
    std::lock_guard lock{mutex_};
    stopped_ = true;
}

changed_.notify_all();
```

또는 stop token을 지원하는 대기 API를 사용할 수 있습니다.

C++20의 `std::condition_variable_any`에는 `std::stop_token`과 함께 사용할 수 있는 wait overload가 있습니다.

핵심은 다음입니다.

```text
stop 요청
+
현재 block된 작업을 깨우는 방법
```

을 함께 설계해야 합니다.

---

## stop callback

stop 요청 시 특정 동작을 수행해야 한다면 `std::stop_callback` 같은 방법을 사용할 수 있습니다.

예를 들어 대기 primitive를 깨우는 구조를 만들 수 있습니다.

다만 callback 자체도 동시 실행될 수 있으므로 callback에서 접근하는 상태에 대한 synchronization과 lifetime을 별도로 고려해야 합니다.

즉 stop mechanism 역시 기존 동시성 규칙에서 예외가 아닙니다.

---

## bounded queue와 backpressure

producer가 consumer보다 빠르면 무제한 queue는 계속 커질 수 있습니다.

```text
producer: 초당 1000개 생성
consumer: 초당 100개 처리
```

차이는 초당 900개씩 누적됩니다.

장시간 실행하면 메모리 사용량이 계속 증가할 수 있습니다.

그래서 queue에 capacity를 둘 수 있습니다.

```text
0 <= queue.size() <= capacity
```

---

## backpressure는 "가득 찼을 때 어떻게 할지"에 대한 정책입니다

capacity에 도달했을 때 가능한 정책은 여러 가지입니다.

### 즉시 거부

```text
queue full
→ 새 작업 거부
→ caller가 queue_full 결과를 받음
```

caller가 재시도 여부를 결정할 수 있습니다.

### producer 대기

```text
queue full
→ producer block
→ consumer가 공간 생성
→ producer 진행
```

처리량을 맞출 수 있지만 producer thread까지 막힌다는 의미가 있습니다.

### 오래된 작업 삭제

실시간 상태 업데이트처럼 최신 값이 더 중요할 때 사용할 수 있습니다.

하지만 어떤 작업을 버렸는지 외부 의미를 정의해야 합니다.

### 우선순위에 따라 교체

낮은 우선순위 작업을 제거하고 높은 우선순위 작업을 넣을 수 있습니다.

이 경우 queue가 단순 FIFO가 아니므로 ordering과 starvation 정책까지 고려해야 할 수 있습니다.

---

## backpressure는 API 계약에 드러나야 합니다

queue가 가득 찼을 때 즉시 거부한다면 caller가 그 결과를 구분할 수 있어야 합니다.

예:

```cpp
enum class SubmitError {
    stopped,
    queue_full
};
```

```cpp
std::expected<JobId, SubmitError>
submit(Job job);
```

`queue_full`을 단순한 `"I/O error"` 문자열과 같은 값으로 반환하면 caller가 다음 행동을 선택하기 어렵습니다.

```text
queue_full
    → 잠시 후 재시도 가능

stopped
    → 재시도해도 현재 서비스에서는 처리 불가
```

오류 종류가 실제 제어 흐름에 영향을 주면 타입으로 구분하는 편이 좋습니다.

---

## 종료와 backpressure가 만날 때

producer가 queue가 비기를 기다리는 동안 시스템이 종료될 수 있습니다.

따라서 대기 predicate가 단순히:

```cpp
queue_.size() < capacity_
```

만 확인해서는 부족할 수 있습니다.

예:

```cpp
space_available_.wait(lock, [this] {
    return stopped_ || queue_.size() < capacity_;
});
```

깨어난 뒤에는 `stopped_` 여부를 먼저 확인합니다.

```cpp
if (stopped_)
    return std::unexpected{SubmitError::stopped};
```

종료 조건을 모든 blocking wait의 predicate에 포함해야 shutdown 중 thread가 영원히 기다리지 않게 만들 수 있습니다.

---

## 시간에는 서로 다른 의미가 있습니다

"시간"이라고 해서 하나의 clock으로 모두 처리하지 않습니다.

프로그램에서는 주로 다음 두 종류를 구분합니다.

```text
경과 시간 / timeout
벽시계 시각 / 날짜
```

이 둘은 요구하는 성질이 다릅니다.

---

## 경과 시간에는 `steady_clock`

timeout이나 duration 측정에는 보통 `std::chrono::steady_clock`을 사용합니다.

```cpp
const auto start = std::chrono::steady_clock::now();

// work

const auto elapsed =
    std::chrono::steady_clock::now() - start;
```

deadline도 만들 수 있습니다.

```cpp
const auto deadline =
    std::chrono::steady_clock::now() + timeout;
```

`steady_clock`의 중요한 성질은 시간이 뒤로 가지 않는 monotonic clock이라는 점입니다.

따라서 경과 시간 계산에 적합합니다.

---

## 왜 `system_clock`을 timeout에 사용하지 않는가

system wall clock은 외부 조정의 영향을 받을 수 있습니다.

예:

```text
NTP 시간 보정
관리자의 시스템 시각 변경
가상 환경의 clock 조정
```

시스템 시각이 앞으로 또는 뒤로 조정되면 단순 wall-clock 차이를 timeout에 사용한 코드가 예상과 다르게 동작할 수 있습니다.

따라서:

```text
얼마나 지났는가?
언제 timeout인가?
```

를 판단할 때는 `steady_clock`이 자연스럽습니다.

---

## 실제 날짜와 시각에는 `system_clock`

로그 timestamp나 사용자에게 보여 줄 실제 시각은 wall clock과 연결되어야 합니다.

예:

```text
2026-08-29 14:32:10
```

이런 값은 `std::chrono::system_clock` 계열이 적합합니다.

정리하면:

```text
steady_clock
    → duration
    → timeout
    → benchmark interval

system_clock
    → 실제 날짜/시각
    → log timestamp
    → 외부 시각 표현
```

---

## 서로 다른 clock의 time point를 섞지 않습니다

다음 두 값은 의미가 다릅니다.

```cpp
auto steady_now = std::chrono::steady_clock::now();
auto system_now = std::chrono::system_clock::now();
```

두 clock의 `time_point`를 같은 기준의 값처럼 직접 비교하려 하지 않습니다.

deadline을 만들었다면 같은 clock으로 현재 시각을 읽어 비교합니다.

```cpp
const auto deadline =
    std::chrono::steady_clock::now() + timeout;

if (std::chrono::steady_clock::now() >= deadline) {
    // timeout
}
```

---

## duration은 단위를 타입으로 표현합니다

`std::chrono`는 시간 단위를 타입으로 표현합니다.

```cpp
using namespace std::chrono_literals;

auto timeout = 500ms;
auto interval = 2s;
```

다음처럼 단위 없는 정수만 전달하는 것보다 의미가 명확합니다.

```cpp
start_timer(500); // 500이 ms인지 s인지 불명확
```

가능하면 API도 duration을 직접 받도록 설계합니다.

```cpp
void wait_for(std::chrono::milliseconds timeout);
```

또는 generic duration을 받을 수도 있습니다.

---

## timeout은 deadline으로 바꾸면 반복 대기에서 유리합니다

여러 번의 wait를 반복할 때 매번 동일한 duration으로 기다리면 전체 시간이 원래 timeout보다 길어질 수 있습니다.

예:

```text
timeout = 5초

wait 1
spurious wakeup
다시 5초 wait
또 wakeup
다시 5초 wait
```

이런 문제를 피하려면 처음에 절대 deadline을 계산하고 그 deadline을 기준으로 기다리는 방식이 유용할 수 있습니다.

```cpp
const auto deadline =
    std::chrono::steady_clock::now() + timeout;
```

그 뒤 남은 시간을 다시 계산하거나 `wait_until()`을 사용합니다.

이렇게 하면 반복 wakeup이 있어도 전체 timeout 기준을 유지하기 쉽습니다.

---

## 테스트에서는 clock을 주입할 수 있습니다

timeout 테스트를 실제 시간 흐름에만 의존하면 test가 느리고 불안정해질 수 있습니다.

예를 들어 production 코드가 항상 직접:

```cpp
std::chrono::steady_clock::now()
```

를 호출하면 테스트가 실제 시간이 지나기를 기다려야 할 수 있습니다.

필요하다면 "현재 시간 제공자"를 dependency로 분리할 수 있습니다.

개념적으로:

```cpp
class Clock {
public:
    virtual TimePoint now() const = 0;
};
```

또는 template이나 callable을 주입할 수 있습니다.

테스트에서는 가짜 clock을 원하는 만큼 진행시켜 timeout 경계를 즉시 검사할 수 있습니다.

모든 작은 프로그램에서 clock abstraction이 필요한 것은 아니지만, 시간 의존 테스트가 복잡해지기 시작하면 고려할 수 있습니다.

---

## 파일을 직접 truncate한 뒤 쓰는 위험

기존 파일을 바로 열어 내용을 비우고 다시 쓰는 방식은 중간 실패에 취약합니다.

예:

```text
기존 target
↓
truncate
↓
새 내용 일부 write
↓
오류 또는 process crash
```

이 경우 이전 정상 내용은 이미 사라졌고 새 내용도 완성되지 않았을 수 있습니다.

결과:

```text
이전 버전 없음
새 버전도 불완전
```

이 될 수 있습니다.

---

## 새 파일을 완성한 뒤 교체합니다

더 안전한 기본 패턴은 다음과 같습니다.

```text
1. 같은 디렉터리에 임시 파일 생성
2. 새 내용을 임시 파일에 모두 기록
3. write/flush/close 오류 확인
4. 임시 파일을 target 이름으로 교체
```

예:

```text
config.json
```

을 직접 덮어쓰기보다:

```text
config.json.tmp
```

를 먼저 완성한 뒤 교체합니다.

이렇게 하면 쓰기 단계에서 실패했을 때 기존 target을 그대로 유지하기 쉽습니다.

---

## temp file을 같은 filesystem에 두는 이유

rename을 이용한 교체는 source와 target이 같은 filesystem에 있을 때 가장 단순하게 사용할 수 있습니다.

다른 filesystem 사이의 이동은 실제로 copy + delete 같은 동작이 필요할 수 있고, 단일 atomic rename으로 처리할 수 없을 수 있습니다.

따라서 교체용 temp file은 일반적으로 target과 같은 디렉터리 또는 같은 filesystem에 둡니다.

---

## rename의 원자성과 내구성은 다릅니다

같은 filesystem 안의 rename은 많은 운영체제와 filesystem에서 directory entry를 원자적으로 바꾸는 기본 수단으로 사용할 수 있습니다.

이때 관찰자는 보통:

```text
이전 이름 상태
또는
새 이름 상태
```

중 하나를 보게 만드는 것을 목표로 합니다.

그러나 다음은 별개의 문제입니다.

```text
rename이 논리적으로 원자적임
≠
전원 장애 뒤 disk에 반드시 남음
```

또한 destination이 이미 존재할 때의 동작과 atomic replacement의 세부사항은 운영체제 및 filesystem API에 따라 차이가 있을 수 있습니다.

따라서 portable C++ 코드에서는 단순히 `std::filesystem::rename()`을 호출했다는 이유만으로 모든 플랫폼에서 동일한 crash-safe replacement semantics가 보장된다고 가정하면 안 됩니다.

---

## `flush`, `close`, `fsync`는 같은 보장이 아닙니다

출력 stream의 `flush()`는 library 또는 OS buffer 쪽으로 데이터를 밀어내는 역할을 하지만, 전원 장애 뒤 물리 저장 장치에 남는 것까지 항상 보장하는 개념은 아닙니다.

crash-safe persistence가 실제 요구사항이라면 운영체제 수준의 durability primitive를 검토해야 합니다.

POSIX 계열에서는 보통 다음과 같은 문제를 생각합니다.

```text
temp file 쓰기
↓
file data를 fsync
↓
close
↓
rename
↓
directory metadata를 fsync
```

정확한 순서와 보장은 filesystem과 운영체제에 따라 달라질 수 있습니다.

또한 표준 C++ filesystem API 자체에는 POSIX `fsync()`와 동일한 portable 기능이 없습니다.

따라서 **일반적인 파일 교체**와 **전원 장애까지 고려한 내구성 보장**은 요구 수준을 분리해서 설계해야 합니다.

---

## 파일 갱신 실패 시 temp file 정리

임시 파일을 쓰다가 실패하면 target을 건드리지 않고 temp file만 정리할 수 있어야 합니다.

예:

```text
write temp
↓
실패
↓
temp 삭제 시도
↓
기존 target 유지
```

temp 파일 삭제 역시 실패할 수 있으므로 cleanup 오류를 어떻게 처리할지도 필요에 따라 정의합니다.

최소한 기존 정상 파일을 먼저 손상시키지 않는 것이 핵심입니다.

---

## 파일 이름 충돌도 고려합니다

고정된 이름 하나만 사용하면 여러 process나 thread가 동시에 저장할 때 충돌할 수 있습니다.

예:

```text
config.json.tmp
```

를 모두가 사용하면 서로의 임시 파일을 덮어쓸 수 있습니다.

동시 저장 가능성이 있다면 고유한 temporary filename을 만들거나, 파일 수준 synchronization 또는 상위 serialization 정책을 정의해야 합니다.

단순한 single-process, single-writer 프로그램이라면 이 복잡성이 필요하지 않을 수 있습니다.

---

## 종료는 하나의 protocol입니다

프로그램 종료를 단순히:

```cpp
stopped_ = true;
```

하나로 끝내면 안 되는 경우가 많습니다.

thread pool이나 queue가 있다면 종료 시 다음 항목을 정해야 합니다.

```text
새 요청을 더 받을 것인가?
이미 queue에 있는 작업은 처리할 것인가 버릴 것인가?
실행 중인 작업은 취소할 것인가 완료시킬 것인가?
대기 중인 worker는 어떻게 깨울 것인가?
누가 thread를 join하는가?
자원은 어느 순서로 파괴되는가?
```

즉 shutdown 자체가 명확한 protocol이어야 합니다.

---

## 종료 순서를 구체적으로 정합니다

한 가지 가능한 종료 순서는 다음과 같습니다.

```text
새 요청 중단
→ 대기 작업 취소 또는 배출 정책 적용
→ 실행 작업에 stop 요청
→ condition variable 대기자 깨움
→ worker가 종료 조건 확인
→ worker join
→ 파일·socket 등 작업 자원 정리
→ synchronization 객체를 포함한 owner 소멸
```

프로젝트마다 정확한 정책은 달라질 수 있지만, 순서가 우연한 destructor 호출에만 의존하지 않도록 해야 합니다.

---

## "drain"과 "cancel"을 구분합니다

종료 시 queue에 남은 작업을 어떻게 할지 명시합니다.

### drain

```text
새 작업은 받지 않음
기존 queue는 끝까지 처리
모두 끝나면 worker 종료
```

데이터 손실을 피해야 하는 batch 작업에서 자연스러울 수 있습니다.

### cancel pending

```text
새 작업은 받지 않음
아직 시작하지 않은 작업은 취소
실행 중 작업에는 stop 요청
worker 종료
```

빠른 종료가 중요한 interactive service에서 사용할 수 있습니다.

두 정책은 사용자에게 보이는 결과가 다르므로 API와 테스트에서 구분해야 합니다.

---

## 종료 상태는 submit과 wait에도 반영합니다

서비스가 종료를 시작한 뒤 새 작업을 받지 않는다면:

```cpp
submit(job)
```

은 명시적인 `stopped` 결과를 반환해야 할 수 있습니다.

queue에 공간이 생기기를 기다리는 producer도 종료 상태를 predicate로 확인해야 합니다.

worker 역시:

```cpp
stopped_ || !queue_.empty()
```

같은 조건으로 깨어날 수 있어야 합니다.

즉 shutdown 상태는 시스템의 여러 blocking 지점에 일관되게 전달되어야 합니다.

---

## worker가 자기 자신을 join하면 안 됩니다

thread는 자기 자신이 종료되기를 기다릴 수 없습니다.

예를 들어 worker callback 안에서:

```cpp
service.stop();
```

을 호출하고 `stop()`이 모든 worker를 즉시 join하려 한다면 현재 worker 자신까지 join하려 할 수 있습니다.

개념적으로:

```text
worker A
↓
stop()
↓
join(worker A)
↓
worker A가 자기 종료를 기다림
```

이는 진행할 수 없습니다.

따라서 `request_stop()`과 최종 `join()` 책임을 나눌 수 있습니다.

예:

```text
worker 내부 stop 요청
    → 상태 변경 + stop request + notify

외부 owner 또는 destructor
    → 최종 join
```

정확한 구조는 ownership에 따라 달라지지만, **누가 join할 수 있는지**를 명확히 해야 합니다.

---

## destructor와 shutdown

RAII 관점에서 thread owner의 destructor가 최종 cleanup을 담당할 수 있습니다.

하지만 destructor가 안전하려면 그 시점에 다음이 보장되어야 합니다.

```text
모든 worker가 종료 가능
blocking wait를 깨울 수 있음
필요한 dependency가 아직 살아 있음
callback이 파괴된 객체를 참조하지 않음
```

따라서 객체 멤버 선언 순서와 외부 dependency 수명도 shutdown과 연결됩니다.

특히 worker thread가 멤버를 참조한다면 thread를 join하기 전에 그 멤버가 파괴되어서는 안 됩니다.

---

## `std::jthread`가 있다고 shutdown 설계가 사라지지 않습니다

`std::jthread`가 destructor에서 stop request와 join을 제공하더라도 다음은 자동으로 결정하지 않습니다.

- queue의 pending 작업을 버릴지 처리할지
- blocking I/O를 어떻게 깨울지
- 여러 worker를 어떤 순서로 종료할지
- callback lifetime을 어떻게 보장할지
- 외부 요청을 언제부터 거부할지

즉 `jthread`는 thread lifetime 관리 도구이지 전체 shutdown 정책 자체는 아닙니다.

---

## 테스트에서 `sleep()`으로 상태를 추측하지 않습니다

동시성 테스트에서 흔한 패턴은 다음과 같습니다.

```cpp
start_worker();

std::this_thread::sleep_for(100ms);

assert(state == expected);
```

이 테스트는 다음을 실제로 보장하지 않습니다.

```text
100ms 안에 worker가 반드시 시작했는가?
CI 환경에서도 충분한가?
scheduler가 다른 thread를 먼저 실행하지 않았는가?
```

빠른 머신에서는 통과하고 느린 머신에서는 실패하거나, 반대로 race가 우연히 숨을 수 있습니다.

---

## 특정 사건을 synchronization으로 기다립니다

테스트가 필요한 것은 "시간이 어느 정도 지났다"가 아니라 보통 구체적인 사건입니다.

예:

```text
worker가 작업을 시작함
queue가 full 상태가 됨
callback 직전 지점에 도달함
stop request를 관찰함
```

이 사건을 직접 signaling하도록 테스트를 구성합니다.

---

## `promise`와 `future`

한 thread가 특정 지점에 도달했음을 다른 thread에 알릴 수 있습니다.

예:

```cpp
std::promise<void> started;
auto ready = started.get_future();

std::jthread worker([&] {
    started.set_value();

    // 계속 실행
});

ready.wait();
```

이제 test thread는 worker가 실제로 `set_value()` 지점까지 도달했다는 사실을 알고 진행합니다.

임의의 `sleep()` 시간보다 의도가 명확합니다.

---

## condition variable로 특정 상태를 기다립니다

테스트 대상이 이미 condition variable을 사용하는 구조라면 상태 predicate를 기다리도록 test hook이나 관찰 API를 설계할 수 있습니다.

중요한 것은:

```text
"충분히 기다렸으니 됐겠지"
```

가 아니라:

```text
"필요한 상태가 실제로 참이 되었음을 확인"
```

하는 것입니다.

---

## barrier와 latch

C++20의 `std::barrier`와 `std::latch`는 여러 thread의 진행 단계를 맞출 때 사용할 수 있습니다.

예를 들어 여러 worker를 모두 같은 시작점까지 모은 뒤 동시에 다음 단계로 진행시키면 특정 경쟁 조건을 재현하기 쉬워질 수 있습니다.

개념적으로:

```text
thread A ─┐
thread B ─┼─> 모두 준비될 때까지 대기
thread C ─┘
              ↓
           다음 단계
```

`latch`는 일반적으로 한 번 카운트가 0이 되면 열린 상태가 되고, `barrier`는 여러 phase에서 반복적으로 동기화하는 데 사용할 수 있습니다.

---

## queue full 테스트는 실제 실행 상태를 먼저 만듭니다

bounded queue의 `queue_full` 동작을 테스트한다고 가정합니다.

단순히 여러 작업을 빠르게 제출하면 worker가 이미 작업을 꺼내 처리해 버릴 수 있습니다.

그러면 예상한 시점에 queue가 가득 차지 않습니다.

더 결정적인 테스트는 다음처럼 구성할 수 있습니다.

```text
1. 첫 작업 제출
2. 첫 작업이 worker에서 실제로 시작했다는 signal 대기
3. 첫 작업을 test-controlled barrier에서 멈춤
4. queue capacity만큼 대기 작업 삽입
5. 추가 submit
6. queue_full 결과 확인
7. 첫 작업 해제
```

이렇게 하면 scheduler 속도에 덜 의존하는 테스트를 만들 수 있습니다.

---

## timeout 테스트는 실제 시간을 기다리지 않습니다

가능하면 clock을 주입하거나, 짧은 wait primitive의 정확한 상태 전환을 사용합니다.

예를 들어 injected clock을 사용하면:

```text
현재 시간 = T0
deadline = T0 + 5s

fake clock을 T0 + 4s로 이동
→ timeout 아님

fake clock을 T0 + 5s로 이동
→ timeout
```

처럼 즉시 경계 조건을 테스트할 수 있습니다.

---

## 동시성 테스트에서 확인할 것은 최종 값만이 아닙니다

다음도 검사 대상입니다.

```text
중복 실행이 없는가?
capacity를 넘지 않는가?
shutdown 뒤 새 작업을 받지 않는가?
대기 thread가 모두 빠져나오는가?
callback이 lock 안에서 호출되지 않는가?
worker가 모두 join되는가?
종료 뒤 observer가 dangling이 되지 않는가?
```

특히 thread leak이나 join 누락은 테스트 프로세스가 끝난다는 이유만으로 놓치기 쉽습니다.

---

## data race 검출 도구도 활용할 수 있습니다

동시성 문제는 테스트 결과만으로 재현되지 않을 수 있습니다.

지원되는 compiler와 플랫폼에서는 ThreadSanitizer 같은 도구가 data race 탐지에 도움이 될 수 있습니다.

하지만 sanitizer가 통과했다고 다음이 자동으로 증명되는 것은 아닙니다.

```text
논리적 invariant가 항상 유지됨
deadlock이 없음
starvation이 없음
shutdown 순서가 올바름
```

도구는 동시성 설계를 대신하지 않습니다.

---

## 자주 놓치는 문제

### mutex를 변수 하나만 보호하는 장치로 생각합니다

실제로는 여러 상태가 함께 만족해야 하는 invariant를 보호해야 할 수 있습니다.

---

### data race만 없으면 thread-safe하다고 생각합니다

check-then-act 같은 여러 연산 사이에 다른 thread가 끼어들어 논리 규칙이 깨질 수 있습니다.

---

### lock 범위를 줄이기 위해 상태 변경을 두 구간으로 나눕니다

그 사이의 불완전한 상태를 다른 thread가 볼 수 있습니다.

---

### 외부 callback을 lock 안에서 실행합니다

재진입 deadlock, 긴 lock 점유, lock ordering 문제가 생길 수 있습니다.

---

### `volatile`로 synchronization을 대신합니다

`volatile`은 일반적인 thread 간 synchronization 도구가 아닙니다.

---

### condition variable의 notify를 상태처럼 생각합니다

notify 자체는 이벤트를 영구 저장하지 않습니다. 실제 predicate 상태가 별도로 있어야 합니다.

---

### `wait()`에서 돌아오면 조건이 참이라고 가정합니다

spurious wakeup과 다른 waiter의 경쟁 때문에 predicate를 다시 확인해야 합니다.

---

### stop request만 보내면 worker가 즉시 끝난다고 생각합니다

worker가 stop token을 확인하거나 blocking wait에서 깨어날 방법이 필요합니다.

---

### bounded queue 종료 시 producer를 깨우지 않습니다

queue 공간을 기다리는 producer가 shutdown 뒤에도 영원히 block될 수 있습니다.

---

### timeout에 `system_clock`을 사용합니다

wall clock 조정 때문에 경과 시간 계산이 흔들릴 수 있습니다.

---

### timeout 반복 대기마다 전체 duration을 다시 사용합니다

spurious wakeup이나 중간 wakeup 때문에 전체 대기 시간이 의도보다 길어질 수 있습니다. deadline 기반 설계를 검토합니다.

---

### target 파일을 먼저 truncate합니다

새 내용 기록 중 실패하면 이전 정상 데이터까지 잃을 수 있습니다.

---

### rename 성공을 전원 장애 내구성 보장으로 해석합니다

atomic namespace update와 durable persistence는 별개의 문제입니다.

---

### worker callback 안의 `stop()`이 자기 자신까지 join합니다

self-join이 발생하지 않도록 stop request와 최종 join 책임을 구분합니다.

---

### 동시성 테스트에서 `sleep()`으로 진행 상태를 추측합니다

scheduler 속도에 따라 flaky test가 됩니다. 명시적인 synchronization으로 필요한 사건을 기다립니다.

---

## 설계할 때의 확인 순서

동시성 기능을 추가할 때 다음 순서로 확인하면 도움이 됩니다.

```text
1. 공유 상태는 무엇인가?
2. 그 상태가 항상 만족해야 하는 invariant는 무엇인가?
3. invariant 전체를 어떤 mutex 또는 atomic 규칙이 보호하는가?
4. 하나의 논리 상태 변경은 한 critical section에서 끝나는가?
5. lock 안에 불필요한 I/O나 외부 callback이 있는가?
6. 기다리는 thread의 predicate는 무엇인가?
7. predicate가 변할 때 waiter를 어떻게 깨우는가?
8. shutdown 상태가 모든 wait predicate에 포함되는가?
9. stop request를 worker가 실제로 관찰하는가?
10. blocking 작업을 깨울 방법이 있는가?
11. 최종 join의 책임자는 누구인가?
```

시간 기능에서는 다음을 확인합니다.

```text
경과 시간/timeout인가?
    → steady_clock

실제 날짜/로그 시각인가?
    → system_clock

반복 wait인가?
    → duration을 반복할지 deadline을 사용할지 확인

테스트가 실제 시간에 의존하는가?
    → clock 주입 필요 여부 검토
```

파일 갱신에서는 다음을 확인합니다.

```text
기존 파일을 먼저 손상시키지 않는가?
temp와 target이 같은 filesystem인가?
쓰기/flush/close 실패를 확인하는가?
rename 교체의 플랫폼 의미를 확인했는가?
전원 장애 내구성까지 필요한가?
필요하다면 OS 수준 fsync 정책을 정의했는가?
```

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- data race의 의미와 여러 연산 사이의 논리적 경쟁 조건을 구분합니다.
- mutex가 단일 변수보다 공유 상태의 불변식을 보호한다는 점을 설명합니다.
- 하나의 논리 상태 변경을 같은 critical section에서 완료합니다.
- lock 범위를 줄이면서도 중간 상태를 다른 thread에 노출하지 않습니다.
- 외부 callback을 lock 밖에서 실행해야 하는 이유를 설명합니다.
- 여러 mutex를 사용할 때 lock ordering과 deadlock 가능성을 확인합니다.
- `volatile`이 thread synchronization을 대신하지 못한다는 점을 설명합니다.
- 단일 atomic 연산과 여러 상태에 걸친 invariant 보호의 차이를 설명합니다.
- condition variable을 실제 predicate와 함께 기다립니다.
- spurious wakeup 때문에 predicate를 다시 확인해야 하는 이유를 설명합니다.
- notify가 상태를 저장하는 기능이 아니라는 점을 설명합니다.
- `notify_one()`과 `notify_all()`을 깨워야 하는 waiter 범위에 따라 선택합니다.
- `std::jthread`의 stop request가 협력적 취소라는 점을 설명합니다.
- blocking wait가 stop request에 반응하도록 별도 wakeup 또는 stop-aware wait를 설계합니다.
- bounded queue에서 capacity 도달 정책을 API 결과로 명확히 표현합니다.
- 종료 중 producer와 worker가 영원히 대기하지 않도록 shutdown 조건을 predicate에 포함합니다.
- 경과 시간과 timeout에는 `steady_clock`, 실제 날짜와 로그 시각에는 `system_clock`을 사용합니다.
- 반복 timeout에서는 deadline 기반 접근이 필요한 이유를 설명합니다.
- 파일을 직접 truncate하는 대신 임시 파일을 완성한 뒤 교체하는 이유를 설명합니다.
- rename의 원자성과 전원 장애 뒤 내구성이 서로 다른 보장임을 설명합니다.
- crash-safe 저장이 필요하면 표준 C++ 범위를 넘어 OS/filesystem 수준 durability를 검토해야 함을 설명합니다.
- shutdown에서 새 요청 중단, pending 작업 정책, stop 요청, waiter 깨움, join, 자원 파괴 순서를 구체적으로 정합니다.
- worker가 자기 자신을 join하지 않도록 stop request와 최종 join 책임을 구분합니다.
- `sleep()` 대신 `promise`/`future`, condition variable, barrier/latch 같은 synchronization으로 동시성 테스트를 결정적으로 구성합니다.
- timeout 테스트에서 필요하다면 clock을 주입해 실제 시간 경과에 의존하지 않습니다.
- data race 탐지 도구가 논리 오류나 deadlock까지 증명해 주는 것은 아님을 설명합니다.
