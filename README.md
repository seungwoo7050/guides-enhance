# C와 POSIX 프로그래밍 가이드

이 저장소는 C로 프로그램을 작성할 때 반복해서 필요한 기본 지식과 POSIX API 사용법을 정리합니다. 모든 문서를 먼저 외운 뒤 개발을 시작하는 방식이 아니라, C의 공통 기반을 익힌 다음 실제 구현 중 필요한 내용을 찾아 쓰는 방식을 전제로 합니다.

```text
C 공통 기반을 읽습니다.
→ 실제 프로그램을 구현합니다.
→ 필요한 주제가 나오면 관련 문서를 찾아봅니다.
→ 구현을 마친 뒤 일정 시간을 둡니다.
→ exercise의 요구사항만 보고 다시 구현합니다.
```

Exercise는 프로젝트 진입 조건이 아닙니다. 이미 사용해 본 지식을 다른 문제에도 적용할 수 있는지 확인하는 용도입니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── 00-roadmap.md
│   ├── 01-foundations/
│   ├── 02-c-language/
│   ├── 03-unix-programming/
│   └── 90-appendix/
└── exercises/
    ├── owned-string/
    ├── diagnostic-formatter/
    ├── record-stream/
    ├── signal-loop/
    ├── command-runner/
    ├── account-simulator/
    ├── int-vector/
    └── command-pipeline/
```

- `docs/`: C와 POSIX API를 설명합니다.
- `exercises/`: 다른 저장소로 옮겨도 빌드하고 테스트할 수 있는 완성된 작은 프로젝트입니다.

전체 사용 순서는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 확인합니다.

## 먼저 읽을 문서

다음 여덟 문서는 특정 프로그램에만 필요한 내용이 아니라 대부분의 C 개발에서 계속 사용하므로 먼저 읽는 편이 좋습니다.

### 기본 개발 과정

- [`편집·컴파일·실행`](docs/01-foundations/01-edit-compile-run.md)
- [`값·분기·반복`](docs/01-foundations/02-values-branches-loops.md)
- [`함수·배열·문자열`](docs/01-foundations/03-functions-arrays-text.md)
- [`입력 오류와 디버깅`](docs/01-foundations/04-input-errors-debugging.md)

### C 프로그램 작성에 공통으로 필요한 내용

- [`프로그램 구성과 전처리`](docs/02-c-language/01-c-program-model.md)
- [`메모리·포인터·문자열`](docs/02-c-language/02-memory-pointers-strings.md)
- [`자료구조와 API 작성`](docs/02-c-language/03-data-structures-api-design.md)
- [`빌드·링크·테스트`](docs/02-c-language/04-build-link-test.md)

## 필요할 때 읽을 문서

| 구현할 내용 | 문서 |
| --- | --- |
| 가변 인자와 포맷 문자열 | [`05-variadic-format-api.md`](docs/02-c-language/05-variadic-format-api.md) |
| `read`, `write`, EOF와 부분 입출력 | [`01-posix-io-streams.md`](docs/03-unix-programming/01-posix-io-streams.md) |
| `fork`, `exec`, 파일 디스크립터와 파이프 | [`02-process-fd-pipe.md`](docs/03-unix-programming/02-process-fd-pipe.md) |
| 시그널 처리와 비동기 이벤트 전달 | [`03-signals-events.md`](docs/03-unix-programming/03-signals-events.md) |
| 명령 문자열 파싱과 외부 프로그램 실행 | [`04-shell-parser-executor.md`](docs/03-unix-programming/04-shell-parser-executor.md) |
| pthread, mutex, 교착 상태와 시간 측정 | [`05-threads-time.md`](docs/03-unix-programming/05-threads-time.md) |

디버거, Readline, Unix 명령을 이용한 출력 검사는 [`docs/90-appendix/`](docs/90-appendix/)에서 필요할 때 찾아봅니다.

## Exercise 사용법

### 핵심 재확인 프로젝트

- [`owned-string`](exercises/owned-string/): 동적 메모리, 별칭 입력, 크기 증가 실패 후 상태 보존
- [`diagnostic-formatter`](exercises/diagnostic-formatter/): 가변 인자, 포맷 해석, 제한된 버퍼 출력
- [`record-stream`](exercises/record-stream/): 부분 읽기, EOF, 호출 사이에 남겨 둘 입력 상태
- [`signal-loop`](exercises/signal-loop/): 시그널 처리기와 일반 코드의 분리
- [`command-runner`](exercises/command-runner/): 문자열 파싱, 메모리 소유, 프로세스 실행과 정리
- [`account-simulator`](exercises/account-simulator/): mutex 순서, 원자적인 상태 변경, 일관된 조회

### 약한 부분을 좁혀 보는 프로젝트

- [`int-vector`](exercises/int-vector/): 동적 배열의 크기 증가와 실패 처리만 따로 확인합니다.
- [`command-pipeline`](exercises/command-pipeline/): 두 프로세스와 파일 디스크립터 처리만 따로 확인합니다.

권장 순서는 다음과 같습니다.

1. 실제 개발을 먼저 수행합니다.
2. 일정 시간이 지난 뒤 exercise의 README와 공개 헤더만 읽습니다.
3. 가이드와 기존 구현을 보지 않고 직접 작성합니다.
4. `make test`와 `make sanitize`를 통과시킵니다.
5. 실패했다면 관련 문서와 진단용 exercise로 원인을 좁힙니다.

## 빌드와 테스트

각 exercise는 자신의 디렉터리 안에서 빌드하고 검사합니다.

```sh
cd exercises/owned-string
make
make test
make sanitize
```

`account-simulator`는 실행 환경에서 ThreadSanitizer를 지원할 때 다음 검사도 제공합니다.

```sh
make thread-sanitize
```

각 프로젝트는 부모 디렉터리의 스크립트나 다른 exercise에 의존하지 않습니다.

## Implementation Order

Exercise의 README와 소스에는 `[Implementation N]` 표기가 있습니다. 이 번호는 파일이나 함수의 나열 순서가 아니라 구현할 때 먼저 결정해야 하는 내용을 나타냅니다.

```text
저장할 상태와 소유자를 정합니다.
→ 유효한 상태 조건을 정합니다.
→ 핵심 동작을 구현합니다.
→ 실패했을 때 보존할 값을 정합니다.
→ 자원을 정리합니다.
```

단순한 보조 함수나 일반 빌드·테스트 명령에는 번호를 붙이지 않습니다.

## 범위

이 저장소는 다음 내용을 다룹니다.

- C 프로그램의 컴파일과 링크
- 전처리기와 헤더 작성
- 포인터, 객체 수명과 동적 메모리
- 함수와 자료구조의 오류 반환 방식
- 정적 라이브러리와 Makefile
- 가변 인자 함수
- POSIX 파일 입출력, 프로세스, 파일 디스크립터, 파이프와 시그널
- 간단한 명령 파싱과 실행
- pthread와 mutex

GUI, 임베디드 하드웨어, 커널 개발, 네트워크 프로토콜 구현, 분산 시스템과 C 원자 연산의 전체 메모리 모델은 직접 다루지 않습니다.
