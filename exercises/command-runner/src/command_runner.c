#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

/* Parser inspection entry point: print owned words without executing commands. */
int main(int argc, char *argv[]) {
    struct pipeline pipeline;
    const char *error = "unknown error";
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <command string>\n", argv[0]);
        return 2;
    }
    if (parse_line(argv[1], &pipeline, &error) != 0) {
        fprintf(stderr, "Syntax error: %s\n", error);
        return 2;
    }
    for (size_t command = 0; command < pipeline.count; command++) {
        for (size_t word = 0; word < pipeline.commands[command].argc; word++) {
            printf("%zu:%zu:%s\n", command, word, pipeline.commands[command].argv[word]);
        }
    }
    pipeline_destroy(&pipeline);
    return 0;
}
