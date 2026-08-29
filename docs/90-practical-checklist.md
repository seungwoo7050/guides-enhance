# Astro 실무 점검표

이 문서는 본문을 대신하지 않습니다. 구현·review·배포·장애 분석에서 현재 변경과 관련된 항목만 확인합니다. Competency exercise가 실패했을 때는 실패한 항목이 포함된 문서만 다시 읽습니다.

## Project 실행

- [ ] 지원하는 Node.js version과 package manager를 확인했습니다.
- [ ] lockfile을 사용해 고정 dependency를 설치합니다.
- [ ] `dev`, `check`, `build`, `preview`, `test` command를 확인했습니다.
- [ ] `astro.config.mjs`의 `site`, `base`, `output`, integrations와 adapter를 확인했습니다.
- [ ] `src/`, `public/`, `dist/`에 어떤 file을 두는지 구분했습니다.
- [ ] development server와 production build 결과를 각각 확인했습니다.

## Rendering 시점

- [ ] 각 page가 build에서 생성되는지 요청마다 생성되는지 확인했습니다.
- [ ] 정적으로 만들 수 있는 route를 불필요하게 server에서 만들지 않습니다.
- [ ] `prerender = false`를 사용한 이유가 분명합니다.
- [ ] `output: "server"`가 필요한 route 비율과 배포 runtime을 확인했습니다.
- [ ] Build-time data와 request-time data의 최신성 요구를 구분했습니다.
- [ ] Adapter output을 실제 production 방식으로 실행했습니다.

## Component와 page

- [ ] `.astro` component script가 browser에 전달되지 않는다는 점을 전제로 작성했습니다.
- [ ] Props는 TypeScript로 제한하고 기본값을 명시했습니다.
- [ ] Page는 URL, data와 metadata를 조합하고 반복 표현은 component로 분리했습니다.
- [ ] Layout은 document metadata와 공통 landmark를 한 번만 만듭니다.
- [ ] Slot은 caller가 넣을 위치가 실제로 필요한 경우에만 사용합니다.
- [ ] Scoped style과 global style의 적용 범위를 구분했습니다.
- [ ] HTML link에는 `<a>`, 사용자 command에는 `<button>`을 사용합니다.

## Route와 URL

- [ ] `src/pages/` file 이름과 공개 URL이 일치합니다.
- [ ] Dynamic route의 `getStaticPaths()`가 유효한 id만 반환합니다.
- [ ] Content id를 공개 URL로 사용한 뒤 임의로 바꾸지 않습니다.
- [ ] Unknown category와 id가 올바른 404로 이어집니다.
- [ ] `site`, `base`와 trailing slash가 production host와 맞습니다.
- [ ] Canonical URL과 내부 link가 같은 규칙을 사용합니다.

## Content Collection

- [ ] 같은 종류의 entry에만 collection을 사용합니다.
- [ ] `src/content.config.ts`에서 loader와 schema를 정의했습니다.
- [ ] title, summary, enum, date와 tag 길이를 build에서 검사합니다.
- [ ] Draft를 route 생성 전에 제외합니다.
- [ ] 목록과 endpoint가 같은 published set과 sort 함수를 사용합니다.
- [ ] Body 전체를 목록 card나 JSON endpoint로 전달하지 않습니다.
- [ ] Loader가 읽는 local·remote source와 build 실패 조건을 문서화했습니다.

## Markdown과 MDX

- [ ] 단순 article에는 Markdown을 우선합니다.
- [ ] Component가 필요한 문서에만 MDX를 사용합니다.
- [ ] Frontmatter와 body의 역할을 구분했습니다.
- [ ] Heading level과 link 규칙을 authoring 문서에 적었습니다.
- [ ] Markdown HTML 허용 여부와 sanitization을 결정했습니다.
- [ ] List page는 summary만 읽고 detail page에서만 body를 render합니다.

## Browser JavaScript와 island

- [ ] 상호작용 없는 component에 `client:*`를 붙이지 않았습니다.
- [ ] 일반 `<script>`로 충분한지 먼저 확인했습니다.
- [ ] Framework component가 hydration 없이 HTML만 render될 수 있음을 활용했습니다.
- [ ] `client:load`, `idle`, `visible`, `media`, `only`를 사용자 우선순위로 선택했습니다.
- [ ] Page 전체를 하나의 React island로 만들지 않았습니다.
- [ ] Island props는 serializable하고 private field가 없습니다.
- [ ] 여러 island가 같은 state를 공유한다면 소유자와 동기화 방식을 명시했습니다.
- [ ] Local storage를 `unknown`으로 읽고 손상된 값을 거절합니다.

## 외부 data

- [ ] HTTP status와 response body 검사를 분리했습니다.
- [ ] API, CMS, cookie, storage와 form 입력을 사용 전에 검사합니다.
- [ ] Timeout과 retry 횟수를 제한했습니다.
- [ ] Build 실패, 이전 snapshot과 section 제외 중 어떤 방식을 쓸지 결정했습니다.
- [ ] External response를 page가 필요한 model로 줄였습니다.
- [ ] Private key와 public environment variable을 분리했습니다.
- [ ] Data source 변경 주기와 rebuild trigger를 정했습니다.

## Form, Action과 endpoint

- [ ] JavaScript 없는 HTML form으로 충분한지 먼저 확인했습니다.
- [ ] Static endpoint와 요청 시 endpoint의 실행 시점을 구분했습니다.
- [ ] 같은 application의 server function에는 Action 사용을 검토했습니다.
- [ ] 외부 caller가 필요한 API에는 명시적인 endpoint를 사용합니다.
- [ ] Server에서도 입력, authentication과 authorization을 확인합니다.
- [ ] 여러 저장 작업은 필요한 transaction 안에서 처리합니다.
- [ ] 중복 제출과 retry를 idempotency 또는 unique constraint로 처리합니다.
- [ ] 사용자 메시지와 server 진단 정보를 분리했습니다.

## Image, font와 SEO

- [ ] Transform할 image는 `src/`, 원본 URL이 필요한 file은 `public/`에 둡니다.
- [ ] `<Image />` 또는 `<Picture />`의 width와 format 수가 실제 layout에 맞습니다.
- [ ] Remote image host를 제한했습니다.
- [ ] 정보 image의 alt가 용도를 설명합니다.
- [ ] Custom font의 language glyph와 weight 크기를 확인했습니다.
- [ ] 모든 공개 page에 title, description과 canonical이 있습니다.
- [ ] Sitemap, RSS와 robots.txt의 목적을 구분했습니다.
- [ ] Structured data가 화면에 실제로 표시한 값과 일치합니다.

## Accessibility와 responsive UI

- [ ] `main`, heading, nav, list, article와 form을 의미에 맞게 사용합니다.
- [ ] 모든 input에 연결된 label이 있습니다.
- [ ] Keyboard로 interactive island를 완료할 수 있습니다.
- [ ] Focus 위치와 `:focus-visible` 표시를 실제 browser에서 확인했습니다.
- [ ] 320px와 200% 확대에서 horizontal overflow가 없습니다.
- [ ] 긴 title과 tag가 card를 넘지 않습니다.
- [ ] Reduced motion preference를 반영했습니다.
- [ ] Loading, success와 failure를 text로 알립니다.

## 검사

- [ ] 가장 위험한 실패와 첫 검사 위치를 적었습니다.
- [ ] Parser, sort와 metadata helper는 unit test로 검사합니다.
- [ ] Content schema와 dynamic route는 production build로 검사합니다.
- [ ] Browser E2E는 build 결과를 대상으로 실행합니다.
- [ ] Hydrated island 수, JavaScript body와 DOM node 예산이 있습니다.
- [ ] 고정 sleep 대신 request와 DOM condition을 기다립니다.
- [ ] Test마다 storage, data와 port를 격리합니다.
- [ ] Private canary가 build output에 없는지 확인합니다.
- [ ] Smoke 성공·실패 뒤 child process가 남지 않습니다.

## 배포

- [ ] Install, build, output과 start command가 문서화되어 있습니다.
- [ ] Static asset과 HTML cache를 구분했습니다.
- [ ] Host의 redirect, slash와 custom 404를 확인했습니다.
- [ ] Production environment variable을 build-time과 runtime으로 구분했습니다.
- [ ] Source commit과 deployment를 연결하는 release id가 있습니다.
- [ ] 배포 URL에서 핵심 page, endpoint와 asset을 smoke test했습니다.
- [ ] On-demand route의 cookie, cache와 private data를 확인했습니다.
- [ ] 이전 artifact로 rollback할 수 있습니다.

## 장애를 좁히는 순서

1. 같은 URL, content id, build와 release에서 재현되는지 확인합니다.
2. Source content와 generated `dist/` file을 비교합니다.
3. Static HTML에 이미 문제가 있는지, hydration 뒤 생기는지 구분합니다.
4. Network에서 page, asset, endpoint와 island script status를 확인합니다.
5. `site`, `base`, slash와 host rewrite를 확인합니다.
6. Content schema, route id와 canonical이 같은 값을 사용하는지 확인합니다.
7. On-demand route라면 adapter log, runtime env와 database timeout을 확인합니다.
8. Browser storage와 service worker 등 이전 client state를 제거하고 다시 확인합니다.
9. 한 원인만 수정한 뒤 production build와 해당 검사부터 다시 실행합니다.
10. 배포 URL에서 핵심 smoke를 다시 통과합니다.
