#ifndef LINE_SERVER_POLLER_HPP
#define LINE_SERVER_POLLER_HPP

#include <vector>

// [Implementation 1] Portable readiness event
// Linux와 BSD의 이벤트 비트를 서버가 사용하는 다섯 값으로 맞춥니다.
struct PollEvent {
    int fd;
    bool readable;
    bool writable;
    bool hangup;
    bool error;

    PollEvent()
        : fd(-1), readable(false), writable(false), hangup(false), error(false) {
    }
};

enum Interest {
    InterestRead = 1,
    InterestWrite = 2
};

class Poller {
public:
    virtual ~Poller() {}
    virtual void add(int fd, int interest) = 0;
    virtual void update(int fd, int interest) = 0;
    virtual void remove(int fd) = 0;
    virtual std::vector<PollEvent> wait(int timeoutMs) = 0;
};

// [Implementation 2] Poller creation for the current operating system

Poller *createPoller();

#endif
