# 재현 가능한 테스트

## 학습 목표

좋은 테스트는 사례 수가 많은 테스트가 아니라 무엇을 확인하고 어떤 잘못된 구현을 잡아내는지 설명할 수 있는 테스트입니다.

이 문서에서는 다음 내용을 다룹니다.

- 계산 코드와 파일·프로세스 입출력을 나눠 테스트하는 방법
- 단위·통합·종단 간 테스트의 역할
- 경곗값과 실패 경로를 선택하는 방법
- 표 기반 테스트, 작은 입력 전수 검사, 고정 시드 사용
- 임시 디렉터리와 테스트용 입력·프로그램으로 외부 상태를 재현하는 방법

필수 프로젝트인 [`data-report`](../../exercises/data-report/README.md)는 입력 검증부터 CLI까지 표준 라이브러리 `unittest`로 검사합니다.

## 선행 개념

- 외부 상태에 의존하지 않는 계산과 파일·프로세스 입출력을 구분할 수 있어야 합니다.
- 정상 사례, 경계 사례, 실패 사례를 나누어 생각할 수 있어야 합니다.

## 계산 코드와 부작용 분리하기

```python
def normalize_words(text: str) -> list[str]:
    return sorted({word.lower() for word in text.split()})
```

위 함수는 파일이나 프로세스 없이 직접 테스트할 수 있습니다.

```python
import unittest


class NormalizeWordsTest(unittest.TestCase):
    def test_removes_duplicates_and_sorts(self) -> None:
        self.assertEqual(normalize_words("B a b"), ["a", "b"])
```

CLI처럼 실제 실행 환경까지 확인해야 하는 부분은 소수의 종단 간 테스트로 보완합니다.

`data-report`에서는 다음처럼 나눕니다.

```text
load_records()  → 실제 임시 파일을 사용하는 통합 테스트
aggregate()     → Record와 Report만 사용하는 단위 테스트
render_text()   → 문자열 결과를 확인하는 단위 테스트
main()          → stdout, stderr, 출력 파일, 종료 상태를 확인하는 통합 테스트
설치된 명령     → 콘솔 스크립트를 실행하는 종단 간 테스트
```

## 테스트 수준 구분하기

| 수준 | 확인하는 범위 | 예시 |
|---|---|---|
| 단위 테스트 | 함수나 타입 하나의 동작 | `Decimal` 합산, `category` 정렬 |
| 통합 테스트 | 여러 모듈과 실제 자원의 연결 | CSV 파일 읽기와 JSON 파일 저장 |
| 종단 간 테스트 | 사용자가 실행하는 최종 진입점 | `python -m data_report` 또는 설치된 `data-report` |

모든 테스트를 하위 프로세스로 실행하면 느리고 실패 원인을 찾기 어렵습니다. 반대로 단위 테스트만 작성하면 CLI 인자, 현재 작업 디렉터리, 출력 스트림, 종료 상태 같은 실제 실행 조건이 빠집니다.

## 경곗값과 분기 겨냥하기

일반적으로 다음 사례를 확인합니다.

- 빈 입력과 최소 입력
- 중복 값
- 마지막 원소에서만 상태가 바뀌는 경우
- 정상값과 오류값이 갈리는 경계의 바로 앞·뒤 값
- 잘못된 타입과 허용하지 않은 필드
- 존재하지 않는 파일과 쓰기 실패
- 유한하지 않은 숫자
- 일부 작업이 성공한 뒤 발생하는 정리 실패

예제 입력을 단순히 여러 개 복사하지 말고, 각 테스트가 어떤 분기와 잘못된 구현을 잡는지 이름에 드러냅니다.

예를 들어 다음 이름은 의도가 구체적입니다.

```text
test_validation_rejects_unknown_fields
test_validation_rejects_non_finite_amount
test_aggregation_sorts_categories_and_uses_decimal
test_cli_reports_invalid_input
```

## 표 기반 테스트

```python
cases = [
    ("", []),
    ("a", ["a"]),
    ("B a b", ["a", "b"]),
]

for input_text, expected in cases:
    with self.subTest(input_text=input_text):
        self.assertEqual(normalize_words(input_text), expected)
```

테스트가 실패했을 때는 입력, 기대값, 실제값을 확인할 수 있어야 합니다.

표 기반 테스트는 같은 규칙에 여러 입력을 적용할 때 적합합니다. 서로 다른 실패 원인을 한 반복문에 억지로 묶으면 어떤 규칙이 깨졌는지 알기 어려우므로 별도 테스트로 나눕니다.

## 작은 입력 공간 전수 검사하기

입력 공간이 충분히 작다면 모든 조합을 확인할 수 있습니다.

```python
from itertools import product

for values in product(range(3), repeat=4):
    self.assertEqual(optimized(values), reference(values))
```

입력 크기가 커지면 조합 수가 급격히 늘어납니다. 가능한 조합 수를 계산한 뒤 현실적인 범위에서만 사용합니다.

## 재현 가능한 무작위 테스트

```python
import random

rng = random.Random(4242)
for _ in range(500):
    values = [
        rng.randint(-100, 100)
        for _ in range(rng.randint(0, 30))
    ]
    self.assertEqual(optimized(values), reference(values))
```

시드를 고정하고 실패 시 실제 입력도 출력해야 합니다. 여러 테스트가 전역 난수 상태를 공유하면 실행 순서에 따라 결과가 달라질 수 있으므로 테스트 전용 `Random` 객체를 사용합니다.

## 독립적인 기준 구현 사용하기

최적화한 구현과 기준 구현은 동작 규칙만 공유하는 편이 좋습니다. 양쪽이 같은 내부 보조 함수를 재사용하면 동일한 버그가 두 구현에 함께 들어가 잘못된 결과가 통과할 수 있습니다.

`command-checker`에서는 프로세스 수집과 결과 비교를 분리합니다. 프로세스를 실행하는 코드가 예상값 비교까지 다시 구현하지 않고, 수집한 값을 순수 비교 함수에 전달합니다.

## 실패 주입하기

정상 경로만 테스트하면 자원 정리와 오류 처리 동작을 확인할 수 없습니다.

- 파일을 읽을 수 없음
- 출력 파일을 쓸 수 없음
- 잘못된 CSV 헤더
- JSON에 예상하지 않은 필드가 있음
- 숫자가 `NaN` 또는 `Infinity`임
- 프로세스가 타임아웃을 넘김
- 자식 프로세스가 파이프를 계속 열어 둠
- `stdout`을 제한 없이 출력함

실패를 반복해서 재현할 수 있도록 임시 디렉터리, 전용 테스트 프로그램, 필요한 경우 모의 객체를 사용합니다.

## 임시 디렉터리 사용하기

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    input_path = root / "data.csv"
    output_path = root / "report.json"
    ...
```

테스트가 실제 사용자 파일을 읽거나 덮어쓰지 않게 합니다. 테스트마다 새 디렉터리를 사용하면 실행 순서에 따른 상태 공유도 줄어듭니다.

## 출력과 종료 상태 검사하기

함수를 직접 호출할 수 있다면 `stdout`과 `stderr`를 임시 스트림으로 바꿔 검사할 수 있습니다.

```python
import contextlib
import io

stderr = io.StringIO()
with contextlib.redirect_stderr(stderr):
    status = main(["missing.txt"])

self.assertEqual(status, 2)
self.assertIn("input file", stderr.getvalue())
```

실제 모듈 진입점과 콘솔 스크립트는 하위 프로세스로 별도 확인합니다. 이때 `check=False`로 실행해 종료 상태와 두 출력 스트림을 직접 검사합니다.

## 환경에 의존하는 테스트

POSIX 프로세스 그룹 테스트는 macOS와 Linux에서만 실행할 수 있습니다. 다른 운영체제에서는 지원 범위 밖임을 명확하게 표시해야 합니다.

```python
@unittest.skipUnless(os.name == "posix", "POSIX 프로세스 그룹이 필요합니다.")
def test_timeout_terminates_spawned_process_group(self) -> None:
    ...
```

실행할 수 없는 테스트를 성공한 것으로 보고해서는 안 됩니다. 건너뛴 이유를 구체적으로 남깁니다.

## 프로젝트에 적용하기

### 필수: `data-report`

다음 오류를 잡아야 합니다.

- CSV와 JSON이 서로 다른 `Report`를 만드는 구현
- 예상하지 않은 필드를 조용히 무시하는 구현
- `NaN`을 합계에 포함하는 구현
- `float` 오차가 합계에 남는 구현
- `category` 출력 순서가 입력 순서에 따라 바뀌는 구현
- `--output`이 지정되어도 `stdout`에만 쓰는 구현
- 입력 오류를 종료 상태 0으로 처리하는 구현

### 선택: `command-checker`

다음 오류를 잡아야 합니다.

- 타임아웃과 출력 상한을 같은 실패로 처리하는 구현
- 병렬 완료 순서를 그대로 결과 순서로 사용하는 구현
- XML 1.0에서 허용하지 않는 문자를 보고서에 그대로 쓰는 구현
- 타임아웃 뒤 자식 프로세스를 남기는 구현

## 완료 기준

- 각 테스트 이름이 확인하려는 동작을 설명합니다.
- 단위·통합·종단 간 테스트가 역할에 따라 나뉘어 있습니다.
- 경곗값과 실패 경로를 반복해서 재현할 수 있습니다.
- 무작위 테스트는 시드와 실패 입력을 남깁니다.
- 임시 디렉터리를 사용해 테스트 간 파일 상태를 공유하지 않습니다.
- 지원하지 않는 환경의 테스트는 구체적인 이유와 함께 건너뜁니다.

다음은 [프로젝트 구조, 패키징과 타입 검사](02-project-structure-packaging-and-typing.md)입니다.
