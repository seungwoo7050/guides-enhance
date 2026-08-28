#include "owned_string.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static void *default_resize(void *context, void *pointer, size_t size) {
    (void)context;
    return realloc(pointer, size);
}

static void default_release(void *context, void *pointer) {
    (void)context;
    free(pointer);
}

/* [Implementation 2] Empty-state initialization and invariant checks */
void owned_string_init(
    struct owned_string *string,
    const struct owned_string_allocator *allocator
) {
    if (string == NULL) {
        return;
    }
    string->data = NULL;
    string->length = 0;
    string->capacity = 0;
    if (allocator != NULL) {
        string->allocator = *allocator;
    } else {
        string->allocator.context = NULL;
        string->allocator.resize = default_resize;
        string->allocator.release = default_release;
    }
}

static int owned_string_has_valid_shape(const struct owned_string *string) {
    if (string->data == NULL) {
        return string->length == 0 && string->capacity == 0;
    }
    return string->capacity > 0 && string->length < string->capacity &&
           string->data[string->length] == '\0';
}

/* [Implementation 3] Capacity calculation for aliased input */
static int choose_capacity(size_t current, size_t required, size_t *out_capacity) {
    size_t capacity = current == 0 ? 16 : current;

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
    *out_capacity = capacity;
    return 0;
}

/* [Implementation 4] Append only after successful resize */
int owned_string_append(struct owned_string *string, const char *source) {
    size_t source_length;
    size_t source_offset = 0;
    size_t required;
    int source_aliases_data = 0;

    if (string == NULL || source == NULL ||
        string->allocator.resize == NULL || string->allocator.release == NULL ||
        !owned_string_has_valid_shape(string)) {
        return -1;
    }
    if (string->data != NULL) {
        for (size_t index = 0; index <= string->length; index++) {
            if (source == string->data + index) {
                source_aliases_data = 1;
                source_offset = index;
                break;
            }
        }
    }
    source_length = strlen(source);
    if (string->length > SIZE_MAX - 1 ||
        source_length > SIZE_MAX - string->length - 1) {
        return -1;
    }
    required = string->length + source_length + 1;
    if (required > string->capacity) {
        size_t new_capacity;
        char *resized;

        if (choose_capacity(string->capacity, required, &new_capacity) != 0) {
            return -1;
        }
        resized = string->allocator.resize(
            string->allocator.context,
            string->data,
            new_capacity
        );
        if (resized == NULL) {
            return -1;
        }
        string->data = resized;
        string->capacity = new_capacity;
        if (source_aliases_data) {
            // realloc이 버퍼를 옮기면 기존 source 포인터는 무효가 됩니다.
            // 이전 버퍼에서 계산한 오프셋으로 새 주소를 구합니다.
            source = string->data + source_offset;
        }
    }
    memmove(string->data + string->length, source, source_length + 1);
    string->length += source_length;
    return 0;
}

/* [Implementation 5] Repeatable cleanup */
void owned_string_destroy(struct owned_string *string) {
    if (string == NULL) {
        return;
    }
    if (string->allocator.release != NULL && string->data != NULL) {
        string->allocator.release(string->allocator.context, string->data);
    }
    string->data = NULL;
    string->length = 0;
    string->capacity = 0;
}
