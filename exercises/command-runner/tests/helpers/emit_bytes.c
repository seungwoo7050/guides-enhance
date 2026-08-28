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
    size_t total;
    size_t offset = 0;

    if (argc != 2 || parse_count(argv[1], &total) != 0) {
        return 2;
    }
    while (offset < total) {
        size_t chunk = total - offset;
        size_t written = 0;

        if (chunk > sizeof buffer) {
            chunk = sizeof buffer;
        }
        for (size_t index = 0; index < chunk; index++) {
            buffer[index] = (unsigned char)((offset + index) % 251u);
        }
        while (written < chunk) {
            ssize_t count = write(STDOUT_FILENO, buffer + written, chunk - written);

            if (count > 0) {
                written += (size_t)count;
            } else if (count == -1 && errno == EINTR) {
                continue;
            } else {
                return 1;
            }
        }
        offset += chunk;
    }
    return 0;
}
