# 커널 경계와 사건

## 학습 목표

- system call, exception, fault와 interrupt를 발생 원인과 재개 위치로 구분합니다.
- kernel mode 진입, block, 선점과 context switch를 서로 다른 사건으로 설명합니다.
- 실패한 요청에서 반환값, 부분 진행량, 남은 자원과 재시도 가능 여부를 확인합니다.

## 핵심 모델

애플리케이션은 CPU 배분, 임의의 physical memory와 장치 상태를 직접 바꾸지 못합니다. 운영체제는 사용자 코드가 허용된 진입점을 통해 요청했을 때만 시스템 전체 상태를 변경합니다.

모드 전환을 일반 함수 호출로 보면 중요한 차이를 놓칩니다. CPU는 정해진 진입점으로 이동하고, 사용자 코드로 돌아갈 위치와 이전 권한을 보존하며, kernel이 사용하는 stack에서 handler를 실행합니다. kernel은 사용자 공간에서 받은 pointer, length, identifier와 권한을 다시 검증합니다.

이 구분은 보안에만 필요하지 않습니다. 여러 process가 같은 CPU, memory와 device를 사용하므로, 한 요청이 중간에 실패하더라도 다른 실행 주체의 상태를 손상시키지 않아야 합니다.

## 사용자 모드와 커널 모드

```text
사용자 모드
- 애플리케이션의 일반 명령 실행
- 허용된 virtual mapping 접근
- system call을 통한 자원 요청

커널 모드
- process와 thread 상태 변경
- scheduling과 timer 처리
- address space와 권한 관리
- filesystem 및 device request 처리
```

kernel mode로 들어갔다고 항상 다른 thread가 실행되는 것은 아닙니다. system call을 처리한 뒤 같은 thread로 돌아오면 mode만 바뀌고 context switch는 일어나지 않습니다.

## 사건을 구분하는 기준

| 사건 | 발생 원인 | 현재 명령과의 관계 | 처리 뒤 가능한 결과 |
| --- | --- | --- | --- |
| system call | 사용자 프로그램의 명시적 요청 | 동기적 | 같은 thread로 반환, block 뒤 반환, 오류 반환 |
| exception | 현재 명령을 실행하면서 CPU가 감지 | 동기적 | handler가 복구하거나 실행 종료 |
| fault | 명령을 끝내려면 kernel 처리가 필요 | 동기적 | 상태를 준비한 뒤 같은 명령 재시도 가능 |
| interrupt | timer 또는 device의 외부 사건 | 비동기적 | 중단한 실행으로 복귀하거나 다른 작업 선택 |

교재마다 `trap`이라는 말을 다르게 사용합니다. 이름보다 다음 질문으로 분류하는 편이 정확합니다.

1. 원인이 현재 명령입니까, 외부 장치입니까?
2. 처리 뒤 같은 명령을 다시 실행합니까?
3. 현재 thread가 계속 실행할 수 있습니까?
4. 기다려야 할 사건이 있다면 어디에 등록됩니까?

page fault는 항상 잘못된 접근을 뜻하지 않습니다. demand-zero page의 첫 접근이나 COW write는 정상적으로 복구할 수 있습니다. 반대로 mapping이 없거나 권한을 위반했다면 process를 계속 실행할 수 없을 수 있습니다.

## system call의 일반적인 처리 순서

```text
1. 사용자 코드가 요청 번호와 인자를 준비합니다.
2. 전용 진입 명령으로 kernel mode에 들어갑니다.
3. 복귀에 필요한 사용자 문맥을 저장합니다.
4. 요청 번호, pointer, length와 권한을 검증합니다.
5. 대상 kernel object를 찾고 필요한 참조나 lock을 확보합니다.
6. 즉시 처리하거나 현재 thread를 BLOCKED로 옮깁니다.
7. 결과, 부분 진행량 또는 오류를 기록합니다.
8. 같은 thread로 복귀하거나 scheduler가 선택할 때까지 기다립니다.
```

사용자 pointer는 kernel pointer가 아닙니다. 주소 범위, mapping, 접근 권한과 길이 계산의 overflow를 확인해야 합니다. 검사와 실제 복사 사이에 mapping이 바뀔 수 있는지도 API와 구현에 따라 고려합니다.

## 즉시 완료, 대기와 부분 실패

### 즉시 완료

필요한 data가 page cache나 kernel buffer에 있고 자원을 바로 확보할 수 있으면 같은 system call 안에서 결과를 반환합니다.

### 대기

장치 completion, timer, unlock 또는 page-in이 필요하면 현재 thread를 wait queue에 등록하고 `BLOCKED`로 바꿉니다. 다른 `READY` 작업이 CPU를 사용합니다. 사건이 발생하면 해당 thread는 `READY`가 되며, scheduler가 다시 선택한 뒤 요청을 이어 갑니다.

### 실패 또는 부분 진행

I/O API는 전체 요청을 처리하지 못하고 일부 byte만 반환할 수 있습니다. interrupt로 대기가 중단되거나 storage가 가득 찬 경우도 있습니다. 따라서 오류 번호만 확인해서는 부족합니다.

```text
반환값: 몇 byte 또는 몇 항목을 처리했습니까?
오류: 어떤 이유로 멈췄습니까?
부분 효과: offset, buffer, mapping 또는 object가 바뀌었습니까?
정리: 실패 뒤 누가 memory, FD와 request를 해제합니까?
재시도: 같은 요청을 그대로 반복해도 안전합니까?
```

## timer interrupt와 선점

timer interrupt가 있어야 사용자 프로그램이 CPU를 계속 점유하더라도 kernel이 다시 제어를 얻을 수 있습니다. handler는 실행 시간, 만료된 timer, time slice와 더 높은 우선순위 작업의 준비 여부를 갱신합니다.

모든 timer interrupt가 context switch를 만들지는 않습니다. 현재 작업을 계속 실행할 수 있으면 같은 문맥으로 돌아갑니다. 반대로 time slice가 끝났거나 더 적합한 작업이 `READY`가 되면 scheduler가 다른 작업을 선택할 수 있습니다.

## interrupt 처리 시간을 짧게 유지하는 이유

interrupt handler가 오래 실행되면 다른 interrupt와 scheduler 처리가 늦어집니다. 따라서 많은 운영체제는 즉시 해야 할 일과 나중에 할 일을 나눕니다.

```text
즉시 처리
- interrupt 원인 확인
- completion 정보 보존
- device에 처리 완료 알림
- 후속 작업 예약

지연 가능
- 큰 packet 처리
- 요청 결과 조립
- waiter 깨우기
- 사용자 공간으로 결과 전달
```

구현마다 softirq, worker, deferred procedure 등 이름은 다르지만, 사건을 잃지 않을 만큼만 기록하고 오래 걸리는 작업을 뒤로 미루는 원리는 같습니다.

## 관찰 예제

```sh
make -C examples build/syscall-boundary
./examples/build/syscall-boundary
```

`syscall-boundary`는 `write` 성공과 존재하지 않는 경로의 `open` 실패를 보여 줍니다. `open`의 음수 반환과 저장한 `errno`가 함께 실패 이유를 나타냅니다.

이 출력만으로 실제 CPU 진입 instruction이나 kernel 내부 handler를 알 수는 없습니다. 사용자 공간에서 관찰 가능한 API 결과만 확인합니다.

## 연결 실습

이 문서와 다음 두 문서를 읽은 뒤 `kernel-model`의 lifecycle을 확인합니다.

- [프로세스, 스레드와 문맥 전환](02-processes-threads-and-context-switches.md)
- [블록, 깨우기와 IPC](04-blocking-wakeup-and-ipc.md)

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.LifecycleTests -v
python3 kernel-model.py lifecycle examples/lifecycle.json
```

## 완료 기준

- 네 사건을 발생 원인과 재개 방식으로 분류할 수 있습니다.
- kernel mode 진입과 context switch가 같은 뜻이 아님을 설명할 수 있습니다.
- block 가능한 요청의 제출, 대기, completion과 재개 순서를 그릴 수 있습니다.
- 실패한 system call에서 반환값 외에 확인할 상태를 나열할 수 있습니다.

## 잘못된 이해

- 모든 system call이 context switch를 만든다고 생각합니다.
- page fault를 모두 프로그램 오류로 분류합니다.
- 오류 번호만 보고 부분 진행량과 정리할 자원을 확인하지 않습니다.
- 사용자 공간 출력만으로 특정 kernel 구현을 단정합니다.

## 자기 설명

- timer interrupt가 선점을 가능하게 해도 매번 작업을 바꾸지 않는 이유는 무엇입니까?
- `read` 요청과 device completion이 서로 다른 사건이어야 하는 이유는 무엇입니까?
- 사용자 pointer를 kernel이 다시 검증해야 하는 이유는 무엇입니까?
