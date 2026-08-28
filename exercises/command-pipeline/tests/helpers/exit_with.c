#include <errno.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    char *end;
    long status;

    if (argc != 2) {
        return 2;
    }
    errno = 0;
    end = NULL;
    status = strtol(argv[1], &end, 10);
    if (errno != 0 || end == argv[1] || *end != '\0' || status < 0 || status > 255) {
        return 2;
    }
    return (int)status;
}
