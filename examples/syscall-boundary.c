#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* [Implementation 1] 소유할 임시 디렉터리와 실패 확인용 path 생성.
 * PID와 재시도 번호를 조합해 충돌을 피하고,
 * 그 안의 없는 경로를 사용합니다. */
static int create_temp_directory(char *path, size_t size) {
    unsigned int attempt;

    attempt = 0U;
    while (attempt < 128U) {
        int written;

        written = snprintf(path, size, "/tmp/kernel-model-syscall-%ld-%u",
            (long)getpid(), attempt);
        if (written < 0 || (size_t)written >= size) {
            errno = ENAMETOOLONG;
            return -1;
        }
        if (mkdir(path, S_IRWXU) == 0)
            return 0;
        if (errno != EEXIST)
            return -1;
        attempt += 1U;
    }
    errno = EEXIST;
    return -1;
}

/* [Implementation 2] `write` 성공과 임시 디렉터리 정리. */
int main(void) {
    const char message[] = "write 호출이 프로세스와 커널의 경계를 넘었습니다.\n";
    char directory[128];
    char missing_path[sizeof(directory) + sizeof("/missing")];
    int descriptor;
    int saved_errno;
    int written;

    if (write(STDOUT_FILENO, message, sizeof(message) - 1U) < 0) {
        perror("write");
        return 1;
    }
    if (create_temp_directory(directory, sizeof(directory)) != 0) {
        perror("임시 디렉터리 생성");
        return 1;
    }
    written = snprintf(missing_path, sizeof(missing_path), "%s/missing", directory);
    if (written < 0 || (size_t)written >= sizeof(missing_path)) {
        (void)rmdir(directory);
        fprintf(stderr, "임시 경로가 너무 깁니다.\n");
        return 1;
    }

    /* [Implementation 3] `open` 직후 `errno` 보존.
     * 이후 정리 함수가 errno를 바꾸더라도
     * ENOENT였다는 근거를 유지합니다. */
    errno = 0;
    descriptor = open(missing_path, O_RDONLY);
    saved_errno = errno;
    if (descriptor >= 0) {
        (void)close(descriptor);
        (void)rmdir(directory);
        fprintf(stderr, "실패 확인용 경로가 예상과 달리 열렸습니다.\n");
        return 1;
    }
    if (rmdir(directory) != 0) {
        perror("rmdir");
        return 1;
    }
    if (saved_errno != ENOENT) {
        fprintf(stderr, "open이 예상하지 않은 오류로 실패했습니다: errno=%d 메시지=%s\n",
            saved_errno,
            strerror(saved_errno));
        return 1;
    }
    printf("open이 예상대로 실패했습니다: errno=%d 메시지=%s\n",
        saved_errno,
        strerror(saved_errno));
    return 0;
}
