#include "command_pipeline.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef TEST_TIMEOUT_SECONDS
#define TEST_TIMEOUT_SECONDS 30
#endif

#define CHECK(expression)                                                   \
    do                                                                      \
    {                                                                       \
        if (!(expression))                                                  \
        {                                                                   \
            fprintf(stderr, "%s:%d: check failed: %s\n",                  \
                    __FILE__, __LINE__, #expression);                       \
            return 1;                                                       \
        }                                                                   \
    } while (0)

static int count_open_descriptors(void) {
    long limit = sysconf(_SC_OPEN_MAX);
    int count = 0;

    if (limit < 0 || limit > 4096) {
        limit = 4096;
    }
    for (int fd = 0; fd < limit; fd++) {
        errno = 0;
        if (fcntl(fd, F_GETFD) != -1 || errno != EBADF) {
            count++;
        }
    }
    return count;
}

static int wait_child(pid_t pid) {
    int raw_status;
    pid_t result;

    do {
        result = waitpid(pid, &raw_status, 0);
    } while (result == -1 && errno == EINTR);
    if (result != pid || !WIFEXITED(raw_status)) {
        return -1;
    }
    return WEXITSTATUS(raw_status);
}

static int check_standard_descriptor_reuse(
    char *emit_path,
    char *expect_path,
    int close_stdin,
    int close_stdout
) {
    pid_t pid = fork();

    if (pid == -1) {
        return -1;
    }
    if (pid == 0) {
        int status = -1;
        char *left[] = {emit_path, "128", NULL};
        char *right[] = {expect_path, "128", NULL};

        if ((close_stdin && close(STDIN_FILENO) == -1) ||
            (close_stdout && close(STDOUT_FILENO) == -1)) {
            _exit(2);
        }
        if (run_pipeline(left, right, &status) != 0 || status != 0) {
            _exit(3);
        }
        _exit(0);
    }
    return wait_child(pid);
}

static int create_non_executable(char path[]) {
    static const char payload[] = "#!/bin/sh\nexit 0\n";
    int fd = mkstemp(path);
    size_t offset = 0;

    if (fd == -1) {
        return -1;
    }
    while (offset < sizeof payload - 1) {
        ssize_t written = write(fd, payload + offset, sizeof payload - 1 - offset);

        if (written > 0) {
            offset += (size_t)written;
        } else if (written == -1 && errno == EINTR) {
            continue;
        } else {
            (void)close(fd);
            (void)unlink(path);
            return -1;
        }
    }
    if (close(fd) == -1) {
        (void)unlink(path);
        return -1;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    int status = -1;
    int before;
    int after;
    char non_executable[] = "/tmp/command-pipeline-XXXXXX";
    char signal_text[32];
    char *left_large[] = {NULL, "4194304", NULL};
    char *right_large[] = {NULL, "4194304", NULL};
    char *left_empty[] = {NULL, "0", NULL};
    char *right_empty[] = {NULL, "0", NULL};
    char *left_failure[] = {NULL, "41", NULL};
    char *right_status[] = {NULL, "37", NULL};
    char *right_signal[] = {NULL, signal_text, NULL};
    char *missing[] = {"./definitely-not-a-command", NULL};
    char *not_executable[] = {non_executable, NULL};
    char *empty_argv[] = {NULL};

    if (argc != 5) {
        fprintf(stderr, "helper paths required\n");
        return 2;
    }
    alarm(TEST_TIMEOUT_SECONDS);
    CHECK(snprintf(signal_text, sizeof signal_text, "%d", SIGTERM) > 0);
    left_large[0] = argv[1];
    right_large[0] = argv[2];
    left_empty[0] = argv[1];
    right_empty[0] = argv[2];
    left_failure[0] = argv[3];
    right_status[0] = argv[3];
    right_signal[0] = argv[4];

    CHECK(run_pipeline(left_large, right_large, &status) == 0);
    CHECK(status == 0);
    // 파이프 끝이 0이나 1을 재사용할 때
    // 최종 stdin/stdout을 닫는 구현을 검출합니다.
    CHECK(check_standard_descriptor_reuse(argv[1], argv[2], 1, 0) == 0);
    CHECK(check_standard_descriptor_reuse(argv[1], argv[2], 0, 1) == 0);
    CHECK(check_standard_descriptor_reuse(argv[1], argv[2], 1, 1) == 0);

    CHECK(run_pipeline(left_empty, right_status, &status) == 0);
    CHECK(status == 37);

    CHECK(run_pipeline(left_failure, right_empty, &status) == 0);
    CHECK(status == 0);

    CHECK(run_pipeline(left_empty, right_signal, &status) == 0);
    CHECK(status == 128 + SIGTERM);

    CHECK(run_pipeline(left_empty, missing, &status) == 0);
    CHECK(status == 127);

    CHECK(create_non_executable(non_executable) == 0);
    CHECK(run_pipeline(left_empty, not_executable, &status) == 0);
    CHECK(status == 126);
    CHECK(unlink(non_executable) == 0);

    before = count_open_descriptors();
    for (int index = 0; index < 100; index++) {
        CHECK(run_pipeline(left_empty, right_empty, &status) == 0);
        CHECK(status == 0);
    }
    after = count_open_descriptors();
    CHECK(before == after);

    status = 919;
    CHECK(run_pipeline(NULL, right_large, &status) == -1);
    CHECK(status == 919);
    CHECK(run_pipeline(left_large, NULL, &status) == -1);
    CHECK(status == 919);
    CHECK(run_pipeline(empty_argv, right_large, &status) == -1);
    CHECK(status == 919);
    CHECK(run_pipeline(left_large, empty_argv, &status) == -1);
    CHECK(status == 919);
    CHECK(run_pipeline(left_large, right_large, NULL) == -1);

    puts("command-pipeline tests passed");
    return 0;
}
