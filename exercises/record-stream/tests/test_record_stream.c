#include "record_stream.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

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

struct failing_allocator {
    size_t calls;
    size_t fail_on_call;
};

static void *test_resize(void *context, void *pointer, size_t size) {
    struct failing_allocator *state = context;

    state->calls++;
    if (state->fail_on_call != 0 && state->calls == state->fail_on_call) {
        return NULL;
    }
    return realloc(pointer, size);
}

static void test_release(void *context, void *pointer) {
    (void)context;
    free(pointer);
}

static int write_all(int fd, const void *data, size_t length) {
    const unsigned char *cursor = data;

    while (length > 0) {
        ssize_t count = write(fd, cursor, length);

        if (count > 0) {
            cursor += (size_t)count;
            length -= (size_t)count;
            continue;
        }
        if (count == -1 && errno == EINTR) {
            continue;
        }
        return -1;
    }
    return 0;
}

static int expect_bytes(
    struct record_reader *reader,
    const void *expected,
    size_t expected_length
) {
    char *record = (char *)0x1;
    size_t length = 999;
    int result = record_reader_next(reader, &record, &length);

    CHECK(result == 1);
    CHECK(length == expected_length);
    CHECK(record != NULL);
    CHECK(record[length] == '\0');
    if (expected_length > 0) {
        CHECK(memcmp(record, expected, expected_length) == 0);
    }
    free(record);
    return 0;
}

static int expect_text(struct record_reader *reader, const char *expected) {
    return expect_bytes(reader, expected, strlen(expected));
}

static int expect_eof(struct record_reader *reader) {
    char *record = (char *)0x1;
    size_t length = 999;

    CHECK(record_reader_next(reader, &record, &length) == 0);
    CHECK(record == (char *)0x1 && length == 999);
    return 0;
}

static int test_fragmented_records(void) {
    int ends[2];
    struct record_reader reader;
    const char *first = "alpha\n\nbeta";
    const char *second = "-continues-across-buffer\nlast";

    CHECK(pipe(ends) == 0);
    CHECK(write_all(ends[1], first, strlen(first)) == 0);
    CHECK(write_all(ends[1], second, strlen(second)) == 0);
    CHECK(close(ends[1]) == 0);

    record_reader_init(&reader, ends[0], NULL);
    CHECK(expect_text(&reader, "alpha") == 0);
    CHECK(expect_text(&reader, "") == 0);
    CHECK(expect_text(&reader, "beta-continues-across-buffer") == 0);
    CHECK(expect_text(&reader, "last") == 0);
    CHECK(expect_eof(&reader) == 0);
    CHECK(expect_eof(&reader) == 0);
    record_reader_destroy(&reader);
    CHECK(reader.fd == -1 && reader.pending == NULL && reader.length == 0 &&
          reader.capacity == 0 && reader.eof == 0 && reader.failed == 0);

    CHECK(fcntl(ends[0], F_GETFD) != -1);
    CHECK(close(ends[0]) == 0);
    return 0;
}

static int test_trailing_newline(void) {
    int ends[2];
    struct record_reader reader;

    CHECK(pipe(ends) == 0);
    CHECK(write_all(ends[1], "tail\n", 5) == 0);
    CHECK(close(ends[1]) == 0);
    record_reader_init(&reader, ends[0], NULL);
    CHECK(expect_text(&reader, "tail") == 0);
    CHECK(expect_eof(&reader) == 0);
    record_reader_destroy(&reader);
    CHECK(close(ends[0]) == 0);
    return 0;
}

static int test_embedded_nul(void) {
    static const unsigned char input[] = {
        'a', 0, 'b', '\n', 'c', 0, 'd'
    };
    static const unsigned char first[] = {'a', 0, 'b'};
    static const unsigned char second[] = {'c', 0, 'd'};
    int ends[2];
    struct record_reader reader;

    CHECK(pipe(ends) == 0);
    CHECK(write_all(ends[1], input, sizeof input) == 0);
    CHECK(close(ends[1]) == 0);
    record_reader_init(&reader, ends[0], NULL);
    CHECK(expect_bytes(&reader, first, sizeof first) == 0);
    CHECK(expect_bytes(&reader, second, sizeof second) == 0);
    CHECK(expect_eof(&reader) == 0);
    record_reader_destroy(&reader);
    CHECK(close(ends[0]) == 0);
    return 0;
}

static int test_independent_readers(void) {
    int left_ends[2];
    int right_ends[2];
    struct record_reader left;
    struct record_reader right;

    CHECK(pipe(left_ends) == 0);
    CHECK(pipe(right_ends) == 0);
    CHECK(write_all(left_ends[1], "left-1\nleft-2\n", 14) == 0);
    CHECK(write_all(right_ends[1], "right-1\nright-2", 15) == 0);
    CHECK(close(left_ends[1]) == 0);
    CHECK(close(right_ends[1]) == 0);

    record_reader_init(&left, left_ends[0], NULL);
    record_reader_init(&right, right_ends[0], NULL);
    CHECK(expect_text(&left, "left-1") == 0);
    CHECK(expect_text(&right, "right-1") == 0);
    CHECK(expect_text(&left, "left-2") == 0);
    CHECK(expect_text(&right, "right-2") == 0);
    CHECK(expect_eof(&left) == 0);
    CHECK(expect_eof(&right) == 0);
    record_reader_destroy(&right);
    record_reader_destroy(&left);
    CHECK(close(right_ends[0]) == 0);
    CHECK(close(left_ends[0]) == 0);
    return 0;
}

static int test_allocator_failure(void) {
    int ends[2];
    struct record_reader reader;
    struct failing_allocator state = {0, 1};
    struct record_reader_allocator allocator = {
        &state,
        test_resize,
        test_release
    };
    char *record = (char *)0x2;
    size_t length = 123;

    CHECK(pipe(ends) == 0);
    CHECK(write_all(ends[1], "allocation failure line\n", 24) == 0);
    CHECK(close(ends[1]) == 0);

    record_reader_init(&reader, ends[0], &allocator);
    // 내부 버퍼 확장 실패가 출력값을 덮거나
    // 다시 읽을 수 있는 상태처럼 남는지 검출합니다.
    CHECK(record_reader_next(&reader, &record, &length) == -1);
    CHECK(record == (char *)0x2 && length == 123);
    CHECK(reader.failed == 1);
    CHECK(record_reader_next(&reader, &record, &length) == -1);
    CHECK(record == (char *)0x2 && length == 123);
    record_reader_destroy(&reader);
    CHECK(fcntl(ends[0], F_GETFD) != -1);
    CHECK(close(ends[0]) == 0);
    return 0;
}

static int test_invalid_inputs(void) {
    struct record_reader reader;
    struct record_reader invalid_reader;
    struct record_reader_allocator invalid_allocator = {NULL, NULL, NULL};
    char *record = (char *)0x3;
    size_t length = 321;

    record_reader_init(NULL, -1, NULL);
    record_reader_init(&reader, -1, NULL);
    CHECK(record_reader_next(NULL, &record, &length) == -1);
    CHECK(record == (char *)0x3 && length == 321);
    CHECK(record_reader_next(&reader, NULL, &length) == -1);
    CHECK(length == 321);
    CHECK(record_reader_next(&reader, &record, NULL) == -1);
    CHECK(record == (char *)0x3);
    CHECK(record_reader_next(&reader, &record, &length) == -1);
    CHECK(record == (char *)0x3 && length == 321);
    CHECK(reader.failed == 1);
    record_reader_destroy(&reader);

    record_reader_init(&invalid_reader, -1, &invalid_allocator);
    CHECK(record_reader_next(&invalid_reader, &record, &length) == -1);
    CHECK(record == (char *)0x3 && length == 321);
    record_reader_destroy(&invalid_reader);
    record_reader_destroy(NULL);
    return 0;
}

int main(void) {
    alarm(15);
    CHECK(test_fragmented_records() == 0);
    CHECK(test_trailing_newline() == 0);
    CHECK(test_embedded_nul() == 0);
    CHECK(test_independent_readers() == 0);
    CHECK(test_allocator_failure() == 0);
    CHECK(test_invalid_inputs() == 0);
    puts("record-stream tests passed");
    return 0;
}
