# 자산, 신뢰 지점과 위협 모델

위협 모델은 공격 이름을 길게 나열하는 문서가 아닙니다. 지켜야 할 상태, 그 상태를 바꿀 수 있는 actor, 입력과 identity를 다시 확인해야 하는 지점, 실패 결과를 연결하는 문서입니다.

## 1. 사용자 기능부터 적기

먼저 시스템을 한 문장으로 정의합니다.

> 사용자는 공개 HTTPS API에서 자신의 보고서를 생성하고 조회하며, background worker가 결과 파일을 object storage에 저장합니다.

이 문장만으로도 다음 구성요소를 찾을 수 있습니다.

```text
사용자
공개 gateway
API
worker
database
object storage
identity provider
release system
audit 저장소
backup
```

도구와 제품 이름보다 사용자가 하는 일과 상태가 어디에 저장되는지 먼저 적습니다.

## 2. 검토 범위 표시

context diagram에는 다음을 구분합니다.

- 이번 검토에서 직접 확인할 component와 version
- 외부 provider와 제3자 service
- production과 분리된 합성 환경
- 변경할 수 없는 legacy component
- 별도 팀이 관리하는 identity, network, storage와 backup

범위 밖의 component도 attack path에 영향을 줄 수 있습니다. 다만 직접 시험하지 않고, 현재 제공된 보장과 확인하지 못한 가정, 문제가 생겼을 때 연락할 대상을 기록합니다.

## 3. 자산 register

자산은 server 이름만 뜻하지 않습니다.

| 분류 | 예 | 확인할 내용 |
|---|---|---|
| 업무 데이터 | account, report, payment state | 누가 읽고 바꿀 수 있습니까? |
| identity | user session, service credential, signing key | 누가 발급·위임·폐기합니까? |
| 제어 권한 | DNS, CI, registry, admin API | 탈취되면 어떤 작업이 가능합니까? |
| 복구 원본 | source, release manifest, backup | 공격자가 운영 데이터와 함께 지울 수 있습니까? |
| 운영 근거 | audit log, deployment record | 조사 대상이 수정할 수 있습니까? |
| 가용성 자원 | queue, connection pool, storage quota | 누가 고갈시킬 수 있고 어떻게 제한합니까? |

자산마다 최소한 다음을 기록합니다.

```text
업무·위험 소유자
상태 정본
읽을 수 있는 주체
바꿀 수 있는 주체
허용된 상태
상태를 바꾸는 사건
보존 기간
복구 원본
유지해야 할 불변식
```

## 4. actor를 capability로 표현하기

“공격자” 하나로 묶지 않습니다.

- 인증되지 않은 외부 사용자
- 일반 사용자 계정을 가진 actor
- 탈취된 session을 가진 actor
- 제한된 service credential을 가진 workload
- CI workflow를 수정할 수 있는 contributor
- host에서 일반 사용자 권한을 얻은 actor
- 실수한 운영자
- 손상된 dependency나 build tool

이름보다 현재 할 수 있는 일을 적습니다.

```text
public request를 보낼 수 있음
일반 사용자의 report ID를 관찰할 수 있음
특정 queue에 job을 만들 수 있음
한 repository branch에 push할 수 있음
read-only backup credential을 가지고 있음
```

Attack path의 각 단계에서는 이전 단계 결과로 새 capability가 실제로 생기는지 확인합니다.

## 5. 다시 검증해야 하는 지점

네트워크 subnet이 바뀌는 곳만 중요한 것은 아닙니다. 한쪽이 주장한 값을 다른 쪽이 그대로 믿으면 안 되는 곳을 찾습니다.

대표 사례:

- browser가 보낸 user identity를 API가 받는 곳
- gateway가 붙인 header를 internal service가 받는 곳
- 사용자의 요청을 service identity로 대신 처리하는 곳
- application이 database row와 object owner를 읽는 곳
- worker가 object storage credential을 사용하는 곳
- CI가 artifact를 registry에 올리는 곳
- registry artifact를 production이 실행하는 곳
- application이 audit event를 별도 저장소로 보내는 곳

각 지점에서 다음을 확인합니다.

1. 누가 어떤 identity를 주장합니까?
2. 그 identity를 무엇으로 증명합니까?
3. 어떤 tenant·job·resource·action까지 허용됩니까?
4. 필요한 정보를 확인하지 못하면 허용합니까, 거절합니까?
5. 판정과 거절 사유를 어디에 기록합니까?
6. proxy, cache와 retry가 원래 identity나 resource를 바꿀 수 있습니까?

## 6. 데이터 이동을 한 가지 의미로 나누기

Diagram의 선 하나에 여러 의미를 섞지 않습니다.

```text
subject identity 전달
업무 command 전달
artifact 다운로드
credential 발급
audit event 전송
backup 복제
```

각 이동에는 다음을 적습니다.

- caller와 callee
- 사용한 identity
- 데이터의 민감도
- authentication과 authorization을 수행하는 component
- 무결성과 기밀성을 지키는 방법
- retry·cache·queue가 결과에 주는 영향
- 남는 log·metric·trace

## 7. 위협 문장

다음 형식을 사용합니다.

```text
[capability]를 가진 [actor]가
[전제]에서 [입력 또는 identity를 받는 지점]을 통과할 때
[빠진 검사 또는 과도한 권한] 때문에
[자산]의 [보안 상태]를 깨뜨릴 수 있습니다.
```

예:

```text
일반 사용자 session을 가진 actor가
report download 요청을 보낼 때
API가 report owner를 확인하지 않으면
다른 사용자의 report 내용을 읽을 수 있습니다.
```

“악성 사용자”, “injection 가능”처럼 actor의 capability와 바뀌는 상태가 없는 표현은 피합니다.

## 8. 정상·경계·실패 사례를 함께 적기

| 종류 | report read 사례 | 확인할 결과 |
|---|---|---|
| 정상 | 소유자가 완료된 자신의 report를 읽음 | 정상 응답과 완전한 allow event |
| 경계 | owner 변경 중, 미완료 report, tenant 누락, session 만료 시각 | 현재 정본과 규칙으로 일관되게 판정 |
| 대표 실패 | 일반 사용자가 다른 owner의 report를 읽으려 함 | 내용과 불필요한 존재 정보가 노출되지 않고 deny event가 남음 |

위협 모델에 정상 사례가 없으면 수정 뒤 사용 가능한 기능을 보존했는지 검사할 수 없습니다.

## 9. attack path 작성

단일 약점보다 capability가 이어지는 과정을 적습니다.

```text
초기 capability
→ 첫 번째 검사 누락으로 새 정보 또는 identity 획득
→ 그 결과가 다음 요청의 전제가 됨
→ 더 넓은 service·storage 권한 사용
→ 중요 자산 영향
```

| 단계 | 전제 | 행동 | 새로 얻는 capability | 필요한 근거 |
|---|---|---|---|---|
| 1 | 일반 user session | 다른 owner의 report 요청 | report 내용 접근 가능성 | API 응답, report owner 정본 |
| 2 | report metadata | internal object key 관찰 | storage 경로 형태 파악 | 응답, queue·storage event |
| 3 | 과도한 worker credential | 다른 job prefix 읽기 | 여러 report 접근 가능성 | credential 정보, storage 판정 event |

직접 검증하지 않은 단계는 `hypothesis`로 남깁니다. 각 단계가 따로 확인됐더라도 같은 version·identity·시간에 실제로 연결됐다는 근거가 없다면 전체 경로를 confirmed라고 표현하지 않습니다.

## 10. 여러 위치에서 같은 경로 끊기

한 곳의 검사만 믿지 않습니다.

```text
API의 object authorization
+ job-scoped worker credential
+ storage prefix 확인
+ allow·deny event
+ 범위 초과 거절 alert
```

공통으로 여러 경로를 끊는 지점은 우선순위가 높습니다. 다만 그 한 지점이 실패했을 때도 다른 검사와 관측이 남도록 설계합니다.

## 11. 가정과 미확인 항목

확인하지 않은 사실을 숨기지 않습니다.

```text
ASSUMPTION: gateway가 외부의 X-User-ID 값을 제거하고 새 값을 넣습니다.
UNKNOWN: production worker credential의 실제 scope는 확인하지 못했습니다.
OUT OF SCOPE: identity provider의 MFA 운영은 별도 팀이 관리합니다.
```

가정이 틀렸을 때 어떤 threat가 다시 열리는지도 연결합니다.

## 12. 다시 검토할 때

다음 변경이 생기면 위협 모델을 갱신합니다.

- 새 public endpoint나 admin 기능
- 새 service, queue, storage 또는 provider
- identity·credential·permission 변경
- data classification 변경
- CI·build·deployment 방식 변경
- incident 또는 새로운 vulnerability class
- identity나 resource 정보를 바꾸는 proxy·cache 추가

## 완료 질문

- network 위치가 같아도 identity와 resource를 다시 확인해야 하는 이유는 무엇입니까?
- actor 이름보다 capability를 적는 편이 유용한 이유는 무엇입니까?
- 위협 하나와 여러 단계의 attack path는 어떻게 다릅니까?
- 한 단계의 합성 검증이 전체 attack path를 증명하지 못하는 이유는 무엇입니까?
- 정상 사례를 위협 모델에 포함해야 하는 이유는 무엇입니까?
