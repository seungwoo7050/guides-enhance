#if defined(__linux__)

#include "Poller.hpp"

#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/epoll.h>
#include <unistd.h>

// [Implementation 2-1] Translate epoll flags and own the epoll descriptor

class EpollPoller : public Poller {
public:
    EpollPoller() : epollFd_(::epoll_create1(EPOLL_CLOEXEC)) {
        if (epollFd_ == -1)
            throwSystemError("epoll_create1");
    }

    ~EpollPoller() {
        if (epollFd_ != -1)
            ::close(epollFd_);
    }

    void add(int fd, int interest) { control(EPOLL_CTL_ADD, fd, interest); }
    void update(int fd, int interest) { control(EPOLL_CTL_MOD, fd, interest); }

    void remove(int fd) {
        if (::epoll_ctl(epollFd_, EPOLL_CTL_DEL, fd, 0) == -1 &&
            errno != ENOENT && errno != EBADF) {
            throwSystemError("epoll_ctl DEL");
        }
    }

    std::vector<PollEvent> wait(int timeoutMs) {
        epoll_event nativeEvents[64];
        int count;
        do {
            count = ::epoll_wait(epollFd_, nativeEvents, 64, timeoutMs);
        }
        while (count == -1 && errno == EINTR);
        if (count == -1)
            throwSystemError("epoll_wait");

        std::vector<PollEvent> events;
        events.reserve(static_cast<std::size_t>(count));
        for (int i = 0; i < count; ++i) {
            PollEvent event;
            event.fd = nativeEvents[i].data.fd;
            event.readable = (nativeEvents[i].events & EPOLLIN) != 0;
            event.writable = (nativeEvents[i].events & EPOLLOUT) != 0;
            event.hangup =
                (nativeEvents[i].events & (EPOLLHUP | EPOLLRDHUP)) != 0;
            event.error = (nativeEvents[i].events & EPOLLERR) != 0;
            events.push_back(event);
        }
        return events;
    }

private:
    int epollFd_;

    static void throwSystemError(const char *operation) {
        throw std::runtime_error(
            std::string(operation) + ": " + std::strerror(errno));
    }

    void control(int operation, int fd, int interest) {
        epoll_event event;
        std::memset(&event, 0, sizeof(event));
        event.data.fd = fd;
        event.events = EPOLLERR | EPOLLHUP | EPOLLRDHUP;
        if (interest & InterestRead)
            event.events |= EPOLLIN;
        if (interest & InterestWrite)
            event.events |= EPOLLOUT;
        if (::epoll_ctl(epollFd_, operation, fd, &event) == -1)
            throwSystemError("epoll_ctl");
    }
};

Poller *createPoller() {
    return new EpollPoller();
}

#endif
