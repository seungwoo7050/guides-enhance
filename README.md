# 사이버보안 분석·검증·대응

이 저장소는 보안을 도구 이름이나 공격 기법 목록으로 배우지 않습니다. 시스템이 지켜야 할 상태를 정하고, 그 상태가 깨질 수 있는 조건을 찾은 뒤, 허가된 범위에서 최소한의 증거로 확인하는 방법을 다룹니다. 확인한 문제는 요구사항, 수정, 회귀 검사, 탐지와 복구까지 연결합니다.

```text
보호할 상태와 근거를 정합니다.
→ 자산·행위자·신뢰 지점을 기준으로 위협을 작성합니다.
→ 허가된 합성 환경에서 필요한 만큼만 검증합니다.
→ 원인을 수정하고 정상·경계·실패 사례를 다시 검사합니다.
→ 거절 event와 alert로 같은 시도를 관찰합니다.
→ 사고가 발생했을 때 신뢰할 수 있는 상태를 다시 만듭니다.
```

이 과정은 프로그래밍 입문이나 운영체제·네트워크 입문을 대신하지 않습니다. 기존 애플리케이션과 서비스 코드를 읽고, JSON·Markdown을 수정하며, Python 테스트를 실행할 수 있는 개발자를 대상으로 합니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
└── exercises/
```

- `docs/`: 보안 상태를 판단하고 검증·수정·탐지·복구하는 데 필요한 개념과 판단 기준을 설명합니다.
- `exercises/`: 문서의 핵심 내용을 완성된 독립 프로젝트로 확인합니다.

## 완료 후 갖춰야 할 능력

전체 필수 경로를 마치면 다음 작업을 수행할 수 있어야 합니다.

1. 보안 목표를 주체·자원·행동·허용 상태가 드러나는 문장으로 작성합니다.
2. 사실, 가설과 결론을 구분하고 각 근거가 보장하는 범위를 설명합니다.
3. 자산, 행위자의 현재 능력, 신뢰해야 하는 지점과 상태 변화를 연결해 위협을 작성합니다.
4. 평가 대상, identity, 허용 행동, 요청량과 중단 조건을 문서로 고정한 뒤 합성 데이터로 최소한만 검증합니다.
5. 인증과 object authorization, service identity와 사용자 권한, credential 발급·만료·폐기를 구분합니다.
6. 위협을 검증 가능한 요구사항으로 바꾸고 정상·경계·실패 사례와 독립된 판정 기준을 만듭니다.
7. 증상만 막는 수정과 공통 원인을 제거하는 수정을 구분하고, 유사한 코드 경로와 기존 credential·파생 데이터를 함께 검토합니다.
8. actor, resource, decision, reason과 correlation을 포함한 event를 설계하고 중복·지연·누락이 탐지에 주는 영향을 설명합니다.
9. 사고 중 사실·가설·결정·조치를 분리하고, containment·eradication·recovery가 각각 무엇을 완료해야 하는지 설명합니다.

## 필수 문서

### 1. 보안 판단과 안전한 검증

- [`01-security-state-and-evidence.md`](docs/01-security-state-and-evidence.md)
- [`02-assets-trust-boundaries-and-threat-models.md`](docs/02-assets-trust-boundaries-and-threat-models.md)
- [`03-scope-authorization-and-rules-of-engagement.md`](docs/03-scope-authorization-and-rules-of-engagement.md)

### 2. 실제 실패 형태

- [`04-risk-vulnerability-and-prioritization.md`](docs/04-risk-vulnerability-and-prioritization.md)
- [`06-application-boundary-failures.md`](docs/06-application-boundary-failures.md)
- [`07-system-identity-and-secret-boundaries.md`](docs/07-system-identity-and-secret-boundaries.md)

### 3. 요구사항, 검사와 수정

- [`10-security-requirements-and-design-invariants.md`](docs/10-security-requirements-and-design-invariants.md)
- [`11-security-testing-and-assurance.md`](docs/11-security-testing-and-assurance.md)
- [`12-remediation-hardening-and-regression.md`](docs/12-remediation-hardening-and-regression.md)

### 4. 탐지와 복구

- [`13-telemetry-detection-and-investigation.md`](docs/13-telemetry-detection-and-investigation.md)
- [`14-incident-response-and-recovery.md`](docs/14-incident-response-and-recovery.md)

전체 순서와 실습 시점은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 정리되어 있습니다.

## 선택 문서

다음 문서는 필수 경로를 마친 뒤 필요에 따라 읽습니다.

- [`05-attack-surface-and-paths.md`](docs/05-attack-surface-and-paths.md): 여러 위협을 capability graph와 공통 차단 지점으로 확장합니다.
- [`08-supply-chain-and-build-trust.md`](docs/08-supply-chain-and-build-trust.md): source, dependency, CI, artifact와 runtime 사이의 신뢰를 다룹니다.
- [`09-vulnerability-validation-and-reporting.md`](docs/09-vulnerability-validation-and-reporting.md): finding의 근거, 최소 재현, 보고와 retest를 더 자세히 다룹니다.
- [`15-security-review-and-release-decision.md`](docs/15-security-review-and-release-decision.md): release 전 근거 검토와 잔여 위험 결정을 다룹니다.
- [`90-standards-map.md`](docs/90-standards-map.md): 본문에서 언급하는 표준과 분류 체계의 역할을 정리합니다.

## 필수 실습

### [`ledgerlab-policy`](exercises/ledgerlab-policy/README.md)

합성 보고서와 작업자 객체에 대한 접근 가능 여부를 판정하는 Python 라이브러리입니다. 다음 내용을 하나의 구현에서 확인합니다.

- 소유자·tenant·완료 상태를 함께 확인하는 보고서 접근 판정
- service identity, job, 만료 시각과 폐기 여부를 확인하는 credential 판정
- 문자열의 일부가 아니라 path segment를 비교하는 객체 범위 확인
- 확인할 수 없는 상태의 기본 거절
- 입력 상태를 바꾸지 않는 판정 함수
- 안정된 `reason_code`와 조사 가능한 authorization event
- 중복과 입력 순서에 영향을 받지 않는 correlation 단위 alert
- 정상 기능과 잘못된 구현을 함께 구분하는 테스트

## 권장 진행 순서

```text
상태·근거·위협·허가
→ 애플리케이션과 identity 실패 형태
→ ledgerlab-policy의 판정 기능 구현·검토
→ 위험 판단·요구사항·telemetry
→ detector 구현·검토
→ test oracle과 회귀 검사
→ 수정·사고 대응·복구
→ 최종 설명과 전체 테스트
```

문서를 모두 읽은 뒤 실습을 시작하지 않습니다. `06`, `07`까지 읽으면 `ledgerlab-policy`의 접근 판정 부분을 먼저 확인합니다. `10`, `13`까지 읽은 뒤 detector를 확인하고, `11`을 읽은 뒤 전체 테스트를 실행합니다.

## 완료 기준

다음 질문에 코드와 테스트 결과를 근거로 답할 수 있으면 필수 경로를 완료한 것으로 봅니다.

- 다른 사용자의 보고서와 다른 job의 객체를 왜 거절해야 합니까?
- 판정에 필요한 actor, tenant, job 또는 현재 시각이 없을 때 왜 허용하면 안 됩니까?
- `job-81`과 `job-81x`를 문자열 prefix로 비교하면 어떤 문제가 생깁니까?
- 만료 시각과 현재 시각이 같을 때 어떤 결과가 나와야 합니까?
- 판정 함수가 입력 상태를 바꾸지 않았음을 어떻게 확인합니까?
- 사람이 읽는 오류 문장보다 `reason_code`가 탐지에 적합한 이유는 무엇입니까?
- 같은 event가 중복되거나 순서가 달라져도 alert 결과가 같아야 하는 이유는 무엇입니까?
- 예상 밖의 허용이 발견됐을 때 즉시 제한, 원인 제거와 안전한 상태 복구를 어떻게 구분합니까?

별도의 외부 프로젝트나 추가 Capstone은 완료 조건이 아닙니다. 필수 문서와 `ledgerlab-policy`만으로 이 저장소의 학습 단위가 끝납니다.
