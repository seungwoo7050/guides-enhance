# 운영 실행과 배포 확인

프런트엔드 변경은 `next build`가 성공했다고 끝나지 않습니다. **빌드 결과물이 실제 운영 방식으로 시작되는지**, **현재 실행 중인 릴리스를 식별할 수 있는지**, **서버 전용 값이 브라우저에 노출되지 않는지**, **외부에서 핵심 경로를 확인할 수 있는지**, **종료 시 프로세스가 남지 않는지**까지 확인해야 합니다.

운영 검증은 다음 단계를 서로 다른 계약으로 봅니다.

```text
설치
→ 같은 dependency graph를 재현할 수 있는가

build
→ 배포 가능한 산출물을 만들 수 있는가

start
→ 그 산출물이 실제 운영 방식으로 실행되는가

health/readiness
→ 외부 요청을 받을 준비가 되었는가

smoke
→ 최소한의 핵심 경로가 실제 서버에서 동작하는가

browser E2E
→ 사용자 기능이 실제 브라우저에서 동작하는가
```

한 단계의 성공이 다음 단계를 자동으로 보장하지 않습니다.

이 문서는 host, container, DNS와 TLS를 구축하는 방법을 다루지 않습니다. 애플리케이션 저장소가 배포 환경에 제공해야 할 **실행 계약(runtime contract)**과 이를 검증하는 방법을 정리합니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- 운영 빌드와 운영 시작 명령을 독립적으로 실행합니다.
- 저장소가 배포 환경에 제공해야 할 runtime contract를 설명합니다.
- process 생존 여부와 readiness를 구분하고 적절한 health 응답을 설계합니다.
- 릴리스 식별자를 health, 서버 log와 오류 기록에 연결합니다.
- 브라우저 공개 값과 서버 전용 환경 변수를 구분합니다.
- 서버 전용 값의 노출을 canary로 탐지합니다.
- 테스트 전용 endpoint가 운영 환경에서 열리지 않는지 확인합니다.
- 운영 서버를 직접 실행하는 smoke test의 시작, 준비 확인, 실패와 정리 과정을 설명합니다.
- 종료 신호와 하위 프로세스 정리를 검증합니다.
- 애플리케이션 저장소와 인프라가 맡아야 할 책임을 구분합니다.

## 배포할 결과물의 실행 방법을 기록합니다

배포 방식과 관계없이 애플리케이션 저장소에는 최소한 다음 정보가 있어야 합니다.

- dependency 설치 명령
- 운영 빌드 명령
- 운영 시작 명령
- 필요한 Node.js 버전
- 실행에 필요한 환경 변수
- 브라우저에 공개되는 환경 변수
- listen host와 port 지정 방법
- health 또는 readiness URL
- 종료 신호를 받은 뒤 정상 종료를 기다릴 최대 시간
- 릴리스 식별자 주입 방법
- smoke test 명령
- 필요한 경우 database migration 또는 bootstrap 순서

예시는 다음과 같습니다.

```text
install npm ci
build   npm run build
start   npm run start -- --hostname 127.0.0.1 --port <port>
health  GET /api/health
smoke   npm run smoke
```

이 명령은 예시입니다. 실제 저장소에서는 `package.json`, Next.js 설정, Dockerfile과 배포 구성을 기준으로 사용합니다.

Docker image 생성과 registry 배포를 인프라 저장소가 담당하더라도 다음 질문의 답은 애플리케이션 저장소가 제공해야 합니다.

```text
어떤 Node.js가 필요합니까?
어떤 명령으로 build합니까?
어떤 명령으로 실행합니까?
어떤 환경 변수가 필수입니까?
어느 host/port에 listen합니까?
언제 요청을 받을 준비가 되었다고 판단합니까?
어떻게 정상 종료합니까?
현재 실행 중인 release를 어떻게 확인합니까?
```

이 정보가 문서화되어 있지 않으면 배포 시스템이 애플리케이션 내부 구현을 추측하게 됩니다.

## build와 start를 별도 계약으로 봅니다

`next build` 성공은 배포 산출물을 만들 수 있다는 뜻입니다. 실제 start가 성공한다는 뜻은 아닙니다.

다음 문제는 build 이후에 드러날 수 있습니다.

- 시작 명령이 잘못되어 있음
- 필요한 runtime 환경 변수가 없음
- 지정한 port를 열지 못함
- 작업 디렉터리가 예상과 다름
- standalone output을 잘못 실행함
- 파일 또는 디렉터리 권한이 잘못됨
- startup 시 외부 dependency 연결에 실패함

따라서 CI나 smoke test에서 가능하면 다음 두 단계를 분리합니다.

```text
build 성공
→ 산출물 생성 확인

start 성공
→ 실제 프로세스 시작
→ health 또는 readiness 성공 확인
```

## 실제 배포 방식과 같은 시작 명령을 사용합니다

운영 서버 검증의 핵심은 특정 명령 문자열을 사용하는 것이 아니라 **배포 환경과 같은 방식으로 산출물을 실행하는 것**입니다.

프로젝트에 따라 다음과 같은 시작 방식이 있을 수 있습니다.

```text
next start

standalone output
node .next/standalone/server.js

container entrypoint

platform 전용 command
```

따라서 smoke test가 `next start`를 사용한다고 해서 실제 배포가 standalone output을 사용한다면 완전히 같은 runtime을 검증한 것이 아닐 수 있습니다.

먼저 실제 배포 artifact와 start command를 확인합니다.

## listen host와 port를 외부에서 지정할 수 있게 합니다

운영 검증에서는 이미 다른 프로세스가 사용하는 port와 충돌하지 않도록 고유한 port를 사용할 수 있어야 합니다.

예를 들어 다음처럼 외부에서 값을 주입할 수 있어야 합니다.

```text
HOSTNAME=127.0.0.1
PORT=43127
```

구체적인 환경 변수 이름이나 CLI option은 프로젝트에 따라 다를 수 있습니다.

중요한 조건은 다음과 같습니다.

```text
smoke test
→ 사용 가능한 port 선택
→ 그 port로 운영 서버 실행
→ 같은 port로 health 요청
```

port가 코드에 고정되어 있으면 병렬 CI, 로컬 테스트와 여러 instance 실행이 어려워집니다.

## Health 응답은 작고 안정적으로 유지합니다

외부 배포 도구나 smoke test가 사용할 health 응답은 필요한 값만 포함합니다.

예를 들어 다음 정도면 충분할 수 있습니다.

```json
{
  "status": "ok",
  "release": "local"
}
```

health endpoint의 목적은 애플리케이션 내부 구조를 공개하는 것이 아니라 외부 시스템이 **현재 프로세스 상태를 안정적으로 판단할 수 있게 하는 것**입니다.

따라서 응답 schema는 작고 장기간 안정적으로 유지합니다.

## liveness와 readiness를 구분합니다

"health"라는 이름 아래 서로 다른 의미를 섞지 않습니다.

```text
liveness
→ 프로세스가 살아 있고 요청 처리 loop가 동작하는가

readiness
→ 실제 사용자 요청을 받을 준비가 되었는가
```

예를 들어 서버 프로세스는 살아 있지만 startup migration 또는 필요한 dependency 연결이 아직 준비되지 않았을 수 있습니다.

이 경우 다음처럼 구분할 수 있습니다.

```text
/live
→ 프로세스가 살아 있으면 200

/ready
→ 사용자 요청 처리에 필요한 준비가 완료되어야 200
```

작은 애플리케이션에서 별도 구분이 불필요하다면 하나의 endpoint를 사용할 수 있습니다. 다만 그 endpoint가 무엇을 의미하는지는 명시해야 합니다.

## readiness에 무엇을 넣을지 신중하게 결정합니다

readiness에서 모든 외부 dependency를 검사하면 실제 사용자 요청 가능 여부를 더 정확히 알 수 있습니다.

하지만 dependency 하나가 일시적으로 느려질 때 health 요청도 느려지거나 전체 instance가 준비되지 않은 것으로 판단될 수 있습니다.

따라서 다음 질문을 기준으로 결정합니다.

```text
이 dependency가 없으면 핵심 요청을 전혀 처리할 수 없는가?
health에서 직접 검사해야 하는가?
startup 단계에서 이미 검증했는가?
health 요청마다 검사하면 비용이 큰가?
```

예를 들어 database가 반드시 필요한 서비스라면 readiness에서 최소 연결 가능 여부를 확인할 수 있습니다. 반대로 선택적 analytics 서비스가 실패했다고 애플리케이션 전체를 not ready로 만들 필요는 없을 수 있습니다.

health에 dependency 상태를 추가할수록 외부 monitoring과 배포 도구가 그 schema에 의존하게 되므로 필요한 값만 유지합니다.

## health는 cache되지 않게 합니다

health는 현재 실행 상태를 확인하는 endpoint이므로 오래된 응답이 재사용되면 안 됩니다.

예를 들어 다음 header를 사용할 수 있습니다.

```http
Cache-Control: no-store
```

중간 cache, browser 또는 CDN이 이전 release의 health 응답을 재사용하지 않도록 합니다.

프로젝트가 별도의 cache layer를 사용한다면 health route가 그것을 우회하는지도 확인합니다.

## health에 민감한 정보를 넣지 않습니다

다음 정보는 health 응답에 포함하지 않습니다.

- 전체 환경 변수
- filesystem path
- stack trace
- database credential
- API token
- cookie
- signing key
- 내부 hostname
- 모든 dependency version
- 민감한 infrastructure topology
- 사용자 데이터

다음처럼 구현 세부사항을 과도하게 공개하지 않습니다.

```json
{
  "status": "ok",
  "databaseUrl": "...",
  "cwd": "/app/current",
  "environment": { "...": "..." }
}
```

health는 debugging endpoint가 아닙니다.

## 테스트 전용 endpoint를 운영에서 닫습니다

E2E 데이터를 초기화하거나 fixture를 만드는 endpoint는 테스트 자동화에 편리합니다.

예를 들어 다음 기능이 있을 수 있습니다.

```text
POST /api/test/reset
POST /api/test/seed
```

하지만 이런 route가 운영에서 활성화되면 일반 사용자 API와 별개의 숨은 데이터 변경 경로가 됩니다.

따라서 **테스트 모드**와 **인증용 비밀값**을 동시에 요구하도록 설계할 수 있습니다.

```ts
const testMode =
  process.env.NODE_ENV === "test" ||
  process.env.PLAYWRIGHT === "1";

const expected =
  process.env.CATALOG_TEST_RESET_TOKEN;

const supplied =
  request.headers.get(
    "x-catalog-test-token",
  );

if (
  !testMode ||
  !expected ||
  supplied !== expected
) {
  return Response.json(
    { code: "not_found" },
    { status: 404 },
  );
}
```

이 코드는 하나의 예입니다. 핵심은 다음과 같습니다.

```text
운영 mode
→ token을 알아도 동작하지 않음

test mode
→ 올바른 token이 없으면 동작하지 않음
```

한 조건만으로 보호하지 않는 이유는 설정 실수 하나가 곧 데이터 변경 권한으로 이어지는 위험을 줄이기 위해서입니다.

## `404`와 `403`의 선택을 이해합니다

조건이 맞지 않을 때 `404`를 반환하면 endpoint 존재 자체를 외부에 드러내지 않는 효과가 있습니다.

```text
404
→ 이 경로가 없는 것처럼 보임
```

반면 일반 admin API라면 인증과 권한 실패를 명확히 나타내기 위해 `401` 또는 `403`이 적합할 수 있습니다.

테스트 전용 endpoint를 감추는 전략과 일반적인 authorization 정책을 같은 규칙으로 적용하지 않습니다.

## 테스트 route를 운영 build에 포함할지 결정합니다

가장 안전한 구조는 운영 artifact에 테스트 전용 route가 아예 포함되지 않는 것입니다.

하지만 프로젝트 구조상 동일한 build에 포함해야 할 수도 있습니다.

이 경우 다음을 확인합니다.

- 기본 운영 설정에서는 비활성화
- test mode와 token을 모두 요구
- 실제 production database와 연결되지 않음
- 가능한 동작 범위를 최소화
- operating smoke test에서 비활성 상태를 확인
- source code에서 일반 사용자 기능과 분리

단순히 "아무도 URL을 모를 것"이라고 가정하지 않습니다.

## 현재 실행 중인 릴리스를 찾을 수 있게 합니다

운영 장애가 발생했을 때 다음 질문에 빠르게 답할 수 있어야 합니다.

```text
현재 어떤 source와 build가 실행 중입니까?
```

일반적인 연결 방식은 다음과 같습니다.

```text
source commit
→ build 또는 image 식별자
→ 실행 instance
→ health와 서버 log
→ browser error report
```

예를 들어 build 과정에서 `APP_RELEASE`를 주입할 수 있습니다.

```text
APP_RELEASE=4f2c7a1
```

값은 commit SHA, image digest, release manifest id 또는 deployment id가 될 수 있습니다.

중요한 것은 **source와 실제 runtime을 연결할 수 있는 안정적인 식별자**라는 점입니다.

## release id는 사용자 데이터가 아닙니다

release id는 일반적으로 사용자 계정이나 세션을 식별하는 값이 아닙니다.

따라서 다음과 같은 위치에서 사용할 수 있습니다.

```text
health 응답
server log
error report
support diagnostics
```

하지만 내부 commit 전체, private repository 정보 또는 민감한 build metadata를 그대로 공개할 필요는 없습니다.

외부 노출이 필요한 경우에는 짧고 안전한 식별자를 사용할 수 있습니다.

## release 기본값을 모호하게 만들지 않습니다

로컬 개발에서 release 환경 변수가 없을 수 있습니다.

이때 빈 문자열이나 `"unknown"`만 반환하면 운영 설정 누락과 로컬 실행을 구분하기 어려울 수 있습니다.

예를 들어 다음처럼 의도를 드러내는 값을 사용할 수 있습니다.

```text
local
development
unversioned
```

운영 환경에서는 release id가 반드시 있어야 한다면 startup 또는 smoke test에서 누락을 실패로 처리할 수도 있습니다.

## 환경 변수의 공개 범위를 구분합니다

환경 변수는 이름만으로 자동 보호되지 않습니다.

### 서버 전용 값

다음 값은 일반적으로 서버에서만 읽어야 합니다.

- database credential
- API credential
- signing key
- private service URL
- 테스트 초기화 token
- 내부 release metadata
- private feature configuration

### 브라우저 공개 값

다음 값은 브라우저에 노출되어도 되는 값이어야 합니다.

- 공개 analytics site id
- browser가 호출할 공개 API origin
- 사용자에게 노출 가능한 feature flag
- public environment name

Next.js의 공개 prefix를 사용하는 값은 브라우저 bundle 또는 응답에서 읽힐 수 있다고 가정합니다.

변수 이름에 다음 단어가 포함되어도 보호되지 않습니다.

```text
SECRET
PRIVATE
INTERNAL
```

실제 보호 여부는 **어느 module에서 읽고, 그 module이 Client Component graph에 들어가는가**에 의해 결정됩니다.

## 환경 변수의 시점을 구분합니다

프런트엔드 framework에서는 어떤 환경 변수가 build 시점에 bundle에 들어가고, 어떤 값이 runtime 서버에서 읽히는지 구분해야 합니다.

다음 질문을 확인합니다.

```text
이 값은 build할 때 고정됩니까?
runtime마다 바꿀 수 있습니까?
client bundle에 들어갑니까?
server process만 읽습니까?
```

특히 브라우저 공개 값은 build artifact에 고정될 수 있으므로 같은 artifact를 여러 환경에 재사용하는 배포 전략과 충돌할 수 있습니다.

정확한 동작은 프로젝트가 사용하는 Next.js 버전과 배포 방식에 따라 확인합니다.

## 서버 전용 module을 Client Component 경계에서 분리합니다

다음 구조는 위험합니다.

```text
server-config.ts
→ process.env.API_SECRET 읽음

client-component.tsx
→ server-config.ts import
```

Client Component가 직접 secret 값을 사용하지 않더라도 import graph 때문에 서버 전용 module이 잘못된 경계에 들어갈 수 있습니다.

서버 전용 값은 브라우저에서 import될 수 없는 module에 격리합니다.

예를 들어 애플리케이션 구조에서 다음처럼 나눌 수 있습니다.

```text
server/
  config.ts
  database.ts

client/
  analytics.ts
```

구체적인 디렉터리 이름보다 **module 경계가 명확한가**가 중요합니다.

## 비밀값 canary로 노출을 검사합니다

정적 분석만으로 모든 secret 노출 경로를 찾기 어렵습니다.

Smoke test에서 예측하기 어려운 문자열을 서버 전용 환경 변수에 넣고 실제 응답에서 검색하면 간단한 동적 검사를 만들 수 있습니다.

예를 들어 다음 값을 만듭니다.

```text
server-only-8c84e4c5f912...
```

중요한 점은 테스트마다 충분히 구분되는 값을 만드는 것입니다.

그 뒤 다음 위치를 확인합니다.

- health response body
- root HTML
- 첫 route가 요청한 JavaScript response body
- 공개 JSON endpoint
- 필요하다면 error page

같은 문자열이 발견되면 서버 전용 값이 외부 결과물에 포함된 것입니다.

## canary 검사가 무엇을 보장하는지 제한적으로 이해합니다

canary가 발견되지 않았다고 해서 모든 secret이 안전하다고 증명되는 것은 아닙니다.

이 검사가 잘 찾는 회귀는 다음과 같습니다.

- `process.env` 전체를 JSON으로 직렬화
- server config object를 response에 넣음
- Client Component가 server config 값을 import
- debug endpoint가 environment 값을 노출

하지만 다음 문제는 놓칠 수 있습니다.

- 다른 secret 변수만 노출됨
- 값이 변환되어 직접 문자열 검색으로 찾기 어려움
- lazy-loaded route에만 노출됨
- 특정 오류 경로에서만 노출됨

따라서 canary는 secret 관리 정책을 대신하는 것이 아니라 **대표적인 accidental exposure를 빠르게 찾는 regression test**입니다.

## JavaScript 응답 검사 범위를 명확히 합니다

"첫 JavaScript 응답"이라는 표현은 구현에 따라 여러 script가 있을 수 있어 모호할 수 있습니다.

보다 명확한 smoke test는 다음처럼 정의할 수 있습니다.

```text
root HTML 요청
→ HTML에서 application script URL 수집
→ 같은 origin의 초기 application JavaScript 응답 요청
→ 각 response body에서 canary 검색
```

framework runtime, route chunk와 shared chunk 중 어느 범위를 검사할지 테스트 코드에 명시합니다.

가능하다면 first route load에서 browser가 실제로 요청한 script response를 수집하는 방식이 더 현실적입니다.

## 현재 실행 중인 release와 canary를 함께 검증합니다

smoke test는 다음 두 종류의 값을 process 환경에 넣을 수 있습니다.

```text
APP_RELEASE
→ 예상 가능한 테스트 release id

SERVER_ONLY_CANARY
→ 예측하기 어려운 secret-like 문자열
```

그 뒤 다음을 확인합니다.

```text
health.release
→ APP_RELEASE와 같음

HTML/JS
→ SERVER_ONLY_CANARY가 없음
```

하나는 **노출되어야 하는 metadata**, 다른 하나는 **절대 노출되어서는 안 되는 server-only 값**입니다.

이 두 검사를 함께 두면 환경 변수 경계를 이해하기 쉽습니다.

## 운영 smoke test는 새 프로세스를 직접 시작합니다

Smoke test는 이미 실행 중인 개발 서버에 기대지 않습니다.

다음 흐름으로 독립적인 운영 프로세스를 시작합니다.

```text
사용 가능한 port 선택
→ 운영 start command 실행
→ stdout/stderr 수집
→ readiness polling
→ release/health 검사
→ root HTML 검사
→ 핵심 API 최소 검사
→ canary 비노출 검사
→ 종료 신호 전송
→ 정상 종료 확인
→ 하위 프로세스 잔존 확인
```

이렇게 해야 smoke test가 실제 배포 artifact와 start command를 검증할 수 있습니다.

## 고유 port를 선택할 때 race를 고려합니다

다음 방식은 흔하지만 작은 race가 있을 수 있습니다.

```text
비어 있는 port 찾음
→ socket 닫음
→ 서버를 그 port로 시작
```

두 단계 사이에 다른 프로세스가 같은 port를 사용할 수 있기 때문입니다.

테스트 환경에서는 충분히 낮은 위험일 수 있지만, 병렬 테스트가 많다면 다음을 고려합니다.

- 테스트 worker별 port 범위 예약
- OS가 할당한 port를 사용할 수 있는 start 방식
- 충돌 발생 시 명확한 오류 처리

중요한 것은 fixed port 하나를 모든 테스트가 공유하지 않는 것입니다.

## readiness는 polling으로 확인합니다

서버 프로세스를 시작한 직후 바로 요청하면 아직 listen 준비가 끝나지 않았을 수 있습니다.

따라서 고정 `sleep`보다 health 또는 readiness endpoint를 polling합니다.

```text
process 시작
→ /api/health 요청
→ 실패하면 짧은 간격 후 다시 시도
→ 전체 제한 시간 안에 성공하면 준비 완료
→ 제한 시간을 넘으면 startup 실패
```

polling에는 다음 두 제한을 둡니다.

```text
각 HTTP 요청 timeout
전체 startup deadline
```

예를 들어 한 요청이 무한히 기다리지 않게 하고, 전체 server startup도 일정 시간 이후 실패시킵니다.

## readiness 실패 시 프로세스 상태를 함께 확인합니다

health polling이 실패했을 때 원인은 두 종류일 수 있습니다.

```text
프로세스가 이미 종료됨
→ startup crash

프로세스는 살아 있지만 health가 준비되지 않음
→ startup hang 또는 dependency 문제
```

따라서 polling loop에서 child process의 종료 여부도 확인합니다.

프로세스가 이미 끝났다면 전체 deadline까지 계속 health를 요청할 이유가 없습니다.

## stdout과 stderr를 제한된 크기로 보존합니다

startup 실패 시 server log는 핵심 진단 정보입니다.

하지만 child process가 매우 많은 출력을 만들면 smoke test 자체의 메모리를 지나치게 사용할 수 있습니다.

따라서 다음처럼 제한할 수 있습니다.

```text
stdout 최근 N KB
stderr 최근 N KB
```

또는 전체 크기를 제한하고 뒤쪽 로그를 유지할 수 있습니다.

실패 메시지에는 다음 정보를 포함하면 도움이 됩니다.

- start command
- exit code 또는 signal
- health URL
- 마지막 HTTP 오류
- stdout/stderr의 제한된 부분

환경 변수 전체는 오류 메시지에 출력하지 않습니다.

## 모든 네트워크 요청에 timeout을 둡니다

smoke test에서 사용하는 다음 요청은 무한히 기다리면 안 됩니다.

- health
- root HTML
- 핵심 API
- JavaScript asset
- shutdown 이후 확인용 요청

각 요청에 timeout을 두고 전체 smoke test에도 상위 deadline을 둘 수 있습니다.

다음처럼 timeout 계층을 구분합니다.

```text
HTTP request timeout
< startup readiness deadline
< 전체 smoke test timeout
```

정확한 값은 프로젝트와 CI 환경에 맞춥니다.

## 실패해도 반드시 프로세스를 정리합니다

검사 중 어느 단계에서 실패하더라도 child process는 종료해야 합니다.

따라서 smoke test 구조는 보통 다음과 같은 형태가 됩니다.

```ts
const process = startServer();

try {
  await waitUntilReady();
  await runSmokeChecks();
} finally {
  await stopServer(process);
}
```

검사 오류가 발생했다고 cleanup이 건너뛰어지면 다음 테스트가 port 충돌로 실패할 수 있습니다.

## 검사 실패와 cleanup 실패를 모두 보존합니다

다음 두 오류가 동시에 발생할 수 있습니다.

```text
root HTML 검사 실패
+
서버 프로세스 종료 실패
```

cleanup 오류가 원래 기능 실패를 덮어쓰거나, 반대로 기능 실패 때문에 process leak을 숨기지 않습니다.

가능하면 두 문제를 모두 결과에 포함합니다.

```text
smoke check failed: root page missing expected heading
cleanup failed: server process still running after SIGTERM
```

운영 검증에서는 process leak 자체도 중요한 실패입니다.

## 하위 프로세스까지 종료합니다

`npm run start`, `pnpm start` 같은 wrapper를 통해 서버를 시작하면 프로세스 구조가 다음과 같을 수 있습니다.

```text
smoke process
└─ package manager
   └─ shell
      └─ node server
```

부모 하나만 종료하면 실제 server가 남을 수 있습니다.

Unix 계열에서는 process group을 만들고 group 전체에 signal을 보내는 방법을 사용할 수 있습니다.

```text
process group 생성
→ SIGTERM 전달
→ grace period 대기
→ 아직 살아 있으면 SIGKILL
→ 종료 확인
```

Windows에서는 process group과 signal 동작이 다르므로 platform에 맞는 process tree 종료 방법을 사용해야 합니다.

## 정상 종료와 강제 종료를 구분합니다

서버가 `SIGTERM`을 받으면 가능하면 진행 중 요청과 resource를 정리하고 종료해야 합니다.

smoke test는 다음을 확인할 수 있습니다.

```text
SIGTERM
→ grace period 안에 정상 종료
```

정상 종료하지 않으면 fallback으로 강제 종료합니다.

```text
SIGKILL
```

하지만 smoke test가 매번 `SIGKILL`로 끝나면서도 성공 처리하면 애플리케이션의 graceful shutdown 문제를 숨길 수 있습니다.

따라서 다음을 구분합니다.

```text
SIGTERM으로 정상 종료
→ 정상

grace period 초과 후 SIGKILL 필요
→ cleanup은 수행했지만 테스트 실패 또는 경고 대상
```

운영 환경이 요구하는 종료 시간과 맞춰 기준을 정합니다.

## 종료 뒤 port가 해제되었는지 확인할 수 있습니다

process 종료 성공만으로 실제 listen socket이 사라졌는지 확실하지 않은 환경이 있을 수 있습니다.

필요하다면 shutdown 뒤 다음을 추가로 확인할 수 있습니다.

```text
child process 종료
→ 해당 port가 더 이상 listen되지 않음
```

또는 바로 같은 port로 새 서버를 시작하는 다음 테스트가 이를 간접적으로 검증할 수 있습니다.

smoke test 성공 후 port를 계속 점유하는 프로세스가 남아 있다면 cleanup 계약이 깨진 것입니다.

## root HTML은 최소 계약만 확인합니다

smoke test는 E2E 전체를 반복하지 않습니다.

root HTML에서는 다음과 같은 작은 신호를 확인할 수 있습니다.

- HTTP 성공
- 예상 content type
- `<main>` 또는 핵심 heading 존재
- 오류 페이지가 아닌지 확인
- canary 비노출

예를 들어 세부 DOM 구조 전체를 snapshot으로 고정하면 사소한 markup 변경에도 smoke가 깨질 수 있습니다.

smoke는 **애플리케이션이 실제로 실행되고 핵심 화면을 반환할 수 있는가**를 확인하는 수준으로 유지합니다.

## 핵심 API도 최소 응답 계약만 검사합니다

주요 API 하나를 smoke에 포함할 수 있습니다.

예를 들어 다음을 확인합니다.

```text
GET /api/projects
→ 예상 status
→ JSON content type
→ 필수 top-level field 존재
```

세부 경곗값과 모든 오류 조건은 Route Handler 또는 API 테스트가 담당합니다.

smoke에서 모든 business rule을 다시 검사하지 않습니다.

## 브라우저 E2E와 smoke의 역할을 구분합니다

health와 smoke가 성공해도 다음 문제는 남아 있을 수 있습니다.

- JavaScript asset load 실패
- hydration 오류
- CSP로 script 실행 실패
- browser navigation 문제
- focus와 keyboard 문제
- runtime API 요청 실패

따라서 다음처럼 역할을 구분합니다.

```text
health/readiness
→ process 준비 확인

smoke
→ 실제 운영 서버의 최소 HTTP 계약 확인

browser E2E
→ 핵심 사용자 기능 확인
```

health 성공을 전체 서비스 성공으로 해석하지 않습니다.

## 현재 실행 중인 릴리스와 오류를 연결합니다

서버 log와 브라우저 오류 report에 release id를 포함하면 장애 시 어떤 build에서 발생했는지 찾기 쉬워집니다.

예를 들어 서버 log의 구조화된 필드로 둘 수 있습니다.

```json
{
  "level": "error",
  "release": "4f2c7a1",
  "requestId": "req_...",
  "message": "..."
}
```

브라우저 오류 보고에서도 공개해도 되는 release id를 넣을 수 있습니다.

```text
browser error
→ release 4f2c7a1
→ server/deployment log와 연결
```

민감한 environment 값을 통째로 error report에 넣지 않습니다.

## request id와 release id의 역할을 구분합니다

두 식별자는 다른 질문에 답합니다.

```text
release id
→ 어떤 build가 실행 중이었는가?

request id
→ 어떤 요청에서 문제가 발생했는가?
```

예를 들어 사용자가 오류 화면을 보고 지원팀에 문의했을 때 다음 두 값이 있으면 추적이 쉬워집니다.

```text
release = 4f2c7a1
requestId = req_83c...
```

request id 생성·전파 방식은 인프라와 애플리케이션 계약에 따라 정합니다.

## 로그에 비밀값을 다시 노출하지 않습니다

server-only canary 검사는 브라우저 노출뿐 아니라 debugging log를 설계할 때도 같은 원칙을 적용하게 해 줍니다.

다음 내용을 log에 그대로 넣지 않습니다.

- 전체 `process.env`
- authorization header
- cookie
- database connection string
- access token
- reset token

필요한 metadata만 구조화해서 기록합니다.

## 애플리케이션과 인프라가 맡을 일을 구분합니다

두 영역이 완전히 독립적인 것은 아니지만, 연결 지점을 명시하면 책임이 분명해집니다.

### 애플리케이션 저장소가 제공할 내용

- dependency 설치 방법
- 운영 build 명령
- 실제 start 명령
- Node.js 버전 요구사항
- runtime 환경 변수 목록과 의미
- browser 공개 환경 변수 목록
- host와 port 지정 방법
- health/readiness endpoint와 schema
- release id 사용 방법
- graceful shutdown 기대 시간
- standalone smoke test
- browser E2E
- 서버 전용 값 client 노출 검사
- 오류 기록에 사용할 request id/release id 위치
- 테스트 전용 route의 활성 조건

### 인프라가 제공할 내용

- host와 container runtime
- process/container restart 정책
- image registry와 배포 승인
- secret 전달 시스템
- DNS와 certificate
- reverse proxy와 load balancer
- health probe 구성
- 중앙 log, metric와 trace 저장소
- alert와 on-call 연결
- backup과 restore
- network policy와 firewall
- host rebuild와 disaster recovery

## 두 영역은 공개 계약으로 연결합니다

애플리케이션과 인프라는 내부 구현을 직접 참조하기보다 명령, environment와 HTTP endpoint로 연결합니다.

좋은 연결은 다음과 같습니다.

```text
인프라
→ APP_RELEASE 환경 변수 설정
→ PORT 설정
→ start command 실행
→ /api/health 확인
```

피해야 할 연결은 다음과 같습니다.

```text
인프라 script
→ 애플리케이션 내부 TypeScript module 직접 import

애플리케이션
→ 특정 배포 플랫폼의 private deployment API를
  불필요하게 직접 호출
```

필요한 platform integration이 있다면 adapter나 명확한 환경 계약으로 격리합니다.

## 운영 실패를 단계별로 좁힙니다

증상이 나타난 위치부터 앞 단계로 돌아가며 확인합니다.

| 증상 | 먼저 확인할 항목 |
| --- | --- |
| build 실패 | Node.js, dependency 설치, type, build 설정, 환경 변수 |
| 프로세스 시작 실패 | start 명령, 작업 디렉터리, runtime 환경 변수, port |
| process 즉시 종료 | stdout/stderr, exit code, startup dependency |
| health 연결 실패 | listen host, port, startup 완료 여부 |
| health `404` | route 생성 여부, base path, 실제 배포 release |
| health `500` | readiness 구현, startup dependency |
| health release 불일치 | 잘못된 deployment, 오래된 instance, 환경 변수 주입 |
| health 성공 후 HTML 실패 | page runtime, server data, routing |
| HTML 성공 후 interaction 실패 | JavaScript asset, CSP, hydration, browser error |
| 특정 API만 실패 | runtime credential, downstream dependency, route contract |
| canary 발견 | client/server module 경계, response serialization, debug endpoint |
| smoke 종료 후 process 잔존 | signal 전달, process group, wrapper script, child tree |
| SIGTERM timeout | graceful shutdown handler, long request, 열린 resource |

문제 하나 때문에 전체 배포 환경을 동시에 바꾸지 않습니다.

## build와 release가 같은지 확인합니다

다음 상황은 흔한 운영 문제입니다.

```text
CI build는 최신
→ 배포 대상은 이전 image

health는 성공
→ release id가 예상과 다름
```

따라서 deployment 검증 시 기대하는 release와 실제 health의 release를 비교합니다.

```text
expected release
4f2c7a1

GET /api/health
release = 9ab1330

→ 배포 대상이 예상과 다름
```

health 자체가 성공해도 원하는 build가 실행 중인지 별도로 확인해야 합니다.

## 여러 instance가 있으면 instance별 차이도 고려합니다

load balancer 뒤에 여러 instance가 있을 경우 일부 instance만 오래된 release일 수 있습니다.

단일 public health 요청만으로 모든 instance를 검증할 수 없는 배포 구조라면 인프라가 instance별 readiness와 deployment 상태를 확인해야 합니다.

애플리케이션은 release id를 health와 log에 제공하여 이 검증을 가능하게 합니다.

```text
instance A → release 4f2c7a1
instance B → release 4f2c7a1
instance C → release old123
```

instance discovery와 rollout 판단은 인프라 책임입니다.

## Smoke test의 예외 처리를 단계별로 만듭니다

smoke test가 실패했을 때 "smoke failed" 한 줄만 출력하면 원인을 찾기 어렵습니다.

각 단계를 이름 붙일 수 있습니다.

```text
[1] process start
[2] readiness
[3] health schema
[4] release match
[5] root HTML
[6] API
[7] canary
[8] shutdown
```

실패 메시지에는 단계와 관찰값을 넣습니다.

```text
readiness failed:
GET http://127.0.0.1:43127/api/health
last error: ECONNREFUSED
server exit code: 1
stderr: ...
```

비밀 환경 변수 값은 포함하지 않습니다.

## 운영 smoke test의 개념적 구조

구체적인 언어와 test framework와 관계없이 다음 구조를 사용할 수 있습니다.

```text
환경 준비
→ random release id
→ secret canary
→ test port

프로세스 시작
→ production start command

준비 대기
→ readiness polling
→ child early-exit 감지

검사
→ health schema
→ release id
→ root HTML
→ 최소 API
→ canary non-exposure

정리
→ SIGTERM
→ grace period
→ 필요 시 강제 종료
→ child/process tree 확인

보고
→ 기능 검사 오류 + cleanup 오류 모두 보존
```

이 흐름을 별도 standalone script로 두면 브라우저 E2E와 독립적으로 실행할 수 있습니다.

## 배포 문서에는 실행 가능한 사실을 적습니다

다음 문장만으로는 부족합니다.

```text
배포 전에 build를 확인합니다.
```

다음처럼 실제 명령과 기대 결과를 기록하는 편이 좋습니다.

```text
Node.js 22 사용
npm ci
npm run build
APP_RELEASE=<release> PORT=<port> npm run start
GET /api/health → 200
response.release == APP_RELEASE
npm run smoke
```

문서가 실제 CI와 다르면 시간이 지나면서 신뢰를 잃습니다.

가능하면 문서의 명령을 package script나 CI가 그대로 사용하게 합니다.

## 적용 완료 기준

실제 프로젝트 디렉터리에서 다음 내용을 확인합니다.

- dependency 설치, 운영 build와 실제 운영 start 명령이 문서화되어 있습니다.
- 필요한 Node.js 버전과 runtime 환경 변수가 문서화되어 있습니다.
- host와 port를 외부에서 지정할 수 있습니다.
- build 성공과 start 성공을 별도 단계로 검사합니다.
- smoke test가 실제 배포 방식과 같은 runtime artifact를 실행합니다.
- health 또는 readiness endpoint가 무엇을 의미하는지 명시되어 있습니다.
- health 응답은 필요한 필드만 반환하고 `Cache-Control: no-store`를 사용합니다.
- health에 credential, stack trace, 내부 path 같은 민감한 정보가 없습니다.
- health의 release가 실행 프로세스에 주입한 release id와 같습니다.
- 운영에서 release id 누락을 허용할지 정책을 정했습니다.
- 테스트 전용 endpoint는 test mode와 token이 모두 없으면 동작하지 않습니다.
- 테스트 전용 endpoint가 운영 데이터에 접근하지 않는 구조입니다.
- 서버 전용 canary가 health, HTML와 초기 application JavaScript 응답에 없습니다.
- canary 검사가 secret 관리 전체를 증명하지 않는다는 한계를 이해합니다.
- smoke test가 고유 port에서 새 운영 프로세스를 직접 시작합니다.
- readiness는 고정 `sleep`이 아니라 polling과 deadline으로 확인합니다.
- child process의 조기 종료를 readiness 실패와 구분합니다.
- 모든 smoke HTTP 요청에 timeout이 있습니다.
- startup 실패 시 제한된 stdout/stderr를 확인할 수 있습니다.
- 검사 도중 실패해도 `finally`에 해당하는 cleanup 경로가 실행됩니다.
- 기능 검사 실패와 cleanup 실패를 모두 보고할 수 있습니다.
- SIGTERM 후 정해진 grace period 안에 정상 종료하는지 확인합니다.
- wrapper가 만든 하위 프로세스까지 정리합니다.
- 강제 종료가 필요했다면 정상 성공으로 숨기지 않습니다.
- health, smoke와 browser E2E의 역할을 구분합니다.
- 서버 log와 오류 기록에서 release id를 확인할 수 있습니다.
- request id와 release id의 역할을 구분합니다.
- 애플리케이션과 인프라가 명령, 환경 변수와 HTTP endpoint라는 공개 계약으로 연결됩니다.
- 배포 실패 시 증상이 처음 나타난 단계부터 원인을 좁힐 수 있습니다.

이 항목에서 실패하면 증상이 처음 나타난 단계부터 확인합니다. build, runtime, health, browser와 infrastructure를 한꺼번에 바꾸지 않습니다.
