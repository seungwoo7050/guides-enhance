#include <ctype.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* [Implementation 1] Growable word buffer */
struct builder {
    char *data;
    size_t length;
    size_t capacity;
};

/* [Implementation 2] Owned argv and command list */
struct command {
    char **argv;
    size_t argc;
    size_t capacity;
};

struct pipeline {
    struct command commands[2];
    size_t count;
};

static void builder_destroy(struct builder *builder) {
    free(builder->data);
    builder->data = NULL;
    builder->length = 0;
    builder->capacity = 0;
}

static int builder_reserve(struct builder *builder, size_t extra) {
    size_t required;
    size_t capacity;
    char *resized;

    if (builder->length == SIZE_MAX ||
        extra > SIZE_MAX - builder->length - 1) {
        return -1;
    }
    required = builder->length + extra + 1;
    if (required <= builder->capacity) {
        return 0;
    }
    capacity = builder->capacity == 0 ? 16 : builder->capacity;
    while (capacity < required) {
        if (capacity > SIZE_MAX / 2) {
            capacity = required;
            break;
        }
        capacity *= 2;
    }
    if (capacity < required) {
        return -1;
    }
    resized = realloc(builder->data, capacity);
    if (resized == NULL) {
        return -1;
    }
    builder->data = resized;
    builder->capacity = capacity;
    return 0;
}

static int builder_append(struct builder *builder, char value) {
    if (builder_reserve(builder, 1) != 0) {
        return -1;
    }
    builder->data[builder->length++] = value;
    return 0;
}

static char *builder_take(struct builder *builder) {
    char *result;

    if (builder_reserve(builder, 0) != 0) {
        return NULL;
    }
    builder->data[builder->length] = '\0';
    result = builder->data;
    builder->data = NULL;
    builder->length = 0;
    builder->capacity = 0;
    return result;
}

static void command_destroy(struct command *command) {
    for (size_t index = 0; index < command->argc; index++) {
        free(command->argv[index]);
    }
    free(command->argv);
    command->argv = NULL;
    command->argc = 0;
    command->capacity = 0;
}

static int command_add_owned_word(struct command *command, char *word) {
    if (command->argc == SIZE_MAX) {
        return -1;
    }
    if (command->argc + 1 >= command->capacity) {
        size_t capacity = command->capacity == 0 ? 4 : command->capacity;
        char **resized;

        while (capacity <= command->argc + 1) {
            if (capacity > SIZE_MAX / 2) {
                return -1;
            }
            capacity *= 2;
        }
        if (capacity > SIZE_MAX / sizeof *command->argv) {
            return -1;
        }
        resized = realloc(command->argv, capacity * sizeof *command->argv);
        if (resized == NULL) {
            return -1;
        }
        command->argv = resized;
        command->capacity = capacity;
    }
    command->argv[command->argc++] = word;
    command->argv[command->argc] = NULL;
    return 0;
}

static void pipeline_destroy(struct pipeline *pipeline) {
    for (size_t index = 0; index < 2; index++) {
        command_destroy(&pipeline->commands[index]);
    }
    pipeline->count = 0;
}

static int is_control_character(char value) {
    return value == '|' || value == '<' || value == '>' ||
           value == ';' || value == '&';
}

/* [Implementation 3] Quote and escape parsing */
static int parse_quoted(
    const char **cursor,
    char quote,
    struct builder *builder,
    const char **out_error
) {
    (*cursor)++;
    while (**cursor != quote) {
        if (**cursor == '\0') {
            *out_error = quote == '\'' ?
                "unclosed single quote" :
                "unclosed double quote";
            return -1;
        }
        if (quote == '"' && **cursor == '\\') {
            (*cursor)++;
            if (**cursor == '\0') {
                *out_error = "missing character after backslash in double quotes";
                return -1;
            }
        }
        if (builder_append(builder, **cursor) != 0) {
            *out_error = "out of memory";
            return -1;
        }
        (*cursor)++;
    }
    (*cursor)++;
    return 0;
}

static int parse_word(
    const char **cursor,
    char **out_word,
    const char **out_error
) {
    struct builder builder = {NULL, 0, 0};
    int started = 0;

    while (**cursor != '\0' &&
           !isspace((unsigned char)**cursor) &&
           !is_control_character(**cursor)) {
        char current = **cursor;

        started = 1;
        if (current == '\\') {
            (*cursor)++;
            if (**cursor == '\0') {
                *out_error = "missing character after backslash";
                builder_destroy(&builder);
                return -1;
            }
            if (builder_append(&builder, **cursor) != 0) {
                *out_error = "out of memory";
                builder_destroy(&builder);
                return -1;
            }
            (*cursor)++;
        } else if (current == '\'' || current == '"') {
            if (parse_quoted(cursor, current, &builder, out_error) != 0) {
                builder_destroy(&builder);
                return -1;
            }
        } else {
            if (builder_append(&builder, current) != 0) {
                *out_error = "out of memory";
                builder_destroy(&builder);
                return -1;
            }
            (*cursor)++;
        }
    }
    if (!started) {
        *out_error = "word expected";
        return -1;
    }
    *out_word = builder_take(&builder);
    if (*out_word == NULL) {
        *out_error = "out of memory";
        builder_destroy(&builder);
        return -1;
    }
    return 0;
}

/* [Implementation 4] Complete syntax validation before execution */
// 문법 전체를 확인한 뒤에만 실행 단계로 넘어갑니다.
// 따라서 오류 입력은 자식을 만들지 않습니다.
static int parse_line(
    const char *line,
    struct pipeline *pipeline,
    const char **out_error
) {
    const char *cursor = line;
    size_t current = 0;

    memset(pipeline, 0, sizeof *pipeline);
    pipeline->count = 1;
    while (*cursor != '\0') {
        while (isspace((unsigned char)*cursor)) {
            cursor++;
        }
        if (*cursor == '\0') {
            break;
        }
        if (*cursor == '|') {
            if (pipeline->commands[current].argc == 0) {
                *out_error = "empty command around pipe";
                goto fail;
            }
            if (pipeline->count == 2) {
                *out_error = "only one pipe is supported";
                goto fail;
            }
            pipeline->count = 2;
            current = 1;
            cursor++;
            continue;
        }
        if (*cursor == '<' || *cursor == '>' ||
            *cursor == ';' || *cursor == '&') {
            *out_error = "unsupported control operator";
            goto fail;
        }
        {
            char *word;

            if (parse_word(&cursor, &word, out_error) != 0) {
                goto fail;
            }
            if (command_add_owned_word(&pipeline->commands[current], word) != 0) {
                free(word);
                *out_error = "out of memory";
                goto fail;
            }
        }
    }
    if (pipeline->commands[0].argc == 0 ||
        pipeline->commands[pipeline->count - 1].argc == 0) {
        *out_error = "empty command";
        goto fail;
    }
    return 0;

fail:
    pipeline_destroy(pipeline);
    return -1;
}

static void close_ignored(int fd) {
    if (fd >= 0) {
        (void)close(fd);
    }
}

/* [Implementation 5] Wait retry and file-descriptor duplication */
static int wait_retry(pid_t pid, int *out_status) {
    pid_t result;

    do {
        result = waitpid(pid, out_status, 0);
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

static int duplicate_to(int source, int destination) {
    int result;

    // 파이프가 닫힌 표준 FD 번호를 재사용하면
    // source와 destination이 같을 수 있습니다.
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

/* [Implementation 6] Child setup and exec failure status */
static void child_exec(
    char *const argv[],
    int input_fd,
    int output_fd,
    int read_fd,
    int write_fd
) {
    int saved_errno;
    static const char message[] = "command execution failed\n";

    if (input_fd != -1 && duplicate_to(input_fd, STDIN_FILENO) != 0) {
        _exit(126);
    }
    if (output_fd != -1 && duplicate_to(output_fd, STDOUT_FILENO) != 0) {
        _exit(126);
    }
    close_pipe_end_after_dup(read_fd, input_fd, output_fd);
    if (write_fd != read_fd) {
        close_pipe_end_after_dup(write_fd, input_fd, output_fd);
    }
    execvp(argv[0], argv);
    saved_errno = errno;
    (void)write(STDERR_FILENO, message, sizeof message - 1);
    _exit(saved_errno == ENOENT ? 127 : 126);
}

/* [Implementation 7] Single command and two-command pipeline */
static int execute_single(const struct command *command, int *out_status) {
    pid_t pid = fork();
    int raw_status;

    if (pid == -1) {
        return -1;
    }
    if (pid == 0) {
        child_exec(command->argv, -1, -1, -1, -1);
    }
    if (wait_retry(pid, &raw_status) != 0) {
        return -1;
    }
    *out_status = public_status(raw_status);
    return 0;
}

static int execute_pair(const struct pipeline *pipeline, int *out_status) {
    int ends[2];
    pid_t left_pid;
    pid_t right_pid;
    int left_status;
    int right_status;
    int left_wait;
    int right_wait;

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
        child_exec(pipeline->commands[0].argv, -1, ends[1], ends[0], ends[1]);
    }
    right_pid = fork();
    if (right_pid == -1) {
        close_ignored(ends[0]);
        close_ignored(ends[1]);
        (void)kill(left_pid, SIGKILL);
        (void)wait_retry(left_pid, &left_status);
        return -1;
    }
    if (right_pid == 0) {
        child_exec(pipeline->commands[1].argv, ends[0], -1, ends[0], ends[1]);
    }
    close_ignored(ends[0]);
    close_ignored(ends[1]);
    left_wait = wait_retry(left_pid, &left_status);
    right_wait = wait_retry(right_pid, &right_status);
    if (left_wait != 0 || right_wait != 0) {
        return -1;
    }
    *out_status = public_status(right_status);
    return 0;
}

static int execute_pipeline(const struct pipeline *pipeline, int *out_status) {
    if (pipeline->count == 1) {
        return execute_single(&pipeline->commands[0], out_status);
    }
    return execute_pair(pipeline, out_status);
}

/* [Implementation 8] CLI exit status and cleanup */
int main(int argc, char *argv[]) {
    struct pipeline pipeline;
    const char *error = "unknown error";
    int status;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <command string>\n", argv[0]);
        return 2;
    }
    if (parse_line(argv[1], &pipeline, &error) != 0) {
        fprintf(stderr, "Syntax error: %s\n", error);
        return 2;
    }
    if (execute_pipeline(&pipeline, &status) != 0) {
        fprintf(stderr, "Execution error: process lifecycle failed\n");
        pipeline_destroy(&pipeline);
        return 125;
    }
    pipeline_destroy(&pipeline);
    return status;
}
