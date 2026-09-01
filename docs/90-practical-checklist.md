# 프런트엔드 실무 점검표

이 문서는 처음부터 끝까지 순서대로 읽는 본문이 아닙니다. 구현, 코드 리뷰, 장애 분석 또는 역량 검증에서 실패한 항목과 관련된 절만 골라 확인합니다.

각 체크 항목은 단순히 "코드가 존재하는가"보다 **사용자 동작, 실행 위치, 데이터 계약 또는 운영 조건을 실제로 확인했는가**를 기준으로 판단합니다.

## 프로젝트 합류

- [ ] `.nvmrc`, `.node-version`, `package.json#engines`, `packageManager`와 잠금 파일을 확인했습니다.
- [ ] 저장소가 사용하는 고정 설치, 형 검사, lint, 단위 테스트, 빌드, E2E, smoke와 운영 시작 명령을 찾았습니다.
- [ ] 개발 서버와 운영 빌드 결과를 각각 실행했습니다.
- [ ] 실제 배포 방식과 같은 운영 시작 명령으로 서버를 실행해 보았습니다.
- [ ] 사용자 URL 하나를 `page`, 데이터 읽기 함수, Client Component, 사용자 명령과 테스트까지 끝까지 추적했습니다.
- [ ] 브라우저, Next.js 서버와 빌드 시점에 실행되는 코드를 구분했습니다.
- [ ] `"use client"`가 만드는 module 경계와 그 아래 import graph를 확인했습니다.
- [ ] 서버 전용 환경 변수와 브라우저 공개 환경 변수를 구분했습니다.
- [ ] CI가 실제로 사용하는 Node.js, 패키지 관리자, 설치 옵션과 검증 명령을 확인했습니다.
- [ ] 로컬에서 성공한 명령과 CI가 실행하는 명령이 불필요하게 다르지 않습니다.

## 사용자 기능

- [ ] 기능을 사용자, 조건, 행동과 관찰 가능한 결과가 포함된 한 문장으로 적었습니다.
- [ ] 입력, 출력, 실패와 비동기 완료 순서를 적었습니다.
- [ ] 첫 변경을 확인 가능한 기능 하나로 제한했습니다.
- [ ] 정상 결과, 빈 결과와 실패를 서로 다른 상태로 구분했습니다.
- [ ] 새로 고침, link 공유와 back/forward 뒤 복원해야 할 값을 정했습니다.
- [ ] 같은 명령이나 요청이 반복될 가능성을 검토했습니다.
- [ ] 사용자가 다른 화면으로 이동한 뒤 늦게 도착한 결과를 어떻게 처리할지 정했습니다.
- [ ] 실패 후 사용자가 다시 시도하거나 안전하게 다음 행동을 할 방법이 있습니다.

## 값의 저장 위치

- [ ] URL 상태, 서버 상태, 화면 상태, 입력 초안, 지속 설정과 계산값을 구분했습니다.
- [ ] 각 값의 source of truth가 어디인지 설명할 수 있습니다.
- [ ] 공유·새로 고침·history 복원이 필요한 검색 조건은 URL에 저장합니다.
- [ ] 서버 응답을 여러 클라이언트 저장소에 같은 의미로 불필요하게 복사하지 않았습니다.
- [ ] 서버가 확정한 값과 사용자가 작성 중인 입력 초안을 분리했습니다.
- [ ] 다른 값에서 결정적으로 계산할 수 있는 값은 별도 state로 저장하지 않고 계산합니다.
- [ ] 서로 배타적인 화면 상태를 discriminated union으로 표현했습니다.
- [ ] `pending`과 `error`에서 마지막 정상 결과를 유지할지 제품 동작으로 정했습니다.
- [ ] 여러 컴포넌트가 공유하는 state를 필요한 범위까지만 올렸습니다.
- [ ] 화면 이동, logout과 사용자 전환 때 초기화할 값을 정했습니다.
- [ ] props 변경이 입력 초안을 언제 초기화하는지 정책을 정했습니다.
- [ ] 목록 항목의 local state가 올바른 대상에 연결되도록 안정적인 `key`를 사용합니다.

## Server Component와 Client Component

- [ ] 데이터베이스, 파일, 비밀값과 서버 전용 service를 서버에 둘 수 있는지 확인했습니다.
- [ ] `"use client"` 범위를 실제 브라우저 API나 사용자 상호작용이 필요한 가장 작은 경계로 제한했습니다.
- [ ] Server Component에서 Client Component에 넘기는 값은 해당 경계를 통과할 수 있는 데이터입니다.
- [ ] 데이터베이스 연결, server service instance와 비밀 설정을 Client Component props로 넘기지 않습니다.
- [ ] 서버 전용 module이 클라이언트 import graph에 포함되지 않습니다.
- [ ] 서버 코드가 같은 애플리케이션의 Route Handler를 단순한 내부 함수 호출 대신 불필요하게 HTTP로 호출하지 않습니다.
- [ ] `loading`, `error`, `not-found` 화면이 단순 메시지로 끝나지 않고 사용자의 다음 행동을 제공합니다.
- [ ] 특정 route의 실제 signature는 프로젝트의 Next.js 버전과 생성된 route type을 따릅니다.

## 외부 입력

- [ ] URL, HTTP, WebSocket, cookie, storage, `postMessage`, 파일과 clipboard 입력을 외부 신뢰 경계로 취급합니다.
- [ ] 외부 값은 필요한 경우 `unknown`으로 받고 runtime에서 검사합니다.
- [ ] TypeScript assertion을 실행 중 검증으로 오해하지 않습니다.
- [ ] object/array/string 같은 구조와 허용 범위·enum·중복 id 같은 의미 제약을 구분해 검사합니다.
- [ ] 중복 query parameter의 처리 규칙을 정했습니다.
- [ ] 음수, 0, 지나치게 큰 값과 알 수 없는 enum을 처리합니다.
- [ ] API 응답을 컴포넌트에 넘기기 전에 필요한 필드와 범위를 검사합니다.
- [ ] 형식이 잘못된 `2xx` 응답을 정상 데이터로 화면에 반영하지 않습니다.
- [ ] 외부 API 표현을 애플리케이션 내부 타입으로 변환하는 경계가 있습니다.
- [ ] 사용자에게 보여 줄 문구와 개발자가 확인할 세부 오류를 분리했습니다.

## URL과 history

- [ ] query를 읽는 parser와 URL을 만드는 serializer가 같은 기본값과 허용 규칙을 사용합니다.
- [ ] `parse(serialize(query))`가 같은 정규화된 의미를 만듭니다.
- [ ] URL에서 생략할 기본값을 정했습니다.
- [ ] 현재 기능이 소유하지 않는 query parameter를 유지할지 삭제할지 정했습니다.
- [ ] `push`와 `replace`를 어떤 사용자 동작에 사용할지 구분했습니다.
- [ ] back/forward로 복원된 상태에서 history를 다시 불필요하게 쓰지 않습니다.
- [ ] back/forward 뒤 현재 URL을 다시 읽고 입력 UI와 데이터를 복원합니다.
- [ ] 입력 초안과 URL에 적용된 검색 조건이 서로 다른 상태라면 그 의미를 구분합니다.

## 요청과 Effect

- [ ] 새 읽기 요청이 이전 요청의 `AbortSignal`을 가능한 범위에서 abort합니다.
- [ ] 응답을 화면에 반영하기 전에 최신 generation 또는 동등한 최신성 기준을 확인합니다.
- [ ] 오래된 성공뿐 아니라 오래된 실패도 현재 화면을 바꾸지 않습니다.
- [ ] 사용자 취소, network 실패, timeout, HTTP 실패, JSON 해석 실패와 응답 계약 오류를 구분합니다.
- [ ] abort를 서버 작업이나 mutation의 rollback으로 해석하지 않습니다.
- [ ] component unmount 뒤 이전 요청 결과가 화면을 바꾸지 않습니다.
- [ ] Effect마다 외부 연결 대상, dependency와 cleanup을 설명할 수 있습니다.
- [ ] event listener, observer, timer, WebSocket과 request가 필요한 시점에 정리됩니다.
- [ ] 렌더링 중 계산 가능한 값을 Effect로 다시 state에 저장하지 않습니다.
- [ ] 특정 사용자 행동 때문에 실행되는 작업은 불필요하게 Effect에 넣지 않습니다.
- [ ] 개발 환경에서 `setup → cleanup → setup`이 반복되어도 동작이 깨지지 않습니다.

## 변경 저장과 충돌

- [ ] 낙관적 갱신 전에 요청 전 서버 확정값을 보관합니다.
- [ ] 화면에 먼저 표시한 optimistic 값과 서버가 최종 확정한 값을 구분합니다.
- [ ] 저장 성공 시 클라이언트가 보낸 값보다 서버 응답의 보정 값과 새 `version`을 최종값으로 사용합니다.
- [ ] 일반 실패에서 서버 표시값을 필요한 경우 rollback하고 입력 초안은 유지합니다.
- [ ] `409 Conflict`에서 요청 전 값이 아니라 최신 서버 값과 사용자 입력 초안을 함께 유지합니다.
- [ ] 충돌 뒤 자동 재시도가 안전한지 서버의 concurrency 계약을 기준으로 판단합니다.
- [ ] 저장 중 중복 제출을 막을지 허용할지 정했습니다.
- [ ] 여러 저장을 허용한다면 오래된 저장 응답이 최신 사용자 의도를 덮지 않게 합니다.
- [ ] mutation을 abort해도 서버 변경이 이미 적용되었을 수 있음을 고려합니다.
- [ ] 충돌, 권한 오류, validation 오류와 network 오류를 사용자에게 다른 의미로 설명합니다.
- [ ] 사용자가 입력을 복구·수정·재시도할 수 있습니다.

## 접근성

- [ ] 이동에는 link, 동작에는 button을 사용합니다.
- [ ] 폼 control에는 사용자가 이해할 수 있는 programmatic name이 있습니다.
- [ ] icon-only button에도 accessible name이 있습니다.
- [ ] 반복되는 control은 대상이 서로 구분되는 accessible name을 가집니다.
- [ ] heading, `main`, form, list와 `article`을 내용의 의미에 맞게 사용합니다.
- [ ] 중요한 대기, 실패, 충돌과 저장 결과를 필요한 경우 live region으로 알립니다.
- [ ] live region이 사소한 모든 UI 변화까지 과도하게 알리지 않습니다.
- [ ] 키보드만으로 주요 기능을 처음부터 끝까지 완료할 수 있습니다.
- [ ] 편집기 열기, 취소, 성공, 일반 실패와 충돌 뒤 focus 위치를 정했습니다.
- [ ] dialog나 inline editor가 닫힌 뒤 focus가 사라지지 않고 논리적인 시작 요소로 돌아갑니다.
- [ ] `autoFocus` 하나로 전체 focus 정책을 대신하지 않습니다.
- [ ] `:focus-visible` 또는 동등한 focus indicator가 실제 화면에서 분명히 보입니다.
- [ ] 상태를 색 하나로만 구분하지 않습니다.

## 좁은 화면과 motion

- [ ] 320px처럼 좁은 viewport에서도 핵심 작업과 문장이 사용할 수 있는 상태로 남습니다.
- [ ] browser zoom과 단순 viewport 축소가 완전히 같은 검사가 아님을 이해합니다.
- [ ] 가능한 범위에서 200% 확대 또는 이에 준하는 layout 압력을 확인했습니다.
- [ ] 공백 없는 긴 문자열, 긴 번역, 긴 오류 문구와 큰 글자에서도 중요한 content가 넘치지 않습니다.
- [ ] input, select와 flex/grid child에 필요한 `min-width: 0` 또는 동등한 제약이 있습니다.
- [ ] page 전체의 의도치 않은 가로 넘침과 component 내부의 의도된 horizontal scroll을 구분합니다.
- [ ] image와 font가 늦게 표시되어도 큰 layout shift가 발생하지 않는지 확인했습니다.
- [ ] motion 감소 설정을 브라우저에서 활성화해 실제 computed style 또는 동작으로 확인했습니다.
- [ ] reduced motion에서도 기능 이해에 필요한 상태 변화는 유지됩니다.

## 테스트

- [ ] 가장 큰 사용자 위험과 이를 검출할 테스트를 먼저 적었습니다.
- [ ] 각 테스트가 잡아야 할 잘못된 구현을 한 문장으로 설명할 수 있습니다.
- [ ] parser, validation, 상태 전이와 요청 수명 관리자는 가능한 범위에서 DOM 없이 검사합니다.
- [ ] Route Handler의 입력, 상태 코드, header와 응답 본문을 직접 검사합니다.
- [ ] Next.js type generation이 필요하다면 clean checkout과 CI에서 재현 가능한 script에 포함되어 있습니다.
- [ ] 요청 완료 순서를 고정 `sleep` 없이 테스트가 직접 제어합니다.
- [ ] 이전 request의 abort와 오래된 결과 폐기를 서로 다른 계약으로 검사합니다.
- [ ] 오래된 성공과 오래된 실패가 최신 화면을 덮지 않는지 확인합니다.
- [ ] unmount 뒤 완료된 이전 요청이 상태를 반영하지 않는지 확인합니다.
- [ ] 예상하지 않은 애플리케이션 API 요청을 발견할 수 있습니다.
- [ ] keyboard, focus, history, layout은 실제 브라우저에서 검사합니다.
- [ ] 운영 빌드 뒤 실제 운영 시작 명령으로 서버를 실행해 브라우저 테스트를 수행합니다.
- [ ] cookie, storage, 서버 fixture, feature flag와 route mock을 테스트 사이에 필요한 범위에서 초기화합니다.
- [ ] browser `console.error`, page error와 서버 오류를 수집합니다.
- [ ] 실패 trace, screenshot, video가 필요한 경우 보존됩니다.
- [ ] 항상 재현되는 오류를 retry로 숨기지 않습니다.
- [ ] 테스트 이름이 내부 구현보다 사용자 계약을 설명합니다.

## 성능

- [ ] 변경 전 baseline 또는 성능 예산이 있습니다.
- [ ] "JavaScript 크기"가 압축 전/후 또는 첫 route 실제 응답 합 중 무엇을 뜻하는지 측정 정의를 정했습니다.
- [ ] 운영 build에서 첫 route의 application JavaScript 크기를 같은 기준으로 비교합니다.
- [ ] DOM element 수가 기능 크기에 비해 갑자기 증가하지 않았습니다.
- [ ] 작은 상호작용 때문에 `"use client"` 경계가 불필요하게 넓어지지 않았습니다.
- [ ] 선택 기능과 큰 library가 첫 route에 불필요하게 포함되지 않습니다.
- [ ] memoization은 실제 측정한 병목이나 비용이 있을 때 사용합니다.
- [ ] 구조적 예산이 실제 사용자 성능 지표 전체를 대신하지 않는다는 점을 이해합니다.
- [ ] 예산을 초과했을 때 이유를 확인하지 않고 기준 숫자만 올리지 않습니다.
- [ ] 배포 전후의 실제 사용자 성능 측정값을 비교할 방법이 있습니다.

## 운영 실행

- [ ] 고정 설치, 운영 빌드와 실제 운영 시작 명령을 문서화했습니다.
- [ ] 필요한 Node.js 버전, runtime 환경 변수, listen host와 port 지정 방법을 문서화했습니다.
- [ ] build 성공과 start 성공을 서로 다른 검증 단계로 취급합니다.
- [ ] smoke test가 실제 배포 방식과 같은 runtime artifact를 실행합니다.
- [ ] liveness와 readiness를 분리할 필요가 있는지 판단했습니다.
- [ ] health/readiness endpoint가 무엇을 의미하는지 명확합니다.
- [ ] health 응답은 필요한 필드만 반환하고 `Cache-Control: no-store`를 포함합니다.
- [ ] health에 환경 변수 전체, credential, stack trace, filesystem path 같은 민감 정보가 없습니다.
- [ ] 릴리스 식별자를 health, 서버 log와 오류 기록에서 찾을 수 있습니다.
- [ ] health의 release가 실행 프로세스에 넣은 release id와 일치합니다.
- [ ] 테스트 전용 endpoint는 test mode와 token이 모두 없으면 동작하지 않습니다.
- [ ] 테스트 전용 endpoint가 실제 운영 데이터에 접근하지 않습니다.
- [ ] 서버 전용 canary가 HTML, health와 초기 application JavaScript 응답에 없습니다.
- [ ] canary 검사가 모든 secret 노출을 증명하는 검사가 아니라 regression detector라는 점을 이해합니다.
- [ ] standalone smoke test는 매 실행에서 충돌하지 않는 port와 network timeout을 사용합니다.
- [ ] readiness는 고정 sleep보다 polling과 전체 deadline으로 확인합니다.
- [ ] child process가 startup 중 조기 종료되면 health timeout과 구분해 보고합니다.
- [ ] startup 실패 시 제한된 stdout/stderr를 확인할 수 있습니다.
- [ ] smoke test 검사 실패 여부와 관계없이 cleanup이 실행됩니다.
- [ ] 기능 검사 실패와 cleanup 실패를 둘 다 보고할 수 있습니다.
- [ ] `SIGTERM` 뒤 정해진 grace period 안에 정상 종료하는지 확인합니다.
- [ ] package manager나 wrapper가 만든 하위 프로세스까지 종료합니다.
- [ ] 강제 종료가 필요했던 사실을 정상적인 graceful shutdown 성공으로 숨기지 않습니다.
- [ ] health, smoke와 browser E2E가 서로 다른 계약을 검사합니다.
- [ ] 애플리케이션이 제공할 실행 정보와 인프라가 제공할 환경을 구분했습니다.

## 장애 원인을 줄이는 순서

1. 같은 URL, 사용자, 입력과 release에서 다시 발생하는지 확인합니다.
2. 예상한 release와 실제 health/log의 release id가 같은지 확인합니다.
3. 개발 서버와 운영 build/start 결과를 비교합니다.
4. 서버 렌더링, hydration, 사용자 event 이후 중 어느 시점부터 값이 달라지는지 찾습니다.
5. URL에 적용된 값, 사용자가 작성 중인 입력 초안과 서버 확정값을 각각 확인합니다.
6. HTTP method, URL, 상태 코드, response body와 요청 완료 순서를 확인합니다.
7. 이전 generation의 응답, 중복 명령과 `version` 충돌 가능성을 확인합니다.
8. 외부 응답이 HTTP에는 성공했지만 runtime 계약 검증에는 실패했는지 확인합니다.
9. 데이터는 맞지만 DOM, CSS, accessible name 또는 focus 표현만 잘못되었는지 분리합니다.
10. request id와 release id로 브라우저 오류와 서버 기록을 연결합니다.
11. 원인과 직접 관련된 한 부분만 수정하고 같은 조건에서 다시 실행합니다.
12. 수정한 단위 계약과 핵심 운영 브라우저 동작을 모두 다시 검사합니다.

## Rewind 선택

- 실행 환경, package, module 경계와 route 추적 문제: `01-project-onboarding.md`
- 상태의 source of truth, 입력 초안과 외부 입력 검사 문제: `02-ui-and-state-architecture.md`
- URL/history, Effect, 요청 순서, 취소와 낙관적 갱신 문제: `03-nextjs-data-effects-and-concurrency.md`
- 테스트 선택, keyboard, focus, 반응형과 성능 문제: `04-testing-accessibility-and-performance.md`
- health/readiness, release, 비밀값과 운영 프로세스 문제: `05-production-runtime-contract.md`
