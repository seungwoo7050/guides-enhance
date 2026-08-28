# 동시성·시간·filesystem

## 사용 시점

이 문서는 고정 선행 범위가 아닙니다. 실제 프로젝트에서 여러 thread가 같은 상태를 다루거나, 취소·timeout·파일 교체가 필요해졌을 때 해당 절을 찾아봅니다.

## data race와 논리 오류

data race는 같은 메모리에 동기화 없이 접근하고 적어도 하나가 쓰는 경우입니다. mutex를 사용해 data race를 없애도 여러 연산 사이의 조건이 깨질 수 있습니다.

```cpp
if (queue.size() < capacity)
    queue.push(job);
```

`size()` 확인과 `push()`가 같은 lock 안에 있지 않으면 두 producer가 모두 빈자리를 봐 capacity를 넘길 수 있습니다.

mutex가 보호하는 것은 변수 하나가 아니라 함께 지켜야 하는 상태입니다.

```text
queue.size() <= capacity
queued 상태인 JobId는 queue에 정확히 한 번 존재
terminal 작업은 queue에 존재하지 않음
```

## lock 범위를 줄이되 상태 변경은 끝냅니다

```cpp
Work work;
{
    std::lock_guard lock{mutex_};
    work = take_next_locked();
}
work();
```

외부 callback을 mutex 안에서 실행하면 오래 걸리거나 다시 같은 객체를 호출해 deadlock이 생길 수 있습니다. 필요한 상태를 꺼내고 lock을 해제한 뒤 호출합니다.

반대로 상태 변경을 여러 lock 구간으로 나누면 중간 상태를 다른 thread가 볼 수 있습니다. 공개 상태가 한 번에 바뀌어야 하는 지점을 먼저 정합니다.

## condition variable은 조건식과 함께 사용합니다

```cpp
std::unique_lock lock{mutex_};
changed_.wait(lock, [this] {
    return stopped_ || !queue_.empty();
});
```

spurious wakeup이 있을 수 있으므로 단순 `wait()` 뒤 상태를 믿지 않습니다. notify는 상태를 대신 저장하지 않습니다. 조건을 먼저 바꾸고 필요한 대기자를 깨웁니다.

## `jthread`와 협력적 취소

`std::jthread`는 소멸 시 stop을 요청하고 join합니다. 그러나 callback이 `stop_token`을 확인하지 않으면 즉시 멈추지 않습니다.

```cpp
void work(std::stop_token token) {
    while (!token.stop_requested()) {
        run_one_step();
    }
}
```

blocking wait는 stop-aware overload 또는 별도 깨움 방법이 필요합니다. 임의의 thread를 강제 종료하면 lock과 자원 정리가 끝나지 않을 수 있습니다.

## bounded queue와 backpressure

queue에 제한이 없으면 producer가 consumer보다 빠를 때 메모리가 계속 증가합니다. capacity에 도달했을 때의 행동을 정합니다.

- 새 작업을 즉시 거부합니다.
- producer가 자리가 날 때까지 기다립니다.
- 오래된 작업을 버립니다.
- 우선순위에 따라 교체합니다.

어느 방식을 택하든 API가 관찰할 결과를 정해야 합니다. `queue_full`을 일반 I/O 오류 문자열과 같은 값으로 돌려주지 않습니다.

## 시간 측정

경과 시간과 timeout에는 `std::chrono::steady_clock`을 사용합니다. 시스템 시각은 NTP 조정이나 사용자의 변경으로 앞뒤로 움직일 수 있습니다.

```cpp
const auto deadline = std::chrono::steady_clock::now() + timeout;
```

로그 시각이나 사용자에게 보여 줄 시각은 `system_clock`이 맞습니다.

## 파일 교체

대상 파일을 먼저 truncate하고 쓰다가 실패하면 이전 내용도 잃습니다. 새 파일을 완성한 뒤 교체합니다.

```text
write temp file
→ flush/close 확인
→ rename temp to target
```

같은 filesystem 안의 rename은 일반적으로 원자적으로 이름을 바꾸지만, 전원 손실 뒤 내구성까지 자동으로 보장하지는 않습니다. crash-safe 저장이 필요하면 file과 directory `fsync`까지 별도로 검토합니다.

## 종료 순서

다음 순서를 구체적으로 정합니다.

```text
새 요청 중단
→ 대기 작업 취소 또는 배출
→ 실행 작업에 stop 요청
→ condition variable 깨움
→ worker join
→ 파일·socket·mutex 보유 객체 소멸
```

worker callback 안에서 `stop()`이 호출될 수 있다면 자기 자신을 join하지 않아야 합니다. 다른 외부 호출이나 소멸자가 최종 join을 수행하게 합니다.

## 테스트

`sleep` 뒤 상태를 추측하지 않습니다.

- `promise`/`future`: 작업 시작과 해제
- condition variable: 특정 상태 도달
- barrier/latch: 여러 thread의 단계 맞춤
- 주입한 clock: timeout 검사

queue full 테스트는 첫 작업이 실제로 실행 중이라는 신호를 받은 뒤 대기열을 채웁니다.

## 완료 기준

- data race와 여러 연산 사이의 논리 오류를 구분합니다.
- mutex가 보호하는 상태 조건을 적습니다.
- condition variable을 predicate와 함께 기다립니다.
- callback을 lock 밖에서 실행할 이유를 설명합니다.
- 취소가 협력 방식이라는 한계를 처리합니다.
- 경과 시간과 실제 시각에 다른 clock을 사용합니다.
- 종료가 모든 thread와 자원의 수명을 끝내는지 테스트합니다.
