# 서로 다른 값이 같은 캐시 라인을 공유할 때

두 스레드는 서로 다른 계수기만 수정합니다. `compact` 배치는 계수기를 붙여 두고, `padded` 배치는 각 값을 64바이트 간격으로 둡니다. 계산 결과가 같은지 먼저 검사한 뒤 실행 시간을 비교합니다.

```sh
make check
make benchmark
```

이 예제는 [멀티코어, 캐시 일관성과 거짓 공유](../../docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md)의 실제 pthread 관찰 자료입니다. 같은 현상을 `processor-model`의 MESI 추적 입력으로도 확인할 수 있습니다.

## 구현 순서

| 순서 | 구현 단계 | 주요 위치 |
| ---: | --- | --- |
| 1 | 비교할 계수기 배치 | `false_sharing.c::compact_counter` |
| 2 | 동시 시작 조건 | `false_sharing.c::start_gate` |
| 3 | 스레드별 독립 갱신 | `false_sharing.c::run_worker` |
| 4 | 한 측정의 자원 수명 | `false_sharing.c::run_case` |
| 4-1 | 동일 조건 비교 | `false_sharing.c::main` |
| 5 | 동일한 pthread 빌드 조건 | `Makefile::$(TARGET)` |

`padded`가 항상 더 빠르다고 가정하지 않습니다. 실행 가능한 CPU 수, 스레드 배치, 반복 횟수, 캐시 라인 크기와 다른 작업 부하에 따라 차이가 작거나 반대로 보일 수 있습니다.

이 프로그램에서 각 스레드는 서로 다른 C 객체를 수정하므로 같은 스칼라 값에 대한 데이터 경쟁은 없습니다. 관찰 대상은 하드웨어가 소유권을 관리하는 단위가 개별 `uint64_t`가 아니라 캐시 라인이라는 점입니다.

실제 코드에 패딩을 무조건 추가하면 메모리 사용량과 캐시·TLB 작업 집합이 늘어납니다. 여러 스레드가 자주 쓰는 주소와 실제 메모리 배치를 확인한 뒤 적용해야 합니다.
