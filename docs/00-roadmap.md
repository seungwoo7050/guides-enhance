# 컴퓨터 구조 학습 로드맵

이 로드맵은 필수 개념을 읽고 바로 실행해 보는 순서를 정합니다. 문서를 많이 읽는 것보다 프로세서가 저장하는 값, 상태가 바뀌는 조건과 실패 원인을 코드와 계산으로 설명하는 데 목적이 있습니다.

## 완료 후 갖춰야 할 능력

- 정수·부동소수점 값과 비트 패턴을 구분합니다.
- ISA, ABI와 마이크로아키텍처가 정하는 내용을 구분합니다.
- 실행 시간을 명령 수, CPI와 클록 주기로 분해합니다.
- 데이터 경로와 5단계 파이프라인에서 값과 제어 신호가 이동하는 과정을 추적합니다.
- 값 전달, 적재 직후 사용 정지와 분기 후 잘못 가져온 명령 제거가 필요한 이유를 설명합니다.
- 캐시 주소를 태그·세트·오프셋으로 나누고 교체·쓰기 상태를 추적합니다.
- VPN·페이지 오프셋·PFN을 계산하고 TLB 실패와 주소 변환 예외를 구분합니다.
- 레지스터 이름 변경, 발행, 실행 완료와 프로그램 순서 반영을 구분하고 정밀한 예외를 설명합니다.
- MESI 상태와 거짓 공유를 캐시 라인 단위로 추적합니다.
- 단순 모델과 실제 하드웨어 측정 결과를 같은 것으로 취급하지 않습니다.

## 전체 필수 경로

```text
표현과 산술
→ Tiny-RISC 실행
→ 성능식
→ 데이터 경로와 제어
→ 5단계 파이프라인
→ 캐시
→ 주소 변환과 TLB
→ 비순차 실행과 추측
→ MESI와 거짓 공유
→ 전체 검증
```

## 1. 데이터 표현

### 문서

[`01-data-representation-and-arithmetic.md`](01-representation-and-isa/01-data-representation-and-arithmetic.md)

### 바로 확인할 코드

- `processor_model/bits.py`
- `BitsTests`

```sh
cd exercises/processor-model
python3 processor-model.py bits add 127 1 --width 8
python3 -m unittest tests.test_processor_model.BitsTests -v
```

### 종료 조건

- 자리올림과 부호 있는 오버플로를 구분합니다.
- 값의 폭, 부호 해석, 바이트 순서와 정렬 조건을 명시할 수 있습니다.
- `0.1`이 f32에서 정확히 표현되지 않는 이유를 설명합니다.

## 2. ISA와 순차 실행

### 문서

[`02-isa-assembly-and-program-execution.md`](01-representation-and-isa/02-isa-assembly-and-program-execution.md)

### 바로 확인할 코드

- `spec/tiny-risc-isa.md`
- `processor_model/isa.py`
- `fixtures/programs/`
- `IsaTests`

```sh
python3 processor-model.py isa fixtures/programs/sum.asm --max-steps 100
python3 -m unittest tests.test_processor_model.IsaTests -v
```

### 종료 조건

- 명령마다 읽는 레지스터, 쓰는 레지스터와 PC 변경을 추적합니다.
- ISA가 정하는 결과와 프로세서 내부 실행 방법을 구분합니다.
- 정렬되지 않은 메모리 접근이 어느 시점에 실패하는지 설명합니다.

## 3. 성능식과 단일 명령 실행

### 문서

1. [`03-performance-cpi-and-amdahl.md`](01-representation-and-isa/03-performance-cpi-and-amdahl.md)
2. [`04-datapath-and-control.md`](02-in-order-execution/04-datapath-and-control.md)

### 바로 확인할 코드

- `processor_model/perf.py`
- `processor_model/control.py`
- `PerformanceTests`
- `ControlTests`

```sh
python3 processor-model.py perf cpu \
  --instructions 1000000000 --cpi 2 --ghz 2
python3 processor-model.py control lw
```

### 종료 조건

- 지연 시간과 처리량을 구분합니다.
- Amdahl의 법칙과 AMAT에 넣는 각 값의 의미를 설명합니다.
- `lw`, `sw`, ALU 명령과 분기가 레지스터와 메모리에 쓰는지 구분합니다.
- 단일 사이클 CPI가 1이어도 클록 주기가 길 수 있는 이유를 설명합니다.

## 4. 파이프라인

### 문서

[`05-pipeline-hazards-and-branching.md`](02-in-order-execution/05-pipeline-hazards-and-branching.md)

### 바로 확인할 코드

- `processor_model/pipeline.py`
- `fixtures/traces/pipeline-*.trace`
- `PipelineTests`

```sh
python3 processor-model.py pipeline \
  fixtures/traces/pipeline-load-use.trace --forwarding full
python3 processor-model.py pipeline \
  fixtures/traces/pipeline-branch.trace --json
```

### 종료 조건

- 구조적 위험, 데이터 위험과 제어 위험을 구분합니다.
- 값 전달로 해결되는 RAW 의존성과 남는 적재 직후 사용 위험을 구분합니다.
- 분기가 실제로 실행됐을 때 버려야 하는 더 젊은 명령을 찾습니다.

선택 관찰:

- [`branch-benchmark`](../examples/branch-benchmark/)

## 5. 캐시

### 문서

[`06-cache-locality-and-amat.md`](03-memory-hierarchy/06-cache-locality-and-amat.md)

### 바로 확인할 코드

- `processor_model/cache.py`
- `fixtures/traces/cache.trace`
- `CacheTests`

```sh
python3 processor-model.py cache fixtures/traces/cache.trace \
  --size 16 --block 4 --ways 1
```

### 종료 조건

- 캐시 크기, 블록 크기와 연관도로 세트 수를 계산합니다.
- 주소를 태그·세트·오프셋으로 나눕니다.
- 최초 접근·충돌·용량 실패의 합이 전체 실패 수와 맞는지 확인합니다.
- 수정된 캐시 라인을 교체할 때 `write-back`이 필요한 이유를 설명합니다.

선택 관찰:

- [`layout-benchmark`](../examples/layout-benchmark/)

## 6. 주소 변환과 TLB

### 문서

[`07-address-translation-and-tlb.md`](03-memory-hierarchy/07-address-translation-and-tlb.md)

### 바로 확인할 코드

- `processor_model/vm.py`
- `fixtures/vm/`
- `VirtualMemoryTests`

```sh
python3 processor-model.py vm fixtures/vm/config.json fixtures/vm/trace.txt
```

### 종료 조건

- 페이지 크기로 VPN과 오프셋을 계산합니다.
- TLB 적중, TLB 실패, 페이지 테이블 순회, 페이지 폴트와 보호 예외를 구분합니다.
- 매핑을 바꾼 뒤 이전 TLB 항목을 제거해야 하는 이유를 설명합니다.

## 7. 비순차 실행과 추측

### 문서

[`08-superscalar-out-of-order-and-speculation.md`](04-parallel-execution/08-superscalar-out-of-order-and-speculation.md)

### 바로 확인할 코드

- `processor_model/predictor.py`
- `processor_model/rob.py`
- `BranchPredictorTests`
- `ReorderBufferTests`

```sh
python3 -m unittest \
  tests.test_processor_model.BranchPredictorTests \
  tests.test_processor_model.ReorderBufferTests -v
```

### 종료 조건

- RAW와 WAR·WAW를 구분합니다.
- 뒤 명령이 먼저 실행을 끝내도 앞 명령보다 먼저 상태에 반영할 수 없는 이유를 설명합니다.
- 폴트가 난 명령보다 젊은 미반영 결과를 버려야 정밀한 예외가 되는 이유를 설명합니다.
- 추측 결과가 상태에 반영되지 않았다는 사실과 프로세서 내부 흔적이 전혀 남지 않았다는 주장을 구분합니다.

## 8. 멀티코어 일관성

### 문서

[`10-multicore-coherence-and-false-sharing.md`](04-parallel-execution/10-multicore-coherence-and-false-sharing.md)

### 바로 확인할 코드

- `processor_model/coherence.py`
- `fixtures/traces/coherence-false-sharing.trace`
- `CoherenceTests`

```sh
python3 processor-model.py coherence \
  fixtures/traces/coherence-false-sharing.trace \
  --cores 2 --line-size 64
```

### 종료 조건

- 두 코어의 읽기·쓰기 순서에 따라 MESI 상태를 적습니다.
- 실제 공유와 거짓 공유를 주소와 캐시 라인으로 구분합니다.
- 캐시 일관성, ISA 메모리 순서와 언어 메모리 모델이 각각 답하는 질문을 구분합니다.

선택 관찰:

- [`false-sharing`](../examples/false-sharing/)

## 선택 학습: SIMD와 벡터화

[`09-simd-vectorization-and-data-layout.md`](04-parallel-execution/09-simd-vectorization-and-data-layout.md)는 필수 완료 조건이 아닙니다. 반복문의 데이터 의존성, 컴파일러 벡터화 또는 데이터 배치를 실제로 다룰 때 사용합니다.

연결 예제:

- [`vectorization-report`](../examples/vectorization-report/)

```sh
make -C examples/vectorization-report check
make -C examples/vectorization-report report
```

## 최종 검증

```sh
cd exercises/processor-model
make check
make demo
```

검사 성공만으로 끝내지 않습니다. 다음 질문에 답할 수 있어야 합니다.

1. 레지스터, 캐시, TLB, ROB와 MESI 모델은 각각 어떤 값을 저장합니까?
2. 각 상태는 어떤 사건에서 교체되거나 무효화됩니까?
3. 잘못된 명령이나 폴트가 아키텍처 상태에 반영되지 않도록 어디에서 막습니까?
4. 모델이 실제 하드웨어에서 생략한 조건은 무엇입니까?
5. 실행 시간만으로 원인을 단정하지 않으려면 어떤 추가 근거가 필요합니까?
