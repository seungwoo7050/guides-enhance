#include "owned_string.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

int main(void) {
    struct failing_allocator state = {0, 0};
    struct owned_string_allocator allocator = {
        &state,
        test_resize,
        test_release
    };
    struct owned_string string;
    struct owned_string default_string;
    struct owned_string invalid_string;
    struct owned_string_allocator invalid_allocator = {NULL, NULL, NULL};

    owned_string_init(&default_string, NULL);
    CHECK(default_string.data == NULL && default_string.length == 0 &&
          default_string.capacity == 0);
    CHECK(owned_string_append(&default_string, "") == 0);
    CHECK(default_string.data != NULL && default_string.length == 0 &&
          default_string.capacity >= 1 && default_string.data[0] == '\0');
    {
        char *old_data = default_string.data;
        size_t old_capacity = default_string.capacity;

        CHECK(owned_string_append(&default_string, "abc") == 0);
        CHECK(default_string.data == old_data);
        CHECK(default_string.capacity == old_capacity);
        CHECK(strcmp(default_string.data, "abc") == 0);
        CHECK(owned_string_append(&default_string, "") == 0);
        CHECK(default_string.data == old_data);
        CHECK(default_string.length == 3);
    }
    owned_string_destroy(&default_string);

    owned_string_init(&invalid_string, &invalid_allocator);
    CHECK(owned_string_append(&invalid_string, "x") == -1);
    CHECK(invalid_string.data == NULL && invalid_string.length == 0 &&
          invalid_string.capacity == 0);
    owned_string_destroy(&invalid_string);

    owned_string_init(&invalid_string, &allocator);
    invalid_string.length = 1;
    invalid_string.capacity = 1;
    CHECK(owned_string_append(&invalid_string, "x") == -1);
    CHECK(invalid_string.data == NULL && invalid_string.length == 1 &&
          invalid_string.capacity == 1);
    invalid_string.length = 0;
    invalid_string.capacity = 0;
    owned_string_destroy(&invalid_string);

    owned_string_init(&string, &allocator);
    state.fail_on_call = state.calls + 1;
    CHECK(owned_string_append(&string, "first allocation fails") == -1);
    CHECK(string.data == NULL && string.length == 0 && string.capacity == 0);
    state.fail_on_call = 0;
    CHECK(owned_string_append(&string, "hello") == 0);
    CHECK(strcmp(string.data, "hello") == 0);
    CHECK(string.length == 5 && string.length < string.capacity);
    CHECK(string.data[string.length] == '\0');
    CHECK(owned_string_append(&string, " world") == 0);
    CHECK(strcmp(string.data, "hello world") == 0);

    owned_string_destroy(&string);
    owned_string_init(&string, &allocator);
    CHECK(owned_string_append(&string, "abcdefghijklmno") == 0);
    CHECK(string.length == 15 && string.capacity == 16);
    CHECK(owned_string_append(&string, string.data) == 0);
    CHECK(strcmp(string.data, "abcdefghijklmnoabcdefghijklmno") == 0);

    owned_string_destroy(&string);
    owned_string_init(&string, &allocator);
    CHECK(owned_string_append(&string, "abcdef") == 0);
    CHECK(owned_string_append(&string, string.data + 2) == 0);
    CHECK(strcmp(string.data, "abcdefcdef") == 0);

    owned_string_destroy(&string);
    owned_string_init(&string, &allocator);
    CHECK(owned_string_append(&string, "abcdefghijklmno") == 0);
    CHECK(owned_string_append(&string, string.data + 5) == 0);
    CHECK(strcmp(string.data, "abcdefghijklmnofghijklmno") == 0);

    while (string.length + 2 < string.capacity) {
        CHECK(owned_string_append(&string, "x") == 0);
    }
    {
        char *old_data = string.data;
        size_t old_length = string.length;
        size_t old_capacity = string.capacity;
        char *snapshot = malloc(old_length + 1);

        CHECK(snapshot != NULL);
        memcpy(snapshot, string.data, old_length + 1);
        // 다음 resize를 실패시켜 data, 내용, length와 capacity가
        // 모두 보존되는지 확인합니다.
        state.fail_on_call = state.calls + 1;
        CHECK(owned_string_append(&string, "forces-growth") == -1);
        CHECK(string.data == old_data);
        CHECK(string.length == old_length);
        CHECK(string.capacity == old_capacity);
        CHECK(strcmp(string.data, snapshot) == 0);
        free(snapshot);
        state.fail_on_call = 0;
    }

    CHECK(owned_string_append(NULL, "x") == -1);
    CHECK(owned_string_append(&string, NULL) == -1);
    owned_string_destroy(&string);
    CHECK(string.data == NULL && string.length == 0 && string.capacity == 0);
    owned_string_destroy(&string);
    owned_string_destroy(NULL);

    puts("owned-string tests passed");
    return 0;
}
