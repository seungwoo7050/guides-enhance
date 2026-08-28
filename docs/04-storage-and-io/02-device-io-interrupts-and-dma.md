# 장치 I/O, interrupt와 DMA

## 학습 목표

- request의 queued, in-flight, completed와 reaped 위치를 추적합니다.
- DMA pin, interrupt completion, cancellation과 timeout이 경쟁할 때 buffer 수명을 설명합니다.
- queue depth, polling과 interrupt coalescing을 정확성 조건 안에서 비교합니다.

## I/O request는 호출 stack보다 오래 살 수 있습니다

장치 요청은 함수 호출 안에서 즉시 끝나지 않을 수 있습니다. kernel이 request를 queue에 넣고 device에 제출한 뒤 현재 thread를 block하면, 실제 transfer와 completion은 나중에 발생합니다.

단순한 상태는 다음과 같습니다.

```text
NEW
→ QUEUED
→ IN_FLIGHT
→ COMPLETED
→ REAPED
```

cancellation이 있으면 다음 경로가 추가됩니다.

```text
QUEUED → CANCELLED → REAPED
IN_FLIGHT → CANCEL_PENDING → CANCELLED → REAPED
```

`COMPLETED`와 `REAPED`를 구분해야 합니다.

- `COMPLETED`: device가 buffer 사용을 끝냈고 kernel이 결과를 기록했습니다.
- `REAPED`: owner가 결과를 받아 마지막 request 참조를 정리했습니다.

completion 직후 request object를 없애면 waiter가 결과를 읽기 전에 사라질 수 있습니다.

## 제출할 때 필요한 정보

```text
request id
owner 또는 completion 대상
operation 종류와 device 위치
buffer 또는 page 목록
전송 길이
queue와 priority 정보
timeout 또는 cancellation 상태
결과와 오류를 저장할 위치
```

owner process가 exit하거나 file을 close하는 경우에도 누가 request를 취소하고 늦은 completion을 처리할지 정해야 합니다.

## queue depth와 backpressure

software queue와 hardware submission queue에는 처리 가능한 request 수가 있습니다.

queue가 가득 찼을 때 선택할 수 있는 동작은 다음과 같습니다.

- 호출자 block
- busy 오류 반환
- 상위 queue에서 대기
- 낮은 priority request 거부
- request 병합 또는 재정렬

queue를 무한히 늘리면 throughput보다 latency와 memory 사용량이 먼저 커질 수 있습니다. queue depth는 device parallelism, 평균 latency와 tail latency를 함께 측정해 정합니다.

`kernel-model`의 `DeviceQueue`는 active request 수가 `queue_depth`를 넘으면 제출을 거부합니다.

## programmed I/O와 DMA

### programmed I/O

CPU가 device register 또는 port를 통해 data를 직접 옮깁니다. 작은 control transfer에는 쓸 수 있지만 큰 data를 옮기면 CPU 사용량이 큽니다.

### DMA

장치가 memory와 직접 data를 주고받습니다.

```text
CPU: buffer와 descriptor 준비
CPU: device에 request 제출
device: memory transfer
interrupt 또는 polling: completion 확인
CPU: 결과 기록과 자원 정리
```

DMA가 CPU 작업을 없애는 것은 아닙니다. page pin, device-visible mapping, descriptor 관리, cache ordering과 completion 처리가 필요합니다.

## DMA buffer 수명

장치가 page를 사용하는 동안 process가 buffer를 해제하거나 memory manager가 frame을 다른 용도로 바꾸면 data corruption이 생길 수 있습니다.

```text
QUEUED
- 아직 device가 접근하지 않으므로 pin이 필요 없을 수 있습니다.

IN_FLIGHT 또는 CANCEL_PENDING
- device가 접근할 수 있으므로 page를 유지합니다.

COMPLETED 또는 completion 뒤 CANCELLED
- device 접근이 끝났으므로 unpin할 수 있습니다.

REAPED
- owner가 결과를 받았고 request 수명도 끝납니다.
```

`kernel-model`은 `pinned` 상태와 `in_flight` set 포함 여부가 같아야 한다고 검사합니다.

## device-visible address

process의 virtual address를 device에 그대로 줄 수는 없습니다.

```text
process virtual address
→ kernel이 확인한 page 목록
→ physical page
→ IOMMU가 제공하는 device-visible address
→ scatter-gather descriptor
```

연속된 user buffer가 physical memory에서는 여러 page로 나뉠 수 있습니다. scatter-gather list는 이 segment를 하나의 request로 표현합니다.

IOMMU는 device가 접근할 수 있는 memory 범위를 제한하고 address translation을 제공할 수 있습니다. mapping을 만들고 없애는 시점은 request 상태와 맞아야 합니다.

## CPU cache와 DMA ordering

platform이 hardware coherent인지, software가 cache maintenance를 해야 하는지 확인해야 합니다.

```text
CPU → device
- CPU가 작성한 descriptor와 data가 device에 보여야 합니다.

device → CPU
- completion 뒤 CPU가 device가 쓴 최신 data를 봐야 합니다.
```

일반 pointer write와 `volatile`만으로 해결되지 않습니다. platform의 DMA API와 memory barrier 규칙을 따라야 합니다.

## interrupt completion

interrupt handler는 보통 오래 걸리는 작업을 모두 처리하지 않습니다.

```text
즉시 수행
- device 상태 확인
- interrupt 원인 acknowledge
- 완료 descriptor 수집 또는 표시
- 후속 처리 예약

후속 처리
- request 결과 조립
- buffer unpin
- completion queue에 추가
- waiter wakeup
```

결과 필드를 기록하기 전에 waiter를 깨우면 waiter가 불완전한 값을 볼 수 있습니다. 결과 공개와 wakeup 순서를 정해야 합니다.

## interrupt coalescing과 polling

### interrupt coalescing

여러 completion을 모으거나 일정 시간이 지난 뒤 interrupt를 발생시킵니다.

- interrupt 횟수를 줄여 throughput을 높일 수 있습니다.
- 개별 request latency가 늘어날 수 있습니다.

### polling

CPU가 completion queue를 반복 확인합니다.

- 높은 부하에서는 interrupt 전환 비용을 줄일 수 있습니다.
- 유휴 상태에서도 CPU를 사용할 수 있습니다.

낮은 부하에서는 interrupt, 높은 부하에서는 제한된 polling을 사용하는 혼합 방식도 있습니다. throughput, tail latency, CPU budget과 power를 함께 봅니다.

## completion과 wakeup 순서

```text
interrupt 또는 polling이 completion 확인
→ request를 in-flight에서 제거
→ bytes transferred와 error 기록
→ buffer unpin 또는 DMA mapping 해제
→ owner completion queue에 request 추가
→ waiter wakeup
→ thread READY
→ scheduler 선택
→ owner가 결과 reap
```

wakeup은 user code가 즉시 실행된다는 뜻이 아닙니다. scheduler가 CPU를 줄 때까지 `READY`에서 기다립니다.

## partial completion과 오류

request는 전체 길이보다 적게 완료될 수 있습니다.

```text
일부 byte 전송
device error
medium error
connection reset
cancel과 completion 경쟁
```

결과에는 다음 정보가 필요합니다.

- 요청 길이
- 실제 전송 길이
- 완료 상태
- 오류와 재시도 가능 여부
- 부분 data의 유효성
- 재시도 offset
- 중복 실행이 안전한지

device operation에 side effect가 있다면 driver가 임의로 같은 write를 반복해서는 안 됩니다.

## cancellation

### queued request

hardware에 제출하기 전이면 pending queue에서 제거하고 `CANCELLED` 결과를 owner에게 전달할 수 있습니다.

### in-flight request

이미 device가 buffer를 사용 중이면 즉시 해제할 수 없습니다.

```text
IN_FLIGHT
→ cancel 요청
→ CANCEL_PENDING
→ 늦은 interrupt completion
→ device 접근 종료와 unpin
→ CANCELLED 결과 전달
```

cancel 호출이 성공했다는 말과 device operation이 실제로 중단됐다는 말은 다를 수 있습니다. API가 어떤 의미를 보장하는지 확인해야 합니다.

## exactly-once result delivery

normal completion과 cancellation이 동시에 결과를 만들면 owner가 같은 request를 두 번 받을 수 있습니다. request는 completion queue 한 곳에만 있어야 하고 `reap`은 한 번만 성공해야 합니다.

late interrupt가 이미 재사용한 request id를 완료하지 않도록 generation 또는 고유 id를 사용할 수 있습니다. 기본 `kernel-model`은 id를 재사용하지 않아 이 문제를 단순화합니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.DeviceTests -v
python3 kernel-model.py io examples/device-io.json
```

invalid snapshot 테스트는 다음 상태를 거부합니다.

- 같은 request가 pending과 in-flight에 동시에 있음
- active request 수가 queue depth를 넘음
- pin 상태와 in-flight 위치가 다름
- completion queue의 owner가 request owner와 다름

## 완료 기준

- request의 제출부터 `reap`까지 상태를 추적할 수 있습니다.
- in-flight cancellation 뒤에도 buffer를 유지해야 하는 이유를 설명할 수 있습니다.
- DMA mapping과 request 수명이 맞아야 하는 이유를 설명할 수 있습니다.
- interrupt, coalescing과 polling의 비용을 비교할 수 있습니다.
- partial completion과 exactly-once result delivery를 설명할 수 있습니다.

## 잘못된 이해

- cancel 성공을 device operation이 즉시 멈췄다는 뜻으로 해석합니다.
- interrupt completion과 user result delivery를 같은 시점으로 봅니다.
- user virtual address를 device에 그대로 전달할 수 있다고 생각합니다.
- completion을 기록하기 전에 waiter를 깨워도 괜찮다고 생각합니다.

## 자기 설명

- `COMPLETED`와 `REAPED`를 분리해야 하는 이유는 무엇입니까?
- in-flight request의 buffer를 cancel 직후 해제하면 어떤 문제가 생깁니까?
- interrupt coalescing이 throughput을 높이면서 latency를 늘릴 수 있는 이유는 무엇입니까?
