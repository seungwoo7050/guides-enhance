# 순회 순서와 공간 지역성 비교

같은 2차원 배열을 같은 횟수만큼 더하면서 반복문 순서만 바꿉니다. 행 우선 순회는 연속 주소를 읽고, 열 우선 순회는 `columns * sizeof(uint32_t)`만큼 건너뜁니다. 두 방식의 검사 합계는 같아야 하며 실행 시간은 관찰값으로만 사용합니다.

```sh
make check
make benchmark
```

이 예제는 [성능식과 측정](../../docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md)과 [캐시, 지역성과 AMAT](../../docs/03-memory-hierarchy/06-cache-locality-and-amat.md)를 연결합니다.

## 구현 순서

| 순서 | 구현 단계 | 주요 위치 |
| ---: | --- | --- |
| 1 | 연속 주소 순회 | `layout_benchmark.c::sum_row_major` |
| 1-1 | 큰 보폭 순회 | `layout_benchmark.c::sum_column_major` |
| 2 | 같은 입력의 독립 측정 | `layout_benchmark.c::main` |
| 3 | 동일한 컴파일 옵션 | `Makefile::$(TARGET)` |

실행 시간 비율을 고정된 정답으로 사용하지 않습니다. CPU, 캐시 크기, 컴파일러, 전원 상태와 다른 프로세스의 부하에 따라 결과가 달라집니다. 비교할 때는 행·열·반복 횟수, 컴파일 옵션, 검사 합계와 여러 번 실행한 분포를 함께 기록합니다.

행렬 전체가 상위 캐시에 들어갈 정도로 크기를 줄이거나 `columns=1`로 바꾼 뒤 두 순회의 차이가 줄어드는지 확인할 수 있습니다.
