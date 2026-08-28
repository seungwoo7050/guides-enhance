#ifndef RECORD_STREAM_H
#define RECORD_STREAM_H

#include <stddef.h>

struct record_reader_allocator {
    void *context;
    void *(*resize)(void *context, void *pointer, size_t size);
    void (*release)(void *context, void *pointer);
};

/* [Implementation 1] Reader state and borrowed file descriptor */
struct record_reader {
    int fd;
    char *pending;
    size_t length;
    size_t capacity;
    int eof;
    int failed;
    struct record_reader_allocator allocator;
};

void record_reader_init(
    struct record_reader *reader,
    int fd,
    const struct record_reader_allocator *allocator
);
int record_reader_next(
    struct record_reader *reader,
    char **out_record,
    size_t *out_length
);
void record_reader_destroy(struct record_reader *reader);

#endif
