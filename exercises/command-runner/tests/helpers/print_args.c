#include <stdio.h>

int main(int argc, char *argv[]) {
    printf("argc=%d\n", argc - 1);
    for (int index = 1; index < argc; index++) {
        printf("arg[%d]=<%s>\n", index - 1, argv[index]);
    }
    return ferror(stdout) ? 1 : 0;
}
