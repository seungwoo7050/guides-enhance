# CPU 스케줄링

## 학습 목표

- workload와 tick 처리 순서를 고정한 뒤 scheduling 정책을 비교합니다.
- response, waiting, turnaround, throughput과 fairness의 차이를 계산합니다.
- 다음 작업을 고르는 규칙과 작업 위치 불변식을 따로 검증합니다.

## 먼저 workload를 적습니다

정책을 비교하기 전에 작업의 입력을 명확히 해야 합니다.

```text
arrival time
CPU burst 목록
burst 사이의 I/O wait
priority 또는 deadline
interactive 또는 batch 여부
CPU-bound 또는 I/O-bound 여부
작업 수와 CPU 수
```

CPU burst만 적고 I/O wait를 빼면 `RUNNING → BLOCKED → READY` 전이를 놓칩니다. block된 작업은 scheduler가 선택할 수 없습니다.

## metric은 서로 다른 목표를 나타냅니다

| metric | 의미 | 한쪽만 줄였을 때 생길 수 있는 문제 |
| --- | --- | --- |
| turnaround time | 도착부터 완료까지 걸린 시간 | 짧은 작업 우선 시 긴 작업이 밀릴 수 있음 |
| response time | 도착부터 첫 실행까지 걸린 시간 | 잦은 선점으로 전환 비용 증가 가능 |
| waiting time | READY 상태에서 기다린 시간 | I/O wait와 혼동하면 잘못 계산함 |
| throughput | 단위 시간에 끝낸 작업 수 | 일부 작업의 긴 지연을 숨길 수 있음 |
| fairness | CPU 배분의 균형 | 처리량과 locality가 나빠질 수 있음 |
| deadline miss | 제한 시간 안에 끝내지 못한 수 | 일반적인 fairness와 다른 선택이 필요함 |

평균만 보면 가장 오래 기다린 작업을 알 수 없습니다. 최대값, 높은 percentile과 starvation 가능성도 함께 봅니다.

## 기본 정책

### FCFS

도착 순서대로 실행하며 CPU burst가 끝나거나 block될 때까지 유지합니다.

- 구현이 단순합니다.
- 긴 작업이 앞에 오면 짧은 작업이 오래 기다리는 convoy effect가 생깁니다.

### SJF와 SRTF

SJF는 예상 CPU burst가 가장 짧은 작업을 선택합니다. SRTF는 남은 시간이 더 짧은 작업이 오면 선점합니다.

- 평균 waiting time을 줄일 수 있습니다.
- 미래 burst를 정확히 알기 어렵습니다.
- 긴 작업이 계속 밀릴 수 있습니다.

### priority scheduling

priority가 높은 작업을 먼저 선택합니다. 같은 priority 안에서 FCFS 또는 round-robin을 사용할 수 있습니다.

- 낮은 priority 작업의 starvation을 막으려면 aging이 필요할 수 있습니다.
- 높은 priority 작업이 낮은 priority 작업의 lock을 기다리는 priority inversion은 scheduler만으로 해결되지 않습니다.

### Round Robin

각 작업에 quantum만큼 CPU를 주고, 끝나지 않았으면 ready queue 뒤로 보냅니다.

```text
quantum이 큼
→ FCFS와 비슷해집니다.

quantum이 작음
→ 첫 응답은 빨라질 수 있지만 context switch가 늘어납니다.
```

quantum은 workload와 전환 비용을 함께 보고 정해야 합니다.

### MLFQ

여러 queue와 서로 다른 quantum을 사용합니다. 짧게 실행하고 자주 block되는 작업은 높은 queue에 두고, CPU를 오래 쓰는 작업은 낮은 queue로 내릴 수 있습니다.

다음 규칙을 적지 않으면 실행 결과를 결정할 수 없습니다.

- 새 작업이 들어갈 queue
- quantum을 모두 썼을 때의 demotion
- I/O 뒤 돌아왔을 때의 queue level
- 전체 priority boost 주기
- 같은 queue 안의 순서

## 한 tick의 처리 순서

같은 시각에 여러 사건이 발생하면 순서에 따라 결과가 달라집니다. `kernel-model`은 다음 순서를 사용합니다.

```text
1. 현재 시각까지 도착한 작업을 READY로 넣습니다.
2. I/O wait가 끝난 작업을 READY로 깨웁니다.
3. CPU가 비어 있으면 정책에 따라 한 작업을 고릅니다.
4. 현재 RUNNING, READY, BLOCKED 상태를 기록합니다.
5. READY 작업의 waiting time을 늘립니다.
6. RUNNING 작업을 한 tick 실행합니다.
7. burst 완료, block, 종료 또는 quantum 만료를 처리합니다.
```

arrival과 quantum 만료의 처리 순서를 바꾸면 timeline과 metric이 달라질 수 있습니다. 따라서 tie-break와 사건 순서를 결과와 함께 기록해야 합니다.

## I/O-bound와 CPU-bound 작업

I/O-bound 작업은 짧은 CPU burst 뒤 자주 block됩니다. CPU-bound 작업은 긴 burst를 사용합니다. I/O 작업이 block된 동안 다른 `READY` 작업이 CPU를 사용하므로 장치 대기 시간을 숨길 수 있습니다.

정책이 참고할 수 있는 상태는 다음과 같습니다.

- 최근 CPU 사용량
- ready queue에서 기다린 시간
- block 빈도
- priority와 queue level
- 남은 quantum

interactive 작업의 응답성을 높이면서 긴 CPU-bound 작업을 굶기지 않는 규칙이 필요합니다.

## 정책과 불변식은 별개입니다

어떤 정책을 사용해도 다음 조건은 항상 지켜야 합니다.

```text
한 작업은 동시에 두 CPU에서 실행하지 않습니다.
BLOCKED 작업은 ready queue에 없습니다.
종료한 작업을 다시 선택하지 않습니다.
ready queue는 존재하는 작업만 참조합니다.
모든 metric은 같은 시간 정의로 계산합니다.
```

작업을 고르는 코드가 잘못돼도 queue 위치까지 오염시키지 않도록 선택과 상태 변경을 나누는 편이 좋습니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.SchedulerTests -v
python3 kernel-model.py schedule examples/schedule.json
```

`examples/schedule.json`의 `policy`를 `fcfs`, `sjf`, `priority`, `rr`, `mlfq`로 바꾸어 다음을 비교합니다.

- 각 tick의 `running`, `ready`, `blocked`
- completion order
- response, waiting, turnaround
- CPU가 idle인 구간

## 다중 CPU에서 추가되는 선택

다중 CPU에서는 다음 작업뿐 아니라 어느 CPU의 queue에 넣을지도 정해야 합니다.

```text
global queue
- 부하 분산이 단순합니다.
- queue lock 경쟁이 커질 수 있습니다.

per-CPU queue
- 선택 비용과 locality가 좋아질 수 있습니다.
- imbalance를 줄이기 위한 migration이 필요합니다.
```

기본 과정은 단일 CPU까지만 구현합니다. CPU affinity, NUMA와 실제 load balancer는 선택 주제로 남깁니다.

## 완료 기준

- 다섯 정책의 선택 규칙과 대표적인 약점을 설명할 수 있습니다.
- response, waiting과 turnaround를 계산할 수 있습니다.
- 같은 시각의 사건 처리 순서가 결과를 바꾸는 예를 들 수 있습니다.
- 정책 선택과 queue 불변식을 따로 검사할 수 있습니다.

## 잘못된 이해

- 평균 waiting time이 가장 작은 정책을 항상 최선이라고 판단합니다.
- I/O wait를 ready queue의 waiting time에 포함합니다.
- MLFQ라는 이름만 적고 demotion, promotion과 boost 규칙을 생략합니다.
- quantum을 줄이면 비용 없이 응답성만 좋아진다고 생각합니다.

## 자기 설명

- SJF가 평균 waiting time을 줄이면서도 starvation을 만들 수 있는 이유는 무엇입니까?
- round-robin quantum이 지나치게 작을 때 어떤 비용이 늘어납니까?
- 같은 workload를 비교할 때 tick 처리 순서를 고정해야 하는 이유는 무엇입니까?
