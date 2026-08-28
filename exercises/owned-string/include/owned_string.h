#ifndef OWNED_STRING_H
#define OWNED_STRING_H

#include <stddef.h>

/* [Implementation 1] Owned buffer and allocator callbacks */
struct owned_string_allocator {
    void *context;
    void *(*resize)(void *context, void *pointer, size_t size);
    void (*release)(void *context, void *pointer);
};

struct owned_string {
    char *data;
    size_t length;
    size_t capacity;
    struct owned_string_allocator allocator;
};

void owned_string_init(
    struct owned_string *string,
    const struct owned_string_allocator *allocator
);
int owned_string_append(struct owned_string *string, const char *source);
void owned_string_destroy(struct owned_string *string);

#endif
