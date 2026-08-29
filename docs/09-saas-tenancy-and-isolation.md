# SaaS tenancy와 isolation

SaaS를 만드는 개발자에게 `tenant`는 핵심 상태입니다.

```text
user
사람 또는 machine identity 하나를 뜻합니다.

tenant
데이터, 설정, 권한, 사용량과 계약을 함께 사용하는 고객 단위를 뜻합니다.
```

B2B 서비스에서는 회사나 workspace가 tenant일 수 있고, B2C 서비스에서는 가정, 팀이나 계정 묶음이 tenant일 수 있습니다. Tenant를 database schema 하나로만 설명하면 request, cache, background job, export와 삭제 작업에서 식별자가 빠질 수 있습니다.

## 1. Tenant를 먼저 정의합니다

다음 질문에 답해야 합니다.

- 누가 tenant를 만듭니까?
- 사용자가 여러 tenant에 가입할 수 있습니까?
- tenant 사이 data 공유를 허용합니까?
- tenant administrator가 할 수 있는 작업은 무엇입니까?
- support operator가 tenant data를 읽거나 수정할 수 있습니까?
- plan, region, key와 backup을 tenant별로 분리합니까?
- suspend, merge, split과 delete를 지원합니까?

정의가 불명확하면 authorization, usage 집계와 deletion 결과도 불명확해집니다.

## 2. Tenant lifecycle

대표 상태는 다음과 같습니다.

```text
REQUESTED
→ PROVISIONING
→ ACTIVE
→ SUSPENDED
→ CLOSING
→ RETENTION
→ DELETED
```

서비스에 따라 다음 상태가 추가될 수 있습니다.

- trial
- payment delinquent
- migration
- legal hold
- export pending
- deletion failed

각 상태에서 허용할 작업을 명시합니다. 예를 들어 `SUSPENDED`에서는 새 write를 막고 read와 export만 허용할 수 있습니다.

## 3. Isolation은 한 가지 방식이 아닙니다

### 모든 자원을 공유합니다

- 같은 application instance
- 같은 database table
- row마다 `tenant_id`

운영 비용은 낮지만 application bug가 여러 tenant에 영향을 줄 수 있고, 한 tenant의 부하가 shared resource를 소진할 수 있습니다.

### Application은 공유하고 data 단위를 분리합니다

- tenant별 schema 또는 database
- tenant별 object prefix나 key

Data를 분리하기 쉽지만 connection, migration, backup과 restore 대상을 더 많이 관리해야 합니다.

### Tenant별 배포를 둡니다

- tenant별 application, database, network 또는 account

격리와 custom 설정에는 유리하지만 provisioning, upgrade, capacity와 비용이 크게 늘어납니다.

모든 component를 같은 방식으로 나눌 필요는 없습니다. 요구하는 격리 수준과 확인 자료를 component별로 정합니다.

## 4. Tenant context를 요청마다 확정합니다

```text
authenticated_subject
tenant_id
membership 또는 service relationship
role 또는 entitlement
request_id
reason
```

Client가 보낸 `tenant_id`를 그대로 믿지 않습니다. 인증된 사용자의 membership이나 신뢰할 수 있는 routing 정보와 연결해 확인합니다.

Background job와 event도 tenant context를 포함하고, 실행할 때 현재 tenant 상태와 권한을 다시 확인해야 합니다.

## 5. Data access

### Shared table

Primary key, foreign key와 query가 tenant를 함께 구분해야 합니다.

```text
PRIMARY KEY (tenant_id, document_id)
FOREIGN KEY (tenant_id, project_id)
WHERE tenant_id = current_tenant
```

`document_id`가 전역에서 고유해도 tenant 검사는 필요합니다. ID를 맞힐 수 있는지와 관계없이 authorization 조건입니다.

### Tenant별 schema 또는 database

Connection 선택이 tenant context와 정확히 연결돼야 합니다.

- connection pool에 이전 tenant 상태가 남지 않는지
- migration version이 tenant마다 달라지지 않는지
- backup과 restore 대상이 올바른지
- credential이 해당 tenant data만 읽는지
- tenant 삭제 시 database와 credential을 함께 정리하는지

### Object storage

Object key, bucket policy와 pre-signed URL에 tenant를 반영합니다. Prefix를 나눴다는 사실만으로 authorization이 자동으로 적용되지는 않습니다.

## 6. Cache

Cache key에 tenant가 빠지면 database query가 안전해도 다른 tenant의 데이터가 반환될 수 있습니다.

```text
bad:  document:{document_id}
good: tenant:{tenant_id}:document:{document_id}:v{version}
```

Eviction과 memory quota도 tenant별로 관찰해야 합니다. 한 tenant가 cache를 채워 다른 tenant의 hit rate를 떨어뜨릴 수 있습니다.

## 7. Queue와 background job

Job payload에는 tenant ID와 작업에 필요한 안정적인 식별자가 들어가야 합니다.

다음 실패를 고려합니다.

- 사용자가 membership을 잃은 뒤 delayed job가 실행됩니다.
- tenant 삭제 뒤 event가 다시 전달됩니다.
- 모든 tenant에 접근할 수 있는 broad workload role을 사용합니다.
- batch 하나에 여러 tenant record가 섞입니다.
- dead-letter replay가 현재 tenant 상태를 확인하지 않습니다.

Worker는 실행 시점의 tenant 상태와 허용 작업을 다시 검사합니다. Workload identity도 필요한 storage와 queue만 접근하게 제한합니다.

## 8. Search, analytics와 model

Primary database 외의 파생 시스템에도 tenant가 포함돼야 합니다.

- search index document의 tenant field
- query에 강제되는 tenant filter
- analytics export partition
- training data 사용 동의
- 작은 cohort를 통해 정보가 드러나는지
- tenant 삭제가 파생 데이터에 전파되는지
- 시스템별 보존 기간 차이

운영 database에서 row를 지웠다고 search index와 log에서도 자동으로 사라졌다고 가정하면 안 됩니다.

## 9. Support와 operator access

지원 도구는 여러 tenant를 넘나드는 강한 접근 경로입니다.

필요한 통제:

- case 또는 접근 사유
- tenant approval이나 사내 규칙
- 필요한 action만 허용
- 짧은 session
- read와 write 분리
- 민감한 field 가림
- 변경할 수 없는 audit 기록
- 고객에게 접근 이력을 보여 줄지 결정

`internal user`라는 이유만으로 tenant 검사를 우회하면 안 됩니다.

## 10. Export

Tenant export에는 다음 항목을 정합니다.

- 포함할 data 범위
- 일관된 snapshot 시점
- format과 schema version
- attachment와 object 포함 여부
- audit와 usage 포함 여부
- 암호화 방식
- download identity와 만료 시각
- cross-tenant negative test

대용량 export는 비동기 job이므로 duplicate, partial output와 retry도 처리해야 합니다.

## 11. Deletion

Tenant 삭제는 row 한 번 지우는 작업이 아닙니다.

```text
새 write 차단
→ final export 또는 legal hold 확인
→ session과 token 폐기
→ primary data 삭제
→ object, cache, index와 queue 정리
→ backup 보존 규칙 적용
→ billing과 audit의 법적 보존 구분
→ 완료 결과 기록
```

각 subsystem의 완료 여부를 따로 기록하고 실패한 단계만 다시 실행할 수 있어야 합니다.

## 12. Noisy neighbor

공유 자원에서는 한 tenant의 사용량이 다른 tenant에 영향을 줍니다.

- CPU와 memory
- database connection과 query
- queue backlog
- storage I/O
- cache
- 외부 API quota
- log volume

대응 방법:

- tenant별 quota와 rate limit
- 작업 종류별 우선순위
- fair queue
- dedicated tier
- per-tenant metric과 alert

## 13. 확인 자료

- cross-tenant request test
- background job의 tenant mismatch test
- cache key test
- export 내용 검토
- support 접근 audit
- tenant 단위 restore 가능 여부 또는 제한 기록
- 부하 시험의 tenant별 latency와 처리량
- deletion 전후 resource inventory

## 14. 공격과 실수를 모두 고려합니다

Cross-tenant leak은 공격자가 ID를 맞혀서만 생기지 않습니다.

- query filter 누락
- 오래된 tenant context
- connection 재사용 오류
- 잘못된 resource policy
- support 도구 bug
- batch join 오류
- analytics export 오류
- cache key 충돌
- restore 대상 mapping 오류

따라서 isolation은 한 endpoint의 입력 검사로 끝나지 않고, tenant data가 지나가는 모든 경로에서 확인해야 합니다.

## 구현 실습과 연결

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 cross-tenant read와 write를 거부하고, event identity를 tenant별로 분리하며, tenant 삭제 뒤 document, output, queue와 resource를 제거합니다. 실제 시스템에서는 같은 조건을 database constraint, cache key, queue payload, object policy와 export test에도 적용해야 합니다.
