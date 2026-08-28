#include <fcntl.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    int fd;

    if (argc != 2) {
        return 2;
    }
    fd = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd == -1) {
        return 1;
    }
    return close(fd) == 0 ? 0 : 1;
}
