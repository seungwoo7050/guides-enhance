# 주소 공간과 page fault

## 학습 목표

- address space, mapping, page, PTE와 physical frame을 구분합니다.
- not-present, protection, COW와 invalid-address fault를 처리 결과에 따라 분류합니다.
- fault 처리 중 frame 할당, I/O, block과 명령 재시도를 추적합니다.

## address space는 mapping의 집합입니다

프로그램의 pointer는 physical memory 위치를 직접 뜻하지 않습니다. 각 process는 자신에게 보이는 virtual address space를 가지며, 운영체제는 어느 범위가 유효한지, 어떤 접근을 허용하는지, 실제 page가 memory에 올라와 있는지 관리합니다.

주소 공간은 다음 영역을 포함할 수 있습니다.

```text
실행 code와 read-only 상수
초기화된 data와 zero-initialized 영역
heap
thread stack
shared library mapping
memory-mapped file
anonymous mapping
guard page와 사용하지 않는 hole
```

각 mapping에는 최소한 다음 정보가 필요합니다.

```text
virtual address 범위
read, write, execute 권한
anonymous 또는 file-backed 여부
private 또는 shared 여부
backing object와 offset
현재 resident 여부
COW, dirty, accessed 상태
```

mapping이 존재한다는 말과 physical frame이 연결돼 있다는 말은 다릅니다. demand paging에서는 유효한 mapping이 있어도 첫 접근 전에는 frame이 없을 수 있습니다.

## 주소 접근을 순서대로 판정합니다

CPU가 virtual address에 접근하면 다음 질문을 차례로 확인합니다.

```text
1. 이 주소가 유효한 mapping 안에 있습니까?
2. 요청한 read, write 또는 execute가 허용됩니까?
3. page가 현재 resident합니까?
4. resident하지 않다면 어디에서 내용을 가져옵니까?
5. COW 또는 lazy allocation 처리가 필요합니까?
6. frame 부족이나 I/O 실패가 발생하면 무엇을 반환합니까?
```

hardware는 page table과 TLB를 사용해 일부 검사를 빠르게 처리합니다. hardware가 현재 접근을 완료할 수 없으면 kernel에 fault를 알립니다.

## fault 종류

### not-present fault

mapping은 유효하지만 page가 resident하지 않습니다.

```text
anonymous demand-zero
→ 새 frame을 확보하고 0으로 채웁니다.

file-backed mapping
→ backing file의 해당 offset을 읽습니다.

swap 또는 compressed backing
→ 보관한 내용을 복원합니다.
```

처리가 끝나면 같은 명령을 다시 실행할 수 있습니다.

### protection fault

mapping은 있지만 요청한 접근을 허용하지 않습니다.

- read-only page에 write
- non-executable page에서 instruction fetch
- user mode에서 kernel-only mapping 접근

일반적으로 복구할 수 없지만, COW write처럼 의도적으로 write 권한을 제거한 경우에는 별도 처리를 거쳐 계속 실행할 수 있습니다.

### invalid address

어떤 mapping에도 속하지 않거나 guard page에 접근한 경우입니다. kernel은 process에 signal 또는 exception을 전달하거나 실행을 종료할 수 있습니다.

### COW fault

여러 address space가 같은 frame을 read-only로 공유하고 있을 때 한쪽이 write하면 발생합니다. 새 frame을 만들고 내용을 복사한 뒤 해당 mapping만 writable로 바꿉니다.

## fault 처리도 block할 수 있습니다

file-backed page를 storage에서 읽어야 한다면 fault handler가 즉시 끝나지 않습니다.

```text
RUNNING thread가 주소 접근
→ page fault로 kernel mode 진입
→ mapping과 권한 확인
→ page-in I/O 제출
→ thread를 BLOCKED로 변경
→ 다른 thread 실행
→ device completion interrupt
→ frame과 PTE 갱신
→ thread를 READY로 변경
→ 다시 선택됐을 때 faulting instruction 재시도
```

따라서 page fault는 memory manager, scheduler, wait queue와 device I/O를 연결합니다.

동시에 여러 thread가 같은 page를 fault하면 누가 I/O를 시작하고 다른 thread는 어디에서 기다릴지 정해야 합니다. 실패 결과도 모든 waiter에게 일관되게 전달해야 합니다.

## 주소 공간 불변식

간단한 모델에서도 다음 관계를 지켜야 합니다.

```text
한 process의 한 VPN에는 현재 mapping이 최대 하나만 있습니다.
resident PTE는 존재하는 frame을 가리킵니다.
frame refcount는 그 frame을 가리키는 PTE 수와 같습니다.
일반 write는 writable mapping에서만 허용합니다.
여러 mapping이 공유하는 frame은 일반 writable 상태가 아닙니다.
unmap 뒤에는 stale PTE와 frame reference가 남지 않습니다.
```

`kernel-model`은 실제 다단계 page table 대신 process별 VPN mapping과 frame object를 사용합니다. 이 단순화로 권한, presence, COW와 refcount를 직접 확인할 수 있습니다.

## demand-zero mapping

anonymous memory를 요청할 때 모든 page를 즉시 할당할 필요는 없습니다.

```text
mapping 생성
→ PTE not-present
→ 첫 접근
→ not-present fault
→ zero-filled frame 연결
```

실제로 사용하지 않는 page의 physical memory 비용을 미룰 수 있습니다. 하지만 allocation API가 성공했더라도 첫 접근에서 frame을 확보하지 못할 수 있습니다. overcommit과 memory pressure를 고려해야 합니다.

## stack growth와 guard page

일부 운영체제는 stack 근처의 fault를 보고 mapping을 제한적으로 늘릴 수 있습니다. 임의의 먼 주소까지 stack으로 인정하면 잘못된 pointer를 숨길 수 있습니다.

보통 다음 조건을 확인합니다.

- 현재 stack pointer와 fault address의 거리
- 최대 stack 크기
- guard page 유지
- 다른 mapping과의 충돌
- thread별 stack 구분

정확한 규칙은 운영체제와 ABI에 따라 다릅니다.

## file-backed mapping

file mapping에서는 다음 세 상태를 구분합니다.

1. process의 virtual mapping
2. page cache에 있는 현재 내용
3. storage에 남아 있는 내용

`MAP_SHARED` 계열 write는 page cache를 dirty하게 만들 수 있지만 곧바로 durability를 보장하지 않습니다. `MAP_PRIVATE` 계열 write는 private COW page를 만들 수 있습니다.

mapping 해제, writeback 요청과 file metadata의 durability는 서로 다른 동작입니다. 자세한 내용은 [파일시스템, page cache와 장애 일관성](../04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md)에서 다룹니다.

## TLB를 운영체제 관점에서 이해하기

TLB는 최근 주소 변환과 권한을 보관합니다. page table이나 permission을 바꾼 뒤 stale translation이 남으면 이전 frame 또는 잘못된 권한으로 접근할 수 있습니다.

```text
mapping 변경은 PTE memory만 바꾸는 것으로 끝나지 않을 수 있습니다.
stale translation을 없앤 뒤 frame을 재사용해야 합니다.
여러 CPU에서 같은 address space를 실행했다면 다른 CPU에도 알려야 할 수 있습니다.
```

TLB set, page-walk cache, ASID와 정확한 instruction은 컴퓨터 구조의 세부 주제로 남깁니다.

## 관찰 예제

### COW

```sh
make -C examples build/cow-observer
./examples/build/cow-observer
```

부모와 자식이 같은 virtual address를 출력하더라도 같은 physical frame을 사용한다는 사실을 직접 증명하지는 않습니다. 자식이 값을 바꾼 뒤 부모 값이 유지되는 사용자 공간 결과만 확인합니다.

### page fault 통계

```sh
make -C examples build/page-fault-observer
./examples/build/page-fault-observer 128
```

각 page의 첫 byte를 쓰고 minor fault 증가량을 출력합니다. 정확한 수치는 allocator, huge page 설정과 실행 환경에 따라 달라집니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.PagingTests -v
python3 kernel-model.py memory examples/memory-cow.json
```

## 완료 기준

- address space, mapping, PTE와 frame을 구분할 수 있습니다.
- not-present, protection, invalid-address와 COW fault를 분류할 수 있습니다.
- page-in이 필요한 fault가 thread를 block시키는 과정을 설명할 수 있습니다.
- PTE와 frame refcount가 일치해야 하는 이유를 설명할 수 있습니다.
- 관찰 예제가 증명할 수 있는 내용과 없는 내용을 구분할 수 있습니다.

## 잘못된 이해

- virtual address를 physical address와 같은 값으로 봅니다.
- mapping이 있으면 항상 frame도 resident하다고 생각합니다.
- page fault를 모두 프로그램 오류라고 판단합니다.
- 같은 virtual address 출력만으로 같은 physical frame을 사용한다고 단정합니다.

## 자기 설명

- valid mapping이 있는데도 not-present fault가 날 수 있는 이유는 무엇입니까?
- read-only page의 write가 항상 process 종료로 이어지지 않는 예는 무엇입니까?
- unmap 뒤 stale TLB를 처리하지 않고 frame을 재사용하면 어떤 문제가 생길 수 있습니까?
