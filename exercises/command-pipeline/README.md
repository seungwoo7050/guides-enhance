# command-pipeline

`command-pipeline`은 두 외부 명령을 POSIX 파이프로 연결하고 오른쪽 명령의 종료 상태를 반환하는 C 라이브러리입니다. 두 자식을 모두 만든 뒤 기다리며, 부모와 각 자식이 사용하지 않는 파이프 끝을 닫습니다.

## 공개 함수

```c
int run_pipeline(
    char *const left_argv[],
    char *const right_argv[],
    int *out_status
);
```

- 두 자식을 만들고 모두 회수하면 `0`을 반환하고 오른쪽 명령의 상태를 `*out_status`에 씁니다.
- `pipe`, `fork`, `waitpid` 같은 부모 측 작업에 실패하면 `-1`을 반환하고 `*out_status`를 바꾸지 않습니다.
- 명령을 찾지 못하면 자식 상태는 `127`입니다.
- 파일은 찾았지만 실행하지 못하면 `126`입니다.
- 시그널 종료는 `128 + signal`로 바꿉니다.

## 빌드

```sh
make
```

정적 라이브러리는 `build/libcommand_pipeline.a`에 생성됩니다.

## 사용 예시

```c
#include "command_pipeline.h"

char *left[] = {"printf", "alpha\\nbeta\\n", NULL};
char *right[] = {"wc", "-l", NULL};
int status;

if (run_pipeline(left, right, &status) != 0) {
    /* pipe 생성, fork 또는 waitpid 실패 */
}
```

## 주요 구현 결정

왼쪽 자식은 stdout을 파이프 쓰기 끝에 연결하고, 오른쪽 자식은 stdin을 파이프 읽기 끝에 연결합니다. 두 자식은 필요하지 않은 파이프 끝을 모두 닫습니다. 부모도 자식을 만든 뒤 두 끝을 바로 닫아 오른쪽 명령이 EOF를 받을 수 있게 합니다.

왼쪽 자식을 만든 직후 기다리지 않습니다. 왼쪽 출력이 파이프 버퍼 용량를 넘으면 오른쪽 자식이 아직 없어 읽어 갈 수 없으므로 서로 진행하지 못할 수 있습니다.

표준 입력이나 표준 출력이 미리 닫혀 있으면 `pipe`가 0이나 1을 새 FD로 사용할 수 있습니다. 이 경우 `dup2(source, destination)`의 두 번호가 같을 수 있으므로 이미 올바른 위치인 FD를 닫지 않습니다.

두 번째 `fork`가 실패하면 이미 만든 왼쪽 자식을 종료하고 `waitpid`로 회수합니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 4 MiB 데이터 전달이 교착 없이 끝나는지
- 표준 FD 0과 1이 파이프 끝으로 재사용되는 경우
- 왼쪽 실패가 오른쪽 종료 상태를 덮지 않는지
- 일반 종료, 시그널 종료, `126`, `127`
- 실행 전후 열린 FD 수가 같은지
- `NULL` 인자와 빈 `argv`
- 실패한 호출이 `out_status`를 덮지 않는지

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

정확히 두 명령만 실행합니다. 명령 문자열 파싱, 입출력 재지정, 환경 변수 대입, 세 개 이상의 파이프와 작업 제어은 제공하지 않습니다.
