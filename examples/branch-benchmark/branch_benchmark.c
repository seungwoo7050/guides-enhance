#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double now_seconds(void) {
    struct timespec value;

    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime 호출 실패");
        exit(2);
    }
    return (double)value.tv_sec + (double)value.tv_nsec / 1000000000.0;
}

static uint32_t next_random(uint32_t *state) {
    uint32_t value = *state;

    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    *state = value;
    return value;
}

/* [Implementation 1] 동일한 비교 연산
 * 입력 배열만 바꾸고 비교식과 누적 작업은 같게 유지합니다. */
static uint64_t count_selected(
    const uint32_t *values,
    size_t count,
    uint32_t threshold
) {
    size_t index;
    uint64_t selected = 0;

    for (index = 0; index < count; ++index) {
        if (values[index] < threshold)
            selected += 1;
    }
    return selected;
}

static size_t parse_size(const char *text) {
    char *end = NULL;
    unsigned long long value;

    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0'
        || value == 0 || value > SIZE_MAX) {
        fprintf(stderr, "항목 수는 양의 정수여야 합니다.\n");
        exit(2);
    }
    return (size_t)value;
}

/* [Implementation 2] 비교 가능한 입력과 측정
 * 두 배열에 같은 임계값을 적용합니다.
 * 선택 수와 실행 시간은 따로 기록합니다. */
int main(int argc, char **argv) {
    size_t count = 8u * 1024u * 1024u;
    uint32_t *predictable;
    uint32_t *unpredictable;
    uint32_t state = 0x12345678u;
    size_t index;
    double started;
    double predictable_seconds;
    double unpredictable_seconds;
    uint64_t predictable_count;
    uint64_t unpredictable_count;

    if (argc == 2)
        count = parse_size(argv[1]);
    else if (argc != 1) {
        fprintf(stderr, "사용법: %s [항목_수]\n", argv[0]);
        return 2;
    }
    if (count > SIZE_MAX / sizeof(*predictable)) {
        fprintf(stderr, "메모리 할당 크기가 표현 범위를 벗어났습니다.\n");
        return 2;
    }

    predictable = malloc(count * sizeof(*predictable));
    unpredictable = malloc(count * sizeof(*unpredictable));
    if (predictable == NULL || unpredictable == NULL) {
        perror("메모리 할당 실패");
        free(predictable);
        free(unpredictable);
        return 2;
    }

    for (index = 0; index < count; ++index) {
        predictable[index] = index < count / 2 ? 0u : UINT32_MAX;
        unpredictable[index] = (next_random(&state) & 1u) ? 0u : UINT32_MAX;
    }

    started = now_seconds();
    predictable_count = count_selected(
        predictable, count, UINT32_MAX / 2u
    );
    predictable_seconds = now_seconds() - started;

    started = now_seconds();
    unpredictable_count = count_selected(
        unpredictable, count, UINT32_MAX / 2u
    );
    unpredictable_seconds = now_seconds() - started;

    printf("항목 수: %zu\n", count);
    printf(
        "예측 가능한 입력: %.9f초, 선택 수: %" PRIu64 "\n",
        predictable_seconds,
        predictable_count
    );
    printf(
        "불규칙한 입력: %.9f초, 선택 수: %" PRIu64 "\n",
        unpredictable_seconds,
        unpredictable_count
    );

    if (predictable_count != count / 2) {
        fprintf(stderr, "예측 가능한 입력의 선택 수가 예상과 다릅니다.\n");
        free(predictable);
        free(unpredictable);
        return 1;
    }
    free(predictable);
    free(unpredictable);
    return 0;
}
