# Runtime Workspace

하나의 pnpm workspace에서 실행 애플리케이션과 공유 패키지를 분리한 작은 TypeScript 프로젝트입니다. 패키지 공개 경로, 환경 변수 검사와 Node.js 이벤트 루프의 실행 순서를 확인합니다.

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

## 테스트

```sh
npm test
```

Node.js의 TypeScript 제거 기능을 사용하므로 의존성을 설치하지 않아도 순수 함수 테스트를 실행할 수 있습니다. 전체 package typecheck와 demo 실행은 `pnpm install` 뒤에 수행합니다.

테스트는 다음을 확인합니다.

- `sum()`이 읽기 전용 입력 배열을 수정하지 않음
- TCP 포트의 최솟값과 최댓값을 허용함
- 빈 문자열, 소수, `NaN`과 범위 밖 숫자를 거부함

## 주요 선택

- 공유 패키지는 계산과 입력 변환만 공개하며 import 시 서버나 타이머를 시작하지 않습니다.
- 애플리케이션은 `@runtime-workspace/math`만 가져옵니다. `packages/math/src` 내부 경로는 공개 API가 아닙니다.
- 환경 변수는 문자열인 상태로 사용하지 않고 포트 범위를 확인한 뒤 숫자로 바꿉니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Workspace package list | `pnpm-workspace.yaml` |
| 2 | Pure sum operation | `packages/math/src/index.ts` |
| 3 | TCP port parsing | `packages/math/src/index.ts` |
| 4 | Public package import | `apps/demo/src/index.ts` |
| 5 | Event-loop observation | `apps/demo/src/index.ts` |

## 범위와 제한

패키지 배포, 번들 생성, worker thread, stream, process signal과 실제 네트워크 서버는 구현하지 않습니다.
