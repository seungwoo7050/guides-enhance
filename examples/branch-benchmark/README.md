# 예측하기 쉬운 분기와 불규칙한 분기 비교

같은 비교식을 두 종류의 입력에 적용합니다. 첫 번째 배열은 앞 절반에서만 조건이 참이고, 두 번째 배열은 고정된 난수열에 따라 참과 거짓이 자주 바뀝니다. 선택한 원소 수로 계산이 실제로 수행됐는지 확인하고, 실행 시간은 관찰값으로만 사용합니다.

```sh
make check
make benchmark
make assembly
```

이 예제는 [성능식과 측정](../../docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md)과 [파이프라인의 위험 요소](../../docs/02-in-order-execution/05-pipeline-hazards-and-branching.md)를 실제 컴파일러 출력과 연결할 때 사용합니다.

## 구현 순서

| 순서 | 구현 단계 | 주요 위치 |
| ---: | --- | --- |
| 1 | 동일한 비교 연산 | `branch_benchmark.c::count_selected` |
| 2 | 비교 가능한 입력과 측정 | `branch_benchmark.c::main` |
| 3 | 동일한 컴파일 옵션 | `Makefile::$(TARGET)` |

두 입력의 실행 시간 비율을 정답으로 고정하지 않습니다. 컴파일러가 조건 이동이나 벡터 비교를 사용하면 실제 분기 명령이 남지 않을 수 있습니다. 먼저 `make assembly`로 `count_selected`가 어떤 명령으로 변환됐는지 확인해야 합니다.

Linux에서 하드웨어 계수기를 사용할 수 있다면 다음과 같이 함께 측정할 수 있습니다.

```sh
perf stat -e cycles,instructions,branches,branch-misses \
  ./build/branch_benchmark 16000000
```

`branch-misses` 지원 여부와 접근 권한은 환경마다 다릅니다. 계수기를 얻지 못했다면 실행 시간 하나만으로 분기 예측기의 내부 동작을 단정하지 않습니다.
