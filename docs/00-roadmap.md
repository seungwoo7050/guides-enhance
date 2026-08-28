# Python 가이드 로드맵

## 목표

이 과정은 Python 문법을 한 번 읽는 데서 끝나지 않습니다. 작은 프로그램의 입력과 출력 규칙을 정하고, 구현하고, 테스트하고, 설치 가능한 형태로 마무리하는 능력을 기르는 것이 목표입니다.

필수 과정을 마치면 다음 작업을 기초부터 다시 공부하지 않고 수행할 수 있어야 합니다.

- Python 파일과 패키지를 올바른 방법으로 실행합니다.
- 가변 객체의 공유와 복사 문제를 설명합니다.
- 외부 입력을 검증해 명확한 내부 타입으로 변환합니다.
- 계산 코드와 파일·터미널 입출력을 분리합니다.
- 예상한 실패와 구현 오류를 구분합니다.
- 경곗값과 실패 경로를 자동으로 검사합니다.
- 프로젝트를 설치하고 콘솔 스크립트로 실행합니다.

## 대상과 선행 지식

Python 사용 경험은 요구하지 않습니다. 변수, 조건문, 반복문, 함수는 첫 번째 문서 묶음에서 필요한 만큼 설명합니다.

다음 작업은 할 수 있어야 합니다.

- 터미널에서 현재 디렉터리를 확인합니다.
- UTF-8 텍스트 파일을 만들고 편집합니다.
- 명령의 표준 출력과 종료 상태를 확인합니다.

## 지원 환경

- Python 3.12 이상
- UTF-8 텍스트 환경
- 필수 과정: Python 3.12를 실행할 수 있는 운영체제
- 선택 과정의 POSIX 프로세스 그룹 기능: macOS 또는 Linux

필수 프로젝트는 Python 표준 라이브러리만 사용합니다.

## 최종 역량

### 1. 실행과 모듈

- 파일 실행과 `python -m` 실행의 차이를 설명합니다.
- `import`할 때 실행되어서는 안 되는 코드를 구분합니다.
- 현재 작업 디렉터리와 소스 파일의 위치를 구분합니다.
- 가상 환경에서 사용 중인 Python 인터프리터를 확인합니다.

### 2. 객체와 컬렉션

- 이름이 객체를 가리킨다는 의미를 설명합니다.
- 얕은 복사와 공유된 내부 객체를 구분합니다.
- `==`와 `is`를 올바르게 사용합니다.
- `list`, `tuple`, `dict`, `set`, `deque`를 용도와 비용에 맞게 선택합니다.

### 3. 함수, 예외와 타입

- 함수의 입력, 반환값, 실패 조건을 함수 이름과 타입에 드러냅니다.
- 외부 입력 오류는 예외로 알리고, 정상 실행 후의 불일치는 결과값으로 표현합니다.
- 타입 힌트가 실행 시 검증을 대신하지 않는다는 점을 설명합니다.

### 4. 반복과 자원 정리

- `iterable`과 `iterator`를 구분합니다.
- 생성기를 한 번만 소비되는 값으로 다룹니다.
- 파일을 `with`로 열고 예외가 발생해도 닫히도록 합니다.

### 5. 파일과 CLI

- `pathlib`로 상대 경로의 기준을 명확하게 표현합니다.
- CSV와 JSON을 표준 라이브러리로 읽습니다.
- 파싱한 값을 필드별로 다시 검증합니다.
- `stdout`, `stderr`, 종료 상태의 용도를 구분합니다.

### 6. 테스트와 패키징

- 단위·통합·종단 간 테스트를 나눕니다.
- 임시 디렉터리와 고정된 입력으로 테스트를 재현합니다.
- `pyproject.toml`, `__main__.py`, 콘솔 스크립트를 구성합니다.
- 설치된 상태에서 프로젝트를 실행합니다.

## 필수 문서

### 1부: 언어와 실행 방식

1. [실행 환경과 모듈](01-language-and-runtime/01-runtime-and-environment.md)
2. [객체와 컬렉션](01-language-and-runtime/02-objects-and-collections.md)
3. [함수, 예외 처리와 타입 검증](01-language-and-runtime/03-functions-errors-and-types.md)
4. [반복자, 생성기와 컨텍스트 관리자](01-language-and-runtime/04-iterators-generators-and-context-managers.md)

### 2부: 파일과 명령줄 프로그램

5. [파일, 구조화된 데이터와 CLI](02-automation/01-files-structured-data-and-cli.md)

### 3부: 검증과 프로젝트 구성

6. [재현 가능한 테스트](03-quality/01-testing.md)
7. [프로젝트 구조, 패키징과 타입 검사](03-quality/02-project-structure-packaging-and-typing.md)

## 필수 프로젝트: `data-report`

[`data-report`](../exercises/data-report/README.md)는 CSV 또는 JSON 파일을 읽고 `category`별 합계와 전체 합계를 출력합니다.

문서와 구현은 다음 순서로 연결합니다.

```text
실행 환경과 모듈
→ 객체와 컬렉션
→ 함수, 예외 처리와 타입 검증
→ 프로젝트 구조, 패키징과 타입 검사
→ Implementation 1: 패키지와 콘솔 스크립트
→ Implementation 1-1: 모듈 진입점
→ Implementation 2: Record와 Report
→ 반복자, 생성기와 컨텍스트 관리자
→ 파일, 구조화된 데이터와 CLI
→ 재현 가능한 테스트
→ Implementation 3: CSV/JSON 입력 검증
→ Implementation 4: category별 집계
→ Implementation 5: 텍스트/JSON 출력
→ Implementation 6: CLI와 파일 저장
→ Implementation 7: 전체 동작 검증
```

처음 네 문서를 모두 암기할 필요는 없습니다. 패키지를 만들고 데이터 모델을 정의할 수 있을 만큼 이해하면 `data-report`를 시작합니다. 이후 파일 처리와 테스트 문서를 읽으면서 프로젝트를 완성합니다.

## 필수 프로젝트 완료 기준

다음 조건을 모두 확인합니다.

- `python -m data_report --help`가 정상 종료합니다.
- CSV와 JSON 입력이 동일한 `Report`를 만듭니다.
- 헤더, 필드, `category`, `amount` 오류를 구체적으로 알립니다.
- `category`별 결과가 정렬되어 입력 순서와 무관합니다.
- 텍스트와 JSON 출력이 같은 `Report`를 사용합니다.
- `--output`을 지정하면 파일에 기록합니다.
- 정상 실행은 0, 입력·파일 오류는 2를 반환합니다.
- `python -m unittest discover -s tests -v`가 통과합니다.
- 설치 후 `data-report` 명령을 실행할 수 있습니다.

여기까지 마치면 필수 과정이 끝납니다.

## 선택 심화 문서

다음 문서는 일반 Python 개발의 선행 조건이 아니라 시스템 자동화가 필요할 때 선택하는 내용입니다.

- [외부 프로세스와 수명 관리](02-automation/02-subprocess-and-process-lifecycle.md)
- [동시성, 취소와 자원 제한](02-automation/03-concurrency-and-cancellation.md)
- [CLI 검사기 설계](03-quality/03-cli-test-runner.md)

## 선택 심화 프로젝트: `command-checker`

[`command-checker`](../exercises/command-checker/README.md)는 외부 CLI 프로그램을 실행하고 `returncode`, `stdout`, `stderr`를 예상값과 비교합니다.

다음 기능이 실제로 필요할 때 진행합니다.

- 외부 명령과 인자 실행
- 타임아웃과 출력 상한
- 자식 프로세스 정리
- 여러 사례의 제한된 병렬 실행
- JSON/JUnit 보고서
- 독립적인 wheel 빌드와 콘솔 스크립트 검증

권장 순서는 다음과 같습니다.

```text
패키지·데이터 모델·JSON 검증
→ 외부 프로세스와 수명 관리
→ 프로세스 실행·파이프 수집·프로세스 그룹 정리
→ 동시성, 취소와 자원 제한
→ 병렬 실행·보고서 생성
→ CLI 검사기 설계
→ 설치된 명령 종단 간 검증
```

## 학습 기록

각 구현 단계에서 다음 내용을 짧게 기록합니다.

- 어떤 입력을 사용했는지
- 어떤 출력과 종료 상태를 기대했는지
- 실패했을 때 실제로 무엇이 달랐는지
- 수정 후 어떤 테스트로 회귀를 막았는지

테스트 통과 여부만 남기지 말고 실패 원인과 수정 이유를 함께 적어야 같은 문제를 다시 만났을 때 활용할 수 있습니다.
