#include "record_stream.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void *default_resize(void *context, void *pointer, size_t size) {
    (void)context;
    return realloc(pointer, size);
}

static void default_release(void *context, void *pointer) {
    (void)context;
    free(pointer);
}

void record_reader_init(
    struct record_reader *reader,
    int fd,
    const struct record_reader_allocator *allocator
) {
    if (reader == NULL) {
        return;
    }
    reader->fd = fd;
    reader->pending = NULL;
    reader->length = 0;
    reader->capacity = 0;
    reader->eof = 0;
    reader->failed = 0;
    if (allocator != NULL) {
        reader->allocator = *allocator;
    } else {
        reader->allocator.context = NULL;
        reader->allocator.resize = default_resize;
        reader->allocator.release = default_release;
    }
}

/* [Implementation 2] Pending-buffer growth without state loss */
static int append_pending(
    struct record_reader *reader,
    const char *data,
    size_t count
) {
    size_t required;

    if (count == 0) {
        return 0;
    }
    if (count > SIZE_MAX - reader->length) {
        return -1;
    }
    required = reader->length + count;
    if (required > reader->capacity) {
        size_t capacity = reader->capacity == 0 ? 16 : reader->capacity;
        char *resized;

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
        resized = reader->allocator.resize(
            reader->allocator.context,
            reader->pending,
            capacity
        );
        if (resized == NULL) {
            return -1;
        }
        reader->pending = resized;
        reader->capacity = capacity;
    }
    memcpy(reader->pending + reader->length, data, count);
    reader->length += count;
    return 0;
}

/* [Implementation 3] Newline search */
static int find_newline(const struct record_reader *reader, size_t *out_index) {
    for (size_t index = 0; index < reader->length; index++) {
        if (reader->pending[index] == '\n') {
            *out_index = index;
            return 1;
        }
    }
    return 0;
}

/* [Implementation 4] Record allocation before consuming input */
static int emit_record(
    struct record_reader *reader,
    size_t record_length,
    size_t consumed,
    char **out_record,
    size_t *out_length
) {
    char *record;

    if (record_length == SIZE_MAX) {
        return -1;
    }
    // 레코드 할당에 실패하면 아직 소비하지 않은 입력 버퍼를
    // 그대로 유지합니다.
    record = malloc(record_length + 1);
    if (record == NULL) {
        return -1;
    }
    if (record_length > 0) {
        memcpy(record, reader->pending, record_length);
    }
    record[record_length] = '\0';
    if (consumed < reader->length) {
        memmove(
            reader->pending,
            reader->pending + consumed,
            reader->length - consumed
        );
    }
    reader->length -= consumed;
    *out_record = record;
    *out_length = record_length;
    return 1;
}

/* [Implementation 5] Read, EOF, and terminal-error handling */
int record_reader_next(
    struct record_reader *reader,
    char **out_record,
    size_t *out_length
) {
    if (reader == NULL || out_record == NULL || out_length == NULL ||
        reader->allocator.resize == NULL || reader->allocator.release == NULL) {
        return -1;
    }
    if (reader->failed) {
        return -1;
    }
    for (;;) {
        size_t newline_index;

        if (find_newline(reader, &newline_index)) {
            int result = emit_record(
                reader,
                newline_index,
                newline_index + 1,
                out_record,
                out_length
            );

            if (result == -1) {
                reader->failed = 1;
            }
            return result;
        }
        if (reader->eof) {
            if (reader->length == 0) {
                return 0;
            }
            {
                int result = emit_record(
                    reader,
                    reader->length,
                    reader->length,
                    out_record,
                    out_length
                );

                if (result == -1) {
                    reader->failed = 1;
                }
                return result;
            }
        }
        {
            char chunk[7];
            ssize_t count;

            do {
                count = read(reader->fd, chunk, sizeof chunk);
            } while (count == -1 && errno == EINTR);
            if (count > 0) {
                if (append_pending(reader, chunk, (size_t)count) != 0) {
                    reader->failed = 1;
                    return -1;
                }
            } else if (count == 0) {
                reader->eof = 1;
            } else {
                reader->failed = 1;
                return -1;
            }
        }
    }
}

/* [Implementation 6] Internal-buffer cleanup without closing fd */
void record_reader_destroy(struct record_reader *reader) {
    if (reader == NULL) {
        return;
    }
    if (reader->allocator.release != NULL && reader->pending != NULL) {
        reader->allocator.release(reader->allocator.context, reader->pending);
    }
    reader->fd = -1;
    reader->pending = NULL;
    reader->length = 0;
    reader->capacity = 0;
    reader->eof = 0;
    reader->failed = 0;
}
