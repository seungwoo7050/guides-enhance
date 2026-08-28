#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

/* [Implementation 19] fork 전 heap 값과 stdout 정리.
 * fork 전에 flush하지 않으면 부모와 자식이
 * 같은 buffered output을 두 번 쓸 수 있습니다. */
int main(void) {
    int *value;
    pid_t child;
    int status;

    value = malloc(sizeof(*value));
    if (value == NULL) {
        perror("malloc");
        return 1;
    }
    *value = 41;
    printf("before fork pid=%ld address=%p value=%d\n", (long)getpid(), (void *)value, *value);
    if (fflush(stdout) == EOF) {
        free(value);
        return 1;
    }

    /* [Implementation 20] 자식의 private write와 `_exit`.
     * 상속받은 stdio 정리 함수를 다시 실행하지 않도록 _exit로 끝냅니다. */
    child = fork();
    if (child < 0) {
        perror("fork");
        free(value);
        return 1;
    }
    if (child == 0) {
        *value = 99;
        printf("child pid=%ld address=%p value=%d\n", (long)getpid(), (void *)value, *value);
        if (fflush(stdout) == EOF)
            _exit(1);
        free(value);
        _exit(0);
    }

    /* [Implementation 21] EINTR를 처리하는 `waitpid`와 부모 값 확인.
     * 결과는 값의 분리만 보여 주며
     * 실제 physical frame은 확인하지 않습니다. */
    for (;;) {
        if (waitpid(child, &status, 0) >= 0)
            break;
        if (errno != EINTR) {
            perror("waitpid");
            free(value);
            return 1;
        }
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "자식 프로세스가 실패했습니다.\n");
        free(value);
        return 1;
    }
    {
        int unchanged;

        unchanged = *value == 41;
        printf("parent pid=%ld address=%p value=%d unchanged=%s\n",
            (long)getpid(),
            (void *)value,
            *value,
            unchanged != 0 ? "yes" : "no");
        free(value);
        return unchanged != 0 ? 0 : 1;
    }
}
