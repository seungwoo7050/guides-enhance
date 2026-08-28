#include "command_pipeline.h"

#include <errno.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void close_ignored(int fd) {
    if (fd >= 0) {
        (void)close(fd);
    }
}

/* [Implementation 2] Wait retry and public exit status */
static int wait_retry(pid_t pid, int *status) {
    pid_t result;

    do {
        result = waitpid(pid, status, 0);
    } while (result == -1 && errno == EINTR);
    return result == pid ? 0 : -1;
}

static int public_status(int raw_status) {
    if (WIFEXITED(raw_status)) {
        return WEXITSTATUS(raw_status);
    }
    if (WIFSIGNALED(raw_status)) {
        return 128 + WTERMSIG(raw_status);
    }
    return 125;
}

/* [Implementation 3] Safe dup2 and pipe-end closing */
static int duplicate_to(int source, int destination) {
    int result;

    // 파이프가 닫힌 표준 FD 번호를 재사용하면
    // 두 번호가 같을 수 있습니다.
    if (source == destination) {
        return 0;
    }
    do {
        result = dup2(source, destination);
    } while (result == -1 && errno == EINTR);
    return result == -1 ? -1 : 0;
}

static void close_pipe_end_after_dup(
    int fd,
    int input_fd,
    int output_fd
) {
    if (fd < 0) {
        return;
    }
    if (fd == STDIN_FILENO && input_fd != -1) {
        return;
    }
    if (fd == STDOUT_FILENO && output_fd != -1) {
        return;
    }
    close_ignored(fd);
}

/* [Implementation 4] Child file-descriptor setup and exec */
static void exec_child(
    char *const argv[],
    int input_fd,
    int output_fd,
    int pipe_read,
    int pipe_write
) {
    int saved_errno;

    if (input_fd != -1 && duplicate_to(input_fd, STDIN_FILENO) != 0) {
        _exit(126);
    }
    if (output_fd != -1 && duplicate_to(output_fd, STDOUT_FILENO) != 0) {
        _exit(126);
    }
    close_pipe_end_after_dup(pipe_read, input_fd, output_fd);
    if (pipe_write != pipe_read) {
        close_pipe_end_after_dup(pipe_write, input_fd, output_fd);
    }
    execvp(argv[0], argv);
    saved_errno = errno;
    _exit(saved_errno == ENOENT ? 127 : 126);
}

/* [Implementation 5] Create both children before waiting */
int run_pipeline(
    char *const left_argv[],
    char *const right_argv[],
    int *out_status
) {
    int ends[2];
    pid_t left_pid;
    pid_t right_pid;
    int left_status;
    int right_status;
    int left_wait_result;
    int right_wait_result;

    if (left_argv == NULL || right_argv == NULL || out_status == NULL ||
        left_argv[0] == NULL || right_argv[0] == NULL) {
        return -1;
    }
    if (pipe(ends) == -1) {
        return -1;
    }
    left_pid = fork();
    if (left_pid == -1) {
        close_ignored(ends[0]);
        close_ignored(ends[1]);
        return -1;
    }
    if (left_pid == 0) {
        exec_child(left_argv, -1, ends[1], ends[0], ends[1]);
    }

    /* [Implementation 6] Cleanup after second fork failure and final status write */
    right_pid = fork();
    if (right_pid == -1) {
        close_ignored(ends[0]);
        close_ignored(ends[1]);
        // 이미 만든 자식을 종료하고 회수해 좀비 프로세스나
        // 실행 중인 자식을 남기지 않습니다.
        (void)kill(left_pid, SIGKILL);
        (void)wait_retry(left_pid, &left_status);
        return -1;
    }
    if (right_pid == 0) {
        exec_child(right_argv, ends[0], -1, ends[0], ends[1]);
    }

    close_ignored(ends[0]);
    close_ignored(ends[1]);
    left_wait_result = wait_retry(left_pid, &left_status);
    right_wait_result = wait_retry(right_pid, &right_status);
    if (left_wait_result != 0 || right_wait_result != 0) {
        return -1;
    }
    *out_status = public_status(right_status);
    return 0;
}
