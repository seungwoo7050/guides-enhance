#include <errno.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    char *end;
    long signal_number;

    if (argc != 2) {
        return 2;
    }
    errno = 0;
    end = NULL;
    signal_number = strtol(argv[1], &end, 10);
    if (errno != 0 || end == argv[1] || *end != '\0' ||
        signal_number <= 0) {
        return 2;
    }
    if (signal((int)signal_number, SIG_DFL) == SIG_ERR) {
        return 2;
    }
    if (kill(getpid(), (int)signal_number) == -1) {
        return 2;
    }
    return 255;
}
