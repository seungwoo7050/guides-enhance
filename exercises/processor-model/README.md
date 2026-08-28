# Processor Model

`processor-model`은 프로세서에서 일어나는 주요 상태 변화를 작은 입력으로 재현하는 Python 프로젝트입니다. 외부 실행 패키지 없이 고정 폭 정수와 IEEE 754 표현, Tiny-RISC 실행, 5단계 파이프라인, 집합 연관 캐시, TLB, 분기 예측기, 재정렬 버퍼와 MESI 일관성을 실행하고 검사할 수 있습니다.

이 프로젝트는 특정 상용 CPU의 정확한 사이클 수를 예측하지 않습니다. 각 모듈이 어떤 값을 저장하고, 어느 조건에서 정지·비우기·교체·무효화·예외가 발생하는지 반복 가능한 결과로 확인하는 데 목적이 있습니다.

## 주요 기능

- 고정 폭 정수의 부호 있는 해석과 부호 없는 해석
- 자리올림, 부호 없는 오버플로와 부호 있는 오버플로의 구분
- `f32`·`f64`의 IEEE 754 필드와 반올림 결과 확인
- Tiny-RISC 어셈블리 파서와 32비트 순차 실행기
- CPU 실행 시간, Amdahl의 법칙과 AMAT 계산
- Tiny-RISC 연산 코드별 단일 사이클 제어 신호 조회
- 전달, 적재 직후 사용 정지와 실행된 분기 비우기를 포함한 5단계 파이프라인 추적
- LRU, 지연 쓰기와 쓰기 할당을 지원하는 집합 연관 캐시
- 최초 접근·충돌·용량 실패 분류
- 페이지 테이블과 LRU TLB를 이용한 주소 변환, 권한 검사와 무효화
- 2비트 포화 계수기 분기 예측기
- 비순차 완료와 순차 반영을 분리한 재정렬 버퍼
- 안정 MESI 상태와 거짓 공유를 재현하는 일관성 모델
- 단위 검사와 실제 명령행 프로세스를 실행하는 통합 검사

## 디렉터리 구성

```text
processor-model/
├── processor-model.py       # 설치 없이 실행하는 명령행 진입점
├── processor_model/         # 계산과 상태 변화 구현
├── fixtures/                # 예제 프로그램과 추적 입력
├── spec/                    # Tiny-RISC ISA 명세
├── tests/                   # 단위 검사와 명령행 통합 검사
├── Makefile
└── pyproject.toml
```

`fixtures/`는 숨겨진 정답 데이터가 아닙니다. README의 명령을 그대로 실행할 수 있는 입력이며, 각 파일은 한 가지 상태 변화를 짧게 재현합니다.

## 요구 사항

- Python 3.12 이상
- 실행 시 외부 패키지 없음
- 설치 시 `pip`와 PEP 517 빌드 백엔드 필요

## 설치와 실행

가상 환경에 설치하면 `processor-model` 명령을 사용할 수 있습니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
processor-model --help
```

설치하지 않고 프로젝트 루트에서 직접 실행할 수도 있습니다.

```sh
python3 processor-model.py --help
```

## 사용법

### 고정 폭 정수와 IEEE 754

```sh
processor-model bits int -1 --width 8
processor-model bits add 127 1 --width 8
processor-model bits float 0.1 --format f32
```

`bits add`는 `carry_out`, `unsigned_overflow`, `signed_overflow`를 따로 반환합니다. 같은 비트 패턴을 사용하더라도 부호 없는 덧셈과 2의 보수 덧셈은 범위를 벗어났는지 판정하는 조건이 다릅니다.

### 성능식

```sh
processor-model perf cpu --instructions 1000000000 --cpi 2 --ghz 2
processor-model perf amdahl --fraction 0.4 --speedup 8
processor-model perf amat --hit-time 1 --miss-rate 0.05 --miss-penalty 80
```

`cpu`의 주파수는 GHz로 입력합니다. `amat`에 전달하는 시간 값은 모두 같은 단위를 사용해야 합니다.

### Tiny-RISC 실행

```sh
processor-model isa fixtures/programs/sum.asm --max-steps 100
processor-model isa fixtures/programs/overflow.asm
```

레지스터, 메모리, 레이블, 정렬과 32비트 순환 규칙은 [`spec/tiny-risc-isa.md`](spec/tiny-risc-isa.md)에 정리되어 있습니다.

### 제어 신호

```sh
processor-model control lw
processor-model control beq
```

출력은 게이트 단위 배선을 뜻하지 않습니다. Tiny-RISC 명령이 레지스터와 메모리를 읽고 쓰는 데 필요한 제어 선택을 표로 나타냅니다.

### 파이프라인 추적

```sh
processor-model pipeline fixtures/traces/pipeline-load-use.trace --forwarding full
processor-model pipeline fixtures/traces/pipeline-branch.trace --json
```

- `--forwarding full`은 일반 ALU 의존성을 전달로 해결하고, 적재 결과를 바로 읽는 명령만 정지시킵니다.
- `--forwarding none`은 ID 단계의 소스가 EX 또는 MEM 단계의 목적지와 겹치면 정지시킵니다.
- `@taken`이 붙은 분기는 EX 단계에서 실행된 것으로 확정하며, IF와 ID에 들어온 더 젊은 명령을 버립니다.
- 출력의 `IF*`, `ID*`는 잘못 가져온 명령을 폐기한 단계를 뜻합니다.

### 캐시 추적

```sh
processor-model cache fixtures/traces/cache.trace \
  --size 16 --block 4 --ways 1
```

세트별 LRU 상태와 3C 실패 분류에 사용하는 완전 연관 보조 캐시를 따로 유지합니다. `--no-write-allocate`를 지정하지 않으면 쓰기 실패에서도 해당 블록을 캐시에 넣습니다.

### 가상 주소 변환

```sh
processor-model vm fixtures/vm/config.json fixtures/vm/trace.txt
```

`MAP`과 `UNMAP`으로 페이지 테이블을 바꾸면 관련 TLB 항목을 즉시 제거합니다. 각 결과에는 TLB 적중 여부, 페이지 테이블 순회 여부, PFN, 물리 주소, 페이지 폴트와 보호 예외가 기록됩니다.

### MESI 일관성 추적

```sh
processor-model coherence \
  fixtures/traces/coherence-false-sharing.trace \
  --cores 2 --line-size 64
```

각 접근은 실행 전후의 코어별 MESI 상태, 버스 사건, 무효화와 메모리 반영 횟수를 남깁니다. 예제는 주소 `0`과 `8`이 서로 다른 값을 가리키지만 같은 64바이트 캐시 라인을 사용해 소유권이 이동하는 상황을 재현합니다.

### 분기 예측기와 재정렬 버퍼 API

`predictor`와 `rob`는 Python API로 제공합니다.

```python
from processor_model.predictor import TwoBitPredictor
from processor_model.rob import ReorderBuffer

predictor = TwoBitPredictor(entries=4)
predicted_taken = predictor.update(0x100, True)

registers: dict[str, int] = {}
rob = ReorderBuffer(capacity=4)
tag = rob.issue("r1")
rob.complete(tag, value=42)
rob.retire(registers)
```

## 검증

문법 검사, 명령행 도움말, 단위 검사와 명령행 통합 검사를 한 번에 실행합니다.

```sh
make check
```

검사만 직접 실행하려면 다음 명령을 사용합니다.

```sh
python3 -m unittest discover -s tests -v
```

대표 입력을 연속해서 실행하려면 다음 명령을 사용합니다.

```sh
make demo
```

## 파일별 역할

| 파일 | 수행하는 일 |
| --- | --- |
| `processor_model/bits.py` | 고정 폭 정수와 IEEE 754 비트 표현 계산 |
| `processor_model/isa.py` | Tiny-RISC 구문 분석과 레지스터·메모리·PC 갱신 |
| `processor_model/perf.py` | CPU 시간, Amdahl의 법칙과 AMAT 계산 |
| `processor_model/control.py` | 연산 코드별 제어 신호 반환 |
| `processor_model/pipeline.py` | 5단계 이동, 전달, 정지와 비우기 추적 |
| `processor_model/cache.py` | 세트별 LRU, 지연 쓰기, 쓰기 할당과 3C 실패 계산 |
| `processor_model/vm.py` | 페이지 테이블, LRU TLB, 권한 검사와 무효화 |
| `processor_model/predictor.py` | 2비트 분기 방향 예측 |
| `processor_model/rob.py` | 발행·완료·순차 반영과 정밀한 예외 처리 |
| `processor_model/coherence.py` | 안정 MESI 상태와 스누핑 버스 사건 추적 |
| `processor_model/cli.py` | 명령행 인자 분석, 파일 입력, 출력과 종료 상태 처리 |

## 주요 설계 판단

### 상태 종류마다 별도 객체를 사용합니다

캐시 라인, TLB 항목, 예측기 계수기, 재정렬 버퍼 항목과 MESI 상태는 생성·교체·무효화 조건이 다릅니다. 각 모듈이 필요한 값과 통계를 직접 저장하므로, 한 종류의 갱신 규칙이 다른 종류의 상태에 섞이지 않습니다.

### 최종 통계와 발생 원인을 함께 기록합니다

`cache`, `vm`, `coherence`, `pipeline`은 합계만 반환하지 않습니다. 주소 분해 결과, 예외, 교체한 블록, 버스 사건, 전후 상태와 사이클별 위치를 함께 기록합니다. 따라서 합계가 같아도 원인이 다른 실행을 구분할 수 있습니다.

### `complete`와 `retire` 시점을 나눕니다

`ReorderBuffer`는 뒤 명령이 먼저 계산되더라도 맨 앞 항목이 준비되지 않으면 레지스터에 반영하지 않습니다. 예외가 맨 앞에서 확인되면 해당 항목과 그보다 뒤에 발행한 미반영 항목을 제거합니다. 이 규칙으로 소프트웨어에 보이는 레지스터 상태가 프로그램 순서를 따르게 합니다.

### Tiny-RISC의 생략 범위를 명시합니다

Tiny-RISC는 RISC-V, MIPS, Arm 또는 x86 바이너리와 호환되지 않습니다. 실제 명령 인코딩, ABI, 예외 벡터, 물리 레지스터 이름 바꾸기와 장치 메모리는 포함하지 않습니다.

## 구현 순서

아래 번호는 파일 순서나 실행 순서가 아닙니다. 완성된 프로젝트를 처음부터 만들 때 먼저 확정해야 하는 데이터와 상태 변화의 의존 순서입니다. 표의 항목은 소스의 `[Implementation N]` 주석과 일치합니다.

| 순서 | 구현 단계 | 주요 위치 |
| ---: | --- | --- |
| 1 | 고정 폭 비트 해석 | `processor_model/bits.py::_validate_width` |
| 1-1 | 고정 폭 덧셈의 상태값 | `processor_model/bits.py::add_fixed` |
| 1-2 | IEEE 754 필드 분해 | `processor_model/bits.py::_float_fields` |
| 2 | Tiny-RISC 명령 표현 | `processor_model/isa.py::Instruction` |
| 2-1 | 데이터 의존 정보 | `processor_model/isa.py::sources_and_destination` |
| 2-2 | 레지스터·메모리·PC 갱신 | `processor_model/isa.py::Machine` |
| 3 | 성능식 계산 | `processor_model/perf.py::cpu_time` |
| 4 | 명령별 제어 신호표 | `processor_model/control.py::CONTROL` |
| 5 | 데이터 위험 판정 | `processor_model/pipeline.py::_has_data_hazard` |
| 5-1 | 5단계 상태 전이 | `processor_model/pipeline.py::simulate` |
| 6 | 캐시 상태 보관 | `processor_model/cache.py::CacheSimulator` |
| 6-1 | 캐시 적중·실패 전이 | `processor_model/cache.py::CacheSimulator.access` |
| 7 | 주소 변환 상태 | `processor_model/vm.py::VirtualMemorySimulator` |
| 7-1 | TLB 조회와 권한 검사 | `processor_model/vm.py::VirtualMemorySimulator._translate` |
| 7-2 | TLB 항목 무효화 | `processor_model/vm.py::VirtualMemorySimulator.run` |
| 8 | 2비트 분기 예측 | `processor_model/predictor.py::TwoBitPredictor` |
| 9 | 재정렬 버퍼 상태 | `processor_model/rob.py::ReorderBuffer` |
| 9-1 | 순차 반영과 정밀한 예외 | `processor_model/rob.py::ReorderBuffer.retire` |
| 10 | 안정 MESI 상태 | `processor_model/coherence.py::MESISimulator` |
| 10-1 | MESI 읽기·쓰기 전이 | `processor_model/coherence.py::MESISimulator.access` |
| 11 | CLI 명령 정의 | `processor_model/cli.py::build_parser` |
| 11-1 | CLI 입력과 결과 연결 | `processor_model/cli.py::run` |
| 11-2 | 오류 종료 상태 | `processor_model/cli.py::main` |
| 12 | 전체 회귀 검사 | `tests/test_processor_model.py::BitsTests` |
| 12-1 | CLI 통합 검사 | `tests/test_cli.py::CliIntegrationTests` |

## 범위와 제한

- 파이프라인은 5단계 순차 실행의 타이밍만 계산하며 레지스터 값은 실행하지 않습니다.
- 분기 결과는 추적 입력의 `@taken`으로 지정합니다.
- 캐시는 실제 데이터를 저장하지 않고 태그, 수정 비트, 교체 상태와 통계만 추적합니다.
- 가상 메모리 모델은 단일 주소 공간과 평면 페이지 테이블을 사용합니다.
- MESI 모델은 안정 상태만 다루며 과도 상태, 상호연결망 중재와 메모리 지연 시간은 생략합니다.
- 분기 예측기는 전역 이력, BTB, 반환 주소 스택과 추측 갱신을 제공하지 않습니다.
- 재정렬 버퍼는 물리 레지스터 파일, 예약 스테이션과 적재·저장 큐를 포함하지 않습니다.
- 출력한 사이클과 지연 시간을 실제 CPU 벤치마크 결과로 해석하면 안 됩니다.
