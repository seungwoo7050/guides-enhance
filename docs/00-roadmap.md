# 학습 로드맵

이 문서는 저장소의 사용 순서를 정합니다. 모든 문서를 순서대로 읽고 모든 exercise를 푸는 방식은 권장하지 않습니다.

```text
공통 기반은 먼저 익힙니다.
특정 기능은 실제로 필요해졌을 때 배웁니다.
Exercise는 개발을 마친 뒤 재구현 능력을 확인할 때 사용합니다.
```

## 1. C 공통 기반

다음 여덟 문서는 먼저 읽습니다.

1. [`편집·컴파일·실행`](01-foundations/01-edit-compile-run.md)
2. [`값·분기·반복`](01-foundations/02-values-branches-loops.md)
3. [`함수·배열·문자열`](01-foundations/03-functions-arrays-text.md)
4. [`입력 오류와 디버깅`](01-foundations/04-input-errors-debugging.md)
5. [`프로그램 구성과 전처리`](02-c-language/01-c-program-model.md)
6. [`메모리·포인터·문자열`](02-c-language/02-memory-pointers-strings.md)
7. [`자료구조와 API 작성`](02-c-language/03-data-structures-api-design.md)
8. [`빌드·링크·테스트`](02-c-language/04-build-link-test.md)

### 이 단계에서 확인할 내용

- 컴파일과 링크가 서로 다른 작업임을 설명할 수 있습니다.
- 헤더에 선언을 두고 `.c` 파일에 정의를 둘 수 있습니다.
- 전처리 결과가 하나의 번역 단위를 만든다는 점을 이해합니다.
- 포인터가 가리키는 객체의 수명을 추적할 수 있습니다.
- 할당한 메모리를 누가 해제하는지 정할 수 있습니다.
- 함수가 실패했을 때 출력 매개변수와 기존 상태를 어떻게 처리할지 정할 수 있습니다.
- Makefile에서 입력 파일과 생성 파일의 관계를 읽을 수 있습니다.
- 컴파일러 경고, 테스트와 sanitizer 결과를 구분해서 볼 수 있습니다.

이 단계에서는 exercise를 먼저 완료할 필요가 없습니다. 작은 C 프로그램을 직접 작성할 수 있다면 실제 구현을 시작합니다.

## 2. 개발 중 필요한 문서 찾기

| 문제가 나타나는 시점 | 읽을 문서 | 확인할 내용 |
| --- | --- | --- |
| 가변 인자를 읽고 포맷 문자열을 해석할 때 | [`05-variadic-format-api.md`](02-c-language/05-variadic-format-api.md) | `va_list`, 기본 인자 승격, 잘린 출력의 전체 길이 |
| `read`/`write`, EOF, 남은 입력을 다룰 때 | [`01-posix-io-streams.md`](03-unix-programming/01-posix-io-streams.md) | 부분 입출력, `EINTR`, 파일 디스크립터 소유자 |
| 외부 프로그램을 파이프로 연결할 때 | [`02-process-fd-pipe.md`](03-unix-programming/02-process-fd-pipe.md) | `fork`, `dup2`, `exec`, `waitpid`, 사용하지 않는 FD 닫기 |
| 시그널을 안전하게 일반 코드로 전달할 때 | [`03-signals-events.md`](03-unix-programming/03-signals-events.md) | 시그널 처리기, `sig_atomic_t`, 시그널 마스크, self-pipe |
| 명령 문자열을 인자로 나누고 실행할 때 | [`04-shell-parser-executor.md`](03-unix-programming/04-shell-parser-executor.md) | 따옴표와 escape, 전체 문법 검사, `argv` 수명 |
| 여러 스레드가 같은 값을 읽고 바꿀 때 | [`05-threads-time.md`](03-unix-programming/05-threads-time.md) | mutex, 잠금 순서, 교착 상태, 단조 시계 |

## 3. Appendix 사용 시점

Appendix는 처음부터 읽지 않습니다.

- [`01-debugger-reference.md`](90-appendix/01-debugger-reference.md): 재현 가능한 오류를 디버거로 추적할 때 사용합니다.
- [`02-readline-integration.md`](90-appendix/02-readline-integration.md): 대화형 입력과 Readline이 반환한 메모리를 다룰 때 사용합니다.
- [`03-unix-text-testing.md`](90-appendix/03-unix-text-testing.md): stdout, stderr, 종료 상태와 텍스트 출력을 셸에서 검사할 때 사용합니다.

## 4. Exercise로 개발 능력 재확인하기

Exercise는 관련 주제를 처음 배우기 위한 선행 과제가 아닙니다. 실제 개발에서 사용한 지식을 다른 작은 문제에 다시 적용할 수 있는지 확인합니다.

바로 이어서 구현하면 기존 코드가 작업 기억에 남아 있어 재확인 효과가 약합니다. 가능하면 며칠 이상의 간격을 두고 README와 공개 헤더만 보고 작성합니다.

### 핵심 exercise

| Exercise | 다시 확인하는 능력 |
| --- | --- |
| [`owned-string`](../exercises/owned-string/) | 동적 메모리 소유권, 별칭 입력, 크기 계산, 할당 실패 후 상태 보존 |
| [`diagnostic-formatter`](../exercises/diagnostic-formatter/) | 가변 인자 타입 규칙, 포맷 해석, 제한된 버퍼에 안전하게 쓰기 |
| [`record-stream`](../exercises/record-stream/) | 부분 읽기, EOF, 호출 사이의 남은 입력, 출력 메모리 소유자 |
| [`signal-loop`](../exercises/signal-loop/) | 시그널 처리기와 일반 코드 분리, 시그널 마스크, 자원 정리 순서 |
| [`command-runner`](../exercises/command-runner/) | 토큰화, 명령 모델 소유권, `fork`/`exec`, 파이프와 종료 상태 |
| [`account-simulator`](../exercises/account-simulator/) | mutex 잠금 순서, 두 값을 한 번에 변경하기, 일관된 조회 |

### 진단용 exercise

- [`int-vector`](../exercises/int-vector/): 동적 배열의 크기 증가와 실패 처리만 따로 확인합니다.
- [`command-pipeline`](../exercises/command-pipeline/): 두 프로세스와 파일 디스크립터 정리만 따로 확인합니다.

## 5. Exercise 완료 기준

다음 조건을 모두 만족해야 합니다.

1. 기존 구현과 가이드를 보지 않고 작성했습니다.
2. 공개 함수의 성공·실패 반환값을 설명할 수 있습니다.
3. 메모리, 파일 디스크립터, 프로세스나 mutex의 소유자와 정리 시점을 설명할 수 있습니다.
4. 실패가 발생한 뒤 어떤 값이 유지되는지 설명할 수 있습니다.
5. 정상 입력뿐 아니라 경계값과 실패 사례를 테스트했습니다.
6. 해당 exercise 디렉터리에서 `make test`와 `make sanitize`를 통과했습니다.

통과하지 못했다면 실패 원인을 좁힙니다.

```text
메모리와 크기 계산 문제       → owned-string 또는 int-vector
가변 인자와 출력 길이 문제    → diagnostic-formatter
부분 입출력과 EOF 문제         → record-stream
시그널 처리 문제               → signal-loop
파일 디스크립터와 프로세스 문제 → command-pipeline
여러 기능을 합치는 문제        → command-runner
공유 상태와 잠금 순서 문제      → account-simulator
```

## 전체 완료 기준

다음 질문에 코드 수준으로 답할 수 있으면 이 저장소의 핵심 목표를 달성한 것입니다.

- 이 포인터가 가리키는 객체는 언제까지 유효합니까?
- 할당한 메모리나 연 파일 디스크립터를 누가 정리합니까?
- 함수가 실패하면 호출 전 상태 중 무엇이 유지됩니까?
- 덧셈이나 크기 계산 전에 overflow를 어떻게 검사합니까?
- `fork` 뒤 부모와 각 자식이 어떤 파일 디스크립터를 닫습니까?
- 문법 오류가 있을 때 외부 프로그램이 실행되지 않도록 어떻게 보장합니까?
- 시그널 처리기에서 일반 함수 호출을 피해야 하는 이유는 무엇입니까?
- 두 스레드가 반대 방향으로 작업해도 교착 상태가 생기지 않도록 어떤 순서로 mutex를 잠급니까?
- 테스트가 확인한 동작과 아직 확인하지 않은 동작은 무엇입니까?
