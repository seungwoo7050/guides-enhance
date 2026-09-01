# Runtime Workspace

하나의 pnpm workspace 안에서 실행 애플리케이션과 공유 패키지를 분리한 작은 TypeScript 프로젝트입니다. 패키지 경계, 공개 import 경로, 환경 변수 검증과 Node.js 이벤트 루프의 기본 실행 순서를 확인합니다.

## 주요 기능

- `apps/*`와 `packages/*`를 나누는 workspace 설정
- `@runtime-workspace/math`의 공개 진입점
- 입력 배열을 바꾸지 않는 `sum()`
- `unknown`에서 시작하는 TCP 포트 검사
- 패키지 내부 파일이 아닌 공개 패키지 이름으로 import
- 동기 코드, 마이크로태스크와 타이머의 실행 순서 출력

## 파일 구성

```text
runtime-workspace/
├── apps/demo/
├── packages/math/
├── tests/
├── package.json
├── pnpm-workspace.yaml
└── tsconfig.base.json
```

`apps/`는 실행 프로그램, `packages/`는 재사용 가능한 패키지를 담는 경계입니다.

공유 패키지를 가져올 때는 다음처럼 공개 이름을 사용합니다.

```text
@runtime-workspace/math
```

다음처럼 내부 소스 경로에 직접 의존하지 않습니다.

```text
packages/math/src/...
```

공개 진입점을 사용해야 패키지 내부 파일 구조가 바뀌어도 사용하는 애플리케이션의 import가 덜 깨집니다.

## 설치와 실행

```sh
corepack enable
pnpm install
pnpm typecheck
pnpm demo
```

정상 실행 결과는 다음 순서입니다.

```text
sum 6
port 4000
sync
microtask
task
```

`PORT`가 정수가 아니거나 `1..65535` 범위를 벗어나면 실행을 중단합니다.

## 환경 변수 검증

Node.js 환경 변수는 기본적으로 문자열 또는 `undefined`입니다.

따라서 다음처럼 바로 숫자로 믿으면 안 됩니다.

```text
process.env.PORT
```

검증 흐름은 다음처럼 생각합니다.

```text
unknown/string | undefined
→ 존재 여부 확인
→ 숫자 형식 확인
→ 정수인지 확인
→ 1..65535 범위 확인
→ number로 반환
```

다음 값은 거부되어야 합니다.

```text
""
"abc"
"3.14"
"NaN"
"0"
"65536"
```

다음 경계는 허용합니다.

```text
"1"
"65535"
```

환경 변수 검증이 끝난 뒤에야 애플리케이션 코드가 안전한 `number`로 사용할 수 있습니다.

## 순수한 공유 패키지

`@runtime-workspace/math`는 계산과 입력 변환만 공개하며 import 시 서버, timer 또는 다른 부작용을 시작하지 않습니다.

즉 다음 성질을 지향합니다.

```text
import package
→ 계산 함수 사용 가능
→ 프로세스가 갑자기 listen 하지 않음
→ timer가 생기지 않음
→ 테스트가 종료되지 않는 문제 없음
```

공유 패키지 import 자체가 실행 환경을 바꾸지 않게 하는 것은 재사용성과 테스트 가능성에 중요합니다.

## 입력을 수정하지 않는 `sum()`

`sum()`은 입력 배열을 읽기만 하고 원본 배열을 변경하지 않습니다.

예:

```text
input = [1, 2, 3]
sum(input) = 6
input은 여전히 [1, 2, 3]
```

호출자가 읽기 전용 배열을 넘길 수 있으므로 함수 타입과 구현 모두 입력을 소유한 것처럼 변경하지 않습니다.

## 이벤트 루프 관찰

demo는 다음 세 종류의 실행을 비교합니다.

```text
동기 코드
Promise 기반 microtask
timer task
```

출력:

```text
sync
microtask
task
```

개념적으로:

```text
현재 동기 호출 스택 실행 완료
→ microtask queue 처리
→ 이후 timer callback 같은 task 실행
```

이 예제는 Node.js 이벤트 루프 전체 규칙을 설명하는 것이 아니라, **같은 턴에서 동기 코드와 Promise microtask, timer가 어떤 상대적 순서로 보이는지**를 좁게 관찰합니다.

실제 Node.js 이벤트 루프에는 I/O, `process.nextTick`, 여러 phase 등 추가 규칙이 있으므로 이 결과 하나를 모든 비동기 실행의 절대 순서로 일반화하지 않습니다.

## 테스트

```sh
npm test
```

Node.js의 TypeScript 제거 기능을 사용하므로 의존성을 설치하지 않아도 순수 함수 테스트를 실행할 수 있습니다. 전체 package typecheck와 demo 실행은 `pnpm install` 뒤에 수행합니다.

테스트는 다음을 확인합니다.

- `sum()`이 읽기 전용 입력 배열을 수정하지 않음
- TCP 포트의 최솟값과 최댓값을 허용함
- 빈 문자열을 거부함
- 소수를 거부함
- `NaN`에 해당하는 입력을 거부함
- 범위 밖 숫자를 거부함

순수 함수 테스트와 전체 workspace typecheck는 검증 범위가 다릅니다.

```text
npm test
→ 독립 계산과 파싱 규칙

pnpm typecheck
→ workspace 패키지 사이 타입/import 연결
```

## 주요 선택

- 공유 패키지는 계산과 입력 변환만 공개하며 import 시 서버나 타이머를 시작하지 않습니다.
- 애플리케이션은 `@runtime-workspace/math`만 가져옵니다. `packages/math/src` 내부 경로는 공개 API가 아닙니다.
- 환경 변수는 문자열인 상태로 사용하지 않고 포트 범위를 확인한 뒤 숫자로 바꿉니다.
- 이벤트 루프 예제는 상대적인 실행 순서를 관찰하기 위한 것으로, Node.js의 모든 비동기 phase를 모델링하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Workspace package list | `pnpm-workspace.yaml` |
| 2 | Pure sum operation | `packages/math/src/index.ts` |
| 3 | TCP port parsing | `packages/math/src/index.ts` |
| 4 | Public package import | `apps/demo/src/index.ts` |
| 5 | Event-loop observation | `apps/demo/src/index.ts` |

먼저 workspace의 패키지 경계를 정한 뒤 순수 공유 API를 만들고, 마지막에 실행 애플리케이션에서 공개 경로를 통해 사용합니다.

## 범위와 제한

패키지 배포, 번들 생성, worker thread, stream, process signal과 실제 네트워크 서버는 구현하지 않습니다.

이 exercise는 monorepo 전체 운영을 다루기보다 다음 기본 경계를 확인합니다.

```text
workspace 구조
공개 package API
입력 검증
import 부작용 최소화
기본 이벤트 루프 순서
```