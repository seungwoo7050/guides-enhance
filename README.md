# 운영체제 원리 가이드

운영체제는 CPU, 메모리, 저장장치와 장치를 여러 실행 주체가 함께 사용할 수 있도록 관리합니다. 이 저장소는 특정 커널의 명령이나 내부 자료구조를 외우는 대신, 운영체제가 유지하는 상태와 상태 전이, 후보를 고르는 기준, 자원 수명, 장애가 발생해도 지켜야 할 불변식을 학습합니다.

학습은 문서를 모두 읽은 뒤 한꺼번에 실습하는 방식으로 진행하지 않습니다. 필요한 개념을 먼저 익힌 다음 `exercises/kernel-model/`의 해당 기능을 확인하고, 테스트가 어떤 오류를 잡는지 설명한 뒤 다음 주제로 넘어갑니다.

자세한 순서는 [학습 경로](docs/00-roadmap.md)에 정리되어 있습니다.

## 완료 후 갖춰야 할 능력

이 저장소를 마치면 다음 내용을 설명하고 작은 상태 모델로 재현할 수 있어야 합니다.

1. system call, exception, fault와 interrupt를 발생 원인과 재개 위치로 구분합니다.
2. process와 thread가 `READY`, `RUNNING`, `BLOCKED`, `TERMINATED` 사이를 이동하는 이유를 추적합니다.
3. FCFS, SJF, priority, round-robin과 MLFQ를 response time, waiting time, throughput, fairness와 starvation 위험으로 비교합니다.
4. race condition, data race, atomicity, visibility와 ordering을 구분하고, 보호할 predicate에 맞춰 동기화 도구를 선택합니다.
5. lost wakeup, cancellation, deadlock, starvation, livelock과 priority inversion을 자원 보유·대기 관계로 분석합니다.
6. address space, mapping, PTE와 physical frame을 구분하고 not-present, protection, COW fault의 처리 결과를 설명합니다.
7. page cache에 보이는 값과 장애 뒤 남는 값을 구분하고, file과 directory의 durability 및 journal recovery를 추적합니다.
8. 장치 요청의 제출, DMA 실행, interrupt completion, cancellation과 결과 회수 사이에서 buffer와 request의 수명을 추적합니다.
9. 정상 결과뿐 아니라 모순된 snapshot을 불변식 검사로 거부하고, 거부 이유를 설명합니다.

## 필수 문서

### 1. 커널 진입과 실행 상태

- [커널 경계와 사건](docs/01-boundary-and-execution/01-kernel-boundary-and-events.md)
- [프로세스, 스레드와 문맥 전환](docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md)
- [블록, 깨우기와 IPC](docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md)
- [CPU 스케줄링](docs/01-boundary-and-execution/03-cpu-scheduling.md)

### 2. 동시성과 진행 보장

- [경쟁, 원자성과 순서](docs/02-concurrency/01-races-atomicity-and-ordering.md)
- [동기화 도구와 조건 대기](docs/02-concurrency/02-synchronization-primitives.md)
- [데드락과 진행 보장](docs/02-concurrency/03-deadlock-and-progress.md)

### 3. 가상 메모리

- [주소 공간과 page fault](docs/03-virtual-memory/01-address-spaces-and-faults.md)
- [요구 페이징, COW와 page replacement](docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md)

### 4. 저장장치와 장치 I/O

- [파일시스템, page cache와 장애 일관성](docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md)
- [장치 I/O, interrupt와 DMA](docs/04-storage-and-io/02-device-io-interrupts-and-dma.md)

이 11개 문서는 모두 필수입니다. 주제가 서로 연결되기는 하지만, 다른 문서로 충분히 대체할 수 있는 내용은 없습니다.

## 필수 실습

[`exercises/kernel-model/`](exercises/kernel-model/README.md)은 운영체제의 주요 상태를 결정론적으로 실행하는 Python 시뮬레이터입니다.

다음 내용을 하나의 프로젝트에서 확인합니다.

- 실행 주체의 상태와 큐 위치
- condition generation과 semaphore handoff
- CPU scheduling 정책과 metric
- deadlock 탐지와 safe sequence
- demand paging, COW와 page replacement
- filesystem durability와 journal recovery
- 장치 요청, DMA pin, cancellation과 completion
- JSON CLI와 잘못된 snapshot 거부

전체 검증은 다음 명령으로 실행합니다.

```sh
make -C exercises/kernel-model check
```

이 프로젝트는 실제 커널을 재현하지 않습니다. 대신 실제 시간, hardware timing과 scheduler 우연성을 제거하여 같은 입력에서 같은 결과를 만듭니다. 따라서 상태 전이와 불변식을 검증하기에 적합합니다.

## 관찰 예제

[`examples/`](examples/README.md)의 C 프로그램은 사용자 공간에서 확인할 수 있는 현상을 보여 줍니다.

```sh
make -C examples check
make -C examples verify
make -C examples sanitizer-check
```

예제는 다음 내용을 관찰합니다.

- `write` 성공과 `open` 실패의 반환값 및 `errno`
- 분리된 atomic load/store에서 발생하는 lost update
- bounded buffer의 condition wait
- 전역 lock order로 제거한 circular wait
- `fork` 뒤 부모와 자식 값의 분리
- anonymous memory를 처음 쓸 때 변하는 minor fault 통계

관찰값만으로 특정 커널의 내부 구현을 단정하지 않습니다. 정확한 주소, fault 수와 실행 시점은 환경에 따라 달라질 수 있습니다.

## 권장 학습 순서

다음 순서는 `kernel-model`의 구현 의존성을 따릅니다.

```text
학습 경로 확인
→ kernel boundary, process/thread, block/wakeup
→ lifecycle 모델과 불변식 확인
→ race와 synchronization
→ condition generation과 semaphore 확인
→ CPU scheduling
→ scheduler trace와 metric 확인
→ deadlock과 진행 보장
→ deadlock 분석 확인
→ address space와 fault
→ paging, COW와 replacement 확인
→ filesystem durability
→ filesystem과 journal recovery 확인
→ device I/O와 DMA
→ request lifetime 확인
→ CLI 및 전체 테스트 실행
→ 부족한 주제만 다시 읽기
```

문서 전체를 먼저 읽을 필요는 없습니다. 다음 구현 단계를 이해하는 데 필요한 문서까지만 읽고 바로 실행 결과와 테스트를 확인합니다.

## 선택 확장

[확장 상태·binary image 실습](docs/80-extended-labs.md)은 필수 과정을 마친 뒤 선택합니다.

다음처럼 더 좁거나 구현 의존성이 큰 주제를 다룹니다.

- page-table 주소 계산
- MLFQ 규칙별 trace
- 학습용 binary filesystem image와 parser
- device descriptor ring의 generation 관리

이 문서를 완료하지 않아도 운영체제 기초 과정은 끝난 것으로 봅니다.

## 요구 환경

필수 실습은 다음 환경을 전제로 합니다.

- Python 3.10 이상
- POSIX `sh`
- `make`

C 관찰 예제에는 다음 항목도 필요합니다.

- C11 compiler
- POSIX thread
- `fork`, `waitpid`, `getrusage`를 제공하는 Unix 계열 환경

Linux와 macOS를 지원합니다. Windows에서는 WSL과 같은 POSIX 환경이 필요합니다.

## 완료 기준

다음을 모두 만족하면 이 과정을 완료한 것으로 봅니다.

- 필수 문서 11개의 핵심 질문에 자신의 말로 답할 수 있습니다.
- `make -C exercises/kernel-model check`가 통과합니다.
- 정상 scenario 9개의 결과가 왜 나오는지 설명할 수 있습니다.
- invalid snapshot 8개가 어떤 불변식을 위반하는지 설명할 수 있습니다.
- scheduling, COW, crash recovery, cancellation 중 하나를 골라 상태 변화를 처음부터 끝까지 추적할 수 있습니다.
- 관찰 예제의 고정된 결과와 환경에 따라 달라지는 값을 구분할 수 있습니다.

## 다루지 않는 범위

이 저장소는 다음 내용을 필수 과정에 포함하지 않습니다.

- 실제 kernel module 또는 device driver 구현
- 특정 운영체제의 scheduler와 memory manager 소스 분석
- real-time scheduling
- NUMA와 multi-CPU load balancing의 세부 구현
- 실제 filesystem on-disk format
- production kernel debugging
- 언어별 전체 memory model과 lock-free memory reclamation

필요해졌을 때 이 저장소의 상태·수명·불변식 모델을 바탕으로 해당 주제를 다시 학습하면 됩니다.
