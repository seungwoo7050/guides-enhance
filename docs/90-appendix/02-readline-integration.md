# Readline 통합

Readline은 터미널 기반 대화형 프로그램에서 다음 기능을 제공하는 입력 라이브러리입니다.

- 한 줄 입력
- 좌우 이동과 문자 편집
- 명령 히스토리
- 일부 시그널 처리 보조
- 현재 입력 줄과 prompt 다시 표시

일반적인 `read`, `fgets`, `getline`과 달리 `readline()`은 **라이브러리가 새로 할당한 문자열의 소유권을 호출자에게 넘깁니다.** 따라서 입력 처리 코드는 문자열의 소유자와 수명을 명확히 정해야 합니다.

또한 Readline은 단순한 문자열 입력 함수가 아니라 터미널 상태, 편집 버퍼, 시그널 처리와 상호작용하므로 다음 세 영역을 구분해서 설계하는 것이 중요합니다.

```text
입력 계층: Readline을 사용해 한 줄을 얻음
파싱 계층: 문자열을 읽어 command model을 생성
실행 계층: command model을 실행하고 자식 프로세스를 관리
```

파서 자체가 Readline에 직접 의존하지 않도록 분리하면 메모리 관리와 테스트가 단순해집니다.

---

## 기본 사용

```c
#include <readline/readline.h>
#include <readline/history.h>
#include <stdlib.h>

int main(void) {
    char *line;

    while ((line = readline("prompt> ")) != NULL) {
        if (line[0] != '\0') {
            add_history(line);
        }

        process_line(line);
        free(line);
    }

    return 0;
}
```

핵심 수명은 다음과 같습니다.

```text
readline()
    ↓
새 문자열 allocation
    ↓
호출자가 사용
    ↓
호출자가 free()
```

즉 다음 규칙을 지킵니다.

- `readline()`이 문자열을 반환하면 호출자가 정확히 한 번 `free()`합니다.
- `readline()`이 `NULL`을 반환하면 해제할 문자열이 없습니다.
- 빈 줄도 문자열 allocation이며, 사용이 끝나면 `free()`해야 합니다.

---

## 빈 줄과 EOF 구분하기

빈 줄과 EOF는 서로 다른 상태입니다.

```text
빈 줄:
    line != NULL
    line[0] == '\0'

EOF:
    line == NULL
```

예를 들어 사용자가 아무 문자도 입력하지 않고 Enter를 누르면 빈 문자열이 반환됩니다.

```c
line != NULL
line[0] == '\0'
```

반면 입력 스트림의 끝에 도달하면 `readline()`은 `NULL`을 반환합니다.

```c
line == NULL
```

따라서 다음과 같은 코드는 빈 줄을 잘못 종료 조건으로 처리할 수 있으므로 피합니다.

```c
if (line == NULL || line[0] == '\0') {
    break;
}
```

대신 두 경우를 분리합니다.

```c
if (line == NULL) {
    /* EOF */
    break;
}

if (line[0] == '\0') {
    /* 빈 줄 */
    free(line);
    continue;
}
```

### Ctrl-D와 EOF

터미널에서 Ctrl-D는 일반적으로 EOF 입력에 사용되지만, **현재 편집 중인 줄의 상태에 따라 Readline의 동작이 달라질 수 있습니다.**

예를 들어 prompt에 아무 문자도 없는 상태에서 Ctrl-D를 누르면 `readline()`이 `NULL`을 반환할 수 있습니다. 반면 이미 문자를 입력한 상태에서는 편집 동작으로 처리될 수도 있습니다.

따라서 대화형 프로그램에서는 다음을 실제 터미널에서 확인해야 합니다.

- 빈 prompt에서 Ctrl-D
- 일부 문자를 입력한 뒤 Ctrl-D
- EOF 뒤 프로그램의 종료 상태
- EOF 직전 출력 형식

---

## 히스토리 추가 시점

Readline은 입력한 모든 줄을 자동으로 프로그램 히스토리에 넣어 주는 것으로 가정하지 않습니다. 프로그램이 원하는 시점에 `add_history()`를 호출합니다.

일반적으로 빈 줄은 히스토리에 넣지 않습니다.

```c
if (line[0] != '\0') {
    add_history(line);
}
```

다음 정책은 프로그램이 직접 결정해야 합니다.

- 빈 줄을 저장할지
- 공백만 있는 줄을 저장할지
- 바로 이전과 동일한 명령을 중복 저장할지
- 파싱에 실패한 명령도 저장할지
- 히스토리에 저장하면 안 되는 민감한 입력이 있는지

예를 들어 공백만 있는 줄을 제외하려면 단순히 `line[0] != '\0'`만으로는 충분하지 않습니다.

```text
""        → 빈 줄
"   "     → 빈 줄은 아니지만 공백만 있는 줄
```

따라서 프로그램이 "실질적으로 비어 있는 입력"을 별도로 정의해야 합니다.

또한 GNU History API의 `add_history()`는 일반적으로 반환값으로 성공 여부를 알려 주는 함수가 아닙니다. 따라서 `add_history()`의 반환값을 검사하는 코드가 있다고 가정해서는 안 됩니다.

---

## 입력 문자열 소유권

`readline()`이 반환한 문자열의 소유권은 호출자에게 있습니다.

기본 흐름은 다음과 같습니다.

```text
readline이 allocation 반환
→ parser가 문자열을 읽음
→ 필요한 데이터를 별도 allocation으로 복사
→ 원본 line이 더 이상 필요 없으면 free
```

중요한 것은 **parser가 원본 문자열을 복사하는지, 아니면 원본 내부를 가리키는 포인터를 저장하는지**입니다.

### 원본을 복사하는 경우

예를 들어 parser가 각 토큰을 새로 할당한다면:

```text
line
 ├─ "echo"
 ├─ "hello"
 └─ "world"

parser
 ├─ strdup("echo")
 ├─ strdup("hello")
 └─ strdup("world")
```

파싱이 끝난 뒤 원본 `line`을 해제해도 command model은 유효합니다.

```c
struct command *cmd = parse_line(line);
free(line);

execute_command(cmd);
```

### 원본 내부를 가리키는 경우

반대로 parser가 원본 문자열의 일부를 직접 가리키는 포인터만 저장한다면:

```text
line allocation
┌─────────────────────┐
│ echo\0hello\0world  │
└─────────────────────┘
   ↑      ↑
 argv[0]  argv[1]
```

`argv[0]`, `argv[1]` 등이 `line` 내부를 가리키므로 다음 코드는 잘못될 수 있습니다.

```c
struct command *cmd = parse_line(line);
free(line);              /* cmd 내부 포인터가 무효가 될 수 있음 */
execute_command(cmd);    /* use-after-free 가능 */
```

이 설계에서는 command model을 사용하는 동안 원본 `line`도 살아 있어야 합니다.

따라서 parser 인터페이스 문서에는 최소한 다음 중 하나를 명시해야 합니다.

```text
A. parser는 입력 문자열을 빌리며 결과도 입력 수명에 의존한다.
B. parser는 필요한 데이터를 모두 복사하며 결과는 입력 수명과 독립적이다.
```

---

## 파서와 Readline adapter 분리

파서가 Readline API를 직접 호출하지 않도록 입력 계층과 파싱 계층을 나누는 것이 좋습니다.

```text
readline adapter:
    Readline에서 한 줄 allocation을 얻음

parser:
    const char *와 길이를 읽어 command model 생성

caller:
    parser의 소유권 규칙에 따라 원본 line 해제
```

예를 들어 parser 인터페이스를 다음처럼 만들 수 있습니다.

```c
struct command *parse_command(const char *text, size_t length);
```

이 함수는 입력을 어디에서 얻었는지 알 필요가 없습니다.

실제 프로그램에서는:

```c
char *line = readline("prompt> ");

if (line != NULL) {
    struct command *cmd = parse_command(line, strlen(line));
    /* 소유권 정책에 따라 적절한 시점에 free(line) */
}
```

테스트에서는 Readline 없이 직접 문자열을 전달할 수 있습니다.

```c
parse_command("echo hello", 10);
```

이 구조의 장점은 다음과 같습니다.

- parser 단위 테스트에서 실제 터미널이 필요하지 않습니다.
- parser가 Readline 전역 상태에 의존하지 않습니다.
- 입력 방식이 바뀌어도 parser를 재사용할 수 있습니다.
- 문자열 수명과 command model의 수명을 명확히 정의하기 쉽습니다.

---

## Readline과 시그널

Readline은 터미널 입력 중 여러 시그널에 대해 자체 처리를 수행할 수 있습니다.

따라서 프로그램이 `SIGINT`, `SIGQUIT` 등의 동작을 직접 설계하려면 먼저 다음을 구분해야 합니다.

```text
상태 1: prompt에서 Readline으로 입력 중
상태 2: 자식 command 실행 중
상태 3: heredoc 등 별도 입력 중
```

같은 `SIGINT`라도 상태에 따라 원하는 동작이 다를 수 있습니다.

예를 들어 shell 형태의 프로그램에서는 다음과 같은 정책을 가질 수 있습니다.

```text
prompt 입력 중:
    현재 입력 줄 취소
    새 prompt 표시
    프로그램 자체는 계속 실행

자식 command 실행 중:
    자식에게 SIGINT가 전달되도록 함
    부모 shell은 계속 실행

heredoc 입력 중:
    heredoc 입력 취소
    현재 명령 실행도 취소
```

이 정책은 프로그램 요구 사항에 따라 달라집니다. 중요한 점은 **시그널 하나에 대해 프로그램 전체에서 동일한 처리를 한다고 가정하지 않는 것**입니다.

### Readline 자체 시그널 처리와의 충돌

Readline은 자체 시그널 처리를 활성화할 수 있으므로 프로그램이 직접 `sigaction()` 등으로 처리기를 설치한다면 Readline의 설정과 충돌할 가능성을 고려해야 합니다.

즉 다음을 명시적으로 결정합니다.

- Readline의 기본 시그널 처리를 사용할 것인지
- 프로그램이 직접 시그널 처리를 담당할 것인지
- prompt와 자식 실행 구간에서 처리기를 바꿀 것인지
- Readline 호출 전에 어떤 상태를 설정하고 호출 후 어떻게 복원할 것인지

사용 중인 Readline 버전과 API 문서를 기준으로 동작을 확인해야 합니다.

---

## 시그널 처리기에서 해야 할 일

시그널 처리기는 일반 함수처럼 아무 함수나 호출할 수 있는 환경이 아닙니다.

POSIX에서는 시그널 처리기에서 호출해도 안전하다고 보장되는 함수가 제한되어 있습니다. 따라서 Readline 함수가 편리해 보인다는 이유만으로 시그널 처리기 안에서 무조건 호출해서는 안 됩니다.

가능하면 시그널 처리기에서는 다음처럼 최소한의 상태만 기록합니다.

```c
static volatile sig_atomic_t got_sigint = 0;

static void handle_sigint(int signo) {
    (void)signo;
    got_sigint = 1;
}
```

그 뒤 일반 제어 흐름에서 해당 상태를 확인합니다.

```text
signal handler:
    최소 작업
    flag 기록

일반 코드:
    flag 확인
    Readline 상태 정리
    prompt 다시 표시
```

실제 구현에서 어떤 Readline 함수를 어디에서 호출할 수 있는지는 사용 중인 버전의 문서를 확인해야 합니다.

---

## Prompt 다시 그리기

대화형 프로그램은 시그널, 비동기 출력, 자식 프로세스 종료 등의 이유로 prompt를 다시 표시해야 할 수 있습니다.

Readline에는 현재 입력 버퍼를 변경하거나 새 줄을 알리고 prompt를 다시 그리는 API가 있습니다. 대표적으로 다음 계열의 기능이 있습니다.

```text
현재 입력 줄 내용 변경
현재 줄 상태 갱신
prompt 다시 표시
```

구체적인 함수 조합은 프로그램이 원하는 UX와 Readline 버전에 따라 달라질 수 있습니다.

중요한 것은 다음 사항을 먼저 정의하는 것입니다.

### 1. 현재 입력을 버릴 것인가

Ctrl-C를 눌렀을 때 현재 입력이:

```text
prompt> echo unfinished
```

라면 다음 중 무엇을 원하는지 정해야 합니다.

```text
A. 현재 줄을 버리고 새 prompt 표시
B. 현재 줄을 유지하고 prompt만 다시 그림
```

shell에서는 일반적으로 A에 가까운 동작을 기대하는 경우가 많지만 프로그램 요구 사항에 따라 다릅니다.

### 2. 새 줄을 먼저 출력할 것인가

출력이 현재 prompt 뒤에 붙지 않도록 새 줄을 출력해야 할 수도 있습니다.

예:

```text
prompt> partial^C
prompt>
```

출력 정책을 정하지 않으면 prompt와 자식 프로세스 출력이 다음처럼 섞일 수 있습니다.

```text
prompt> child outputprompt>
```

### 3. 자식 출력과 prompt를 구분할 것인가

자식 프로세스가 stdout이나 stderr에 출력하는 동안 부모가 prompt를 다시 그리면 화면이 뒤섞일 수 있습니다.

따라서 prompt는 일반적으로 다음 시점을 기준으로 관리합니다.

```text
자식 실행 시작
→ 부모는 prompt 표시 중단
→ 자식 종료 또는 정지 상태 처리
→ 필요한 상태 복원
→ 다음 prompt 표시
```

---

## 빌드

기본적인 링크 방법은 다음과 같습니다.

```sh
cc repl.c -lreadline -o repl
```

Readline 헤더가 표준 include 경로에 없다면 include 경로를 추가할 수 있습니다.

```sh
cc -I/path/to/include repl.c -lreadline -o repl
```

라이브러리가 표준 library 경로에 없다면 다음과 같이 지정할 수 있습니다.

```sh
cc -I/path/to/include repl.c -L/path/to/lib -lreadline -o repl
```

여기서 역할은 다음과 같습니다.

```text
-I/path/to/include
    컴파일할 때 헤더를 찾을 경로

-L/path/to/lib
    링크할 때 라이브러리를 찾을 경로

-lreadline
    Readline 라이브러리와 링크
```

링크 옵션의 순서는 사용하는 링커와 빌드 방식에 따라 중요할 수 있습니다. 일반적으로 라이브러리는 해당 라이브러리를 사용하는 object 파일 뒤에 두는 형태가 안전합니다.

```sh
cc repl.o -lreadline -o repl
```

---

## Makefile에서 분리하기

환경마다 Readline 설치 위치가 다를 수 있으므로 include 옵션, linker 검색 경로, 실제 링크 라이브러리를 분리해 두는 것이 좋습니다.

```make
CPPFLAGS += $(READLINE_CPPFLAGS)
LDFLAGS += $(READLINE_LDFLAGS)
LDLIBS += -lreadline
```

각 변수의 일반적인 역할은 다음과 같습니다.

```text
CPPFLAGS:
    전처리기와 include 경로 옵션
    예: -I/opt/readline/include

LDFLAGS:
    링커의 검색 경로와 링크 방식 옵션
    예: -L/opt/readline/lib

LDLIBS:
    실제 링크할 라이브러리
    예: -lreadline
```

외부 환경에서 다음처럼 값을 덮어쓸 수 있습니다.

```sh
make \
  READLINE_CPPFLAGS="-I/opt/readline/include" \
  READLINE_LDFLAGS="-L/opt/readline/lib"
```

이렇게 하면 Makefile 안에 특정 개발자의 로컬 설치 경로를 직접 넣지 않아도 됩니다.

---

## Readline이 없는 환경

Readline을 사용할 수 없는 시스템에서 어떻게 동작할지도 명시해야 합니다.

예를 들어 다음 선택지가 있습니다.

```text
A. Readline이 없으면 빌드 실패
B. Readline 기능을 비활성화한 별도 빌드 제공
C. fgets/getline 기반의 단순 입력 adapter로 대체
```

중요한 것은 사용자가 모르는 사이에 동작이 조용히 달라지지 않게 하는 것입니다.

예를 들어 Readline이 없을 때 자동으로 `getline()`을 사용한다면 다음 기능이 사라질 수 있습니다.

- 방향키 기반 줄 편집
- 히스토리 탐색
- Readline 전용 키 바인딩
- Readline과 연결된 일부 시그널 동작

따라서 대체 입력 방식을 사용한다면 빌드 로그, 도움말 또는 문서에서 차이를 명시합니다.

---

## 오류와 종료

Readline 통합에서는 "입력 실패", "파싱 실패", "프로그램 종료"를 하나의 상태로 합치지 않는 것이 좋습니다.

### `readline()`이 `NULL`을 반환한 경우

보통 EOF를 의미합니다.

프로그램 정책에 따라:

```text
대화형 shell:
    정상 종료

상위 루프가 있는 프로그램:
    EOF 상태를 상위 계층에 반환
```

처럼 처리할 수 있습니다.

### parser가 실패한 경우

예를 들어 문법 오류라면:

```text
입력 line 확보
→ parser 실패
→ 오류 메시지 출력
→ line 정리
→ 다음 prompt
```

가 일반적인 대화형 프로그램의 흐름입니다.

반면 내부 불변식 위반이나 복구 불가능한 오류라면 프로그램을 종료할 수도 있습니다.

즉 **모든 parser 실패를 동일하게 취급하지 않고 복구 가능한 사용자 입력 오류와 내부 오류를 구분**하는 것이 좋습니다.

### 출력 실패

stdout 또는 stderr 출력 자체가 실패할 수도 있습니다.

예를 들어 출력 대상이 닫힌 pipe라면 prompt를 계속 표시해도 의미가 없을 수 있습니다.

따라서 다음을 구분합니다.

```text
사용자 입력 오류:
    다음 prompt로 복구 가능

입출력 채널 오류:
    계속 대화형 실행이 가능한지 판단 필요

내부 메모리/상태 오류:
    정상 복구가 가능한지 별도 판단
```

---

## 메모리 정리 예제

다음은 성공과 실패 경로에서 `line`을 정확히 한 번 해제하도록 구조를 명확히 한 예입니다.

```c
for (;;) {
    char *line = readline("prompt> ");

    if (line == NULL) {
        break;
    }

    if (line[0] != '\0') {
        add_history(line);
    }

    struct command *cmd = parse_command(line);

    if (cmd == NULL) {
        free(line);
        continue;
    }

    execute_command(cmd);
    destroy_command(cmd);
    free(line);
}
```

단 이 코드가 올바르려면 `command`가 `line` 내부를 가리키지 않거나, `destroy_command(cmd)`가 실행될 때까지 `line`이 살아 있어야 한다는 소유권 규칙이 필요합니다.

즉 메모리 정리 코드를 볼 때는 단순히 `free(line)`이 존재하는지만 확인하면 안 됩니다.

```text
언제 free하는가?
그 시점에 line을 참조하는 객체가 남아 있지 않은가?
모든 오류 경로에서도 정확히 한 번 free되는가?
```

를 함께 확인해야 합니다.

---

## 테스트할 내용

대화형 동작은 일반 함수 테스트와 실제 터미널 테스트를 분리하는 것이 좋습니다.

### 일반 함수 테스트

터미널 없이 검사할 수 있는 로직입니다.

- 빈 문자열
- 공백만 있는 문자열
- 일반 명령 문자열
- 따옴표 처리
- escape 처리
- parser 실패
- parser 실패 뒤 메모리 정리
- command model 소유권
- 반복 입력 뒤 누수 여부
- 너무 긴 입력
- 잘못된 UTF-8 또는 프로그램이 허용하지 않는 문자 입력

이 테스트에서는 Readline 자체보다 parser와 command model의 동작을 검증합니다.

### 실제 터미널 확인

터미널 상태와 Readline 동작이 필요한 항목입니다.

- 빈 prompt에서 Ctrl-D
- 입력 중 Ctrl-D
- Ctrl-C
- Ctrl-\ 또는 프로그램이 처리하는 다른 시그널
- 빈 줄 입력
- 공백만 있는 줄의 history 정책
- 중복 명령의 history 정책
- 여러 줄 실행 뒤 prompt 모양
- 자식 command 실행 중 Ctrl-C
- 자식 command가 stdout/stderr에 출력하는 동안 prompt 상태
- heredoc 입력 중 시그널 동작
- 종료 뒤 터미널 상태가 정상으로 복원되는지

### PTY 기반 테스트

PTY(pseudo-terminal)를 사용하면 일부 대화형 동작을 자동화할 수 있습니다.

PTY 기반 테스트로 다음을 검증할 수 있습니다.

```text
프로그램 실행
→ prompt 문자열 확인
→ 입력 전송
→ Ctrl-C 또는 Ctrl-D에 해당하는 터미널 입력 전송
→ 다음 prompt 또는 종료 상태 확인
```

하지만 다음 차이는 테스트 결과에 영향을 줄 수 있습니다.

- 운영체제
- 터미널 드라이버
- Readline 버전
- locale
- 키 바인딩 설정
- 테스트 환경의 PTY 구현

따라서 CI에서 PTY 테스트를 사용한다면 실행 환경과 Readline 버전을 함께 기록하는 것이 좋습니다.

---

## 완료 기준

Readline 통합이 완료되었다고 판단하려면 최소한 다음 조건을 만족해야 합니다.

1. `readline()`이 반환한 각 문자열을 정확히 한 번 `free()`합니다.
2. 빈 줄과 EOF를 별도 상태로 처리합니다.
3. 공백만 있는 줄과 중복 명령의 history 정책이 명확합니다.
4. parser가 원본 `line`을 빌리는지 필요한 데이터를 복사하는지 문서화합니다.
5. `line`을 해제하는 시점이 parser 결과의 수명과 모순되지 않습니다.
6. prompt 입력 중, 자식 실행 중, heredoc 입력 중의 시그널 동작을 구분합니다.
7. 시그널 처리기에서 수행하는 작업을 최소화합니다.
8. prompt를 다시 그릴 때 현재 입력을 버릴지 유지할지 정의합니다.
9. Readline 의존성을 parser에서 분리합니다.
10. Readline이 없는 환경의 빌드 정책을 명시합니다.
11. 자동 함수 테스트와 실제 터미널 테스트의 범위를 구분합니다.
12. PTY 기반 테스트를 사용한다면 터미널과 Readline 버전 차이를 기록합니다.

이 기준의 핵심은 Readline을 단순한 "문자열 입력 함수"로 취급하지 않는 것입니다. **입력 문자열의 소유권, 터미널 상태, 시그널 처리, prompt 표시, parser 수명을 서로 독립된 문제로 구분한 뒤 명시적으로 연결**해야 안정적인 대화형 프로그램을 만들 수 있습니다.
