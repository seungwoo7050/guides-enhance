# 배포와 운영 검증

Astro application의 배포 단위는 project 설정에 따라 달라집니다. 기본 static output은 `dist/`의 HTML과 asset을 배포하고, adapter를 사용한 route는 해당 runtime이 요구하는 server output과 설정을 함께 배포합니다.

배포 platform을 고르기 전에 **어떤 file과 command가 실제 제품인지** 먼저 정합니다.

## 이 문서를 읽는 시점

- 실제 domain에 배포합니다.
- static host, Node server, serverless 또는 edge를 선택합니다.
- build command와 output directory를 설정합니다.
- environment variable과 release identifier를 주입합니다.
- preview 성공 뒤 production smoke 조건을 정합니다.

## 배포 형식을 먼저 확인합니다

### Static output

일반적으로 필요한 값:

```text
install   npm ci
build     npm run build
output    dist/
```

Host는 HTML, CSS, JavaScript, image와 JSON file을 전달합니다. Astro server process는 없습니다.

### Adapter output

필요한 값은 adapter마다 다릅니다.

- build command
- server entry 또는 function directory
- static asset directory
- runtime version
- environment variable
- start command 또는 platform binding
- routing configuration

README와 deployment config에 실제 값을 기록합니다. Platform이 자동 감지했다고 해서 application 저장소가 실행 방법을 몰라도 되는 것은 아닙니다.

## 고정 dependency로 build합니다

- 지원하는 Node.js version을 명시합니다.
- 하나의 package manager와 lockfile을 사용합니다.
- CI에서 frozen install을 사용합니다.
- install script와 native dependency를 review합니다.
- build log에 Astro, adapter와 integration version을 남깁니다.

Developer machine의 global package에 의존하지 않습니다.

## `site`, `base`와 trailing slash를 production URL에 맞춥니다

```js
export default defineConfig({
  site: "https://example.com",
  base: "/docs",
  trailingSlash: "always"
});
```

확인할 내용:

- canonical origin과 실제 domain이 같은가?
- subpath 배포라면 asset과 link가 `base`를 포함하는가?
- host의 slash redirect와 build 형식이 일치하는가?
- staging build가 production canonical을 잘못 출력하지 않는가?
- custom 404가 host에서 실제 404 status로 전달되는가?

Absolute path `/favicon.svg`와 hard-coded link는 `base`가 있을 때 깨질 수 있습니다. Project helper나 `import.meta.env.BASE_URL` 사용 여부를 검토합니다.

## Static host header와 redirect를 설정합니다

Astro가 file을 만들더라도 CDN header와 redirect는 hosting 설정이 담당할 수 있습니다.

필요한 항목:

- hashed asset의 장기 cache
- HTML의 짧은 cache 또는 revalidation
- `Content-Type`
- compression
- HTTPS redirect
- `www` 또는 apex domain 정규화
- trailing slash redirect
- security header
- custom 404

HTML을 1년 cache하면서 file name을 고정하면 새 배포가 오래 보이지 않을 수 있습니다. Asset과 HTML의 cache 전략을 분리합니다.

## Environment variable 공개 범위를 확인합니다

- `PUBLIC_` prefix는 browser output에 들어갈 수 있습니다.
- private key는 build 또는 server runtime에서만 읽습니다.
- staging과 production 값을 분리합니다.
- build-time 값과 request-time 값을 구분합니다.
- secret rotation 뒤 rebuild가 필요한지 확인합니다.
- build log에 값 전체를 출력하지 않습니다.

Static site에서 private env를 바꾸어도 이미 배포된 HTML은 바뀌지 않습니다. 새 build와 배포가 필요합니다.

## Release를 식별합니다

문제가 생겼을 때 다음을 연결할 수 있어야 합니다.

```text
source commit
→ CI build
→ artifact 또는 deployment id
→ 공개 release label
→ browser와 server 오류
```

정적 site에서는 작은 build label을 footer나 metadata에 넣을 수 있습니다. 내부 정보 전체를 공개하지 말고 support가 deployment를 찾을 수 있는 안전한 id를 사용합니다.

## Preview와 production을 구분합니다

`astro preview`는 local build 확인용입니다. 모든 production adapter와 CDN 동작을 그대로 재현하지 않습니다.

최소 검증 순서:

1. clean install을 수행합니다.
2. `astro check`와 unit test를 실행합니다.
3. production build를 만듭니다.
4. static output이면 `astro preview`로 핵심 route를 확인합니다.
5. adapter output이면 실제 start command 또는 platform emulator를 실행합니다.
6. browser E2E를 실행합니다.
7. 배포한 URL에서 smoke test를 실행합니다.

## Static build smoke test

확인할 예:

- `index.html`, 404와 핵심 dynamic route가 존재합니다.
- JSON·RSS·sitemap file이 생성되었습니다.
- private canary가 output에 없습니다.
- canonical이 production origin을 가리킵니다.
- Home route는 의도한 island 수를 유지합니다.
- 핵심 asset이 200으로 응답합니다.
- preview process가 test 뒤 남지 않습니다.

File 존재 검사와 HTTP response 검사를 함께 사용합니다. File만 있어도 hosting route 설정이 틀리면 접근할 수 없습니다.

## On-demand runtime smoke test

추가 확인:

- server process 또는 function이 시작됩니다.
- health/readiness URL이 응답합니다.
- release가 기대한 값입니다.
- cookie와 redirect가 production URL에서 동작합니다.
- private route가 권한 없이 열리지 않습니다.
- Action과 server endpoint가 입력 오류를 올바르게 반환합니다.
- runtime secret이 HTML과 JavaScript에 없습니다.
- 종료 signal 뒤 connection과 process가 정리됩니다.

Serverless/edge에서는 process 종료 대신 function log, cold start와 platform health를 확인합니다.

## 배포 실패를 분류합니다

| 증상 | 먼저 확인할 내용 |
| --- | --- |
| route 404 | output path, `base`, slash, host rewrite |
| CSS·image 404 | asset base URL, CDN path, case-sensitive file name |
| local만 성공 | Node/runtime, adapter, env, filesystem 가정 |
| 오래된 HTML | CDN cache, deployment target, service worker |
| canonical 오류 | `site`, staging env, base path |
| form 실패 | Action/endpoint runtime, CORS, CSRF, method |
| server route 500 | runtime log, database, secret, timeout |
| 배포 후 JavaScript 증가 | integration 변경, island 범위, source map |

증상마다 한 설정을 바꾸고 같은 URL에서 다시 확인합니다.

## Rollback과 content rebuild를 준비합니다

- 이전 artifact를 다시 배포할 수 있어야 합니다.
- content source 변경과 application code 변경을 구분합니다.
- database migration이 있다면 code rollback과 호환되는지 확인합니다.
- static content가 잘못됐을 때 rebuild trigger를 수동 실행할 수 있어야 합니다.
- CDN purge 범위와 소요 시간을 압니다.
- rollback 후 canonical, asset와 API version을 다시 확인합니다.

## 완료 기준

- static output과 adapter output의 배포 단위를 설명할 수 있습니다.
- Node, package manager, build command와 output path를 고정할 수 있습니다.
- `site`, `base`, slash와 host routing을 맞출 수 있습니다.
- private/public environment variable과 build/runtime 값을 구분할 수 있습니다.
- preview, deployed static output와 on-demand runtime을 각각 smoke test할 수 있습니다.
- release 식별과 rollback 방법을 문서화할 수 있습니다.

## 공식 문서

- [Deploy your Astro site](https://docs.astro.build/en/guides/deploy/)
- [Configuration reference](https://docs.astro.build/en/reference/configuration-reference/)
- [Adapters](https://docs.astro.build/en/guides/integrations-guide/)
- [Environment variables](https://docs.astro.build/en/guides/environment-variables/)
