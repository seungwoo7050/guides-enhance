#include "int_vector.h"

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
    struct int_vector_allocator allocator = {
        &state,
        test_resize,
        test_release
    };
    struct int_vector vector;
    struct int_vector default_vector;
    struct int_vector invalid_vector;
    struct int_vector_allocator invalid_allocator = {NULL, NULL, NULL};
    int value = 777;

    int_vector_init(&default_vector, NULL);
    CHECK(int_vector_push(&default_vector, -7) == 0);
    value = 0;
    CHECK(int_vector_get(&default_vector, 0, &value) == 0 && value == -7);
    int_vector_destroy(&default_vector);

    int_vector_init(&invalid_vector, &invalid_allocator);
    CHECK(int_vector_push(&invalid_vector, 1) == -1);
    CHECK(invalid_vector.data == NULL && invalid_vector.size == 0 &&
          invalid_vector.capacity == 0);
    int_vector_destroy(&invalid_vector);

    int_vector_init(&invalid_vector, &allocator);
    invalid_vector.size = 1;
    CHECK(int_vector_push(&invalid_vector, 1) == -1);
    value = 321;
    CHECK(int_vector_get(&invalid_vector, 0, &value) == -1 && value == 321);
    invalid_vector.size = 0;
    int_vector_destroy(&invalid_vector);

    int_vector_init(&vector, &allocator);
    CHECK(vector.data == NULL && vector.size == 0 && vector.capacity == 0);
    CHECK(int_vector_get(&vector, 0, &value) == -1);
    CHECK(value == 321);

    state.fail_on_call = state.calls + 1;
    CHECK(int_vector_push(&vector, 99) == -1);
    CHECK(vector.data == NULL && vector.size == 0 && vector.capacity == 0);
    state.fail_on_call = 0;

    for (int item = 0; item < 32; item++) {
        CHECK(int_vector_push(&vector, item * 3) == 0);
        CHECK(vector.size == (size_t)item + 1);
        CHECK(vector.size <= vector.capacity);
    }
    for (size_t index = 0; index < vector.size; index++) {
        value = -1;
        CHECK(int_vector_get(&vector, index, &value) == 0);
        CHECK(value == (int)index * 3);
    }

    while (vector.size < vector.capacity) {
        CHECK(int_vector_push(&vector, 1234) == 0);
    }
    {
        size_t old_size = vector.size;
        size_t old_capacity = vector.capacity;
        int *old_data = vector.data;
        int *snapshot = malloc(old_size * sizeof *snapshot);

        CHECK(snapshot != NULL);
        memcpy(snapshot, vector.data, old_size * sizeof *snapshot);
        state.fail_on_call = state.calls + 1;
        CHECK(int_vector_push(&vector, 9999) == -1);
        CHECK(vector.data == old_data);
        CHECK(vector.size == old_size);
        CHECK(vector.capacity == old_capacity);
        CHECK(memcmp(vector.data, snapshot, old_size * sizeof *snapshot) == 0);
        free(snapshot);
        state.fail_on_call = 0;
    }

    value = 888;
    CHECK(int_vector_get(&vector, vector.size, &value) == -1);
    CHECK(value == 888);
    CHECK(int_vector_get(&vector, 0, NULL) == -1);
    CHECK(int_vector_get(NULL, 0, &value) == -1);
    CHECK(int_vector_push(NULL, 1) == -1);

    int_vector_destroy(&vector);
    CHECK(vector.data == NULL && vector.size == 0 && vector.capacity == 0);
    int_vector_destroy(&vector);
    int_vector_destroy(NULL);

    puts("int-vector tests passed");
    return 0;
}
