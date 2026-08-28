#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

/* [Implementation 22] process 단위 minor fault 통계 읽기.
 * getrusage 값만으로는 어떤 메모리 접근이
 * fault를 일으켰는지 알 수 없습니다. */
static long minor_faults(void) {
    struct rusage usage;

    if (getrusage(RUSAGE_SELF, &usage) != 0)
        return -1L;
    return usage.ru_minflt;
}

/* [Implementation 23] 입력, page 크기와 곱셈 overflow 검사. */
int main(int argc, char **argv) {
    long page_size;
    long pages;
    char *memory;
    long before;
    long after;
    long index;
    char *end;
    volatile unsigned char *memory_view;
    uint64_t touch_checksum;

    pages = 4096L;
    if (argc > 1) {
        end = NULL;
        pages = strtol(argv[1], &end, 10);
        if (argv[1][0] == '\0' || end == NULL || *end != '\0' || pages <= 0L || pages > 1000000L) {
            fprintf(stderr, "사용법: %s [pages:1..1000000]\n", argv[0]);
            return 2;
        }
    }
    page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0L) {
        fprintf(stderr, "페이지 크기를 확인할 수 없습니다.\n");
        return 1;
    }
    if ((unsigned long)pages > (unsigned long)(SIZE_MAX / (size_t)page_size)) {
        fprintf(stderr, "요청한 매핑이 너무 큽니다.\n");
        return 1;
    }
    memory = calloc((size_t)pages, (size_t)page_size);
    if (memory == NULL) {
        perror("calloc");
        return 1;
    }

    /* [Implementation 24] page별 실제 접근과 checksum 계산.
     * volatile 접근은 write 제거를 막으며,
     * fault 수 자체는 환경에 따라 달라집니다. */
    memory_view = (volatile unsigned char *)memory;
    before = minor_faults();
    index = 0L;
    touch_checksum = 0U;
    while (index < pages) {
        unsigned char value;

        value = (unsigned char)((index % 251L) + 1L);
        memory_view[index * page_size] = value;
        touch_checksum += memory_view[index * page_size];
        index += 1L;
    }
    after = minor_faults();
    if (before < 0L || after < 0L) {
        perror("getrusage");
        free(memory);
        return 1;
    }
    printf("page_size=%ld touched_pages=%ld touch_checksum=%" PRIu64
        " minor_fault_delta=%ld\n",
        page_size,
        pages,
        touch_checksum,
        after - before);
    free(memory);
    return 0;
}
