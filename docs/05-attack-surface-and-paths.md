# 공격 가능한 지점과 공격 경로

공격 가능한 지점은 공개 port 목록보다 넓습니다. Actor가 관찰하거나 호출하고, 값을 바꾸고, identity를 위임받거나 재사용할 수 있는 모든 지점을 포함합니다. 공격 경로는 한 단계에서 얻은 capability가 다음 단계의 사전 조건이 되는 상태 변화의 연속입니다.

이 문서는 필수 위협 모델을 여러 service와 운영 자원으로 확장할 때 사용하는 보조 자료입니다.

## 1. 여섯 가지 관점

### 외부·내부 호출 지점

- public·internal API
- admin UI와 maintenance endpoint
- message queue, webhook와 file import
- plugin·extension과 package interface
- debug, health와 metrics endpoint

### Identity

- user session
- service account와 workload identity
- CI·deployment identity
- backup·registry·DNS credential
- signing key와 certificate
- emergency account

### 실행 기능

- query, template와 expression interpreter
- shell·process 실행
- plugin, hook와 job runner
- build script와 installer
- parser와 deserializer

### 저장소

- database row와 tenant 구분
- object storage key와 prefix
- local file과 temporary directory
- cache와 search index
- backup과 snapshot
- audit event 저장소

### 배포 경로

- source repository
- dependency resolver
- CI runner와 build 환경
- registry와 artifact
- deployment controller

### 관측과 복구

- log·metric·trace 저장소
- alert 전달
- incident 도구
- backup catalog와 restore credential
- runbook과 status page

관측·복구 자원을 빼면 공격자가 근거와 복구 원본을 함께 손상시키는 경로를 놓칠 수 있습니다.

## 2. 각 호출 지점에서 확인할 판단

```text
누가 호출했습니까?
어떤 identity를 근거로 삼습니까?
어떤 resource와 action을 허용합니까?
입력값이 다른 interpreter·storage·service에서 어떻게 사용됩니까?
결과와 거절 사유는 어디에 남습니까?
```

Gateway가 `X-User-ID`를 덮어쓴다고 가정하더라도 internal service를 직접 호출할 수 있다면 그 header를 그대로 신뢰해서는 안 됩니다.

## 3. capability graph

Host 이름보다 actor가 할 수 있는 일을 node로 둡니다.

```text
public request 전송
일반 user session 사용
report ID 관찰
worker queue에 job 생성
service credential 읽기
다른 object prefix 읽기
release artifact 변경
backup 삭제
```

각 edge에는 다음을 적습니다.

- 필요한 capability
- 사용한 약점이나 잘못된 가정
- 수행한 행동
- 새로 얻는 capability
- 확인할 근거
- 현재 차단 장치

## 4. capability가 넓어지는 대표 방식

### Identity 재사용

Service가 원래 사용자의 권한 대신 자신의 넓은 credential로 downstream을 호출하면 사용자별 resource 범위가 사라질 수 있습니다.

### 데이터가 실행 제어값으로 바뀜

단순 데이터라고 생각한 값이 path, query, template, command, configuration 또는 package 이름으로 해석되면 actor가 실행 동작을 바꿀 수 있습니다.

### 작업과 무관한 기본 권한

Process가 현재 작업에 필요하지 않은 file, socket, metadata와 credential을 읽을 수 있으면 하나의 bug가 더 넓은 영향으로 이어집니다.

### 신뢰받는 배포 경로

Build와 registry는 정상적인 배포 권한으로 code execution을 전달합니다. 이 경로가 손상되면 application vulnerability가 없어도 production에서 code가 실행될 수 있습니다.

### 복구 자원과 운영 권한의 결합

Production write identity가 backup 삭제 권한까지 가지면 운영 데이터 손상이 복구 원본 삭제로 이어질 수 있습니다.

## 5. 공격 경로 예

```text
초기 capability
  일반 사용자 session

1단계
  전제: 다른 report ID를 관찰할 수 있음
  약점: download route가 report owner를 확인하지 않음
  결과: 다른 사용자의 report 내용을 읽을 가능성

2단계
  전제: response에 internal object key가 포함됨
  약점: user-facing API와 worker가 같은 storage 이름 규칙을 사용함
  결과: storage key 형식을 파악함

3단계
  전제: worker 요청을 만들거나 worker credential을 얻음
  약점: credential이 여러 tenant prefix를 읽을 수 있음
  결과: 더 많은 report에 접근할 가능성
```

확인하지 않은 단계는 가설로 둡니다. 한 단계가 반증되면 그 단계를 전제로 하는 전체 경로도 끊깁니다.

## 6. 자동화가 주는 차이

자동화된 actor는 다음 작업을 빠르게 반복할 수 있습니다.

- identifier·parameter·상태 조합 탐색
- 실패 원인을 기록하고 다른 경로 선택
- 여러 service의 약한 신호 결합
- 긴 시간 동안 정해진 한도까지 반복
- 낮은 확률의 race나 timing 조건 재시도

따라서 단일 문자열 차단보다 identity, resource, rate, time과 egress를 실제 판정 지점에서 제한해야 합니다. 탐지는 한 요청뿐 아니라 actor, resource, service와 시간을 연결해야 합니다.

## 7. 공통 차단 지점과 독립된 검사

먼저 여러 경로가 공유하는 지점을 찾습니다.

- identity와 credential 발급
- public 요청을 privileged service로 전달하는 gateway
- artifact를 production release로 승격하는 검증기
- tenant와 resource를 판정하는 중앙 authorization 함수
- audit와 backup처럼 조사·복구에 필요한 저장소

그러나 한 지점만 믿지는 않습니다.

```text
API object authorization
+ job-scoped service credential
+ storage prefix 검사
+ allow·deny event
+ 범위 초과 접근 alert
```

## 8. 목록을 현재 상태로 유지하기

공격 가능한 지점 목록에는 다음을 기록합니다.

```text
component
업무·위험 owner
상태 정본 owner
접근을 판정하는 component
event 보관 담당자
public·internal 노출
사용 identity
입력 지점
데이터 분류
outbound dependency
release source
recovery source
마지막 검토 시각
```

다음 변경이 생기면 목록을 갱신합니다.

- 새 endpoint, queue, bucket와 repository
- 새 role, token과 credential
- public exposure나 network rule 변경
- dependency·package source 변경
- CI·registry·deployment 방식 변경
- backup·logging provider 변경

## 9. 경로를 안전하게 확인하기

가장 위험한 마지막 행동부터 실행하지 않습니다.

1. 각 단계의 source·configuration 근거를 읽습니다.
2. 합성 resource와 test identity를 준비합니다.
3. 영향이 낮은 단계부터 독립적으로 확인합니다.
4. 결과를 synthetic marker로 판정합니다.
5. 실제 중요 자산에 닿기 전에 멈춥니다.
6. allow·deny와 detection event를 보존합니다.
7. 만든 object와 credential을 정리합니다.

각 단계가 별도로 확인돼도 같은 version·시간·identity에서 실제로 이어졌다는 근거가 없다면 `not proven end-to-end`로 남깁니다.

## 10. 수정 뒤 전체 경로 다시 보기

한 finding을 수정한 뒤 다음을 확인합니다.

- 다른 route에서 같은 owner 검사가 빠져 있지 않습니까?
- 다른 service identity나 storage 경로로 우회할 수 있습니까?
- 임시 차단 장치가 실제 요청 지점에 적용됐습니까?
- detector가 수정된 거절과 새로운 우회를 관찰합니까?
- recovery source는 운영 권한과 독립돼 있습니까?

## 완료 질문

- port가 공개되지 않아도 공격 가능한 지점이 될 수 있는 자원은 무엇입니까?
- host 목록보다 capability graph가 유용한 이유는 무엇입니까?
- 데이터가 실행 제어값으로 바뀌는 지점은 어디입니까?
- 한 단계의 합성 검증과 전체 경로 확인은 어떻게 다릅니까?
- 한 지점을 수정한 뒤 전체 경로를 다시 봐야 하는 이유는 무엇입니까?
