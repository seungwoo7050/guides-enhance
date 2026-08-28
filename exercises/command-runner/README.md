# command-runner

`command-runner`는 명령 문자열 하나를 해석해 단일 외부 프로그램이나 두 프로그램으로 이루어진 파이프를 실행하는 작은 CLI입니다. 전체 문법을 먼저 확인하고 `argv` 메모리를 완성한 뒤에만 자식 프로세스를 만듭니다.

## 지원 문법

- 인용되지 않은 공백은 인자를 나눕니다.
- 작은따옴표 안의 문자는 그대로 보존합니다.
- 큰따옴표 안의 `\`는 다음 문자 하나를 일반 문자로 만듭니다.
- 인용되지 않은 `\`도 다음 문자 하나를 일반 문자로 만듭니다.
- 붙어 있는 일반 문자와 인용 구간은 하나의 인자가 됩니다.
- `''`와 `""`는 길이 0인 인자를 만듭니다.
- 인용되지 않은 `|` 하나를 지원합니다.
- 인용되지 않은 `<`, `>`, `;`, `&`는 지원하지 않으며 문법 오류로 처리합니다.

## 종료 상태

- 문법 오류와 잘못된 CLI 인자는 `2`입니다.
- 실행 파일을 찾지 못하면 `127`입니다.
- 파일은 찾았지만 실행하지 못하면 `126`입니다.
- 시그널로 종료한 자식은 `128 + signal`입니다.
- 파이프를 실행하면 오른쪽 명령의 상태를 반환합니다.
- 부모가 `fork`나 `waitpid`를 완료하지 못하면 `125`입니다.

## 빌드와 실행

```sh
make
./build/command-runner "printf 'alpha beta\\n' | wc -w"
```

## 주요 구현 결정

문자열 builder는 문자를 모아 NUL로 끝나는 문자열을 만든 뒤 소유권을 `struct command`에 넘깁니다. 각 `command`는 자신의 `argv` 배열과 모든 word를 해제합니다.

파싱 중에는 외부 프로그램을 실행하지 않습니다. 열린 따옴표, 끝의 `\`, 빈 파이프 쪽이나 지원하지 않는 연산자를 발견하면 지금까지 할당한 단어를 정리하고 상태 `2`로 끝냅니다. 따라서 문법 오류가 외부 프로그램의 부수 효과를 만들지 않습니다.

파이프를 실행할 때는 두 자식을 모두 만든 뒤 부모가 파이프 끝을 닫고 기다립니다. 왼쪽 자식을 먼저 기다리면 파이프 버퍼 용량보다 큰 출력을 쓰는 동안 교착될 수 있습니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 작은따옴표, 큰따옴표, escape와 붙은 인용 구간
- 빈 인자와 공백 분리
- 인용하거나 escape한 제어 문자
- 문법 오류가 외부 프로그램을 실행하지 않는지
- 4 MiB 파이프가 교착 없이 끝나는지
- 닫힌 표준 FD 번호를 pipe가 재사용하는 경우
- 일반 종료, `126`, `127`, 시그널 종료
- 오른쪽 명령의 종료 상태 반환

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Growable word buffer | `src/command_runner.c` |
| 2 | Owned argv and command list | `src/command_runner.c` |
| 3 | Quote and escape parsing | `src/command_runner.c` |
| 4 | Complete syntax validation before execution | `src/command_runner.c` |
| 5 | Wait retry and file-descriptor duplication | `src/command_runner.c` |
| 6 | Child setup and exec failure status | `src/command_runner.c` |
| 7 | Single command and two-command pipeline | `src/command_runner.c` |
| 8 | CLI exit status and cleanup | `src/command_runner.c` |

## 범위

대화형 프롬프트, 환경 변수 확장, 명령 치환, glob 패턴 확장, 입출력 재지정, 논리 연산자, 세 개 이상의 명령을 잇는 파이프와 작업 제어는 구현하지 않습니다. 일반 셸을 대체하지 않고 위 문법만 일정하게 실행합니다.
