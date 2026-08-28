#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t event_write_fd = -1;
static volatile sig_atomic_t usr1_pending;
static volatile sig_atomic_t term_pending;

/* [Implementation 1] Async-signal-safe event capture */
static void handle_signal(int signal_number) {
    static const unsigned char wake = (unsigned char)'W';
    int saved_errno = errno;
    int fd = (int)event_write_fd;

    if (signal_number == SIGUSR1) {
        usr1_pending = 1;
    } else if (signal_number == SIGTERM) {
        term_pending = 1;
    }
    if (fd >= 0) {
        // O_NONBLOCK인 self-pipe가 가득 차도 pending 플래그가 사건을 보존합니다.
        ssize_t ignored = write(fd, &wake, 1);
        (void)ignored;
    }
    errno = saved_errno;
}

static int set_close_on_exec(int fd) {
    int flags = fcntl(fd, F_GETFD);

    if (flags == -1) {
        return -1;
    }
    return fcntl(fd, F_SETFD, flags | FD_CLOEXEC) == -1 ? -1 : 0;
}

static int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL);

    if (flags == -1) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1 ? -1 : 0;
}

/* [Implementation 2] Non-blocking close-on-exec self-pipe */
static int configure_pipe(int read_fd, int write_fd) {
    if (set_close_on_exec(read_fd) != 0 ||
        set_close_on_exec(write_fd) != 0 ||
        set_nonblocking(write_fd) != 0) {
        return -1;
    }
    return 0;
}

/* [Implementation 3] Handler installation with rollback */
static int install_handlers(
    int write_fd,
    struct sigaction *old_usr1,
    struct sigaction *old_term
) {
    struct sigaction action;

    memset(&action, 0, sizeof action);
    action.sa_handler = handle_signal;
    if (sigemptyset(&action.sa_mask) == -1 ||
        sigaddset(&action.sa_mask, SIGUSR1) == -1 ||
        sigaddset(&action.sa_mask, SIGTERM) == -1) {
        return -1;
    }
    action.sa_flags = 0;
    event_write_fd = write_fd;
    if (sigaction(SIGUSR1, &action, old_usr1) == -1) {
        event_write_fd = -1;
        return -1;
    }
    if (sigaction(SIGTERM, &action, old_term) == -1) {
        (void)sigaction(SIGUSR1, old_usr1, NULL);
        event_write_fd = -1;
        return -1;
    }
    return 0;
}

static void restore_handlers(
    const struct sigaction *old_usr1,
    const struct sigaction *old_term
) {
    (void)sigaction(SIGUSR1, old_usr1, NULL);
    (void)sigaction(SIGTERM, old_term, NULL);
}

/* [Implementation 4] Wake-byte read and blocked pending snapshot */
static int wait_for_wake(int fd) {
    unsigned char wake;

    for (;;) {
        ssize_t count = read(fd, &wake, 1);

        if (count == 1) {
            return 0;
        }
        if (count == -1 && errno == EINTR) {
            continue;
        }
        return -1;
    }
}

static int take_pending_events(
    const sigset_t *blocked,
    int *out_usr1,
    int *out_term
) {
    sigset_t previous;

    // pending 플래그를 읽고 지우는 동안 같은 시그널을 막아
    // 사건 유실을 피합니다.
    if (sigprocmask(SIG_BLOCK, blocked, &previous) == -1) {
        return -1;
    }
    *out_usr1 = usr1_pending != 0;
    *out_term = term_pending != 0;
    usr1_pending = 0;
    term_pending = 0;
    if (sigprocmask(SIG_SETMASK, &previous, NULL) == -1) {
        return -1;
    }
    return 0;
}

/* [Implementation 5] Initialization while signals are blocked */
int main(void) {
    int ends[2] = {-1, -1};
    sigset_t blocked;
    sigset_t previous;
    struct sigaction old_usr1;
    struct sigaction old_term;
    int exit_status = 1;
    int installed = 0;
    int unblocked = 0;

    if (setvbuf(stdout, NULL, _IOLBF, 0) != 0) {
        return 1;
    }
    if (sigemptyset(&blocked) == -1 ||
        sigaddset(&blocked, SIGUSR1) == -1 ||
        sigaddset(&blocked, SIGTERM) == -1 ||
        sigprocmask(SIG_BLOCK, &blocked, &previous) == -1) {
        return 1;
    }
    if (pipe(ends) == -1 || configure_pipe(ends[0], ends[1]) != 0 ||
        install_handlers(ends[1], &old_usr1, &old_term) != 0) {
        goto cleanup;
    }
    installed = 1;

    if (printf("ready pid=%ld\n", (long)getpid()) < 0 || fflush(stdout) == EOF) {
        goto cleanup;
    }
    if (sigprocmask(SIG_SETMASK, &previous, NULL) == -1) {
        goto cleanup;
    }
    unblocked = 1;

    /* [Implementation 6] Event handling and ordered cleanup */
    for (;;) {
        int saw_usr1;
        int saw_term;

        if (wait_for_wake(ends[0]) != 0 ||
            take_pending_events(&blocked, &saw_usr1, &saw_term) != 0) {
            goto cleanup;
        }
        if (saw_usr1 && puts("event=SIGUSR1") == EOF) {
            goto cleanup;
        }
        if (saw_term) {
            if (puts("event=SIGTERM") == EOF) {
                goto cleanup;
            }
            exit_status = 0;
            break;
        }
    }

cleanup:
    if (unblocked && sigprocmask(SIG_BLOCK, &blocked, NULL) == -1) {
        exit_status = 1;
    }
    event_write_fd = -1;
    if (installed) {
        restore_handlers(&old_usr1, &old_term);
    }
    if (ends[0] != -1) {
        (void)close(ends[0]);
    }
    if (ends[1] != -1) {
        (void)close(ends[1]);
    }
    if (sigprocmask(SIG_SETMASK, &previous, NULL) == -1) {
        exit_status = 1;
    }
    return exit_status;
}
