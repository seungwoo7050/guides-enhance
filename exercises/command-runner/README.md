# command-runner

`command-runner`는 명령 문자열 하나를 자체 문법으로 해석해 다음 중 하나를 실행하는 작은 CLI입니다.

```text
단일 외부 프로그램

또는

외부 프로그램 | 외부 프로그램
```

전체 문법을 먼저 검사하고 모든 `argv` 메모리를 완성한 뒤에만 자식 프로세스를 만듭니다. 따라서 문법 오류가 있는 입력은 일부 명령만 먼저 실행되는 부수 효과를 만들지 않습니다.

이 프로그램은 일반 셸을 호출해 문자열을 넘기는 방식이 아니라, 아래에 정의된 제한된 문법을 직접 파싱합니다.

## 지원 문법

### 공백

인용되지 않은 공백은 인자를 나눕니다.

```text
echo hello world
```

는 개념적으로 다음 `argv`를 만듭니다.

```text
argv[0] = "echo"
argv[1] = "hello"
argv[2] = "world"
```

여러 개의 인용되지 않은 공백은 인자 사이의 구분자로 사용되며, 공백 자체가 인자 내용에 들어가지는 않습니다.

### 작은따옴표

작은따옴표 안의 문자는 닫는 작은따옴표가 나올 때까지 그대로 하나의 인자 내용에 포함됩니다.

```text
printf 'alpha beta'
```

에서 `alpha beta`는 공백을 포함한 하나의 인자입니다.

### 큰따옴표

큰따옴표 안에서도 공백은 인자를 나누지 않습니다.

이 문법에서 큰따옴표 안의 `\`는 다음 문자 하나를 일반 문자로 만듭니다.

예:

```text
"hello\"world"
```

는 따옴표 문자를 인자 안에 포함시킬 수 있습니다.

이 규칙은 일반적인 POSIX shell 전체 문법을 그대로 구현한다는 뜻이 아닙니다. 이 프로그램은 문서에 정의된 단순화된 escape 규칙만 지원합니다.

### 인용되지 않은 backslash

인용되지 않은 `\`도 바로 다음 문자 하나를 일반 문자로 만듭니다.

예:

```text
hello\ world
```

는 다음 하나의 인자를 만듭니다.

```text
hello world
```

문자열 마지막에 `\`만 남아 다음 문자가 없으면 문법 오류입니다.

### 붙어 있는 구간은 하나의 인자

일반 문자와 인용 구간이 공백 없이 붙어 있으면 하나의 word로 연결됩니다.

예:

```text
ab'cd'"ef"
```

는 다음 하나의 인자를 만듭니다.

```text
abcdef
```

### 빈 인자

다음 두 표현은 길이가 0인 인자를 만듭니다.

```text
''
""
```

"아무 인자도 없음"과 "길이가 0인 인자 하나"는 다릅니다.

예를 들어:

```text
program
```

과:

```text
program ""
```

은 서로 다른 `argv`입니다.

### 파이프

인용되지 않고 escape되지 않은 `|` 하나만 파이프 연산자로 사용합니다.

```text
left arg | right arg
```

파이프의 왼쪽과 오른쪽에는 각각 실행할 명령이 있어야 합니다.

따라서 다음은 문법 오류입니다.

```text
| right
left |
left || right
```

인용하거나 escape한 `|`는 연산자가 아니라 일반 문자로 취급됩니다.

예:

```text
echo '|'
echo \|
```

### 지원하지 않는 연산자

인용되지 않은 다음 문자는 지원하지 않으며 문법 오류로 처리합니다.

```text
<
>
;
&
```

인용하거나 escape하여 일반 문자로 만든 경우에는 인자 내용으로 사용할 수 있습니다.

즉 이 프로그램은 다음과 같은 일반 셸 기능을 해석하지 않습니다.

```text
cmd > file
cmd < file
a ; b
a & b
```

## 문법 오류

다음과 같은 입력은 자식 프로세스를 만들기 전에 문법 오류로 처리합니다.

- 닫히지 않은 작은따옴표
- 닫히지 않은 큰따옴표
- 문자열 끝의 단독 `\`
- 파이프 왼쪽 명령이 없음
- 파이프 오른쪽 명령이 없음
- 지원하지 않는 인용되지 않은 연산자
- 허용 범위를 벗어난 파이프 구성

핵심 규칙은 다음과 같습니다.

```text
전체 문자열 파싱
→ 전체 문법 검증
→ command/argv 메모리 완성
→ 그 뒤에만 실행 시작
```

따라서 다음과 같이 앞부분은 정상 명령이지만 뒤에 문법 오류가 있는 입력도 앞 명령을 먼저 실행하지 않습니다.

```text
touch side-effect ; unsupported
```

## 종료 상태

프로그램의 공개 종료 상태는 다음과 같습니다.

- 문법 오류와 잘못된 CLI 인자는 `2`
- 실행 파일을 찾지 못하면 `127`
- 파일은 찾았지만 실행하지 못하면 `126`
- 시그널로 종료한 자식은 `128 + signal`
- 파이프를 실행하면 오른쪽 명령의 상태를 반환
- 부모가 `fork`나 `waitpid`를 완료하지 못하면 `125`

여기서 `125`는 외부 명령 자체의 종료 상태가 아니라 **명령 실행을 관리하는 부모 프로세스가 실행 절차를 완료하지 못한 경우**를 구분하기 위한 상태입니다.

파이프에서는 왼쪽 명령의 상태가 최종 CLI 상태를 덮지 않습니다.

예:

```text
left status  = 1
right status = 0
최종 status   = 0
```

## 빌드와 실행

```sh
make
./build/command-runner "printf 'alpha beta\n' | wc -w"
```

위 입력은 하나의 명령 문자열이며, `command-runner`가 그 문자열 안의 인용과 `|`를 직접 해석합니다.

## 주요 구현 결정

### growable word builder

파서는 현재 word를 만들기 위해 확장 가능한 문자열 builder를 사용합니다.

예를 들어:

```text
ab'cd'"ef"
```

를 읽을 때 parser는 세 구간을 별도 argv 원소로 만들지 않고 하나의 builder에 이어 붙입니다.

```text
"ab"
→ "abcd"
→ "abcdef"
```

word가 끝나면 마지막에 NUL 문자를 추가하여 C 문자열로 완성합니다.

### command가 argv와 word를 소유

builder가 완성한 문자열의 소유권은 `struct command`로 넘어갑니다.

각 command는 개념적으로 다음 메모리를 소유합니다.

```text
argv 배열
├─ argv[0] → 별도 할당된 word
├─ argv[1] → 별도 할당된 word
└─ ...
```

정리할 때는 각 word와 argv 배열을 모두 해제해야 합니다.

이 소유권이 명확해야 파싱 중간 실패에서도 이미 만든 word만 정확히 정리할 수 있습니다.

### 파싱과 실행을 분리

파싱 중에는 외부 프로그램을 실행하지 않습니다.

예를 들어 다음 입력을 처리하다가 마지막에 닫히지 않은 따옴표를 발견했다면:

```text
printf ok | echo "unterminated
```

이미 `printf` 쪽 command model을 만들었더라도 실행해서는 안 됩니다.

대신:

```text
문법 오류 확인
→ 지금까지 할당한 command와 word 정리
→ 상태 2로 종료
```

합니다.

이 설계는 문법 오류에 대해 **실행 전 원자성**을 제공합니다. 즉 입력 전체가 유효할 때만 어떤 외부 프로그램도 시작합니다.

### 파이프는 두 자식을 먼저 생성

두 명령 파이프의 기본 흐름은 다음과 같습니다.

```text
pipe 생성
→ left fork
→ right fork
→ 부모 pipe 끝 닫기
→ 두 자식 wait
```

왼쪽 자식을 만든 직후 기다리면 왼쪽 출력이 pipe 버퍼 크기를 넘을 때 오른쪽에서 읽어 줄 프로세스가 아직 없어 교착될 수 있습니다.

따라서 테스트는 4 MiB 같은 큰 출력을 사용해 이 구조가 실제로 동시에 진행되는지 확인합니다.

### 닫힌 표준 FD 재사용

프로그램 실행 전에 stdin 또는 stdout이 닫혀 있으면 `pipe()`가 새 pipe 끝에 FD `0` 또는 `1`을 배정할 수 있습니다.

따라서 자식에서 `dup2`를 사용할 때:

```text
source FD == destination FD
```

인 경우를 고려해야 합니다.

이미 목적 위치에 있는 FD를 정리 코드가 다시 닫지 않도록 해야 실제 stdin/stdout 연결이 유지됩니다.

### 자식의 exec 실패 상태

자식 프로세스에서 외부 명령 실행에 실패하면 단순히 부모 코드로 돌아오면 안 됩니다. 자식은 정해진 공개 상태로 종료해야 합니다.

```text
명령을 찾지 못함      → 127
찾았지만 실행 못 함   → 126
```

부모는 `waitpid`로 이 상태를 회수해 CLI 종료 상태로 변환합니다.

### `waitpid` 중단 처리

`waitpid`가 시그널 때문에 `EINTR`로 중단될 수 있으므로 필요한 경우 재시도합니다.

자식 프로세스가 실제로 회수되기 전에 기다림을 포기하면 zombie가 남거나 잘못된 `125`를 반환할 수 있습니다.

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

문법 테스트에서는 단순히 올바른 입력이 성공하는지만 확인하지 않고, 잘못된 입력이 **외부 명령을 전혀 실행하지 않았는지**까지 확인해야 합니다.

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

다음 기능은 구현하지 않습니다.

- 대화형 prompt
- 환경 변수 확장
- 명령 치환
- glob 패턴 확장
- 입출력 재지정
- 논리 연산자
- 세 개 이상의 명령을 잇는 파이프
- 작업 제어

즉 일반 셸을 대체하지 않으며, **이 문서에 정의된 제한된 문자열 문법만 일정하게 파싱하고 실행**합니다.