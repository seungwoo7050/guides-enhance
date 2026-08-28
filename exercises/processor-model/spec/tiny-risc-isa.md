# Tiny-RISC ISA 명세

`Tiny-RISC`는 `processor-model`에서 사용하는 작은 텍스트 기반 ISA입니다. 데이터패스, 레지스터 의존성, 메모리 접근과 제어 이동을 같은 명령 의미로 설명하기 위해 정의했습니다.

실제 RISC-V, MIPS, Arm 또는 다른 상용 ISA의 바이너리 인코딩, ABI, 예외 처리 방식과 호환되지 않습니다. 입력은 어셈블리 텍스트이며 바이너리 명령 생성은 제공하지 않습니다.

## 소프트웨어에 보이는 상태

```text
PC                 다음에 실행할 명령의 인덱스
r0..r7             32비트 정수 레지스터 8개
memory             리틀 엔디언 바이트 주소 메모리
halted             halt 실행 여부
```

모든 산술 결과는 하위 32비트만 남긴 뒤 2의 보수 정수로 표시합니다. 비트 연산도 같은 32비트 패턴에 적용합니다.

### `r0`

`r0`은 항상 0인 레지스터입니다.

- 소스로 읽으면 `0`을 반환합니다.
- 목적지로 지정한 쓰기는 버립니다.
- 각 명령을 실행한 뒤에도 `r0 == 0`을 보장합니다.

### PC 단위

PC는 바이트 주소가 아니라 명령 인덱스입니다.

```text
PC=0 → 첫 번째 명령
PC=1 → 두 번째 명령
```

레이블도 명령 인덱스로 해석합니다. 실제 ISA의 명령 정렬과 PC 상대 바이트 오프셋은 다루지 않습니다.

## 입력 형식

한 줄에 명령 하나를 작성하며 `#` 뒤는 주석입니다.

```asm
start:
    li   r1, 4
    li   r2, 0
loop:
    add  r2, r2, r1
    addi r1, r1, -1
    bne  r1, r0, loop
    halt
```

레이블은 `[A-Za-z_][A-Za-z0-9_]*` 형식을 사용합니다. 같은 레이블을 두 번 정의하거나 존재하지 않는 레이블을 참조하면 구문 분석 단계에서 거부합니다.

정수 리터럴은 Python의 `int(text, 0)` 규칙을 따릅니다.

```text
42       십진수
-7       음의 십진수
0xff     16진수
0b1010   2진수
0o17     8진수
```

## 명령 요약

| 명령 | 형식 | 읽는 값 | 변경하는 상태 |
| --- | --- | --- | --- |
| `li` | `li rd, imm` | 즉시값 | `rd` |
| `add` | `add rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `addi` | `addi rd, rs1, imm` | `rs1`, 즉시값 | `rd` |
| `sub` | `sub rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `and` | `and rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `or` | `or rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `xor` | `xor rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `lw` | `lw rd, offset(base)` | `base`, 메모리 워드 | `rd` |
| `sw` | `sw rs, offset(base)` | `rs`, `base` | 메모리 워드 |
| `beq` | `beq rs1, rs2, label` | `rs1`, `rs2` | PC |
| `bne` | `bne rs1, rs2, label` | `rs1`, `rs2` | PC |
| `j` | `j label` | 레이블 | PC |
| `halt` | `halt` | 없음 | `halted`, PC |

## 산술과 논리 명령

### `li rd, imm`

```text
R[rd] ← wrap32(imm)
PC ← PC + 1
```

`li`는 큰 상수를 여러 실제 명령으로 만드는 과정을 생략하기 위한 의사 명령입니다.

### `add rd, rs1, rs2`

```text
R[rd] ← wrap32(R[rs1] + R[rs2])
PC ← PC + 1
```

부호 있는 오버플로 예외는 발생하지 않으며 하위 32비트만 남깁니다.

### `addi rd, rs1, imm`

```text
R[rd] ← wrap32(R[rs1] + imm)
PC ← PC + 1
```

즉시값 필드의 폭은 제한하지 않습니다.

### `sub rd, rs1, rs2`

```text
R[rd] ← wrap32(R[rs1] - R[rs2])
PC ← PC + 1
```

### `and`, `or`, `xor`

```text
R[rd] ← wrap32(R[rs1] OP R[rs2])
PC ← PC + 1
```

## 메모리 접근

메모리는 바이트 주소를 사용하고 워드는 4바이트입니다. 워드는 리틀 엔디언으로 저장합니다.

유효한 워드 접근은 다음 조건을 모두 만족해야 합니다.

```text
address % 4 == 0
0 <= address
address + 4 <= memory_size
```

조건을 위반하면 실행기는 `RuntimeError`를 발생시키고 실행을 중단합니다. 실패한 명령은 레지스터나 메모리에 정상 결과를 남기지 않습니다.

### 유효 주소 계산

```text
effective_address = R[base] + offset
```

주소 계산에는 32비트 순환을 적용하지 않습니다. 음수 주소와 메모리 범위를 벗어난 접근을 거부합니다.

### `lw rd, offset(base)`

```text
address ← R[base] + offset
R[rd] ← signed32(memory[address .. address+3], little-endian)
PC ← PC + 1
```

### `sw rs, offset(base)`

```text
address ← R[base] + offset
memory[address .. address+3] ← low32(R[rs]), little-endian
PC ← PC + 1
```

`sw`의 첫 레지스터는 저장할 값이며 목적지 레지스터는 없습니다.

## 제어 이동

### `beq rs1, rs2, label`

```text
if R[rs1] == R[rs2]:
    PC ← labels[label]
else:
    PC ← PC + 1
```

### `bne rs1, rs2, label`

```text
if R[rs1] != R[rs2]:
    PC ← labels[label]
else:
    PC ← PC + 1
```

### `j label`

```text
PC ← labels[label]
```

링크 레지스터, 반환 주소와 호출 규약은 제공하지 않습니다.

### `halt`

```text
halted ← true
PC ← PC + 1
```

정상 종료는 `halt` 실행으로 정의합니다. 결과의 PC는 `halt` 다음 명령 인덱스를 가리킵니다.

## 실행 실패 조건

다음 조건에서는 정상 결과 대신 오류가 발생합니다.

- PC가 프로그램 범위를 벗어납니다.
- 실행 횟수가 `max_steps`를 넘습니다.
- 정렬되지 않은 워드 주소를 사용합니다.
- 메모리 범위를 벗어난 주소를 사용합니다.
- 연산 코드, 레지스터, 피연산자 또는 레이블이 잘못되었습니다.

기본 `max_steps`는 100,000입니다.

## 단일 사이클 제어 신호

`processor-model control <opcode>`는 다음 필드를 반환합니다.

| 필드 | 의미 |
| --- | --- |
| `reg_write` | 레지스터 파일에 결과를 쓸지 여부 |
| `alu_src` | 두 번째 ALU 피연산자의 출처 |
| `alu_op` | ALU가 수행할 연산 |
| `mem_read` | 데이터 메모리를 읽을지 여부 |
| `mem_write` | 데이터 메모리에 쓸지 여부 |
| `writeback` | 레지스터에 쓸 값의 출처 |
| `branch` | 분기 조건 |
| `jump` | 무조건 점프 여부 |

예를 들어 `lw`는 다음 경로를 사용합니다.

```text
기준 레지스터 읽기
→ 즉시값 오프셋 선택
→ ALU에서 유효 주소 계산
→ 데이터 메모리 읽기
→ 읽은 값을 목적지 레지스터에 기록
```

이 표는 정확한 배선 폭, 멀티플렉서 인코딩 또는 임계 경로의 지연 시간을 정의하지 않습니다.

## 파이프라인 추적용 확장

`pipeline` 하위 명령은 레지스터 값을 계산하지 않습니다. 정적 명령의 의존 관계와 입력에 표시한 분기 결과를 사용해 단계별 타이밍만 계산합니다.

```text
IF → ID → EX → MEM → WB
```

실행된 분기 또는 점프에는 `@taken`을 붙입니다.

```text
li r1, 1
beq r1, r1, target @taken
addi r4, r0, 99
addi r5, r0, 88
target:
addi r4, r0, 7
```

적용하는 규칙은 다음과 같습니다.

- 분기는 EX 단계에서 확정됩니다.
- 기본값은 분기하지 않음으로 예측합니다.
- 실행된 분기는 IF와 ID에 있는 더 젊은 명령을 버립니다.
- `branch_penalty`만큼 추가 명령 인출을 멈춥니다.
- `@taken`은 `beq`, `bne`, `j`에만 사용할 수 있습니다.
- `IF*`, `ID*`는 잘못 가져온 명령을 버린 단계를 뜻합니다.

`--forwarding full`에서는 일반 ALU 결과를 전달 경로로 제공하고, 적재 결과를 바로 읽는 명령에만 한 사이클을 추가합니다. `--forwarding none`에서는 ID 단계의 소스가 EX 또는 MEM 단계의 목적지와 겹치면 정지시킵니다.

## 실행 예

```sh
processor-model isa fixtures/programs/sum.asm --max-steps 100
```

이 프로그램은 `5 + 4 + 3 + 2 + 1`을 계산해 메모리 주소 `0`에 저장하고 다시 `r3`으로 읽습니다. 정상 결과는 `r2 == 15`, `r3 == 15`, `memory[0] == 15`입니다.
