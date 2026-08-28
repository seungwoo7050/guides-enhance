#include "account.h"

#include <limits.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

#define CHECK(expression)                                                   \
    do                                                                      \
    {                                                                       \
        if (!(expression))                                                  \
        {                                                                   \
            fprintf(stderr, "%s:%d: check failed: %s\n",                  \
                    __FILE__, __LINE__, #expression);                       \
            return 1;                                                       \
        }                                                                   \
    } while (0)

struct start_gate {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    size_t expected;
    size_t ready;
    int open;
};

struct worker_argument {
    struct account *source;
    struct account *destination;
    struct start_gate *gate;
    size_t iterations;
    int failed;
};

struct observer_argument {
    struct account *left;
    struct account *right;
    struct start_gate *gate;
    size_t iterations;
    long expected_total;
    int failed;
};

static int gate_init(struct start_gate *gate, size_t expected) {
    gate->expected = expected;
    gate->ready = 0;
    gate->open = 0;
    if (pthread_mutex_init(&gate->mutex, NULL) != 0) {
        return -1;
    }
    if (pthread_cond_init(&gate->condition, NULL) != 0) {
        (void)pthread_mutex_destroy(&gate->mutex);
        return -1;
    }
    return 0;
}

static int gate_wait(struct start_gate *gate) {
    if (pthread_mutex_lock(&gate->mutex) != 0) {
        return -1;
    }
    gate->ready++;
    (void)pthread_cond_broadcast(&gate->condition);
    while (!gate->open) {
        if (pthread_cond_wait(&gate->condition, &gate->mutex) != 0) {
            (void)pthread_mutex_unlock(&gate->mutex);
            return -1;
        }
    }
    (void)pthread_mutex_unlock(&gate->mutex);
    return 0;
}

static int gate_open_when_ready(struct start_gate *gate) {
    if (pthread_mutex_lock(&gate->mutex) != 0) {
        return -1;
    }
    while (gate->ready < gate->expected) {
        if (pthread_cond_wait(&gate->condition, &gate->mutex) != 0) {
            (void)pthread_mutex_unlock(&gate->mutex);
            return -1;
        }
    }
    gate->open = 1;
    (void)pthread_cond_broadcast(&gate->condition);
    (void)pthread_mutex_unlock(&gate->mutex);
    return 0;
}

static void gate_destroy(struct start_gate *gate) {
    (void)pthread_cond_destroy(&gate->condition);
    (void)pthread_mutex_destroy(&gate->mutex);
}

static void *worker_main(void *opaque) {
    struct worker_argument *argument = opaque;

    if (gate_wait(argument->gate) != 0) {
        argument->failed = 1;
        return NULL;
    }
    for (size_t index = 0; index < argument->iterations; index++) {
        if (account_transfer(argument->source, argument->destination, 1) != 0) {
            argument->failed = 1;
            break;
        }
    }
    return NULL;
}

static void *observer_main(void *opaque) {
    struct observer_argument *argument = opaque;

    if (gate_wait(argument->gate) != 0) {
        argument->failed = 1;
        return NULL;
    }
    for (size_t index = 0; index < argument->iterations; index++) {
        long total;
        long left_balance;
        long right_balance;

        if (account_total(argument->left, argument->right, &total) != 0 ||
            total != argument->expected_total ||
            account_get_balance(argument->left, &left_balance) != 0 ||
            account_get_balance(argument->right, &right_balance) != 0 ||
            left_balance < 0 || right_balance < 0) {
            argument->failed = 1;
            break;
        }
    }
    return NULL;
}

int main(void) {
    enum {
        WORKER_COUNT = 8,
        OBSERVER_COUNT = 2,
        THREAD_COUNT = WORKER_COUNT + OBSERVER_COUNT
    };
    struct account left;
    struct account right;
    struct account full;
    struct account spare;
    struct account same_id;
    struct account invalid = {0};
    struct start_gate gate;
    pthread_t worker_threads[WORKER_COUNT];
    pthread_t observer_threads[OBSERVER_COUNT];
    struct worker_argument workers[WORKER_COUNT];
    struct observer_argument observers[OBSERVER_COUNT];
    long value;
    long total;

    alarm(60);
    CHECK(account_init(NULL, 1, 0) == -1);
    CHECK(account_init(&left, 1, -1) == -1);
    CHECK(account_init(&left, 1, 200000) == 0);
    CHECK(account_init(&right, 2, 200000) == 0);

    value = 999;
    CHECK(account_get_balance(&left, &value) == 0 && value == 200000);
    CHECK(account_get_balance(NULL, &value) == -1 && value == 200000);
    CHECK(account_get_balance(&invalid, &value) == -1 && value == 200000);
    CHECK(account_get_balance(&left, NULL) == -1);

    total = 888;
    CHECK(account_total(&left, &left, &total) == 0 && total == 200000);
    CHECK(account_total(NULL, &right, &total) == -1 && total == 200000);
    CHECK(account_total(&left, &invalid, &total) == -1 && total == 200000);
    CHECK(account_total(&left, &right, NULL) == -1);

    CHECK(account_transfer(NULL, &right, 1) == -1);
    CHECK(account_transfer(&left, NULL, 1) == -1);
    CHECK(account_transfer(&invalid, &right, 1) == -1);
    CHECK(account_transfer(&left, &right, -1) == -1);
    CHECK(account_transfer(&left, &right, 0) == 0);
    CHECK(account_transfer(&left, &right, 300000) == -1);
    CHECK(account_transfer(&left, &left, 10) == 0);
    CHECK(account_get_balance(&left, &value) == 0 && value == 200000);

    CHECK(account_init(&same_id, 1, 10) == 0);
    CHECK(account_transfer(&left, &same_id, 1) == -1);
    total = 777;
    CHECK(account_total(&left, &same_id, &total) == -1 && total == 777);
    account_destroy(&same_id);

    // 이체 스레드와 조회 스레드를 동시에 시작해 잠금 누락과
    // 반대 순서 교착을 검출합니다.
    CHECK(gate_init(&gate, THREAD_COUNT) == 0);
    for (size_t index = 0; index < WORKER_COUNT; index++) {
        workers[index].source = index % 2 == 0 ? &left : &right;
        workers[index].destination = index % 2 == 0 ? &right : &left;
        workers[index].gate = &gate;
        workers[index].iterations = 15000;
        workers[index].failed = 0;
        CHECK(pthread_create(
            &worker_threads[index], NULL, worker_main, &workers[index]
        ) == 0);
    }
    for (size_t index = 0; index < OBSERVER_COUNT; index++) {
        observers[index].left = &left;
        observers[index].right = &right;
        observers[index].gate = &gate;
        observers[index].iterations = 20000;
        observers[index].expected_total = 400000;
        observers[index].failed = 0;
        CHECK(pthread_create(
            &observer_threads[index], NULL, observer_main, &observers[index]
        ) == 0);
    }
    CHECK(gate_open_when_ready(&gate) == 0);
    for (size_t index = 0; index < WORKER_COUNT; index++) {
        CHECK(pthread_join(worker_threads[index], NULL) == 0);
        CHECK(workers[index].failed == 0);
    }
    for (size_t index = 0; index < OBSERVER_COUNT; index++) {
        CHECK(pthread_join(observer_threads[index], NULL) == 0);
        CHECK(observers[index].failed == 0);
    }
    gate_destroy(&gate);

    CHECK(account_get_balance(&left, &value) == 0 && value == 200000);
    CHECK(account_get_balance(&right, &value) == 0 && value == 200000);
    CHECK(account_total(&left, &right, &total) == 0 && total == 400000);

    CHECK(account_init(&full, 3, LONG_MAX) == 0);
    CHECK(account_init(&spare, 4, 10) == 0);
    CHECK(account_transfer(&spare, &full, 1) == -1);
    CHECK(account_get_balance(&full, &value) == 0 && value == LONG_MAX);
    CHECK(account_get_balance(&spare, &value) == 0 && value == 10);
    total = 777;
    CHECK(account_total(&full, &spare, &total) == -1 && total == 777);

    account_destroy(&spare);
    account_destroy(&full);
    account_destroy(&right);
    account_destroy(&left);
    account_destroy(&left);
    account_destroy(&invalid);
    account_destroy(NULL);

    puts("account-simulator tests passed");
    return 0;
}
