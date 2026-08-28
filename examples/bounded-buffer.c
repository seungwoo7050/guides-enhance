#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

enum { BUFFER_CAPACITY = 8 };

/* [Implementation 8] ring 위치, 종료 여부와 통계 보호.
 * 하나의 mutex로 함께 보호해야 count와 실제 slot 수가 어긋나지 않습니다. */
typedef struct s_buffer {
    int values[BUFFER_CAPACITY];
    size_t head;
    size_t tail;
    size_t count;
    int producer_done;
    long long produced_sum;
    long long consumed_sum;
    size_t produced_count;
    size_t consumed_count;
    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} t_buffer;

/* [Implementation 9] mutex와 condition의 부분 초기화 정리.
 * 중간에 실패하면 이미 만든 동기화 자원만 역순으로 해제합니다. */
static int buffer_init(t_buffer *buffer) {
    buffer->head = 0U;
    buffer->tail = 0U;
    buffer->count = 0U;
    buffer->producer_done = 0;
    buffer->produced_sum = 0LL;
    buffer->consumed_sum = 0LL;
    buffer->produced_count = 0U;
    buffer->consumed_count = 0U;
    if (pthread_mutex_init(&buffer->mutex, NULL) != 0)
        return -1;
    if (pthread_cond_init(&buffer->not_empty, NULL) != 0) {
        (void)pthread_mutex_destroy(&buffer->mutex);
        return -1;
    }
    if (pthread_cond_init(&buffer->not_full, NULL) != 0) {
        (void)pthread_cond_destroy(&buffer->not_empty);
        (void)pthread_mutex_destroy(&buffer->mutex);
        return -1;
    }
    return 0;
}

static void buffer_destroy(t_buffer *buffer) {
    (void)pthread_cond_destroy(&buffer->not_full);
    (void)pthread_cond_destroy(&buffer->not_empty);
    (void)pthread_mutex_destroy(&buffer->mutex);
}

/* [Implementation 10] full predicate 확인과 enqueue.
 * 빈 slot이 생길 때까지 조건을 다시 확인하고,
 * 생산 통계도 같은 mutex 아래에서 바꿉니다. */
static int buffer_push(t_buffer *buffer, int value) {
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    while (buffer->count == BUFFER_CAPACITY) {
        if (pthread_cond_wait(&buffer->not_full, &buffer->mutex) != 0) {
            (void)pthread_mutex_unlock(&buffer->mutex);
            return -1;
        }
    }
    buffer->values[buffer->tail] = value;
    buffer->tail = (buffer->tail + 1U) % BUFFER_CAPACITY;
    buffer->count += 1U;
    buffer->produced_count += 1U;
    buffer->produced_sum += value;
    (void)pthread_cond_signal(&buffer->not_empty);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

/* [Implementation 11] 생산 종료 공개와 waiter wakeup.
 * 종료 여부를 같은 mutex 아래에서 바꾸고,
 * 기다리는 consumer를 모두 깨웁니다. */
static int mark_producer_done(t_buffer *buffer) {
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    buffer->producer_done = 1;
    (void)pthread_cond_broadcast(&buffer->not_empty);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

/* [Implementation 12] empty-or-done 확인과 dequeue.
 * item이 없고 생산도 끝났을 때만 종료하며,
 * slot을 비우면 producer 하나를 깨웁니다. */
static int buffer_pop(t_buffer *buffer, int *value, int *finished) {
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    while (buffer->count == 0U && buffer->producer_done == 0) {
        if (pthread_cond_wait(&buffer->not_empty, &buffer->mutex) != 0) {
            (void)pthread_mutex_unlock(&buffer->mutex);
            return -1;
        }
    }
    if (buffer->count == 0U) {
        *finished = 1;
        return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
    }
    *value = buffer->values[buffer->head];
    buffer->head = (buffer->head + 1U) % BUFFER_CAPACITY;
    buffer->count -= 1U;
    buffer->consumed_count += 1U;
    buffer->consumed_sum += *value;
    *finished = 0;
    (void)pthread_cond_signal(&buffer->not_full);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

static void *consumer_main(void *argument) {
    t_buffer *buffer;
    int value;
    int finished;

    buffer = argument;
    finished = 0;
    while (finished == 0) {
        if (buffer_pop(buffer, &value, &finished) != 0)
            return (void *)1;
    }
    return NULL;
}

static int parse_items(const char *text, int *value) {
    char *end;
    long parsed;

    end = NULL;
    parsed = strtol(text, &end, 10);
    if (text[0] == '\0' || end == NULL || *end != '\0' || parsed <= 0L || parsed > 100000L)
        return -1;
    *value = (int)parsed;
    return 0;
}

/* [Implementation 13] producer와 consumer 결과 검증.
 * 두 실행 주체를 모두 회수한 뒤 생산·소비 개수와 합계를 비교합니다. */
int main(int argc, char **argv) {
    t_buffer buffer;
    pthread_t consumer;
    int items;
    int item;
    int producer_failed;
    void *status;
    int result;

    items = 1000;
    if (argc > 1 && parse_items(argv[1], &items) != 0) {
        fprintf(stderr, "사용법: %s [items:1..100000]\n", argv[0]);
        return 2;
    }
    if (buffer_init(&buffer) != 0) {
        fprintf(stderr, "버퍼 초기화에 실패했습니다.\n");
        return 1;
    }
    if (pthread_create(&consumer, NULL, consumer_main, &buffer) != 0) {
        fprintf(stderr, "소비자 스레드를 만들지 못했습니다.\n");
        buffer_destroy(&buffer);
        return 1;
    }

    producer_failed = 0;
    item = 1;
    while (item <= items) {
        if (buffer_push(&buffer, item) != 0) {
            producer_failed = 1;
            break;
        }
        item += 1;
    }
    if (mark_producer_done(&buffer) != 0)
        producer_failed = 1;

    status = NULL;
    if (pthread_join(consumer, &status) != 0 || status != NULL)
        producer_failed = 1;
    printf("produced=%zu consumed=%zu sums_match=%s\n",
        buffer.produced_count,
        buffer.consumed_count,
        buffer.produced_sum == buffer.consumed_sum ? "yes" : "no");
    result = producer_failed == 0
        && buffer.produced_count == buffer.consumed_count
        && buffer.produced_sum == buffer.consumed_sum ? 0 : 1;
    buffer_destroy(&buffer);
    return result;
}
