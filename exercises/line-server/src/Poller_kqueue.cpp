#if defined(__APPLE__) || defined(__FreeBSD__) || \
    defined(__OpenBSD__) || defined(__NetBSD__)

#include "Poller.hpp"

#include <cerrno>
#include <cstring>
#include <map>
#include <stdint.h>
#include <stdexcept>
#include <string>
#include <sys/event.h>
#include <sys/time.h>
#include <unistd.h>

// [Implementation 2-2] Track kqueue filters and merge events by descriptor
// kqueue는 read와 write를 별도 이벤트로 돌려주므로 같은 fd의 결과를 하나로 합칩니다.
class KqueuePoller : public Poller {
public:
    KqueuePoller() : kqueueFd_(::kqueue()), interests_() {
        if (kqueueFd_ == -1)
            throwSystemError("kqueue");
    }

    ~KqueuePoller() {
        if (kqueueFd_ != -1)
            ::close(kqueueFd_);
    }

    void add(int fd, int interest) {
        const std::pair<std::map<int, int>::iterator, bool> inserted =
            interests_.insert(std::make_pair(fd, 0));
        if (!inserted.second)
            throw std::runtime_error("descriptor already registered in kqueue");
        try {
            applyDifference(fd, 0, interest);
            inserted.first->second = interest;
        }
        catch (...) {
            try { removeFilters(fd, interest); } catch (...) {}
            interests_.erase(inserted.first);
            throw;
        }
    }

    void update(int fd, int interest) {
        std::map<int, int>::iterator found = interests_.find(fd);
        if (found == interests_.end())
            throw std::runtime_error("descriptor not registered in kqueue");
        const int oldInterest = found->second;
        try {
            applyDifference(fd, oldInterest, interest);
        }
        catch (...) {
            try { applyDifference(fd, interest, oldInterest); } catch (...) {}
            throw;
        }
        found->second = interest;
    }

    void remove(int fd) {
        std::map<int, int>::iterator found = interests_.find(fd);
        if (found == interests_.end())
            return;
        removeFilters(fd, found->second);
        interests_.erase(found);
    }

    std::vector<PollEvent> wait(int timeoutMs) {
        struct kevent nativeEvents[64];
        timespec timeout;
        timeout.tv_sec = timeoutMs / 1000;
        timeout.tv_nsec = (timeoutMs % 1000) * 1000000L;
        int count;
        do {
            count = ::kevent(kqueueFd_, 0, 0, nativeEvents, 64, &timeout);
        }
        while (count == -1 && errno == EINTR);
        if (count == -1)
            throwSystemError("kevent wait");

        std::map<int, PollEvent> merged;
        for (int i = 0; i < count; ++i) {
            const int fd = static_cast<int>(nativeEvents[i].ident);
            PollEvent &event = merged[fd];
            event.fd = fd;
            event.readable = event.readable || nativeEvents[i].filter == EVFILT_READ;
            event.writable = event.writable || nativeEvents[i].filter == EVFILT_WRITE;
            event.hangup = event.hangup || (nativeEvents[i].flags & EV_EOF) != 0;
            event.error = event.error || (nativeEvents[i].flags & EV_ERROR) != 0;
        }

        std::vector<PollEvent> events;
        events.reserve(merged.size());
        for (std::map<int, PollEvent>::const_iterator it = merged.begin();
             it != merged.end(); ++it)
            events.push_back(it->second);
        return events;
    }

private:
    int kqueueFd_;
    std::map<int, int> interests_;

    static void throwSystemError(const char *operation) {
        throw std::runtime_error(
            std::string(operation) + ": " + std::strerror(errno));
    }

    void applyDifference(int fd, int oldInterest, int newInterest) {
        struct kevent changes[2];
        int count = 0;
        appendChange(changes, count, fd, EVFILT_READ,
                     (oldInterest & InterestRead) != 0,
                     (newInterest & InterestRead) != 0);
        appendChange(changes, count, fd, EVFILT_WRITE,
                     (oldInterest & InterestWrite) != 0,
                     (newInterest & InterestWrite) != 0);
        if (count != 0 && ::kevent(kqueueFd_, changes, count, 0, 0, 0) == -1)
            throwSystemError("kevent change");
    }

    static void appendChange(struct kevent *changes, int &count, int fd,
                             int16_t filter, bool had, bool wants) {
        if (had == wants)
            return;
        EV_SET(&changes[count], fd, filter,
               wants ? EV_ADD | EV_ENABLE : EV_DELETE, 0, 0, 0);
        ++count;
    }

    void removeFilters(int fd, int interest) {
        struct kevent changes[2];
        int count = 0;
        if (interest & InterestRead)
            EV_SET(&changes[count++], fd, EVFILT_READ, EV_DELETE, 0, 0, 0);
        if (interest & InterestWrite)
            EV_SET(&changes[count++], fd, EVFILT_WRITE, EV_DELETE, 0, 0, 0);
        if (count != 0 && ::kevent(kqueueFd_, changes, count, 0, 0, 0) == -1 &&
            errno != ENOENT && errno != EBADF) {
            throwSystemError("kevent delete");
        }
    }
};

Poller *createPoller() {
    return new KqueuePoller();
}

#endif
