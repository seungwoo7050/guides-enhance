#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

/* [Implementation 1] 원소별 독립 연산
 * `restrict` 규칙을 만족하면 각 원소를
 * 다른 원소와 독립적으로 계산할 수 있습니다. */
static void saxpy(
    float *restrict output,
    const float *restrict left,
    const float *restrict right,
    float scale,
    size_t count
) {
    size_t index;

    for (index = 0; index < count; ++index)
        output[index] = left[index] * scale + right[index];
}

/* [Implementation 2] 반복 간 의존성
 * 다음 반복이 이전 결과를 읽으므로
 * 일반적인 원소별 벡터화와 비교할 수 있습니다. */
static float recurrence(const float *input, size_t count) {
    size_t index;
    float value = 0.0f;

    for (index = 0; index < count; ++index)
        value = value * 0.999f + input[index];
    return value;
}

/* [Implementation 3] 최적화 뒤 결과 검사
 * 고정 입력의 검사 합계와 점화식 결과로
 * 계산 제거와 잘못된 변환을 검출합니다. */
int main(void) {
    enum { count = 4096 };
    float *left = malloc(sizeof(*left) * count);
    float *right = malloc(sizeof(*right) * count);
    float *output = malloc(sizeof(*output) * count);
    size_t index;
    double checksum = 0.0;
    float dependent;

    if (left == NULL || right == NULL || output == NULL) {
        perror("메모리 할당 실패");
        free(left);
        free(right);
        free(output);
        return 2;
    }
    for (index = 0; index < count; ++index) {
        left[index] = (float)index * 0.25f;
        right[index] = (float)(count - index) * 0.5f;
    }

    saxpy(output, left, right, 1.5f, count);
    for (index = 0; index < count; ++index)
        checksum += output[index];
    dependent = recurrence(output, count);

    printf(
        "검사 합계: %.6f, 점화식 결과: %.6f\n",
        checksum,
        (double)dependent
    );
    if (!isfinite(checksum) || !isfinite(dependent)
        || fabs(checksum - 7340288.0) > 0.001
        || fabs((double)dependent - 1624937.25) > 0.001) {
        fprintf(stderr, "기준 계산과 다른 결과가 나왔습니다.\n");
        free(left);
        free(right);
        free(output);
        return 1;
    }
    free(left);
    free(right);
    free(output);
    return 0;
}
