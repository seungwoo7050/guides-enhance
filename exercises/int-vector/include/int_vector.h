#ifndef INT_VECTOR_H
#define INT_VECTOR_H

#include <stddef.h>

/* [Implementation 1] Owned array and allocator callbacks */
struct int_vector_allocator {
    void *context;
    void *(*resize)(void *context, void *pointer, size_t size);
    void (*release)(void *context, void *pointer);
};

struct int_vector {
    int *data;
    size_t size;
    size_t capacity;
    struct int_vector_allocator allocator;
};

void int_vector_init(
    struct int_vector *vector,
    const struct int_vector_allocator *allocator
);
int int_vector_push(struct int_vector *vector, int value);
int int_vector_get(const struct int_vector *vector, size_t index, int *out_value);
void int_vector_destroy(struct int_vector *vector);

#endif
