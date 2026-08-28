# 확장 상태 및 binary image 실습

이 문서는 필수 11개 문서와 `kernel-model` 검증을 마친 뒤 선택하는 확장 과정입니다. page-table 주소 계산, 자세한 MLFQ trace, 학습용 filesystem image와 device descriptor ring을 다룹니다.

필수 과정의 완료 기준에는 포함하지 않습니다. 실제 문제에서 해당 주제가 필요해졌거나 binary parser와 ring ownership을 더 깊게 연습하려는 경우에 진행합니다.

## 공통 완료 조건

각 실습은 다음 자료를 함께 작성합니다.

```text
입력 형식 또는 workload 규칙
상태와 자원 소유 표
정상 입력과 결과
한 조건만 깨뜨린 실패 입력 둘 이상
실행 시간 상한
구현과 독립된 결과 계산 또는 checksum
```

구현이 만든 출력을 그대로 정답으로 사용하지 않습니다. 작은 입력은 손으로 계산하거나 별도 oracle로 검증합니다.

## 1. 주소 변환 계산

page 크기가 `2^k` byte라면 virtual address를 VPN과 offset으로 나눌 수 있습니다.

```text
vpn = virtual_address // page_size
offset = virtual_address % page_size
physical_address = frame * page_size + offset
```

page size가 256이고 virtual address가 300이며 VPN 1이 frame 2를 가리키면 다음과 같습니다.

```text
vpn = 1
offset = 44
physical address = 556
```

offset이 변환 전후에 같다는 점은 계산을 검증하는 간단한 조건입니다.

### 입력 검사

- address와 page size는 음수가 아닙니다.
- page size는 2의 거듭제곱입니다.
- VPN은 page table 범위 안에 있어야 합니다.
- `present`가 꺼져 있으면 frame 값이 있어도 바로 변환하지 않습니다.
- read, write와 execute 권한은 주소 계산과 별도로 검사합니다.

다단계 page table을 구현한다면 level 수와 index bit 수를 입력으로 둡니다. 특정 architecture의 고정된 level 수를 일반 규칙으로 사용하지 않습니다.

### 실패 입력

- page size가 0 또는 2의 거듭제곱이 아님
- VPN이 table 범위를 벗어남
- `present=false`
- write 권한이 없는 mapping에 write 요청
- physical address 계산이 정수 범위를 넘음

## 2. MLFQ trace

MLFQ는 이름이 아니라 규칙 묶음입니다.

```text
queue 수
queue별 quantum
새 작업이 시작할 level
quantum 소진 시 demotion
I/O block과 wakeup 시 level 변경
주기적 priority boost
같은 queue 안의 tie-break
```

다음 workload를 비교합니다.

1. 긴 CPU burst 하나
2. 짧은 CPU burst와 I/O를 반복하는 작업
3. 긴 작업이 기다리는 동안 짧은 작업이 계속 도착하는 입력

각 tick마다 다음 값을 기록합니다.

- `running`
- queue level별 ready 목록
- blocked 목록과 wakeup 시각
- 현재 작업의 남은 quantum
- demotion, promotion 또는 boost 이유

boost를 끈 경우와 켠 경우를 비교하여 CPU-bound 작업의 최대 ready wait가 어떻게 달라지는지 설명합니다.

### 독립 검증

작은 tick 수에서는 각 시각의 후보를 정책 규칙으로 직접 다시 계산합니다. 구현과 같은 queue helper를 oracle에서 공유하지 않습니다.

## 3. `KMODFS01` 학습용 image

이 실습은 실제 filesystem의 on-disk format이 아닙니다. 256-byte block 6개로 이름, inode와 data block 연결을 읽는 제한된 format을 정의합니다.

```text
block 0: superblock
block 1: inode table
block 2: root directory entries
block 3: /hello.txt data
block 4: /docs directory entries
block 5: /docs/note.txt data
```

### superblock

- magic
- format version
- block size
- block count
- inode table 시작 block
- root inode
- image checksum

모든 multi-byte integer의 byte order를 명시합니다.

### inode

- inode number
- file 또는 directory 종류
- byte size
- direct block 하나

### directory entry

- inode number
- name length
- 최대 27-byte UTF-8 name

### 범위 검사

field를 읽기 전에 다음 조건을 검사합니다.

```text
offset >= 0
field_size >= 0
offset <= image_size
field_size <= image_size - offset
```

`offset + field_size <= image_size`만 사용하면 고정 폭 정수에서 덧셈 overflow를 놓칠 수 있습니다.

### checksum

checksum field를 0으로 둔 전체 image의 SHA-256을 사용합니다. parser와 builder가 같은 잘못된 범위를 사용하지 않도록 test에서는 digest를 독립적으로 다시 계산합니다.

### 최소 손상 입력

- magic 또는 version 불일치
- block size와 전체 image 길이 불일치
- checksum 불일치
- 중복 inode number
- image 밖 block index
- 존재하지 않는 inode를 가리키는 entry
- name length 초과 또는 잘못된 UTF-8
- root로 다시 이어지는 directory cycle

생성한 binary image와 실행 log는 repository에 넣지 않습니다. disposable 작업 디렉터리에서 생성하고 검사한 뒤 제거합니다.

## 4. Device descriptor ring

ring에는 producer sequence, consumer sequence와 slot generation이 필요합니다.

```text
FREE
→ DRIVER_OWNED
→ DEVICE_OWNED
→ COMPLETED
→ FREE
```

다음 조건을 지켜야 합니다.

- descriptor 하나를 driver와 device가 동시에 소유하지 않습니다.
- producer가 완료되지 않은 descriptor를 덮어쓰지 않습니다.
- ownership을 넘기기 전에 descriptor와 buffer가 device에 보입니다.
- completion을 확인한 뒤 device write가 CPU에 보입니다.
- reset, timeout과 double interrupt에서도 buffer를 한 번만 회수합니다.

ring index는 wrap되므로 단순히 `producer < consumer`로 빈 slot을 판단하지 않습니다. 단조 증가 sequence와 `sequence % capacity`를 나누거나 generation bit를 사용합니다.

### 최소 scenario

capacity 2, sequence 0에서 다음 사건을 실행합니다.

1. request 두 개 제출
2. 세 번째 제출의 backpressure 확인
3. 첫 request를 device에 넘기고 완료
4. owner가 결과를 받기 전에 slot 재사용 시도
5. 결과를 받은 뒤 slot 재사용
6. 이전 generation의 늦은 completion 거부

### 실패 입력

- 같은 slot을 driver와 device가 동시에 소유
- 완료 전 producer가 slot 덮어쓰기
- 이전 generation의 completion을 새 request에 적용
- cancellation과 normal completion이 모두 buffer 해제

## 진행 순서

```text
필수 과정 완료
→ 네 실습 중 필요한 주제 선택
→ 작은 입력을 손으로 계산
→ 입력 parser 또는 state model 구현
→ 정상 입력 확인
→ 한 조건만 깨뜨린 실패 입력 추가
→ 독립 oracle 또는 checksum으로 검증
→ 실행 시간과 생성 파일 정리 확인
```

## 완료 기준

- 네 실습 중 두 개 이상을 완료합니다.
- 각 실습에 정상 입력과 실패 입력을 둘 이상 둡니다.
- 모든 입력을 정한 시간 안에 처리합니다.
- parser 또는 state machine이 잘못된 입력을 구체적인 이유로 거부합니다.
- 구현과 독립된 경로로 결과를 검증합니다.
- 특정 CPU, kernel 또는 storage에만 성립하는 가정은 별도로 적습니다.

## 잘못된 구현

- image 길이를 확인하기 전에 field를 읽습니다.
- builder 출력만 정답으로 사용해 builder와 parser의 공통 오류를 놓칩니다.
- MLFQ의 quantum, boost와 tie-break를 정하지 않습니다.
- descriptor slot 번호만 보고 이전 generation의 completion을 받아들입니다.
- timeout 뒤 child process나 생성 파일이 남습니다.

## 자기 설명

- checksum이 맞아도 inode 범위와 directory graph를 별도로 검사해야 하는 이유는 무엇입니까?
- page-table offset 계산이 permission과 `present` 검사를 대신하지 못하는 이유는 무엇입니까?
- MLFQ가 짧은 I/O-bound 작업을 우대하면서 긴 작업을 굶길 수 있는 조건은 무엇입니까?
- 같은 slot 번호라도 이전 generation의 completion을 거부해야 하는 이유는 무엇입니까?
