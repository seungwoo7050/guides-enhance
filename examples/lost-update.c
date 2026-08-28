#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* [Implementation 4] barrier와 worker 공유 상태 정의. */
typedef struct s_barrier {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    unsigned int participants;
    unsigned int waiting;
    unsigned int generation;
} t_barrier;

typedef struct s_worker {
    t_barrier *barrier;
    atomic_ulong *counter;
    unsigned long rounds;
    int use_fetch_add;
} t_worker;

/* [Implementation 5] generation 기반 반복 barrier 초기화.
 * 초기화가 중간에 실패하면 이미 만든 동기화 자원만
 * 역순으로 해제합니다. */
static int barrier_init(t_barrier *barrier, unsigned int participants) {
    if (participants == 0U)
        return -1;
    if (pthread_mutex_init(&barrier->mutex, NULL) != 0)
        return -1;
    if (pthread_cond_init(&barrier->condition, NULL) != 0) {
        (void)pthread_mutex_destroy(&barrier->mutex);
        return -1;
    }
    barrier->participants = participants;
    barrier->waiting = 0U;
    barrier->generation = 0U;
    return 0;
}

static int barrier_wait(t_barrier *barrier) {
    unsigned int generation;

    if (pthread_mutex_lock(&barrier->mutex) != 0)
        return -1;
    generation = barrier->generation;
    barrier->waiting += 1U;
    if (barrier->waiting == barrier->participants) {
        barrier->waiting = 0U;
        barrier->generation += 1U;
        if (pthread_cond_broadcast(&barrier->condition) != 0) {
            (void)pthread_mutex_unlock(&barrier->mutex);
            return -1;
        }
    } else {
        while (generation == barrier->generation) {
            if (pthread_cond_wait(&barrier->condition, &barrier->mutex) != 0) {
                (void)pthread_mutex_unlock(&barrier->mutex);
                return -1;
            }
        }
    }
    return pthread_mutex_unlock(&barrier->mutex) == 0 ? 0 : -1;
}

static void barrier_destroy(t_barrier *barrier) {
    (void)pthread_cond_destroy(&barrier->condition);
    (void)pthread_mutex_destroy(&barrier->mutex);
}

/* [Implementation 6] 분리된 load/store와 atomic RMW 비교.
 * 두 경로를 같은 실행 순서로 고정하며,
 * counter 외의 메모리 순서는 사용하지 않습니다. */
static void *worker_main(void *argument) {
    t_worker *worker;
    unsigned long round;

    worker = argument;
    round = 0UL;
    while (round < worker->rounds) {
        if (worker->use_fetch_add != 0) {
            if (barrier_wait(worker->barrier) != 0)
                return (void *)1;
            (void)atomic_fetch_add_explicit(worker->counter, 1UL, memory_order_relaxed);
        } else {
            unsigned long observed;

            observed = atomic_load_explicit(worker->counter, memory_order_relaxed);
            if (barrier_wait(worker->barrier) != 0)
                return (void *)1;
            atomic_store_explicit(worker->counter, observed + 1UL, memory_order_relaxed);
        }
        if (barrier_wait(worker->barrier) != 0)
            return (void *)1;
        round += 1UL;
    }
    return NULL;
}

static int parse_rounds(const char *text, unsigned long *value) {
    char *end;
    unsigned long parsed;

    end = NULL;
    parsed = strtoul(text, &end, 10);
    if (text[0] == '\0' || end == NULL || *end != '\0'
        || parsed == 0UL || parsed > 10000000UL)
        return -1;
    *value = parsed;
    return 0;
}

/* [Implementation 7] 입력 검증, thread 회수와 결과 출력.
 * 두 worker가 모두 끝난 뒤에만 예상 증가량과 실제 counter를 비교합니다. */
int main(int argc, char **argv) {
    const char *mode;
    unsigned long rounds;
    atomic_ulong counter;
    t_barrier barrier;
    pthread_t thread;
    t_worker workers[2];
    void *status;
    void *main_status;
    int use_fetch_add;
    int index;

    mode = argc > 1 ? argv[1] : "split";
    rounds = 1000UL;
    if (argc > 2 && parse_rounds(argv[2], &rounds) != 0) {
        fprintf(stderr, "사용법: %s split|fetch-add [rounds:1..10000000]\n", argv[0]);
        return 2;
    }
    if (strcmp(mode, "split") == 0)
        use_fetch_add = 0;
    else if (strcmp(mode, "fetch-add") == 0)
        use_fetch_add = 1;
    else {
        fprintf(stderr, "사용법: %s split|fetch-add [rounds:1..10000000]\n", argv[0]);
        return 2;
    }

    atomic_init(&counter, 0UL);
    if (barrier_init(&barrier, 2U) != 0) {
        fprintf(stderr, "배리어 초기화에 실패했습니다.\n");
        return 1;
    }
    index = 0;
    while (index < 2) {
        workers[index].barrier = &barrier;
        workers[index].counter = &counter;
        workers[index].rounds = rounds;
        workers[index].use_fetch_add = use_fetch_add;
        index += 1;
    }
    if (pthread_create(&thread, NULL, worker_main, &workers[0]) != 0) {
        fprintf(stderr, "스레드를 만들지 못했습니다.\n");
        barrier_destroy(&barrier);
        return 1;
    }
    main_status = worker_main(&workers[1]);
    status = NULL;
    if (pthread_join(thread, &status) != 0 || status != NULL || main_status != NULL) {
        fprintf(stderr, "스레드 실행이 실패했습니다.\n");
        barrier_destroy(&barrier);
        return 1;
    }
    barrier_destroy(&barrier);
    printf("mode=%s rounds=%lu expected=%lu actual=%lu\n",
        mode,
        rounds,
        rounds * 2UL,
        atomic_load_explicit(&counter, memory_order_relaxed));
    return 0;
}
