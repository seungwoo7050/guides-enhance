# 표준과 외부 자료 지도

이 문서는 본문에서 언급하는 표준, 분류 체계와 도구의 역할을 구분합니다. 항목을 모두 적용하는 것이 목표는 아닙니다. 현재 threat와 requirement에 필요한 판본과 항목을 선택하고, 실제 test·event·finding에 연결합니다.

이 문서의 판본 확인 기준일은 **2026-08-09**입니다. Living catalog와 도구는 학습·검토 시점에 다시 확인해야 합니다.

## 1. 위험 관리와 운영 수명 주기

### NIST Cybersecurity Framework 2.0

- 역할: Govern, Identify, Protect, Detect, Respond, Recover의 상위 outcome 지도
- 사용할 때: threat model, review packet, incident·recovery에서 빠진 활동을 확인할 때
- 한계: 구체적인 구현과 test method를 직접 정하지 않습니다.

### NIST SP 800-61 Rev. 3

- 역할: NIST CSF 2.0에 통합된 incident response 권고
- 사용할 때: 사고 준비, detection, response, recovery와 사후 개선을 정리할 때

## 2. 보안 평가

### NIST SP 800-115

- 역할: 기술 보안 평가의 계획·수행·분석·완화 개요
- 주의: 2008년 문서이므로 현대 cloud, container와 공급망 세부 사항은 최신 자료로 보완합니다.

### OWASP Web Security Testing Guide

- 확인 기준: stable 4.2, 5.0 개발 중
- 역할: web application과 service의 test scenario 설계
- 사용할 때: 판본과 scenario ID를 기록하고 현재 scope에 맞는 항목만 선택합니다.

## 3. 애플리케이션 보안 요구사항

### OWASP Application Security Verification Standard 5.0.0

- 역할: web application의 검사 가능한 기술 요구사항
- 사용할 때: `v5.0.0-<requirement>`처럼 판본과 ID를 함께 기록합니다.
- 한계: 자신의 threat model, 업무 상태와 runtime evidence를 대신하지 않습니다.

### OWASP Cheat Sheet Series

- 역할: 특정 통제를 구현할 때 참고하는 실무 자료
- 사용할 때: 사용 중인 framework·language의 공식 문서와 함께 확인합니다.

## 4. 약점과 공격 행동 분류

### CWE 4.20

- 역할: software·hardware weakness와 공통 원인을 분류합니다.
- 사용할 때: finding 분류, 유사 경로 탐색과 재발 방지
- 주의: CWE ID만으로 severity와 실제 도달 가능성을 판단하지 않습니다.

### CAPEC 3.9

- 역할: attack pattern을 정리한 vocabulary
- 사용할 때: threat brainstorming과 abuse case 작성

### MITRE ATT&CK 19.2

- 기준 snapshot: 2026-08-09에 확인한 19.2
- 역할: 관찰된 adversary behavior, Detection Strategies, Analytics와 Data Components를 분류합니다.
- 사용할 때: attack-path context, detector가 필요한 event와 합성 시나리오를 연결할 때
- 한계: 자신의 system-specific threat model이나 control checklist를 대신하지 않습니다.
- 기록할 내용: catalog snapshot, technique·object version과 실제 event schema mapping

## 5. 취약점 severity

### FIRST CVSS 4.0

- 역할: vulnerability의 Base, Threat와 Environmental 특성을 같은 형식으로 기록합니다.
- 사용할 때: finding severity 근거
- 주의: `Attack Complexity`와 `Attack Requirements`를 구분하고 Vulnerable System·Subsequent System 영향을 각각 기록합니다.
- 한계: Supplemental metric은 상황을 설명하지만 CVSS-BTE 점수를 직접 바꾸지 않습니다. 조직 priority와 risk acceptance를 점수 하나로 대신할 수 없습니다.

## 6. 안전한 개발과 공급망

### NIST SP 800-218 SSDF 1.1

- 상태: Final
- 역할: 안전한 개발 practice를 software development lifecycle에 포함하는 공통 framework

### NIST SP 800-218 Rev. 1 SSDF 1.2

- 확인 기준: 2025-12-17 Initial Public Draft
- 사용할 때: 1.2의 변경 내용을 사용하면 draft임을 표시하고 1.1 Final과 구분합니다.

### SLSA 1.2

- 상태: Approved
- 역할: source·build 공급망 threat, provenance와 verification
- 사용할 때: source에서 artifact까지의 writer, builder와 검증 근거를 정리할 때
- 한계: attestation은 명시된 source·build 성질을 설명하며 artifact의 무취약성과 production 허용을 보장하지 않습니다.

### OpenSSF Scorecard

- 확인 기준 release: 5.5.0
- 분류: versioned 표준이 아니라 도구
- 역할: open-source project의 자동 확인 가능한 공급망 practice 신호
- 한계: 점수가 project 전체와 특정 release의 안전을 보장하지 않습니다.

### CISA Secure by Design

- 확인 기준: 2023-10 refined joint guide
- 분류: 고정된 표준보다 지속해서 갱신되는 initiative
- 역할: 제조자가 안전한 기본값과 vulnerability class 제거를 제품 설계에 포함하도록 요구하는 원칙

## 7. Vulnerability disclosure

### NIST SP 800-216

- 역할: 미국 연방 통제 아래 software·hardware·digital service의 vulnerability disclosure 절차 수립 권고
- 한계: 모든 조직과 관할에 적용되는 법률 자문이나 safe harbor 문구를 대신하지 않습니다.

### `SECURITY.md`

- 역할: repository별 지원 version, private reporting channel과 처리 방법 확인

## 8. 사용 규칙

1. 표준 이름과 판본을 기록합니다.
2. Requirement ID를 인용하면 판본도 함께 적습니다.
3. 해당 자료가 해결하는 문제와 해결하지 못하는 문제를 구분합니다.
4. 자신의 system context와 맞지 않는 항목을 기계적으로 적용하지 않습니다.
5. 표준이나 catalog가 갱신되면 기존 mapping을 다시 확인합니다.
6. 표준, living catalog와 도구를 같은 방식으로 versioning하지 않습니다.
7. CWE·CAPEC·ATT&CK mapping에는 실제 사용한 snapshot을 남깁니다.
8. Tool output은 candidate이며, 실행 version과 configuration을 함께 기록합니다.

## 완료 질문

- ASVS와 WSTG는 각각 어떤 문제에 적합합니까?
- CWE ID가 severity를 자동으로 정하지 못하는 이유는 무엇입니까?
- ATT&CK mapping이 detector coverage를 자동으로 증명하지 못하는 이유는 무엇입니까?
- CVSS 점수와 조직의 처리 priority를 분리해야 하는 이유는 무엇입니까?
- SLSA provenance가 artifact의 무취약성을 보장하지 못하는 이유는 무엇입니까?
