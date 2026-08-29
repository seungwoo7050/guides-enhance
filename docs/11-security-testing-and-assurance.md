# 보안 테스트와 확인 범위

보안 테스트 하나가 시스템 전체의 안전을 증명하지는 않습니다. 각 검사 방법은 다른 종류의 실패를 찾으며, 실행 환경과 입력에 따라 놓치는 부분이 생깁니다.

## 1. 도구보다 질문을 먼저 정하기

```text
어떤 보안 상태를 확인합니까?
어느 component·version·configuration을 검사합니까?
어떤 actor·state·input을 사용합니까?
통과와 실패를 무엇으로 판정합니까?
이 검사로 확인하지 못하는 범위는 무엇입니까?
```

이 질문에 답하지 못하면 scanner 결과가 있어도 무엇을 확인했는지 설명하기 어렵습니다.

## 2. 검사 수준

### Unit·component test

적합한 대상:

- authorization 함수
- parser와 validator
- credential scope 계산
- 상태 변경 함수
- encoding과 serialization

한계:

- 실제 framework 연결, proxy, DB rule과 runtime identity를 놓칠 수 있습니다.

### Integration test

적합한 대상:

- subject와 resource owner 판정
- DB constraint와 transaction
- service 간 identity 전달
- storage·queue 접근 판정
- audit event 생성

한계:

- production topology, secret과 network 설정이 다를 수 있습니다.

### End-to-end security test

적합한 대상:

- gateway에서 storage까지 실제 요청 경로
- release configuration
- 여러 service의 trace 연결

한계:

- 느리고 실패 원인을 좁히기 어렵습니다.
- 모든 입력 조합을 확인할 수 없습니다.
- 실제 환경에서는 상태 변경과 가용성 위험이 있습니다.

## 3. 정적 분석

실행하지 않고 source, bytecode와 configuration을 검사합니다.

잘 찾는 후보:

- 위험한 API 사용
- source에서 sink까지 이어지는 data flow
- secret 형태
- 과도한 permission과 설정 오류
- memory·lifetime 문제

놓치기 쉬운 내용:

- runtime configuration
- framework가 동적으로 만든 route와 middleware 순서
- 실제 identity·network·data 상태
- 업무 규칙과 service 간 object authorization

경고는 candidate입니다. Suppression에도 근거, 적용 version과 재검토 조건을 남깁니다.

## 4. 동적 분석

실행 중인 application에 요청을 보내 response와 상태를 관찰합니다.

- 실제 parser, route와 middleware 확인
- cookie·header·오류 응답 확인
- 입력과 authorization 실패 탐색

한계:

- 도달한 경로만 확인합니다.
- account, data와 crawler coverage에 의존합니다.
- destructive action 위험이 있습니다.
- 원인을 직접 알려 주지는 않습니다.

승인한 요청량과 합성 데이터를 사용합니다.

## 5. Fuzzing과 property-based test

Fuzzing은 많은 입력으로 crash, hang과 불변식 위반을 찾습니다.

필요한 조건:

```text
검사할 함수와 입력 형식
입력 크기 한도
시간·memory·output 한도
crash 판정 기준
중복 crash 분리
최소 재현 입력
회귀 corpus
```

Crash가 보안 취약점인지 별도로 판단해야 합니다. Crash가 없다는 사실도 parser 전체가 안전하다는 증거는 아닙니다.

Property-based test는 예시 하나보다 유지해야 할 성질을 검사합니다.

- 다른 tenant 접근은 명시적인 위임 요구사항이 없으면 거절됨
- parse→serialize 결과가 허용 schema를 보존함
- malformed credential이 권한을 만들지 않음
- 같은 idempotency key의 반복 요청이 유효한 상태 변경을 최대 한 번만 만듦

Generator가 만들지 못한 입력은 여전히 확인하지 못합니다. 전체 입력 공간이나 분산 시스템의 exactly-once 처리를 수학적으로 증명하는 방법은 아닙니다.

## 6. Dependency와 artifact 검사

- 알려진 취약점 database와 version 대조
- license·출처·지원 상태
- SBOM 목록
- artifact의 malware·secret scan
- signature·provenance 검증

한계:

- 아직 공개되지 않은 취약점은 찾지 못합니다.
- 취약 version이 있어도 실제 code path에 도달하지 않을 수 있습니다.
- version 식별이 틀릴 수 있습니다.
- clean scan이 source와 build의 무결성을 증명하지 않습니다.

Signature, provenance, SBOM과 reproducible build가 각각 무엇을 확인하고 무엇을 확인하지 못하는지 구분합니다.

## 7. Configuration과 실제 판정

- network·storage·IAM 규칙
- container·host 설정
- CI workflow permission
- secret·logging 설정
- backup·retention

Text lint만으로 실행 중 effective permission을 증명하지 않습니다. 가능한 경우 실제 test principal과 합성 resource로 allow·deny를 확인합니다.

## 8. 수동 code·design review

도구가 놓치기 쉬운 영역입니다.

- 업무 상태 변경
- service identity와 delegation
- 예외·fallback
- 여러 service의 attack path
- 복구 방법과 incident 권한
- custom authorization helper

“보안 코드”만 보지 않고 requirement가 모든 실제 호출 경로와 실패 처리에 적용되는지 확인합니다.

## 9. 독립적인 평가의 위치

Penetration test는 정해진 시점과 범위에서 수행하는 독립 검증입니다. 개발 과정의 requirement, code review와 regression을 대신하지 않습니다.

좋은 평가는 다음을 포함합니다.

- 명확한 목적과 허가 범위
- 현재 system context와 threat model
- 자동·수동 방법의 조합
- 최소 영향 재현
- finding, 원인, 수정과 retest
- 확인하지 못한 범위와 시간 제한

## 10. Test oracle

약한 판정 기준:

```text
status가 403이면 안전합니다.
```

더 강한 판정 기준:

```text
foreign subject와 resource 조합을 authorization 함수가 거절합니다.
+ response에 foreign data와 불필요한 존재 정보가 없습니다.
+ DB·storage 상태가 바뀌지 않습니다.
+ downstream service를 호출하지 않습니다.
+ audit event가 subject·resource·decision·reason을 기록합니다.
+ 정상 owner 요청은 계속 성공합니다.
```

Fixture 누락, dependency timeout과 process crash 때문에 우연히 요청이 실패한 것을 보안 통제 성공으로 오해하지 않습니다.

## 11. 정상·경계·실패 입력

- owner와 foreign owner
- same role과 other tenant
- revoked·expired·wrong audience credential
- exact expiry
- duplicate·out-of-order·concurrent action
- malformed·oversized·unexpected type
- unavailable dependency와 timeout
- partial write·retry·rollback
- audit sink 실패
- stale cache·old artifact·old credential

## 12. Known-bad 구현으로 검사기 확인

검사기가 실제 잘못된 구현을 거부하는지 봅니다.

- owner 비교 제거
- resource scope를 wildcard로 변경
- path를 문자열 prefix로만 비교
- exact expiry를 허용
- signature 검증 우회
- audit field 누락
- 오류 fallback을 allow로 변경
- detector를 빈 결과로 변경

Production code를 약화해 배포하지 않습니다. 격리된 fixture나 별도 mutation에서 실행합니다.

## 13. 확인 행렬

| Requirement | Unit | Integration | E2E | Static | Manual | Runtime evidence |
|---|---:|---:|---:|---:|---:|---:|
| object authorization | 적용 | 적용 | 적용 | 후보 탐색 | 적용 | allow·deny event |
| job-scoped credential | scope 계산 | 적용 | 적용 | 설정 검사 | 적용 | issue·use event |
| trusted artifact | verifier | 적용 | 적용 | workflow 검토 | 적용 | runtime digest |
| restore integrity | 일부 | restore 실행 | 운영 훈련 | 설정 검토 | 적용 | restore 결과 |

각 칸은 `applicable-pass`, `applicable-fail`, `not-run`, `unknown`, 근거가 있는 `N/A` 중 하나로 기록합니다. 빈 칸을 자동으로 `N/A`로 해석하지 않습니다.

## 14. 근거의 유효 기간

다음 변화가 생기면 이전 결과가 현재 상태를 설명하지 못할 수 있습니다.

- code·configuration 변경
- dependency·tool update
- 새 exploit 공개
- topology·identity 변경
- test 환경 차이
- certificate·credential 만료

Source version, 실행 환경, 시각과 다시 실행할 조건을 남깁니다.

## 완료 질문

- 정적 분석과 동적 분석이 서로 대체할 수 없는 이유는 무엇입니까?
- status code 하나가 약한 판정 기준인 이유는 무엇입니까?
- Fuzzing crash와 security vulnerability는 어떻게 다릅니까?
- Clean dependency scan이 공급망 무결성을 증명하지 못하는 이유는 무엇입니까?
- 검사기 자체를 known-bad 구현으로 확인해야 하는 이유는 무엇입니까?
