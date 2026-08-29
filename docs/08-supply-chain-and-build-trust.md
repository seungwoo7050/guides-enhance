# 소프트웨어 공급망과 빌드 신뢰

Production이 실행하는 code는 source만으로 결정되지 않습니다.

```text
source
+ dependency
+ build tool
+ CI identity
+ build 환경
+ artifact registry
+ deployment 설정
+ runtime configuration
```

이 문서는 dependency, CI, artifact와 release를 집중적으로 검토할 때 사용하는 심화 자료입니다.

## 1. 지켜야 할 상태

- source 변경은 승인된 identity와 review를 거칩니다.
- build input은 version과 digest로 식별할 수 있습니다.
- build process는 의도하지 않은 dependency와 secret을 사용하지 않습니다.
- artifact가 어느 source와 builder에서 만들어졌는지 추적할 수 있습니다.
- registry에서 받은 bytes가 승인된 digest와 같습니다.
- deployment는 검증을 통과한 artifact만 실행합니다.
- 손상된 digest와 signer를 여러 실행 지점에서 거절할 수 있습니다.

## 2. Source에서 runtime까지 연결하기

```text
개발자 identity
→ source repository
→ review·merge 규칙
→ CI workflow
→ runner와 build 환경
→ dependency source
→ artifact
→ registry
→ release manifest
→ production runtime
```

각 단계에서 다음을 확인합니다.

- 누가 쓰고 승인할 수 있습니까?
- 어떤 credential을 사용합니까?
- 입력과 출력이 변경 불가능한 식별자를 가집니까?
- build·promotion·deployment 결과를 무엇으로 확인합니까?
- 이전 안전한 상태로 돌아갈 수 있습니까?

## 3. Source integrity

- protected branch와 review 규칙
- required check를 실행하는 주체와 bypass 권한
- maintainer·bot·app token scope
- workflow file 변경 승인
- tag·release 생성 권한
- force push와 history rewrite 제한
- generated·vendored code의 원본

Signed commit 하나는 해당 commit의 서명을 확인하는 근거일 뿐, review, CI, dependency와 artifact 전체를 자동으로 보장하지 않습니다.

## 4. Dependency 신뢰

Lockfile이 있어도 다음 문제가 남습니다.

- package maintainer 또는 source registry 손상
- 비슷한 package 이름
- transitive dependency
- install script와 build plugin
- registry proxy와 mirror가 다른 bytes를 반환함
- 삭제·교체된 artifact
- 알려진 취약점과 지원 종료
- 출처를 알 수 없는 binary

최소 기록 항목:

```text
name·version·digest
source registry·repository
transitive path
runtime·build·test 용도
알려진 취약점
지원 상태
update owner
```

Dependency를 추가할 때 실제 필요한 capability와 더 단순한 대안이 있는지 확인합니다.

## 5. Build 환경

대표 위험:

- mutable base image와 toolchain
- host의 넓은 credential
- shared runner의 남은 file과 process
- build 중 임의 network download
- untrusted PR code와 release secret의 동시 사용
- build cache 오염
- output에 포함된 secret과 debug file

대응:

- 일회성·격리 runner
- job에 필요한 최소 credential
- input digest 고정
- network destination 제한
- build 결과와 사용한 input 목록 보존
- untrusted contribution과 release build 분리

같은 환경에서 다시 같은 결과가 나오는 repeatable build와 독립된 환경에서 같은 bytes가 나오는 reproducible build를 구분합니다. 결과가 같아도 source 자체가 안전하거나 builder가 손상되지 않았다는 사실까지 증명하지는 않습니다.

## 6. Artifact identity

Tag와 filename은 바뀔 수 있습니다. Release는 immutable digest와 metadata로 식별합니다.

```text
artifact digest
source revision
workflow와 builder identity
build time
platform
SBOM
provenance
signature 또는 attestation
검증 결과
```

Signature는 특정 key가 특정 bytes에 유효한 서명을 만들었다는 사실을 보여 줍니다. Signer가 승인된 builder인지, source가 review됐는지, artifact에 취약점이 없는지까지 자동으로 보장하지 않습니다.

## 7. SBOM과 provenance

### SBOM

Artifact에 포함된 component를 조사하는 목록입니다. 누락과 오식별이 있을 수 있고, runtime download와 외부 service는 포함되지 않을 수 있습니다. Component가 목록에 있다는 사실만으로 취약 code에 실제로 도달할 수 있는지는 알 수 없습니다.

### Provenance

Artifact가 어떤 source, builder, parameter와 materials로 만들어졌는지 설명하는 statement입니다. Statement를 만든 identity와 build 환경이 신뢰 대상입니다. 문법적으로 유효해도 거짓 정보, 손상된 builder와 기록되지 않은 input 가능성은 남습니다.

## 8. Registry와 promotion

- push, delete와 retag 권한 분리
- immutable artifact와 보존 기간
- scan 결과의 범위와 한계
- environment promotion 때 다시 build하는지 여부
- release manifest와 runtime digest 비교
- 차단한 digest와 폐기한 signer의 배포 거절
- rollback artifact 보존
- registry 손상 때 사용할 복구 원본

Registry에서 artifact를 삭제해도 cache, mirror와 이미 실행 중인 instance가 사라지지는 않습니다. 차단한 digest와 signer를 registry, promotion verifier, deployment controller와 runtime inventory에 전파하고 실행 중 instance를 교체해야 합니다.

## 9. CI credential

CI는 repository, registry, cloud, secret store와 signing service를 연결하므로 영향이 큽니다.

- 장기 static secret보다 short-lived workload identity를 사용합니다.
- repository, branch, environment와 audience를 제한합니다.
- PR code가 release secret을 읽지 못하도록 실행 환경을 나눕니다.
- 발급·사용·거절 event를 남깁니다.

## 10. 공급망 사고

다음 순서로 영향을 조사합니다.

1. 영향 source·version·artifact digest
2. build·publish identity와 시각
3. artifact를 실행한 release와 환경
4. runtime에서 artifact가 가진 capability
5. 접근할 수 있던 credential과 데이터
6. log·audit·backup의 신뢰 상태
7. revoke·rollback·rebuild 범위
8. clean source·builder·credential로 신뢰 재설정

Package version을 올리는 것만으로 끝나지 않을 수 있습니다. Builder와 signing key가 손상됐다면 새 artifact도 같은 경로로 만들면 안 됩니다.

## 완료 질문

- source가 안전해도 artifact가 손상될 수 있는 지점은 어디입니까?
- lockfile, signature와 provenance가 각각 보장하지 못하는 것은 무엇입니까?
- PR build와 release build를 분리해야 하는 이유는 무엇입니까?
- SBOM과 provenance는 어떻게 다릅니까?
- registry에서 artifact를 삭제한 뒤에도 추가 작업이 필요한 이유는 무엇입니까?
