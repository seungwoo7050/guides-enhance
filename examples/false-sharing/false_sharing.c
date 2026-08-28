#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define CACHE_LINE_BYTES 64u

/* [Implementation 1] 비교할 계수기 배치
 * 값의 갱신 방식은 같게 두고 캐시 라인 안의 간격만 바꿉니다. */
struct compact_counter {
    volatile uint64_t value;
};

struct padded_counter {
    volatile uint64_t value;
    unsigned char padding[CACHE_LINE_BYTES - sizeof(uint64_t)];
};

/* [Implementation 2] 동시 시작 조건
 * 뮤텍스와 조건 변수가 모든 스레드의 도착 여부를 함께 보호합니다. */
struct start_gate {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    size_t arrived;
    size_t expected;
    int open;
};

struct worker {
    size_t index;
    uint64_t iterations;
    int padded;
    struct compact_counter *compact;
    struct padded_counter *separated;
    struct start_gate *gate;
};

static double now_seconds(void) {
    struct timespec value;

    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime 호출 실패");
        exit(2);
    }
    return (double)value.tv_sec + (double)value.tv_nsec / 1000000000.0;
}

static void gate_wait(struct start_gate *gate) {
    pthread_mutex_lock(&gate->mutex);
    gate->arrived += 1;
    if (gate->arrived == gate->expected) {
        gate->open = 1;
        pthread_cond_broadcast(&gate->condition);
    }
    while (!gate->open)
        pthread_cond_wait(&gate->condition, &gate->mutex);
    pthread_mutex_unlock(&gate->mutex);
}

/* [Implementation 3] 스레드별 독립 갱신
 * 각 스레드는 자신의 값만 수정합니다.
 * 같은 객체에 대한 데이터 경쟁 없이 캐시 라인 경쟁만 관찰합니다. */
static void *run_worker(void *opaque) {
    struct worker *worker = opaque;
    uint64_t iteration;

    gate_wait(worker->gate);
    if (worker->padded) {
        for (iteration = 0; iteration < worker->iterations; ++iteration)
            worker->separated[worker->index].value += 1;
    } else {
        for (iteration = 0; iteration < worker->iterations; ++iteration)
            worker->compact[worker->index].value += 1;
    }
    return NULL;
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

static int initialize_gate(struct start_gate *gate, size_t threads) {
    gate->arrived = 0;
    gate->expected = threads;
    gate->open = 0;
    if (pthread_mutex_init(&gate->mutex, NULL) != 0)
        return -1;
    if (pthread_cond_init(&gate->condition, NULL) != 0) {
        pthread_mutex_destroy(&gate->mutex);
        return -1;
    }
    return 0;
}

static void destroy_gate(struct start_gate *gate) {
    pthread_cond_destroy(&gate->condition);
    pthread_mutex_destroy(&gate->mutex);
}

/* [Implementation 4] 한 측정의 자원 수명
 * 정렬 할당부터 스레드 생성·회수와 최종 값 검사까지
 * 한 함수 안에서 끝내 누락된 정리를 막습니다. */
static double run_case(size_t threads, uint64_t iterations, int padded) {
    pthread_t *ids = calloc(threads, sizeof(*ids));
    struct worker *workers = calloc(threads, sizeof(*workers));
    struct compact_counter *compact = NULL;
    struct padded_counter *separated = NULL;
    struct start_gate gate;
    size_t index;
    double started;
    double elapsed;

    if (ids == NULL || workers == NULL)
        goto allocation_failure;
    if (padded) {
        if (posix_memalign(
                (void **)&separated,
                CACHE_LINE_BYTES,
                threads * sizeof(*separated)
            ) != 0)
            separated = NULL;
        if (separated == NULL)
            goto allocation_failure;
        for (index = 0; index < threads; ++index)
            separated[index].value = 0;
    } else {
        if (posix_memalign(
                (void **)&compact,
                CACHE_LINE_BYTES,
                threads * sizeof(*compact)
            ) != 0)
            compact = NULL;
        if (compact == NULL)
            goto allocation_failure;
        for (index = 0; index < threads; ++index)
            compact[index].value = 0;
    }
    if (initialize_gate(&gate, threads) != 0) {
        fprintf(stderr, "시작 동기화 장치를 초기화하지 못했습니다.\n");
        exit(2);
    }

    started = now_seconds();
    for (index = 0; index < threads; ++index) {
        workers[index].index = index;
        workers[index].iterations = iterations;
        workers[index].padded = padded;
        workers[index].compact = compact;
        workers[index].separated = separated;
        workers[index].gate = &gate;
        if (pthread_create(&ids[index], NULL, run_worker, &workers[index]) != 0) {
            fprintf(stderr, "pthread_create 호출이 실패했습니다.\n");
            exit(2);
        }
    }
    for (index = 0; index < threads; ++index)
        pthread_join(ids[index], NULL);
    elapsed = now_seconds() - started;

    for (index = 0; index < threads; ++index) {
        uint64_t value = padded
            ? separated[index].value
            : compact[index].value;
        if (value != iterations) {
            fprintf(
                stderr,
                "%zu번 계수기 값이 예상과 다릅니다: %" PRIu64 "\n",
                index,
                value
            );
            exit(1);
        }
    }
    destroy_gate(&gate);
    free(ids);
    free(workers);
    free(compact);
    free(separated);
    return elapsed;

allocation_failure:
    perror("메모리 할당 실패");
    free(ids);
    free(workers);
    free(compact);
    free(separated);
    exit(2);
}

/* [Implementation 4-1] 동일 조건 비교
 * 스레드 수와 반복 횟수는 그대로 두고
 * 배치만 바꿔 두 실행 시간을 관찰합니다. */
int main(int argc, char **argv) {
    size_t threads = 2;
    uint64_t iterations = 5000000;
    double compact_seconds;
    double padded_seconds;

    if (argc == 3) {
        threads = parse_size(argv[1], "스레드 수");
        iterations = (uint64_t)parse_size(argv[2], "반복 횟수");
    } else if (argc != 1) {
        fprintf(stderr, "사용법: %s [스레드_수 반복_횟수]\n", argv[0]);
        return 2;
    }
    if (threads > 64) {
        fprintf(stderr, "스레드 수는 64 이하여야 합니다.\n");
        return 2;
    }

    compact_seconds = run_case(threads, iterations, 0);
    padded_seconds = run_case(threads, iterations, 1);
    printf("스레드 수: %zu, 반복 횟수: %" PRIu64 "\n", threads, iterations);
    printf("조밀한 배치: %.9f초\n", compact_seconds);
    printf("분리한 배치: %.9f초\n", padded_seconds);
    return 0;
}
