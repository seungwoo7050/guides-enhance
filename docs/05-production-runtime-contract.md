# 운영 실행과 배포 확인

프런트엔드 변경은 `next build`가 성공했다고 끝나지 않습니다. 배포할 결과물이 실제 서버에서 시작되는지, 현재 릴리스를 식별할 수 있는지, 서버 전용 값이 브라우저에 노출되지 않는지, 외부에서 핵심 경로를 확인할 수 있는지까지 확인해야 합니다.

이 문서는 host, container, DNS와 TLS를 구축하는 방법을 다루지 않습니다. 애플리케이션 저장소가 배포 환경에 제공해야 할 실행 방법과 확인 항목을 정리합니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- 운영 빌드와 운영 시작 명령을 독립적으로 실행합니다.
- readiness 확인에 사용할 작은 health 응답을 만듭니다.
- 릴리스 식별자를 health와 오류 기록에 연결합니다.
- 브라우저 공개 값과 서버 전용 환경 변수를 구분합니다.
- 테스트 전용 endpoint가 운영 환경에서 열리지 않는지 확인합니다.
- 운영 서버를 직접 실행하는 smoke test의 시작, 실패와 정리 과정을 설명합니다.

## 배포할 결과물의 실행 방법을 기록합니다

배포 방식과 관계없이 애플리케이션 저장소에는 다음 정보가 있어야 합니다.

- 설치 명령
- 빌드 명령
- 시작 명령
- 필요한 Node.js 버전
- 실행에 필요한 환경 변수
- 브라우저에 공개되는 환경 변수
- listen host와 port 지정 방법
- health URL
- 종료 신호를 받은 뒤 끝나야 할 시간
- 릴리스 식별자 주입 방법
- smoke test 명령

예시는 다음과 같습니다.

```text
build   npm run build
start   npm run start -- --hostname 127.0.0.1 --port <port>
health  GET /api/health
smoke   npm run smoke
```

Docker image 생성과 registry 배포를 인프라 저장소가 담당하더라도, 어떤 명령과 환경 변수로 애플리케이션을 실행해야 하는지는 애플리케이션 저장소가 제공해야 합니다.

## Health 응답은 작고 안정적으로 유지합니다

외부 배포 도구가 사용할 health 응답은 필요한 값만 포함합니다.

```json
{
  "status": "ok",
  "release": "local"
}
```

응답에는 `Cache-Control: no-store`를 둡니다. 다음 정보는 health에 넣지 않습니다.

- 환경 변수 전체
- filesystem path
- 모든 dependency version
- stack trace
- database credential
- token과 cookie
- 내부 hostname

단순한 프로세스 생존 여부와 외부 dependency 준비 여부를 따로 확인해야 한다면 endpoint를 분리할 수 있습니다. 외부 dependency가 없는 작은 애플리케이션에서는 요청을 처리할 수 있는지와 현재 릴리스만 반환해도 충분합니다.

공개 필드를 계속 늘리면 배포 script와 monitoring 도구가 애플리케이션 내부 구현에 의존하게 됩니다. 필요한 값만 안정적으로 유지합니다.

## 테스트 전용 endpoint를 운영에서 닫습니다

E2E 데이터를 초기화하는 endpoint는 편리하지만 운영 환경에서 열리면 데이터를 바꾸는 숨은 제어 경로가 됩니다.

다음 두 조건을 모두 요구할 수 있습니다.

1. `NODE_ENV=test` 또는 별도의 명시적인 테스트 모드가 켜져 있습니다.
2. 요청 헤더의 token이 서버 환경 변수의 token과 정확히 일치합니다.

하나라도 맞지 않으면 `403` 대신 `404`를 반환해 endpoint의 존재를 드러내지 않는 방법을 선택할 수 있습니다.

```ts
const testMode =
  process.env.NODE_ENV === "test" ||
  process.env.PLAYWRIGHT === "1";

const expected = process.env.CATALOG_TEST_RESET_TOKEN;
const supplied = request.headers.get("x-catalog-test-token");

if (!testMode || !expected || supplied !== expected) {
  return Response.json({ code: "not_found" }, { status: 404 });
}
```

이 방식은 일반적인 admin API를 대신하지 않습니다. 테스트 전용 route가 운영 빌드에 포함되어야 한다면 기능을 작게 유지하고, 운영 설정에서 닫혀 있는지 단위 테스트와 smoke test로 확인합니다.

## 현재 실행 중인 릴리스를 찾을 수 있게 합니다

장애가 발생했을 때 다음 질문에 답할 수 있어야 합니다.

```text
현재 어떤 source와 build가 실행 중입니까?
```

일반적인 연결 방식은 다음과 같습니다.

```text
source commit
→ build 또는 image 식별자
→ health 응답과 서버 log
→ 브라우저 오류 보고서
```

`APP_RELEASE` 같은 환경 변수에 commit SHA, image digest 또는 release manifest id를 넣을 수 있습니다. 값이 없을 때는 로컬 실행임을 분명히 나타내는 기본값을 사용합니다.

사용자 화면에 내부 commit 전체를 노출할 필요는 없습니다. 고객 지원 담당자가 서버 log와 연결할 수 있는 짧고 안전한 식별자를 보여 줄 수 있습니다.

## 환경 변수의 공개 범위를 구분합니다

### 서버 전용

- API credential
- signing key
- private service URL
- database credential
- 테스트 초기화 token
- 공개할 필요가 없는 release metadata

### 브라우저 공개

- 공개 analytics site id
- 브라우저가 호출할 공개 origin
- 사용자에게 보여도 되는 feature flag

공개 prefix가 붙은 값은 브라우저 bundle이나 응답에서 읽힐 수 있다고 가정합니다. 변수 이름에 `SECRET`이 포함되어도 보호되지 않습니다. Client Component가 불러오는 module에서 서버 전용 값을 읽지 않습니다.

## 비밀값 canary로 노출을 검사합니다

Smoke test가 시작할 때 예측하기 어려운 문자열을 서버 전용 환경 변수에 넣습니다.

```text
server-only-<random value>
```

그 뒤 다음 응답과 파일에서 같은 문자열을 찾습니다.

- health 본문
- root HTML
- 첫 route가 불러온 JavaScript 응답 본문
- 필요하다면 공개 JSON endpoint

문자열이 발견되면 서버 전용 값이 응답이나 브라우저 bundle에 들어간 것입니다.

이 검사가 모든 비밀값 노출을 증명하지는 않습니다. 하지만 실수로 `process.env` 전체를 직렬화하거나 서버 module을 Client Component가 불러오는 회귀를 빠르게 찾을 수 있습니다.

## 운영 smoke test가 확인할 항목

Smoke test는 기존 개발 서버에 의존하지 않고 새 운영 프로세스를 직접 시작해야 합니다.

```text
사용 가능한 port 선택
→ 운영 프로세스 시작
→ 제한 시간 안에서 health 준비 확인
→ health 필드와 release 확인
→ root HTML의 핵심 요소 확인
→ 주요 API의 최소 응답 형식 확인
→ 비밀값 canary 비노출 확인
→ 프로세스 종료
→ 남은 하위 프로세스 확인
```

모든 네트워크 요청에는 시간 제한을 둡니다. 프로세스가 시작되지 않거나 health가 준비되지 않으면 stdout과 stderr를 제한된 크기로 보존해 오류 메시지에 포함합니다.

검사 중 실패해도 `finally`에서 프로세스를 종료합니다. 기능 검사와 프로세스 정리가 모두 실패했다면 하나를 숨기지 않고 두 오류를 함께 보고합니다.

## 하위 프로세스까지 종료합니다

`next start`를 wrapper script나 패키지 관리자를 통해 실행하면 하위 프로세스가 한 단계 더 생길 수 있습니다. Unix 계열에서는 process group에 신호를 보내고, 제한 시간 안에 끝나지 않으면 강제 종료할 수 있습니다.

```text
SIGTERM 전송
→ 일정 시간 대기
→ 여전히 실행 중이면 SIGKILL 전송
→ 종료 여부 확인
```

Windows에서는 process group 처리 방식이 다르므로 `child.kill()` 또는 platform에 맞는 process tree 종료 방법을 사용합니다.

Smoke test가 성공했더라도 port를 계속 점유하는 프로세스가 남으면 검증 script가 올바르지 않습니다.

## 애플리케이션과 인프라가 맡을 일을 구분합니다

### 애플리케이션 저장소가 제공할 내용

- 설치, 빌드와 시작 명령
- Node.js와 실행 환경 변수 요구 사항
- listen host와 port 지정 방법
- health 응답 형식
- 릴리스 식별자
- 브라우저 E2E와 standalone smoke test
- 서버 전용 값이 클라이언트 결과물에 포함되지 않는 검사
- 오류 기록에 넣을 request id와 release id

### 인프라가 제공할 내용

- host와 container runtime
- image registry와 배포 승인
- DNS, certificate와 reverse proxy
- 중앙 log, metric와 trace 저장소
- alert와 on-call 연결
- backup, restore와 host rebuild
- network rule과 secret 배포 시스템

두 영역은 문서화된 명령과 HTTP 응답으로 연결합니다. 인프라가 애플리케이션 내부 module을 호출하거나, 애플리케이션이 특정 배포 platform의 내부 API에 불필요하게 의존하지 않게 합니다.

## 운영 실패를 좁히는 순서

| 증상 | 먼저 확인할 항목 |
| --- | --- |
| 프로세스 시작 실패 | Node.js, 시작 명령, 작업 디렉터리, 환경 변수, port |
| health `404` | route 생성 여부, base path, 배포된 release |
| health 성공 후 화면 실패 | page 데이터, client asset, runtime 설정 |
| HTML 성공 후 interaction 실패 | JavaScript asset, CSP, hydration, 브라우저 오류 |
| release가 예상과 다름 | 잘못된 배포 대상, 오래된 instance, cache |
| smoke 종료 후 프로세스가 남음 | signal 전달, process group, start wrapper |

health 성공을 전체 사용자 기능 성공으로 해석하지 않습니다. health는 프로세스 준비 여부를 확인하고, 핵심 사용자 기능은 별도의 브라우저 E2E로 확인합니다.

## 적용 완료 기준

실제 프로젝트 디렉터리에서 다음 내용을 확인합니다.

- 고정 설치, 운영 빌드와 운영 시작 명령이 문서화되어 있습니다.
- 운영 프로세스가 고유 port에서 시작됩니다.
- health는 필요한 필드만 반환하고 `no-store`를 포함합니다.
- health의 release가 실행 프로세스에 넣은 값과 같습니다.
- 테스트 전용 endpoint는 테스트 모드와 token 없이는 동작하지 않습니다.
- 서버 전용 canary가 health, HTML와 첫 JavaScript 응답에 없습니다.
- smoke test의 모든 네트워크 요청에 시간 제한이 있습니다.
- 성공과 실패 모두 하위 프로세스를 정리합니다.
- 운영 브라우저 E2E의 핵심 사용자 기능이 통과합니다.

이 항목에서 실패하면 증상이 처음 나타난 단계부터 확인합니다. 전체 배포 환경을 한꺼번에 바꾸지 않습니다.
