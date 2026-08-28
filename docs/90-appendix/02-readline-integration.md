# Readline 통합

Readline은 대화형 입력, 줄 편집과 명령 히스토리 기능을 제공합니다. 일반 `read`나 `getline`과 달리 라이브러리가 할당한 문자열을 반환하므로 입력 결과의 메모리 수명을 분명히 관리해야 합니다.

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

`readline`이 반환한 문자열은 호출자가 `free`합니다. EOF에서는 `NULL`을 반환합니다.

## 빈 줄과 EOF 구분하기

```text
빈 줄:  유효한 allocation, line[0] == '\0'
EOF:    line == NULL
```

빈 줄을 종료로 처리하지 않습니다. 대화형 프로그램에서 Ctrl-D는 현재 입력 상태에 따라 EOF 또는 다른 동작으로 나타날 수 있으므로 실제 환경에서 확인합니다.

## 히스토리 추가 시점

일반적으로 빈 줄은 히스토리에 넣지 않습니다.

```c
if (line[0] != '\0') {
    add_history(line);
}
```

공백만 있는 줄을 넣을지, 중복 명령를 넣을지는 프로그램이 정합니다. Readline이 자동으로 판단한다고 가정하지 않습니다.

## 입력 문자열 소유권

다음 순서를 지킵니다.

```text
readline이 allocation 반환
→ 파서가 읽거나 필요한 데이터를 별도 할당
→ line이 더 이상 필요 없으면 free
```

파서가 line 내부를 가리키는 포인터만 저장한다면 line을 먼저 해제해서는 안 됩니다. 파서가 각 토큰을 복사하는지, 원본 line의 수명에 의존하는지 정합니다.

## Readline과 시그널

Readline은 자체 시그널 처리를 제공할 수 있습니다. 대화형 프로그램이 `SIGINT`, `SIGQUIT` 동작을 직접 제어하려면 사용 중인 Readline 버전과 설정을 확인해야 합니다.

프로그램이 직접 처리기를 설치한다면 다음을 구분합니다.

- prompt에서 입력 중일 때
- 자식 command가 실행 중일 때
- heredoc 같은 별도 입력을 받을 때

같은 `SIGINT`라도 상황에 따라 줄을 취소하거나 자식에게 전달하거나 프로그램을 종료할 수 있습니다.

시그널 처리기에서 Readline 함수를 무조건 호출하지 않습니다. 해당 함수가 시그널 처리기에서 안전한지 문서를 확인하고, 가능하면 flag와 일반 제어 흐름으로 처리합니다.

## Prompt 다시 그리기

Readline API에는 현재 줄을 정리하고 prompt를 다시 표시하는 함수가 있습니다. 구체적인 호출 조합은 버전과 프로그램 동작에 따라 달라질 수 있습니다.

중요한 점은 다음입니다.

- handler에서 허용할 작업을 최소화합니다.
- 출력 중인 자식 프로세스와 prompt 출력이 섞이지 않게 합니다.
- 새 줄을 출력할지 현재 입력을 유지할지 명시합니다.
- 각 Readline 함수의 반환값과 지원 범위를 확인합니다.

## 빌드

시스템에 따라 헤더와 라이브러리 경로가 다를 수 있습니다.

```sh
cc repl.c -lreadline -o repl
```

일부 환경에서는 include path나 library path가 추가로 필요합니다.

```sh
cc -I/path/to/include repl.c -L/path/to/lib -lreadline -o repl
```

Makefile에서는 환경에서 덮어쓸 수 있게 분리할 수 있습니다.

```make
CPPFLAGS += $(READLINE_CPPFLAGS)
LDFLAGS += $(READLINE_LDFLAGS)
LDLIBS += -lreadline
```

Readline이 설치되지 않은 환경에서 자동으로 다른 입력 방식으로 바꿀지, 기능을 빌드하지 않을지 정합니다. 조용히 동작이 달라지지 않게 합니다.

## 일반 입력과 Readline adapter 분리

파서가 Readline에 직접 의존하지 않도록 입력 함수와 파싱 함수를 나눌 수 있습니다.

```text
readline adapter: 한 줄 allocation을 얻음
parser: const char *와 길이를 읽어 command model 생성
caller: 원본 line 해제
```

이렇게 하면 parser 테스트에서 Readline 없이 문자열을 직접 전달할 수 있습니다.

## 오류와 종료

- `readline`이 `NULL`: EOF로 종료할지 별도 상태를 반환할지 정합니다.
- `add_history` 실패를 어떻게 처리할지 사용 중인 API 문서를 확인합니다.
- parser 실패: line을 해제하고 다음 prompt를 받을지 프로그램을 종료할지 정합니다.
- 출력 실패: prompt를 계속 표시할 수 있는지 판단합니다.

## 테스트할 내용

자동 테스트가 터미널 동작을 완전히 재현하기는 어렵습니다. 다음을 나눠 검사합니다.

### 일반 함수 테스트

- 빈 문자열
- 공백만 있는 문자열
- 따옴표와 escape
- parser 실패 뒤 메모리 정리

### 실제 터미널 확인

- Ctrl-D
- Ctrl-C
- 빈 줄과 history
- 여러 줄 실행 뒤 prompt 모양
- 자식 command 실행 중 시그널

PTY 기반 테스트를 사용하면 일부 대화형 동작을 자동화할 수 있지만 터미널과 Readline 버전 차이를 기록해야 합니다.

## 완료 기준

1. `readline`이 반환한 문자열을 정확히 한 번 `free`합니다.
2. 빈 줄과 EOF를 구분합니다.
3. 파서가 원본 line을 빌리는지 복사하는지 설명합니다.
4. prompt와 자식 실행 중 시그널 동작을 구분합니다.
5. Readline 의존성을 parser에서 분리합니다.
6. 자동 테스트와 실제 터미널 확인 범위를 구분합니다.
