# 이벤트 형식, 버전과 순서

## 목표

이벤트와 API의 필드 모양뿐 아니라 단위, 의미, 호환성, 중복 ID와 필요한 순서 범위를 명확히 정합니다. 배포 버전이 섞이거나 이벤트 순서가 바뀌어도 상태를 잘못 적용하지 않게 합니다.

## 직렬화 성공은 호환성을 뜻하지 않습니다

다음 JSON은 형식만으로 의미를 알 수 없습니다.

```json
{"amount": 1000}
```

`1000`이 원인지 센트인지, 세금 포함인지, 음수를 허용하는지 알 수 없다면 타입이 같아도 다른 업무 입력입니다. channel 이름, enum 값, partition key와 sequence도 공개 형식의 일부입니다.

## 형식과 의미를 함께 기록합니다

다음 항목을 문서와 검증 코드에 포함합니다.

- API 또는 event 이름
- schema version
- 필드 타입과 필수 여부
- 숫자의 단위와 정밀도
- 시간대와 timestamp 의미
- enum 값을 추가할 때의 처리 방법
- `null`과 필드 누락의 차이
- event ID와 중복 판정 방법
- 순서를 보장하는 대상
- 보존 기간과 재처리 가능 기간
- producer와 consumer가 각각 확인할 항목

schema version은 `1`부터 시작하는 양수로 취급합니다. `0`이나 음수는 미래 버전이 아니라 잘못된 입력이므로 격리하지 않고 거절합니다.

## 변경을 additive와 breaking으로 구분합니다

기존 consumer가 모르는 필드를 무시할 수 있다면 선택 필드 추가는 보통 additive 변경입니다. 다음 변경은 별도 전환 계획이 필요합니다.

- 필수 필드 추가
- 필드의 의미나 단위 변경
- 기존 consumer가 모르는 enum 값을 거절하는 경우
- 필드 제거
- 같은 이름을 다른 상태에 재사용
- partition key 변경
- 순서를 보장하는 범위 변경

이전 consumer가 새 event를 읽는 경우와 새 consumer가 이전 event를 읽는 경우를 모두 검사합니다.

## 필요한 대상 안에서만 순서를 보장합니다

모든 이벤트의 전역 순서를 맞추는 것은 비싸고 대부분 필요하지 않습니다. 예약 한 건처럼 같은 aggregate 안의 상태 변화만 순서대로 처리하면 충분한 경우가 많습니다.

```text
reservation-1: CREATED(1) → ACCEPTED(2) → COMPLETED(3)
reservation-2: CREATED(1) → REJECTED(2)
```

aggregate별 sequence를 두면 다음을 구분할 수 있습니다.

- 같은 event ID와 같은 입력: 중복 전달
- 예상한 다음 sequence: 즉시 적용
- 예상보다 큰 sequence: 앞선 event가 없으므로 보류
- 예상보다 작은 sequence: 오래된 전달 또는 충돌
- 지원하지 않는 schema version: 격리
- 같은 aggregate와 sequence에 다른 event: 충돌

서로 다른 aggregate는 독립적으로 처리합니다.

## 동기 API도 혼합 버전을 고려합니다

롤링 배포 중에는 이전 producer와 새 consumer, 새 producer와 이전 consumer가 동시에 실행됩니다. 동기 API의 response field, error code와 enum도 같은 방식으로 검사합니다. 필드를 제거하기 전에는 실제 consumer가 더 이상 사용하지 않는지 확인해야 합니다.

## 흔한 잘못

- producer와 consumer가 channel 이름을 각각 하드코딩합니다.
- 필드 타입만 같으면 의미도 같다고 봅니다.
- 모르는 enum 값이 오면 consumer 전체가 중단됩니다.
- partition key를 바꾸면서 순서 보장 범위를 갱신하지 않습니다.
- 도착 시각으로 업무 순서를 결정합니다.
- 지원하지 않는 schema version을 조용히 적용하거나 버립니다.
- 전역 순서가 필요하지 않은데 모든 event를 한 partition으로 보냅니다.

## 검증 방법

최소한 다음 경우를 검사합니다.

- 이전 consumer와 additive field가 추가된 event
- 새 consumer와 이전 버전 event
- 잘못된 channel
- `0`, 음수와 지원하지 않는 schema version
- 같은 aggregate의 sequence `2 → 1 → 3`
- 같은 event ID 재전달
- 같은 sequence를 서로 다른 event가 주장하는 충돌
- 서로 다른 aggregate의 독립 처리

각 입력을 적용, 보류, 중복, 격리 또는 거절 중 하나로 명확히 분류해야 합니다.

## 관련 프로젝트

[`contracts-and-order`](../../exercises/contracts-and-order/)는 channel, schema version, event ID와 aggregate sequence를 함께 검사합니다.

## 완료 기준

- 필드 형식과 업무 의미를 함께 기록할 수 있습니다.
- additive 변경과 breaking 변경을 구분할 수 있습니다.
- 필요한 순서 범위를 aggregate 수준으로 제한할 수 있습니다.
- 혼합 버전과 순서 역전 테스트를 작성할 수 있습니다.
