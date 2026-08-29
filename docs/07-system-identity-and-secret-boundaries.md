# System identity와 credential의 보안 실패

시스템 보안은 `root`와 일반 사용자만 구분하는 문제가 아닙니다. Process, service, container, CI job, operator와 automated worker가 어떤 identity로 실행되고 어떤 file·network·credential을 사용할 수 있는지 추적해야 합니다.

## 1. 실행 identity 목록

각 workload에 다음을 기록합니다.

```text
실행 user·group
process·container 격리 설정
읽고 쓸 수 있는 filesystem 범위
inbound caller와 outbound destination
사용 가능한 credential
kernel·runtime capability
audit event 저장 위치
```

현재 기능과 무관한 권한이 기본으로 제공되면 application bug 하나가 더 넓은 capability로 이어질 수 있습니다.

## 2. 권한이 넓어지는 지점

권한 상승은 exploit 하나만 뜻하지 않습니다.

- 수정 가능한 service unit·startup script·binary path
- 넓은 `sudo` 규칙과 privileged helper
- privileged socket·daemon API
- setuid, Linux capability와 device 접근
- writable host mount와 container runtime socket
- cloud metadata와 workload credential
- admin API에 도달할 수 있는 network·identity

“현재 user가 root가 될 수 있는가?”보다 다음을 묻습니다.

```text
현재 가진 capability가 어떤 보호 작업으로 바뀔 수 있습니까?
그 전이에 필요한 file·process·credential·network는 무엇입니까?
```

## 3. Service identity와 사용자 위임

Service가 사용자를 대신해 다른 service를 호출할 때 두 identity를 구분합니다.

### 사용자 identity를 downstream에 전달

- 원래 subject와 resource 범위를 유지하기 쉽습니다.
- user token을 그대로 전달할지, downstream 전용으로 제한된 token을 발급할지 결정해야 합니다.
- issuer, audience, lifetime과 delegation chain을 확인합니다.
- 호출한 workload와 실제 사용자 모두를 event에 남깁니다.

### Service identity로 호출

- workload 자체의 identity는 명확해집니다.
- 사용자의 resource 범위가 사라질 수 있습니다.
- broad service credential을 사용하면 confused deputy 문제가 생길 수 있습니다.
- tenant, job와 resource 정보의 출처와 무결성을 별도로 확인해야 합니다.
- 사용자 context가 없을 때 service의 넓은 권한으로 대신 허용하면 안 됩니다.

좋은 판정은 calling service, delegated actor와 실제 권한을 적용할 subject를 구분합니다. 평문 identity header는 신뢰 근거가 아니며, token exchange로 만든 새 token도 원래 actor와 service가 가진 범위를 넘어서는 안 됩니다.

## 4. 최소 권한을 구체적으로 적기

“read-only”만으로는 부족할 수 있습니다.

```text
어느 tenant·collection·prefix입니까?
어떤 action과 field를 읽습니까?
어느 시간 동안 유효합니까?
어느 workload와 network에서 사용할 수 있습니까?
한 번만 사용할 수 있습니까, 반복할 수 있습니까?
```

Job 단위 credential에는 가능한 한 다음 정보가 있어야 합니다.

- 짧은 만료 시간
- 정확한 audience
- tenant·job·resource scope
- 발급 이유와 parent identity
- 폐기 방법과 verifier 반영 지연
- 발급·사용·거절 event

## 5. Secret과 credential

Secret은 노출되면 안 되는 값이고, credential은 identity나 권한을 증명하는 데 쓰는 값입니다. 모든 secret이 credential은 아니지만 credential이 노출되면 즉시 새로운 capability가 생길 수 있습니다.

```text
생성
→ 저장
→ 전달
→ 사용
→ 원문을 남기지 않고 관찰
→ 교체
→ 폐기
→ 삭제
```

각 단계의 담당자와 근거를 기록합니다.

### 폐기의 실제 의미

Credential을 폐기한다는 것은 verifier가 이후 제시된 credential을 더 이상 받아들이지 않도록 만드는 일입니다. 이미 복사된 bytes를 회수하거나, 과거에 만든 session과 완료된 action을 되돌리는 작업은 아닙니다.

Self-contained token을 verifier가 issuer에 확인하지 않는다면 만료 전까지 즉시 폐기되지 않을 수 있습니다. 짧은 lifetime, introspection, denylist, session invalidation과 key 교체 가운데 실제 방식을 정하고 cache까지 반영되는 최대 시간을 측정합니다.

## 6. Secret가 노출되는 곳

- source, configuration과 example
- build argument, image layer와 artifact
- environment와 process 목록
- command line과 shell history
- debug endpoint와 crash dump
- log, trace와 오류 응답
- CI output과 test report
- backup과 snapshot
- client bundle과 mobile package
- support ticket, chat과 clipboard

Scanner가 secret 형태를 찾았다고 현재 유효한 credential로 확정하지 않습니다. 반대로 지금 invalid하다는 이유만으로 과거 노출 기간의 영향이 없었다고 결론 내리지 않습니다.

## 7. 안전한 credential 교체

문자열 한 번 교체하는 것으로 끝나지 않습니다.

```text
새 credential 생성
→ 제한된 consumer에 전달
→ 새 credential 사용 가능 여부 확인
→ traffic 전환
→ 이전 credential 사용 관찰
→ 이전 credential 폐기
→ cache·session·artifact 정리
→ 결과와 rollback 정보 기록
```

완료 기준은 새 값이 만들어졌다는 사실이 아닙니다. 새 credential로 정상 기능이 동작하고, 확인 가능한 모든 verifier가 이전 값을 거절하며, 남은 사용과 파생 session을 처리했는지 확인해야 합니다.

## 8. Container와 sandbox

Container는 자동으로 강한 격리를 제공하지 않습니다. 다음 설정은 영향을 넓힐 수 있습니다.

- privileged mode
- 넓은 Linux capability
- host PID·network namespace
- writable host mount
- container runtime socket
- host secret·cloud metadata 접근
- 제한 없는 process·memory·disk·network

Container 안의 UID 0이 곧 host root인 것은 아니지만, non-root로 실행한다는 사실만으로 host 격리가 증명되지도 않습니다. 실제 namespace, capability, mount, socket과 credential을 확인합니다.

## 9. Internal network는 identity가 아님

다음 가정은 위험합니다.

- source IP만 보고 service를 신뢰함
- gateway가 붙인 header를 direct request에서도 신뢰함
- DNS 이름을 identity 증명으로 사용함
- queue에 message를 만들 수 있으면 모든 command를 허용함
- service mesh의 암호화가 authorization까지 해결한다고 생각함

Network 위치는 보조 정보일 수 있지만 principal과 resource 판정을 대신하지 않습니다.

## 10. Lateral movement

내부 이동은 host 사이 이동만 뜻하지 않습니다.

```text
user session
→ application service identity
→ queue producer 권한
→ worker identity
→ storage credential
→ backup·registry·control plane
```

각 단계에서 새로 얻는 capability, resource scope와 만료 시각을 적습니다. 다음 방법으로 경로를 끊습니다.

- identity 분리
- audience·tenant·job·resource 제한
- ingress·egress 제한
- short-lived credential
- 필요한 시점에만 주는 권한
- 별도 audit 저장소
- 비정상 위임과 scope 사용 탐지

## 11. Emergency access

Emergency account는 평상시 편의를 위한 관리자 계정이 아닙니다.

- 별도 보관과 강한 authentication
- 사용 전 승인 또는 즉시 알림
- 짧은 유효 시간
- 모든 action 기록
- 사용 뒤 credential reset
- 정기적인 복구 훈련

항상 열려 있어도 위험하고, 실제 사고 때 사용할 수 없어도 위험합니다.

## 12. Hardening의 한계

- read-only filesystem은 임의 쓰기를 줄이지만 다른 tenant 데이터 읽기를 막지 않습니다.
- non-root container는 host 권한을 낮추지만 broad storage credential을 제한하지 않습니다.
- firewall은 도달 가능성을 줄이지만 허용된 service 사이의 confused deputy를 막지 않습니다.

각 조치가 어떤 attack-path edge를 실제로 끊는지 적습니다.

## 완료 질문

- service identity와 end-user authorization을 왜 분리해야 합니까?
- read-only credential도 위험할 수 있는 이유는 무엇입니까?
- credential 폐기와 과거 session 정리가 별도 작업인 이유는 무엇입니까?
- container와 internal network를 완전한 신뢰 근거로 볼 수 없는 이유는 무엇입니까?
- hardening 조치가 어떤 공격 단계를 막는지 어떻게 확인합니까?
