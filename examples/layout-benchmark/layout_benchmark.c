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

static size_t parse_size(const char *text, const char *name) {
    char *end = NULL;
    unsigned long long value;

    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0'
        || value == 0 || value > SIZE_MAX) {
        fprintf(stderr, "%s는 양의 정수여야 합니다.\n", name);
        exit(2);
    }
    return (size_t)value;
}

/* [Implementation 1] 연속 주소 순회
 * C의 행 우선 배치와 같은 방향으로 읽는 기준 구현입니다. */
static uint64_t sum_row_major(
    const uint32_t *matrix,
    size_t rows,
    size_t columns,
    size_t rounds
) {
    uint64_t total = 0;
    size_t round;
    size_t row;
    size_t column;

    for (round = 0; round < rounds; ++round) {
        for (row = 0; row < rows; ++row) {
            for (column = 0; column < columns; ++column)
                total += matrix[row * columns + column];
        }
    }
    return total;
}

/* [Implementation 1-1] 큰 보폭 순회
 * 주소식과 덧셈 횟수는 유지하고 반복문 순서만 바꿉니다. */
static uint64_t sum_column_major(
    const uint32_t *matrix,
    size_t rows,
    size_t columns,
    size_t rounds
) {
    uint64_t total = 0;
    size_t round;
    size_t row;
    size_t column;

    for (round = 0; round < rounds; ++round) {
        for (column = 0; column < columns; ++column) {
            for (row = 0; row < rows; ++row)
                total += matrix[row * columns + column];
        }
    }
    return total;
}

/* [Implementation 2] 같은 입력의 독립 측정
 * 크기 계산의 오버플로를 먼저 검사하고 두 순회의 합계가 같은지 확인합니다. */
int main(int argc, char **argv) {
    size_t rows = 1024;
    size_t columns = 1024;
    size_t rounds = 4;
    size_t count;
    uint32_t *matrix;
    size_t index;
    double started;
    double row_seconds;
    double column_seconds;
    uint64_t row_sum;
    uint64_t column_sum;

    if (argc != 1 && argc != 4) {
        fprintf(stderr, "사용법: %s [행_수 열_수 반복_횟수]\n", argv[0]);
        return 2;
    }
    if (argc == 4) {
        rows = parse_size(argv[1], "행 수");
        columns = parse_size(argv[2], "열 수");
        rounds = parse_size(argv[3], "반복 횟수");
    }
    if (rows > SIZE_MAX / columns
        || rows * columns > SIZE_MAX / sizeof(*matrix)) {
        fprintf(stderr, "행렬 크기가 size_t 표현 범위를 벗어났습니다.\n");
        return 2;
    }

    count = rows * columns;
    matrix = malloc(count * sizeof(*matrix));
    if (matrix == NULL) {
        perror("메모리 할당 실패");
        return 2;
    }
    for (index = 0; index < count; ++index)
        matrix[index] = (uint32_t)((index * 2654435761u) & 1023u);

    started = now_seconds();
    row_sum = sum_row_major(matrix, rows, columns, rounds);
    row_seconds = now_seconds() - started;

    started = now_seconds();
    column_sum = sum_column_major(matrix, rows, columns, rounds);
    column_seconds = now_seconds() - started;

    printf(
        "행 수: %zu, 열 수: %zu, 반복 횟수: %zu\n",
        rows,
        columns,
        rounds
    );
    printf(
        "행 우선 순회: %.9f초, 검사 합계: %" PRIu64 "\n",
        row_seconds,
        row_sum
    );
    printf(
        "열 우선 순회: %.9f초, 검사 합계: %" PRIu64 "\n",
        column_seconds,
        column_sum
    );
    if (row_sum != column_sum) {
        fprintf(stderr, "두 순회의 검사 합계가 다릅니다.\n");
        free(matrix);
        return 1;
    }
    free(matrix);
    return 0;
}
