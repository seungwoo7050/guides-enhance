#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>

static int parse_count(const char *text, size_t *out_count) {
    char *end;
    unsigned long long value;

    errno = 0;
    end = NULL;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > SIZE_MAX) {
        return -1;
    }
    *out_count = (size_t)value;
    return 0;
}

int main(int argc, char *argv[]) {
    unsigned char buffer[4096];
    size_t expected;
    size_t offset = 0;

    if (argc != 2 || parse_count(argv[1], &expected) != 0) {
        return 2;
    }
    while (offset < expected) {
        size_t request = expected - offset;
        ssize_t count;

        if (request > sizeof buffer) {
            request = sizeof buffer;
        }
        do {
            count = read(STDIN_FILENO, buffer, request);
        } while (count == -1 && errno == EINTR);
        if (count <= 0) {
            return 1;
        }
        for (ssize_t index = 0; index < count; index++) {
            unsigned char wanted = (unsigned char)((offset + (size_t)index) % 251u);

            if (buffer[index] != wanted) {
                return 1;
            }
        }
        offset += (size_t)count;
    }
    for (;;) {
        ssize_t count = read(STDIN_FILENO, buffer, sizeof buffer);

        if (count == 0) {
            return 0;
        }
        if (count == -1 && errno == EINTR) {
            continue;
        }
        return 1;
    }
}
