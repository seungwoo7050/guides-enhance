# 컴퓨터 구조 가이드

이 저장소는 값의 비트 표현부터 명령 실행, 메모리 접근, 비순차 실행과 멀티코어 일관성까지 단계적으로 설명합니다.

특정 CPU 제품의 기능을 외우는 것이 목적은 아닙니다. 문서와 `processor-model`을 완료한 뒤 다음 질문에 답할 수 있는 상태를 목표로 합니다.

- 고정 폭 정수와 IEEE 754 값은 어떤 비트 패턴으로 표현됩니까?
- ISA가 정하는 동작과 프로세서 내부 구현은 어떻게 다릅니까?
- 명령 수, CPI와 클록 주기를 이용해 실행 시간을 어떻게 설명합니까?
- 데이터 경로와 5단계 파이프라인은 명령을 어떻게 처리합니까?
- 값 전달, 정지와 잘못 가져온 명령 제거는 언제 필요합니까?
- 캐시와 TLB는 무엇을 저장하며 언제 실패하거나 무효화됩니까?
- 비순차 실행에서 실행 완료와 프로그램 순서 반영을 왜 구분합니까?
- 여러 코어가 같은 캐시 라인을 사용할 때 MESI 상태와 거짓 공유는 어떻게 발생합니까?

## 저장소 구성

```text
.
├── README.md
├── docs/
├── examples/
└── exercises/
```

- `docs/`는 개념, 계산 방법과 상태 변화를 설명합니다.
- `examples/`는 컴파일러와 실제 실행 환경에서 나타나는 성능 차이를 작은 C 프로그램으로 관찰합니다.
- `exercises/processor-model/`은 문서의 핵심 내용을 하나의 독립 실행형 Python 프로젝트로 검증합니다.

## 필수 문서

### 1. 표현, ISA와 성능식

- [`01-data-representation-and-arithmetic.md`](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md)
- [`02-isa-assembly-and-program-execution.md`](docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md)
- [`03-performance-cpi-and-amdahl.md`](docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md)

### 2. 순차 실행

- [`04-datapath-and-control.md`](docs/02-in-order-execution/04-datapath-and-control.md)
- [`05-pipeline-hazards-and-branching.md`](docs/02-in-order-execution/05-pipeline-hazards-and-branching.md)

### 3. 메모리 계층

- [`06-cache-locality-and-amat.md`](docs/03-memory-hierarchy/06-cache-locality-and-amat.md)
- [`07-address-translation-and-tlb.md`](docs/03-memory-hierarchy/07-address-translation-and-tlb.md)

### 4. 현대 CPU 실행과 멀티코어

- [`08-superscalar-out-of-order-and-speculation.md`](docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md)
- [`10-multicore-coherence-and-false-sharing.md`](docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md)

[`09-simd-vectorization-and-data-layout.md`](docs/04-parallel-execution/09-simd-vectorization-and-data-layout.md)는 선택 문서입니다. 기본 실행 모델과 메모리 계층을 익힌 뒤 실제 벡터화 문제가 생겼을 때 학습합니다.

## 필수 실습 프로젝트

[`exercises/processor-model/`](exercises/processor-model/)은 다음 내용을 하나의 프로젝트에서 확인합니다.

```text
고정 폭 비트 표현
→ Tiny-RISC 실행
→ 성능식
→ 제어 신호
→ 5단계 파이프라인
→ 캐시
→ 주소 변환과 TLB
→ 분기 예측기와 재정렬 버퍼
→ MESI 일관성
→ 전체 회귀 검사
```

각 모듈을 처음부터 다시 작성하는 것만이 학습 방법은 아닙니다. 소스와 검사 코드를 읽고, 입력을 바꿔 실행하며, 상태가 바뀌는 이유와 실패 조건을 설명할 수 있어야 합니다.

```sh
cd exercises/processor-model
make check
make demo
```

## 권장 진행 방식

모든 문서를 먼저 읽은 뒤 실습 프로젝트를 한 번에 보는 방식은 권장하지 않습니다. 개념을 이해할 만큼 읽고 바로 해당 모듈과 검사를 확인합니다.

```text
데이터 표현 문서
→ bits 명령과 검사
→ ISA 문서
→ Tiny-RISC 실행과 검사
→ 성능식·데이터 경로·파이프라인 문서
→ perf·control·pipeline 검사
→ 캐시·TLB 문서
→ cache·vm 추적 입력과 검사
→ 비순차 실행·MESI 문서
→ predictor·ROB·coherence 검사
→ 전체 회귀 검사
```

세부 순서는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 정리되어 있습니다.

## 예제의 역할

| 예제 | 확인하는 내용 |
| --- | --- |
| [`branch-benchmark`](examples/branch-benchmark/) | 입력 패턴과 실제 분기 명령의 관계 |
| [`layout-benchmark`](examples/layout-benchmark/) | 순회 순서와 공간 지역성 |
| [`false-sharing`](examples/false-sharing/) | 서로 다른 값이 같은 캐시 라인에 있을 때의 경합 |
| [`vectorization-report`](examples/vectorization-report/) | 컴파일러 벡터화 보고서와 결과 검증 |

예제의 실행 시간은 고정 정답이 아닙니다. 컴파일러가 생성한 어셈블리, 검사 합계, 입력 크기와 여러 번 측정한 결과를 함께 확인해야 합니다.

## 완료 기준

다음 조건을 모두 만족하면 필수 과정을 완료한 것으로 봅니다.

1. `exercises/processor-model/`에서 `make check`가 성공합니다.
2. 주어진 명령과 추적 입력의 주요 상태 변화를 손으로 설명할 수 있습니다.
3. 캐시 실패, TLB 실패, 페이지 폴트와 캐시 일관성 무효화를 서로 구분합니다.
4. 실행 완료와 프로그램 순서 반영, 캐시 일관성과 메모리 일관성을 같은 개념으로 설명하지 않습니다.
5. 모델이 생략한 조건을 밝히고 실제 CPU 측정값과 모델 결과를 구분합니다.

## 범위

이 저장소는 다음 내용을 기본 완료 조건으로 두지 않습니다.

- 특정 제조사 CPU의 공개되지 않은 일시 상태
- 프로세서 RTL 설계와 검증
- 운영체제의 페이지 할당·교체 방식
- 언어별 원자적 연산 API와 잠금 없는 알고리즘의 정확성 증명
- GPU나 전용 가속기 설계
- SIMD 내장 함수 최적화 전반

필수 개념을 마친 뒤 실제 문제에 필요한 주제를 추가로 학습합니다.
