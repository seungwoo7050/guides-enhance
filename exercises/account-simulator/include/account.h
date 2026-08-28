#ifndef ACCOUNT_H
#define ACCOUNT_H

#include <pthread.h>

struct account {
    unsigned long id;
    long balance;
    pthread_mutex_t mutex;
    int initialized;
};

int account_init(struct account *account, unsigned long id, long balance);
int account_transfer(struct account *source, struct account *destination, long amount);
int account_get_balance(struct account *account, long *out_balance);
int account_total(struct account *left, struct account *right, long *out_total);
void account_destroy(struct account *account);

#endif
