# 검사와 성능

Astro project는 정적 HTML, build-time data, browser script와 선택적인 server runtime을 함께 가질 수 있습니다. 한 검사 도구로 모두 확인하려 하지 말고, 실패를 가장 직접적으로 재현하는 위치에서 검사합니다.

## 이 문서를 읽는 시점

- build가 성공하지만 page 동작이 불안정합니다.
- Content Collection schema와 route 생성 규칙을 고정하려고 합니다.
- island 수나 browser JavaScript가 늘었습니다.
- keyboard, focus, responsive layout을 검사해야 합니다.
- adapter output 또는 static `dist/`를 배포하기 전에 확인합니다.

## 먼저 실패 결과를 적습니다

| 위험 | 사용자 영향 | 첫 검사 위치 |
| --- | --- | --- |
| 잘못된 metadata가 build됨 | 깨진 page와 URL 공개 | Content schema + build |
| 같은 content의 정렬이 page마다 다름 | 목록·JSON 불일치 | 순수 함수 unit test |
| dynamic route 누락 | 공개 link가 404 | build output + browser |
| page 전체가 hydration됨 | 초기 JavaScript 증가 | production browser response |
| favorite state가 손상됨 | button crash 또는 상태 유실 | browser test |
| canonical origin 오류 | 검색 engine에 중복 URL | helper unit + generated HTML |
| private env가 output에 포함됨 | secret 노출 | static artifact scan |
| preview process가 남음 | CI hang와 port 점유 | smoke process test |

Test 이름에는 내부 구현보다 막으려는 실패가 드러나야 합니다.

## 검사 위치를 나눕니다

### `astro check`

잘 잡는 문제:

- `.astro` template와 TypeScript type
- component props 오류
- import와 framework component type
- 일부 접근성·markup 진단

잡지 못하는 문제:

- 외부 data의 runtime shape
- 실제 browser focus와 layout
- build route 누락
- production output의 secret 문자열

### Vitest

적합한 대상:

- parser와 validation helper
- sort, filter와 mapping
- canonical URL helper
- state reducer
- resource selection
- performance budget file 형식

Astro page 자체를 억지로 unit test하기보다 page가 사용하는 순수 함수를 분리합니다.

### Production build

확인하는 문제:

- Content Collection schema
- `getStaticPaths()` route 생성
- missing import와 asset 처리
- static endpoint 생성
- client/server module graph
- adapter output 생성

Build 성공만으로 browser 행동까지 증명되지는 않습니다.

### Playwright

적합한 대상:

- link navigation과 404
- generated metadata
- client island hydration
- `localStorage`와 reload
- accessible name와 focus
- 320px, 확대와 overflow
- reduced motion
- JavaScript response body와 DOM node

E2E에서는 production build를 preview하거나 실제 adapter runtime을 실행합니다.

### Standalone smoke

적합한 대상:

- 필요한 build file 존재
- 공개 JSON field
- private canary 부재
- preview 또는 server process 시작
- 핵심 HTML과 endpoint 응답
- 성공·실패 뒤 child process 정리

## Content schema는 build test입니다

잘못된 fixture를 별도 temporary collection에서 build하거나 schema의 핵심 정규화 함수를 unit test할 수 있습니다.

검출할 오류:

- 빈 title과 summary
- 알 수 없는 category
- 잘못된 date
- 중복 공개 id
- 지나치게 긴 tag
- draft가 공개 route에 포함됨

Schema만 통과한다고 content가 유용한 것은 아닙니다. link와 image 존재, heading 규칙 등 authoring 품질 검사는 별도로 둡니다.

## `getStaticPaths()`의 결과를 build output으로 확인합니다

Dynamic route는 함수 반환 모양만 검사하지 말고 실제 file을 확인합니다.

```text
dist/resources/http-status-reference/index.html
dist/categories/web/index.html
dist/resources.json
```

File 수, 예상 route와 canonical을 검사하면 content query와 route 생성이 함께 고정됩니다.

## Island 수와 JavaScript 예산을 둡니다

Astro를 사용한다고 자동으로 JavaScript가 적어지는 것은 아닙니다. Page 전체를 React component로 만들고 `client:load`를 붙이면 일반 SPA와 비슷한 비용을 냅니다.

측정 가능한 예산 예시:

```json
{
  "maximumDetailJavaScriptBytes": 220000,
  "maximumDetailDomNodes": 220,
  "maximumHydratedIslands": 1
}
```

Browser test에서 다음을 셉니다.

- route가 실제 요청한 script response body 합계
- `<astro-island>` element 수
- 전체 DOM element 수
- 핵심 image body size

예산 숫자는 project 규모와 실제 측정을 근거로 정합니다. Framework upgrade 뒤에는 같은 hardware와 route에서 다시 확인합니다.

## Hydration directive를 검증합니다

- Home page에는 island가 정말 없는가?
- 상세 page에는 favorite button 하나만 있는가?
- `client:visible` component가 viewport에 들어오기 전에 실행되지 않는가?
- `client:idle` 기능이 interaction을 늦추지 않는가?
- `client:only` 때문에 no-JS content가 사라지지 않는가?

HTML source와 network response를 함께 확인합니다. 화면이 보인다는 이유만으로 server render와 browser render를 구분할 수는 없습니다.

## Network test에서 고정 sleep을 피합니다

Remote API나 Action의 순서를 검사한다면 request를 명시적으로 보류하고 해제합니다.

```text
느린 이전 요청 보류
→ 새 요청 완료
→ 이전 요청 해제
→ 최신 화면 유지 확인
```

`setTimeout(1000)`은 느린 환경에서 실패하고 빠른 환경에서 시간을 낭비합니다. URL, response, status message와 DOM condition을 기다립니다.

## Accessibility는 browser에서 확인합니다

필수 확인:

- `main`, heading, nav, list와 article 사용
- form control과 label 연결
- keyboard로 island 기능 사용
- visible focus indicator
- loading·success·error status 전달
- 320px와 200% 확대에서 horizontal overflow 없음
- reduced motion preference 반영

Scanner만으로 focus 이동과 실제 keyboard 작업 완료 여부를 확인할 수 없습니다.

## Image와 font도 production response를 측정합니다

- LCP image가 필요한 width로 내려오는가?
- 같은 원본에서 불필요한 variant를 많이 만들지 않았는가?
- custom font가 사용하지 않는 weight를 포함하는가?
- Korean glyph file이 초기 route에 과도한 비용을 만들지 않는가?
- image width/height가 layout shift를 막는가?

Build file size와 browser가 실제 받은 body는 다를 수 있습니다. 둘 다 필요한 경우 구분해 기록합니다.

## Secret canary를 build에 넣습니다

Static build도 private API key로 data를 읽을 수 있습니다. 임의 canary 값을 private environment variable에 넣고 `dist/` 전체에서 문자열을 검색합니다.

```text
private canary 주입
→ production build
→ HTML, JSON, JavaScript, source map 검색
→ 발견 시 실패
```

이 검사가 모든 노출을 증명하지는 않지만 private env를 client code에 import하는 회귀를 잡을 수 있습니다.

## Test data를 독립적으로 만듭니다

- 각 test가 필요한 content id를 명시합니다.
- browser storage를 test마다 초기화합니다.
- on-demand data는 transaction 또는 fixture로 복원합니다.
- port를 고정하지 않고 사용 가능한 값을 고릅니다.
- test가 기존 development server를 재사용하지 않습니다.
- failure trace와 server output을 보존합니다.

## 완료 기준

- parser, build, browser와 smoke에서 각각 잡을 문제를 구분할 수 있습니다.
- dynamic route를 실제 build file로 확인할 수 있습니다.
- hydrated island, JavaScript와 DOM에 측정 가능한 예산을 둘 수 있습니다.
- keyboard, viewport와 reduced motion을 production browser에서 확인할 수 있습니다.
- private canary와 process cleanup을 smoke test로 확인할 수 있습니다.

## 공식 문서

- [Testing](https://docs.astro.build/en/guides/testing/)
- [Type checking](https://docs.astro.build/en/guides/typescript/#type-checking)
- [Build configuration](https://docs.astro.build/en/reference/configuration-reference/#build-options)
- [Client directives](https://docs.astro.build/en/reference/directives-reference/#client-directives)
