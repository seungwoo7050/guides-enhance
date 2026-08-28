# Python

Python으로 작은 프로그램을 설계하고, 외부 입력을 검증하며, 테스트와 패키징까지 마무리하는 과정을 정리한 저장소입니다.

문법을 빠르게 훑는 데서 끝내지 않습니다. 다음 작업을 혼자 반복할 수 있는 수준을 목표로 합니다.

```text
실행 방법과 입력 규칙을 정합니다.
→ 데이터를 명확한 타입으로 변환합니다.
→ 계산과 파일 입출력을 분리합니다.
→ 오류와 경곗값을 테스트합니다.
→ 설치해서 실행할 수 있는 프로젝트로 완성합니다.
```

## 완료 후 갖춰야 할 역량

필수 과정을 마치면 다음 내용을 설명하고 구현할 수 있어야 합니다.

- 스크립트 실행과 `python -m` 실행의 차이를 설명합니다.
- 이름과 객체, 가변성과 불변성, `==`와 `is`를 구분합니다.
- 함수의 입력·반환값·실패 조건을 명확히 정합니다.
- 타입 힌트와 실행 시 입력 검증의 역할을 구분합니다.
- 반복자와 생성기, 컨텍스트 관리자로 데이터 처리와 자원 정리를 표현합니다.
- `pathlib`, CSV, JSON, `argparse`를 사용해 작은 CLI 프로그램을 작성합니다.
- 단위 테스트, 통합 테스트, 종단 간 테스트를 목적에 맞게 나눕니다.
- `pyproject.toml`, 모듈 진입점, 콘솔 스크립트를 포함한 Python 프로젝트를 구성합니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs
│   ├── 00-roadmap.md
│   ├── 01-language-and-runtime
│   │   ├── 01-runtime-and-environment.md
│   │   ├── 02-objects-and-collections.md
│   │   ├── 03-functions-errors-and-types.md
│   │   └── 04-iterators-generators-and-context-managers.md
│   ├── 02-automation
│   │   ├── 01-files-structured-data-and-cli.md
│   │   ├── 02-subprocess-and-process-lifecycle.md
│   │   └── 03-concurrency-and-cancellation.md
│   └── 03-quality
│       ├── 01-testing.md
│       ├── 02-project-structure-packaging-and-typing.md
│       └── 03-cli-test-runner.md
└── exercises
    ├── data-report
    └── command-checker
```

`docs/`에는 구현에 필요한 개념을 정리합니다. `exercises/`에는 다른 저장소로 옮겨도 빌드·실행·테스트할 수 있는 완성된 프로젝트를 둡니다.

## 필수 학습 범위

### 1. 언어와 실행 방식

- [실행 환경과 모듈](docs/01-language-and-runtime/01-runtime-and-environment.md)
- [객체와 컬렉션](docs/01-language-and-runtime/02-objects-and-collections.md)
- [함수, 예외 처리와 타입 검증](docs/01-language-and-runtime/03-functions-errors-and-types.md)
- [반복자, 생성기와 컨텍스트 관리자](docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md)

Python 코드가 어떻게 실행되는지, 값이 어떻게 공유되는지, 함수가 어떤 입력을 받고 어떻게 실패하는지를 먼저 익힙니다.

### 2. 파일, 구조화된 데이터와 CLI

- [파일, 구조화된 데이터와 CLI](docs/02-automation/01-files-structured-data-and-cli.md)

파일을 읽고 CSV와 JSON을 검증한 뒤 프로그램 내부에서 사용할 값으로 변환하는 방법을 다룹니다. 정상 출력과 오류 출력을 분리하고 종료 상태를 반환하는 방법도 함께 익힙니다.

### 3. 테스트와 프로젝트 구성

- [재현 가능한 테스트](docs/03-quality/01-testing.md)
- [프로젝트 구조, 패키징과 타입 검사](docs/03-quality/02-project-structure-packaging-and-typing.md)

구현을 함수 단위와 실제 실행 단위로 검증하고 설치 가능한 Python 패키지로 정리합니다.

## 필수 프로젝트

### [`data-report`](exercises/data-report)

CSV 또는 JSON 파일을 읽어 `category`별 합계와 전체 합계를 만드는 CLI 프로그램입니다.

이 프로젝트에서 다음 작업을 직접 확인합니다.

- 패키지와 모듈 진입점 구성
- 불변 `Record`와 `Report` 정의
- CSV/JSON 필드 검증
- `Decimal` 기반 합산
- 입력 순서와 무관한 결과 정렬
- 텍스트/JSON 출력
- 파일 저장과 종료 상태 처리
- `unittest` 기반 검증
- 콘솔 스크립트 설치

`data-report`의 테스트와 설치 실행까지 통과하면 필수 과정이 끝납니다.

## 선택 심화 범위

다음 내용은 일반 Python 개발에 반드시 필요한 선행 지식이 아닙니다. 외부 프로그램을 안전하게 실행하거나 여러 작업을 동시에 처리해야 할 때 학습합니다.

- [외부 프로세스와 수명 관리](docs/02-automation/02-subprocess-and-process-lifecycle.md)
- [동시성, 취소와 자원 제한](docs/02-automation/03-concurrency-and-cancellation.md)
- [CLI 검사기 설계](docs/03-quality/03-cli-test-runner.md)
- [`command-checker`](exercises/command-checker)

`command-checker`는 JSON에 기록한 예상값에 따라 외부 CLI 프로그램을 실행하고 결과를 검사합니다. 타임아웃, 출력 상한, POSIX 프로세스 그룹 정리, 병렬 실행, JSON/JUnit 보고서까지 다루므로 시스템 자동화가 필요할 때 선택해서 진행합니다.

## 권장 진행 순서

```text
00-roadmap
→ 실행 환경과 모듈
→ 객체와 컬렉션
→ 함수, 예외 처리와 타입 검증
→ 프로젝트 구조, 패키징과 타입 검사
→ data-report: 패키지와 데이터 모델
→ 반복자, 생성기와 컨텍스트 관리자
→ 파일, 구조화된 데이터와 CLI
→ 재현 가능한 테스트
→ data-report: 입력 검증, 집계, 출력, CLI, 테스트
→ 설치 후 실행 확인
→ 필수 과정 완료
```

모든 문서를 먼저 읽은 뒤 구현을 시작하지 않습니다. `data-report`를 시작할 수 있는 개념을 익히면 곧바로 프로젝트를 만들고, 필요한 문서를 이어서 읽으면서 기능을 완성합니다.

선택 심화 과정은 다음 순서가 적절합니다.

```text
command-checker의 패키지·데이터 모델·JSON 검증
→ 외부 프로세스와 수명 관리
→ 프로세스 실행과 파이프 정리
→ 동시성, 취소와 자원 제한
→ 병렬 실행과 보고서
→ CLI 검사기 설계
→ 설치·종단 간 검증
```

## 완료 기준

필수 과정은 다음 조건을 모두 만족하면 완료한 것으로 봅니다.

- `data-report`의 CSV와 JSON 입력이 같은 `Report`를 만듭니다.
- 잘못된 필드, 빈 `category`, 유효하지 않은 `amount`를 거부합니다.
- 합산에 `Decimal`을 사용하며 결과 순서가 항상 같습니다.
- 정상 결과는 `stdout`, 오류는 `stderr`에 출력합니다.
- 성공은 종료 상태 0, 입력 또는 파일 오류는 종료 상태 2를 반환합니다.
- 프로젝트 내부 테스트가 모두 통과합니다.
- wheel을 설치하거나 프로젝트를 직접 설치한 뒤 `data-report` 콘솔 스크립트를 실행할 수 있습니다.

## 요구 환경

- Python 3.12 이상
- UTF-8 텍스트 환경

필수 과정은 Python 3.12를 실행할 수 있는 운영체제에서 진행할 수 있습니다. `command-checker`의 프로세스 그룹 종료와 논블로킹 파일 디스크립터 처리는 macOS와 Linux를 대상으로 합니다.
