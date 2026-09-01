# command-pipeline

`command-pipeline`은 두 외부 명령을 POSIX 파이프로 연결하여 다음 형태의 실행을 수행하는 C 라이브러리입니다.

```text
left command stdout
        │
        ▼
      pipe
        │
        ▼
right command stdin
```

두 자식을 모두 만든 뒤 부모가 기다리며, 최종 공개 종료 상태는 **오른쪽 명령의 종료 상태**를 기준으로 합니다.

## 공개 함수

```c
int run_pipeline(
    char *const left_argv[],
    char *const right_argv[],
    int *out_status
);
```

`left_argv`와 `right_argv`는 일반적인 `exec` 계열 함수가 사용하는 형태처럼 **마지막 원소가 `NULL`인 argv 배열**이어야 합니다.

개념적으로 다음과 같은 배열입니다.

```c
char *left[] = {"printf", "hello\n", NULL};
char *right[] = {"wc", "-l", NULL};
```

반환 규칙은 다음과 같습니다.

- 두 자식을 만들고 모두 회수하면 함수 자체는 `0`을 반환하고 오른쪽 명령의 공개 종료 상태를 `*out_status`에 씁니다.
- `pipe`, `fork`, `waitpid` 같은 부모 측 작업에 실패하면 `-1`을 반환하고 `*out_status`를 변경하지 않습니다.
- 실행할 명령을 찾지 못하면 해당 자식의 상태를 `127`로 만듭니다.
- 실행 파일은 찾았지만 실행할 수 없으면 해당 자식의 상태를 `126`으로 만듭니다.
- 자식이 시그널로 종료하면 공개 상태는 `128 + signal`로 변환합니다.

여기서 함수의 반환값과 `*out_status`는 역할이 다릅니다.

```text
run_pipeline 반환값:
    파이프 생성, fork, wait 같은 "부모 측 실행 절차"의 성공 여부

*out_status:
    실제 오른쪽 외부 명령의 결과
```

따라서 오른쪽 명령이 상태 `7`로 정상 종료했더라도 두 자식을 정상적으로 만들고 회수했다면:

```text
run_pipeline(...) == 0
*out_status == 7
```

이 될 수 있습니다.

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/libcommand_pipeline.a
```

## 사용 예시

```c
#include "command_pipeline.h"

char *left[] = {"printf", "alpha\nbeta\n", NULL};
char *right[] = {"wc", "-l", NULL};
int status;

if (run_pipeline(left, right, &status) != 0) {
    /* pipe 생성, fork 또는 waitpid 실패 */
}
```

성공적으로 실행되면 개념적으로 셸의 다음 파이프와 비슷한 데이터 흐름이 만들어집니다.

```sh
printf 'alpha\nbeta\n' | wc -l
```

이 라이브러리는 셸 문법을 파싱하는 것이 아니라 이미 나누어진 두 `argv` 배열을 실행합니다.

## 주요 구현 결정

### 두 자식을 모두 만든 뒤 기다림

왼쪽 자식을 만든 직후 기다리지 않습니다.

잘못된 순서는 다음과 같습니다.

```text
fork(left)
→ wait(left)
→ fork(right)
```

왼쪽 명령의 출력이 pipe 버퍼보다 크면:

```text
left:
    pipe에 계속 쓰려 함

right:
    아직 생성되지 않아 읽는 프로세스가 없음

parent:
    left가 끝나기를 wait 중
```

이 되어 진행이 멈출 수 있습니다.

올바른 순서는 다음과 같습니다.

```text
pipe 생성
→ fork(left)
→ fork(right)
→ parent가 사용하지 않는 pipe 끝 닫음
→ 두 자식 wait
```

오른쪽 자식이 동시에 읽을 수 있어야 왼쪽의 큰 출력도 계속 흘러갈 수 있습니다.

### 각 프로세스는 사용하지 않는 pipe 끝을 닫음

pipe에는 읽기 끝과 쓰기 끝이 있습니다.

```text
pipefd[0] = read end
pipefd[1] = write end
```

왼쪽 자식은 stdout을 쓰기 끝에 연결합니다.

```text
left stdout → pipe write end
```

오른쪽 자식은 stdin을 읽기 끝에 연결합니다.

```text
pipe read end → right stdin
```

각 자식은 연결이 끝난 뒤 더 이상 필요하지 않은 원래 pipe FD를 닫습니다. 부모도 두 자식을 만든 뒤 읽기 끝과 쓰기 끝을 모두 닫습니다.

특히 부모가 쓰기 끝을 계속 열어 두면 오른쪽 프로세스 입장에서는 아직 pipe를 쓸 수 있는 프로세스가 존재한다고 보일 수 있으므로, 왼쪽 자식이 끝나도 EOF를 받지 못할 수 있습니다.

### `dup2`의 source와 destination이 같을 수 있음

일반적으로 왼쪽 자식은 다음과 같은 연결을 만듭니다.

```text
dup2(pipe_write, STDOUT_FILENO)
```

하지만 프로그램 시작 전에 stdout이 닫혀 있었다면 `pipe()`가 새 쓰기 끝에 FD `1`을 배정할 수도 있습니다.

그러면:

```text
pipe_write == STDOUT_FILENO
```

이 됩니다.

이 경우 이미 원하는 FD 번호이므로, 연결 이후 정리 코드가 그 FD를 "원래 pipe FD"라고 생각해 닫아 버리면 실제 stdout까지 닫게 됩니다.

따라서 `source == destination`인 경우를 고려해 중복 FD를 안전하게 정리해야 합니다.

같은 문제는 stdin이 미리 닫혀 있어 pipe 읽기 끝이 FD `0`으로 재사용되는 경우에도 발생할 수 있습니다.

### 두 번째 `fork` 실패 시 첫 번째 자식 회수

다음 순서에서:

```text
fork(left) 성공
fork(right) 실패
```

이미 왼쪽 자식은 실행 중입니다.

부모가 단순히 `-1`을 반환하면 왼쪽 자식이 계속 남거나 zombie가 될 수 있습니다. 따라서 실패 경로에서도 이미 만든 자식을 종료시키고 `waitpid`로 회수해야 합니다.

이 실패는 부모 측 실행 실패이므로 `*out_status`는 호출 전 값을 유지합니다.

### `waitpid`는 중단될 수 있음

`waitpid`는 시그널 전달 때문에 `EINTR`로 중단될 수 있습니다. 이 경우 자식이 반드시 사라진 것은 아니므로, 단순히 실패로 끝내지 않고 필요한 경우 다시 `waitpid`를 호출해 실제 자식 상태를 회수합니다.

즉 "wait 함수 호출이 한 번 실패했다"와 "자식 회수 자체가 불가능하다"를 구분해야 합니다.

### 자식 상태를 공개 종료 상태로 변환

`waitpid`가 돌려주는 값은 그대로 프로세스의 일반적인 종료 코드가 아닙니다. 상태를 해석해야 합니다.

개념적으로:

```text
정상 종료:
    WIFEXITED(status)
    → WEXITSTATUS(status)

시그널 종료:
    WIFSIGNALED(status)
    → 128 + WTERMSIG(status)
```

형태로 공개 상태를 만듭니다.

이 라이브러리는 파이프 전체의 상태로 오른쪽 명령의 결과를 사용하므로 왼쪽 명령이 실패해도 오른쪽 명령의 상태를 덮어쓰지 않습니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 4 MiB 데이터 전달이 교착 없이 끝나는지
- 표준 FD 0과 1이 pipe 끝으로 재사용되는 경우
- 왼쪽 실패가 오른쪽 종료 상태를 덮지 않는지
- 일반 종료, 시그널 종료, `126`, `127`
- 실행 전후 열린 FD 수가 같은지
- `NULL` 인자와 빈 `argv`
- 실패한 호출이 `out_status`를 덮지 않는지

4 MiB 테스트는 단순히 작은 문자열이 통과하는지만 보는 것이 아니라, **pipe 버퍼보다 큰 데이터에서도 두 프로세스가 동시에 진행하는 구조인지**를 검증합니다.

FD 개수 검사는 성공 경로뿐 아니라 반복 실행 뒤 pipe 끝이나 자식 관련 FD가 누수되지 않는지도 확인하는 목적이 있습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Public two-command execution API | `include/command_pipeline.h` |
| 2 | Wait retry and public exit status | `src/command_pipeline.c` |
| 3 | Safe dup2 and pipe-end closing | `src/command_pipeline.c` |
| 4 | Child file-descriptor setup and exec | `src/command_pipeline.c` |
| 5 | Create both children before waiting | `src/command_pipeline.c` |
| 6 | Cleanup after second fork failure and final status write | `src/command_pipeline.c` |

## 범위

정확히 두 명령만 실행합니다.

다음 기능은 제공하지 않습니다.

- 명령 문자열 파싱
- `<`, `>` 같은 입출력 재지정 문법
- 환경 변수 대입 문법
- 세 개 이상의 명령을 잇는 파이프
- 작업 제어
- 일반 셸 문법

즉 이 라이브러리의 입력은 셸 문자열이 아니라 **이미 완성된 두 개의 `argv` 배열**입니다.