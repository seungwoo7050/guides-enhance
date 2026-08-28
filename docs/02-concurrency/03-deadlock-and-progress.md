# 데드락과 진행 보장

## 학습 목표

- 정상 block, deadlock, starvation, livelock과 priority inversion을 관찰 가능한 상태로 구분합니다.
- wait-for graph와 여러 instance 자원 계산으로 진행할 수 없는 작업을 찾습니다.
- 예방, 회피, 탐지와 복구 방법의 전제와 비용을 비교합니다.

## 멈춘 것처럼 보이는 상태를 구분합니다

### 정상 block

작업이 I/O, timer, condition 또는 message를 기다립니다. 필요한 외부 사건이 발생하면 진행할 수 있습니다.

### deadlock

작업 집합이 서로 필요한 자원을 기다려 외부 개입 없이는 어느 작업도 진행할 수 없습니다.

### starvation

다른 작업은 계속 완료되지만 특정 작업은 scheduler 또는 lock queue에서 계속 밀립니다.

### livelock

작업들이 실행되고 상태도 바뀌지만 서로 양보하거나 충돌을 반복하여 완료하지 못합니다.

### priority inversion

높은 priority 작업이 낮은 priority 작업이 보유한 자원을 기다리면서, 중간 priority 작업 때문에 간접적으로 더 늦게 실행됩니다.

진단할 때는 다음을 확인합니다.

```text
CPU를 사용하고 있습니까?
상태 값이 계속 바뀝니까?
어떤 작업이라도 완료됩니까?
특정 작업만 오래 기다립니까?
기다리는 사건이 외부에서 올 수 있습니까?
누가 무엇을 보유하고 무엇을 기다립니까?
```

## wait-for graph

단일 instance 자원에서는 작업 사이의 대기 관계를 graph로 줄일 수 있습니다.

```text
A가 B가 가진 자원을 기다림 → A → B
B가 C가 가진 자원을 기다림 → B → C
C가 A가 가진 자원을 기다림 → C → A
```

cycle이 있으면 해당 작업들은 서로를 기다립니다. 단일 instance 자원에서는 cycle이 deadlock의 충분한 증거가 될 수 있습니다.

`kernel-model`의 `find_wait_cycle`은 DFS의 현재 stack에 다시 들어오는 edge를 찾고 cycle 경로를 복원합니다. 이미 탐색을 끝낸 node로 향하는 edge는 cycle로 잘못 판단하지 않습니다.

## 여러 instance 자원

자원 종류별로 여러 개가 있을 때는 cycle만으로 충분하지 않을 수 있습니다. 다음 상태를 사용합니다.

```text
available[resource]
allocation[task][resource]
outstanding[task][resource]
```

현재 `available`로 요청을 만족할 수 있는 작업을 하나 골라 완료했다고 가정하고, 그 작업이 가진 allocation을 돌려받습니다. 더 이상 제거할 작업이 없을 때 남은 집합이 현재 진행할 수 없는 작업입니다.

## Coffman 조건

deadlock이 생기려면 전통적으로 다음 네 조건이 함께 필요합니다.

1. **상호 배제**: 한 resource를 동시에 하나의 작업만 사용합니다.
2. **보유 후 대기**: 가진 resource를 놓지 않고 다른 resource를 기다립니다.
3. **강제 회수 불가**: system이 resource를 임의로 빼앗아도 안전하지 않습니다.
4. **순환 대기**: 대기 관계에 cycle이 있습니다.

이 목록은 암기보다 어느 조건을 없앨 수 있는지 찾는 데 사용합니다.

```text
상호 배제 완화
→ immutable data, copy 또는 공유 가능한 resource 사용

보유 후 대기 제거
→ 필요한 resource를 한 번에 요청하고 실패하면 모두 반납

강제 회수 허용
→ rollback 가능한 작업 또는 lease 사용

순환 대기 제거
→ 모든 작업이 같은 lock order 사용
```

각 방법에는 비용이 있습니다. resource를 한 번에 잡으면 동시에 실행할 수 있는 범위가 줄고, rollback에는 이전 상태가 필요합니다.

## 전역 lock order

`examples/dining-cycle.c`는 필요한 두 lock 중 번호가 작은 것을 먼저 획득합니다.

```sh
make -C examples build/dining-cycle
./examples/build/dining-cycle 100
```

모든 edge가 낮은 번호에서 높은 번호로 향하므로 circular wait를 만들 수 없습니다.

이 프로그램이 보장하지 않는 항목도 구분해야 합니다.

- 모든 diner가 지정한 횟수만큼 완료하는지는 확인합니다.
- 공정한 대기 시간은 보장하지 않습니다.
- starvation이 절대 없다는 것도 증명하지 않습니다.

## try-lock과 livelock

```text
첫 lock 획득
둘째 lock 실패
첫 lock 반납
즉시 다시 시도
```

두 작업이 같은 시점에 반복하면 서로 계속 양보하면서 완료하지 못할 수 있습니다. random backoff, priority 또는 중앙 arbiter가 충돌을 줄일 수 있지만, random delay 자체가 정확성을 증명하지는 않습니다.

진행 보장 용어도 구분합니다.

```text
blocking
- 다른 작업이 resource를 반납해야 진행합니다.

lock-free
- system 전체에서 어떤 작업인가는 계속 진행합니다.
- 특정 작업은 계속 실패할 수 있습니다.

wait-free
- 각 작업이 유한한 단계 안에 완료합니다.

obstruction-free
- 혼자 실행하면 완료할 수 있습니다.
```

## starvation

다음 규칙에서 starvation이 생길 수 있습니다.

- 낮은 priority 작업보다 높은 priority 작업이 계속 도착합니다.
- reader-preference lock에서 writer가 계속 밀립니다.
- unfair mutex를 일부 thread가 반복해서 다시 획득합니다.
- MLFQ의 낮은 queue가 boost되지 않습니다.
- semaphore가 waiter 순서를 보장하지 않습니다.

완화 방법에는 aging, FIFO wait queue, quota와 periodic boost가 있습니다. 평균 latency뿐 아니라 최대 대기 시간과 작업별 service share를 확인해야 합니다.

## 안전 상태와 회피

회피 알고리즘은 각 작업의 최대 요구량을 알아야 합니다.

```text
available
allocation[task]
maximum[task]
need = maximum - allocation
```

현재 `available`로 `need`를 만족할 수 있는 작업을 찾고, 완료했다고 가정해 allocation을 돌려받습니다. 모든 작업을 제거할 수 있으면 safe sequence가 있습니다.

```text
unsafe
- 앞으로의 요청 순서에 따라 deadlock이 생길 수 있습니다.
- 현재 이미 deadlock이라는 뜻은 아닙니다.

deadlocked
- 현재 요청과 allocation으로는 완료할 작업이 없습니다.
```

Banker 계열 방법은 최대 요구량을 미리 알아야 하고 resource 이용률을 낮출 수 있으므로 모든 system에 적합하지 않습니다.

## 탐지 뒤 복구

deadlock을 찾은 뒤에는 다음 중 하나를 선택할 수 있습니다.

- 작업 하나를 종료합니다.
- rollback 가능한 작업을 이전 상태로 되돌립니다.
- resource를 강제로 회수합니다.
- 운영자에게 상태를 알리고 수동으로 복구합니다.

희생 작업을 고를 때는 이미 수행한 작업량, 보유 resource, priority와 반복 실패 가능성을 고려합니다. 작업을 종료하면 열린 file, transaction과 external side effect를 어떻게 정리할지도 확인해야 합니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.DeadlockTests -v
python3 kernel-model.py deadlock examples/deadlock-cycle.json
python3 kernel-model.py deadlock examples/deadlock-safe.json
```

## 완료 기준

- 정상 block, deadlock, starvation, livelock과 priority inversion을 구분할 수 있습니다.
- 단일 instance wait-for graph에서 cycle을 찾을 수 있습니다.
- 여러 instance 자원에서 완료 가능한 작업을 줄여 나갈 수 있습니다.
- unsafe와 deadlocked 상태의 차이를 설명할 수 있습니다.
- 전역 lock order가 circular wait를 없애는 이유와 보장하지 않는 항목을 설명할 수 있습니다.

## 잘못된 이해

- 프로그램이 오래 멈췄다는 이유만으로 deadlock이라고 단정합니다.
- graph에 cycle이 있으면 여러 instance 자원에서도 항상 deadlock이라고 판단합니다.
- try-lock과 즉시 재시도가 deadlock을 항상 해결한다고 생각합니다.
- lock-free가 모든 thread의 공정한 완료를 뜻한다고 생각합니다.

## 자기 설명

- system 전체가 진행해도 특정 작업이 starvation 상태일 수 있는 이유는 무엇입니까?
- unsafe 상태가 현재 deadlock과 다른 이유는 무엇입니까?
- lock order가 deadlock은 막아도 starvation 부재를 증명하지 못하는 이유는 무엇입니까?
