# Spring Data Redis 어댑터

> 읽는 시점: 실제 프로젝트에 Redis를 캐시, 제한 상태, 임시 조정 수단으로 도입할 때

Redis를 추가하기 전에 무엇을 저장하고 Redis가 실패했을 때 어떤 동작을 허용할지 먼저 정합니다. 이 문서는 Spring Data Redis의 연결, key 형식, 직렬화, TTL, DB commit 이후 갱신을 다룹니다.

## Redis에 저장하는 값의 용도를 구분합니다

Redis는 여러 용도로 사용할 수 있지만 각 용도의 실패 처리 방식은 다릅니다.

- 조회 cache는 없어도 데이터베이스에서 다시 만들 수 있습니다.
- 계산 결과 memoization은 재계산 비용과 TTL을 관리해야 합니다.
- rate limit은 Redis 장애 때 요청을 허용할지 거부할지 정해야 합니다.
- lease나 임시 lock은 만료 시간과 소유자 token이 필요합니다.

하나의 `RedisTemplate<Object, Object>`에 모든 값을 섞지 않습니다. 용도마다 key prefix, value 형식, TTL, 실패 시 동작을 정합니다.

## key와 value 형식을 명시합니다

Java 기본 직렬화는 사용하지 않습니다. 문자열, 명시적인 JSON, version이 있는 binary schema 중 하나를 선택합니다.

```text
key: publication:result:v1:{sha256(actor-length + actor + idempotency-key)}
value: {"id":"...","actorId":"...","title":"..."}
ttl: 24h
```

시간, 금액, enum을 어떤 형식으로 저장할지 정합니다. Java package 이름이 바뀌었다는 이유로 기존 값을 읽지 못하는 형식을 피합니다.

민감한 원문 key를 그대로 Redis에 남기지 않도록 길이 prefix나 hash를 사용할 수 있습니다. 단순 문자열 연결은 구분자 충돌을 만들 수 있으므로 각 값이 어디서 끝나는지 알 수 있게 인코딩합니다. TTL은 코드에 숨기지 말고 설정으로 받고 양수인지 시작 단계에서 검사합니다.

## DB commit 뒤에 cache를 갱신합니다

정확한 결과는 데이터베이스 transaction과 constraint로 만듭니다. cache는 commit이 성공한 뒤 갱신합니다.

```text
DB transaction에서 상태 저장
→ commit 성공
→ Redis에 결과 저장
```

transaction 안에서 Redis를 먼저 갱신하면 DB rollback 뒤에도 잘못된 cache 값이 남을 수 있습니다. `@TransactionalEventListener(phase = AFTER_COMMIT)`을 사용하거나 transaction을 실행하는 Bean 밖에서 cache를 갱신합니다.

cache 저장이 실패해도 이미 commit된 업무 결과를 실패로 바꾸지 않는 경우가 많습니다. 이때 실패 횟수를 metric에 남기고 다음 조회에서 DB 결과로 cache를 복구합니다.

## 캐시에 값이 없으면 DB를 먼저 확인합니다

이미 완료된 멱등 요청이라면 Redis miss 때문에 외부 판단을 다시 호출하면 안 됩니다.

```text
Redis 결과 조회
→ 없거나 실패하면 DB 완료 결과 조회
→ DB 결과가 있으면 Redis 복구 후 반환
→ 둘 다 없을 때만 새 처리 시작
```

첫 요청이 성공한 뒤 외부 정책이 바뀌었더라도 같은 멱등성 key는 첫 완료 결과를 반환해야 합니다. Redis는 조회를 빠르게 할 뿐 결과의 존재 여부를 최종 결정하지 않습니다.

반대로 rate limit처럼 Redis에만 있는 상태라면 장애 시 fail-open 또는 fail-closed를 업무 위험에 따라 정합니다. 이 선택을 예외 처리 코드 안에 숨기지 않습니다.

## 대량 만료와 cache miss를 관찰합니다

많은 key가 동시에 만료되면 데이터베이스로 요청이 몰릴 수 있습니다.

- TTL에 제한된 무작위 차이를 둡니다.
- 같은 key의 동시 재계산을 하나로 합칩니다.
- warm-up 작업의 속도를 제한합니다.
- DB connection pool과 cache fallback 요청 수를 제한합니다.

문제가 관찰되지 않았는데 기법을 모두 추가하기보다 cache hit 비율, miss 지연, DB 부하를 먼저 측정합니다.

## Rewind가 필요한 징후

- Redis 장애 때 중복 업무 행이 생성됩니다.
- DB rollback 뒤에도 cache에 성공 결과가 남습니다.
- 같은 멱등성 key의 cache miss가 외부 API를 다시 호출합니다.
- TTL이 없거나 0 이하인 값이 저장됩니다.
- Java class 이름 변경 뒤 기존 cache를 읽지 못합니다.
- 사용자 ID나 요청 ID를 metric tag로 넣어 값 종류가 계속 늘어납니다.

Redis와 Outbox를 함께 연습하려면 전문 exercise인 [`idempotent-operation-outbox`](../../exercises/idempotent-operation-outbox/)를 선택적으로 수행합니다.
