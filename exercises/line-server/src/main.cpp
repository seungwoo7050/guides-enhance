#include "Poller.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <climits>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace {
const std::size_t MaxInputLine = 8192;
const std::size_t MaxPendingOutput = 65536;
volatile sig_atomic_t stopRequested = 0;

void onSignal(int) {
    stopRequested = 1;
}

void installSignalHandler(int signalNumber) {
    struct sigaction action;
    std::memset(&action, 0, sizeof(action));
    action.sa_handler = onSignal;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    if (::sigaction(signalNumber, &action, 0) == -1)
        throw std::runtime_error("sigaction");
}

int parsePort(const char *text) {
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 || value > 65535)
        throw std::invalid_argument("port must be in range 0..65535");
    return static_cast<int>(value);
}

// [Implementation 3] Create non-blocking close-on-exec sockets
// listener와 client socket 모두 non-blocking·close-on-exec으로 설정합니다.
void setSocketFlags(int fd) {
    const int statusFlags = ::fcntl(fd, F_GETFL, 0);
    if (statusFlags == -1 ||
        ::fcntl(fd, F_SETFL, statusFlags | O_NONBLOCK) == -1) {
        throw std::runtime_error("fcntl O_NONBLOCK");
    }

    const int descriptorFlags = ::fcntl(fd, F_GETFD, 0);
    if (descriptorFlags == -1 ||
        ::fcntl(fd, F_SETFD, descriptorFlags | FD_CLOEXEC) == -1) {
        throw std::runtime_error("fcntl FD_CLOEXEC");
    }
}

int makeListener(int port) {
    const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
        throw std::runtime_error("socket");

    try {
        const int enabled = 1;
        if (::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR,
                         &enabled, sizeof(enabled)) == -1) {
            throw std::runtime_error("setsockopt SO_REUSEADDR");
        }
        setSocketFlags(fd);

        sockaddr_in address;
        std::memset(&address, 0, sizeof(address));
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(static_cast<unsigned short>(port));

        if (::bind(fd, reinterpret_cast<sockaddr *>(&address),
                   sizeof(address)) == -1) {
            throw std::runtime_error(std::string("bind: ") + std::strerror(errno));
        }
        if (::listen(fd, 64) == -1)
            throw std::runtime_error("listen");
        return fd;
    }
    catch (...) {
        ::close(fd);
        throw;
    }
}

int actualPort(int fd) {
    sockaddr_in address;
    socklen_t length = sizeof(address);
    if (::getsockname(fd, reinterpret_cast<sockaddr *>(&address), &length) == -1)
        throw std::runtime_error("getsockname");
    return ntohs(address.sin_port);
}

ssize_t sendWithoutSigpipe(int fd, const char *data, std::size_t size) {
#ifdef MSG_NOSIGNAL
    return ::send(fd, data, size, MSG_NOSIGNAL);
#else
    return ::send(fd, data, size, 0);
#endif
}

// [Implementation 4] Own one client descriptor and its buffered state
// Connection이 client fd와 입출력 버퍼, 전송 위치, 종료 상태를 함께 소유합니다.
class Connection {
public:
    explicit Connection(int fd)
        : fd_(fd), input_(), output_(), writeOffset_(0), lineCount_(0),
          closeAfterWrite_(false), dead_(false) {
    }

    ~Connection() {
        if (fd_ != -1)
            ::close(fd_);
    }

    int fd() const { return fd_; }
    bool dead() const { return dead_; }
    bool closeAfterWrite() const { return closeAfterWrite_; }
    bool wantsWrite() const { return writeOffset_ < output_.size(); }

    void requestCloseAfterWrite() {
        closeAfterWrite_ = true;
        if (!wantsWrite())
            dead_ = true;
    }

    void markDead() { dead_ = true; }

    // [Implementation 5] Accumulate bytes until a complete line is available
    // 줄바꿈을 받을 때까지 바이트를 누적하고 완성된 줄만 처리합니다.
    void readReady() {
        char buffer[4096];
        for (;;) {
            const ssize_t received = ::recv(fd_, buffer, sizeof(buffer), 0);
            if (received > 0) {
                input_.append(buffer, static_cast<std::size_t>(received));
                if (!extractLines() || dead_ || closeAfterWrite_)
                    return;
            }
            else if (received == 0) {
                requestCloseAfterWrite();
                return;
            }
            else if (errno == EINTR) {
                continue;
            }
            else if (errno == EAGAIN || errno == EWOULDBLOCK) {
                return;
            }
            else {
                dead_ = true;
                return;
            }
        }
    }

    // [Implementation 6] Resume partial writes and enforce the output limit
    // 일부 전송은 다음 writable event에서 이어 쓰며 출력 상한을 넘기면 해당 연결만 닫습니다.
    void writeReady() {
        while (writeOffset_ < output_.size()) {
            const ssize_t sent = sendWithoutSigpipe(
                fd_, output_.data() + writeOffset_, output_.size() - writeOffset_);
            if (sent > 0)
                writeOffset_ += static_cast<std::size_t>(sent);
            else if (sent == -1 && errno == EINTR)
                continue;
            else if (sent == -1 && (errno == EAGAIN || errno == EWOULDBLOCK))
                return;
            else {
                dead_ = true;
                return;
            }
        }

        output_.clear();
        writeOffset_ = 0;
        if (closeAfterWrite_)
            dead_ = true;
    }

private:
    int fd_;
    std::string input_;
    std::string output_;
    std::size_t writeOffset_;
    std::size_t lineCount_;
    bool closeAfterWrite_;
    bool dead_;

    std::size_t pendingOutput() const {
        return output_.size() - writeOffset_;
    }

    bool queue(const std::string &message) {
        const std::size_t pending = pendingOutput();
        if (pending > MaxPendingOutput || message.size() > MaxPendingOutput - pending) {
            dead_ = true;
            return false;
        }
        output_.append(message);
        return true;
    }

    bool extractLines() {
        for (;;) {
            const std::size_t newline = input_.find('\n');
            if (newline == std::string::npos) {
                if (input_.size() > MaxInputLine)
                    dead_ = true;
                return !dead_;
            }
            if (newline > MaxInputLine) {
                dead_ = true;
                return false;
            }

            std::string line = input_.substr(0, newline);
            input_.erase(0, newline + 1);
            if (!line.empty() && line[line.size() - 1] == '\r')
                line.erase(line.size() - 1);
            processLine(line);
            if (dead_ || closeAfterWrite_)
                return !dead_;
        }
    }

    void processLine(const std::string &line) {
        if (line == "QUIT") {
            if (queue("BYE\n"))
                closeAfterWrite_ = true;
            return;
        }
        if (line == "COUNT") {
            std::ostringstream response;
            response << "COUNT " << lineCount_ << '\n';
            queue(response.str());
            return;
        }
        ++lineCount_;
        queue("ECHO " + line + "\n");
    }
};

typedef std::map<int, Connection *> ClientMap;

// [Implementation 7] Register an accepted client before transferring ownership
// flags 설정, poller 등록, map 삽입이 모두 성공한 뒤에만 map으로 소유권을 넘깁니다.
void acceptAll(int listener, Poller &poller, ClientMap &clients) {
    for (;;) {
        const int fd = ::accept(listener, 0, 0);
        if (fd == -1) {
            if (errno == EINTR)
                continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK)
                return;
            throw std::runtime_error("accept");
        }

        Connection *connection = 0;
        bool registered = false;
        try {
            setSocketFlags(fd);
            connection = new Connection(fd);
            poller.add(fd, InterestRead);
            registered = true;

            const std::pair<ClientMap::iterator, bool> inserted =
                clients.insert(std::make_pair(fd, connection));
            if (!inserted.second)
                throw std::logic_error("duplicate client descriptor");
            connection = 0;
        }
        catch (...) {
            if (registered) {
                try { poller.remove(fd); } catch (...) {}
            }
            if (connection != 0)
                delete connection;
            else
                ::close(fd);
            throw;
        }
    }
}

void destroyClients(Poller *poller, ClientMap &clients) {
    while (!clients.empty()) {
        ClientMap::iterator current = clients.begin();
        const int fd = current->first;
        Connection *connection = current->second;
        clients.erase(current);
        if (poller != 0) {
            try { poller->remove(fd); } catch (...) {}
        }
        delete connection;
    }
}
} // namespace

// [Implementation 8] Dispatch readiness events and close every descriptor once
// 보낼 데이터가 있을 때만 writable을 감시합니다. 항상 감시하면 event loop가 불필요하게 반복됩니다.
int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "usage: line_server port\n";
        return 1;
    }

    std::signal(SIGPIPE, SIG_IGN);
    int listener = -1;
    Poller *poller = 0;
    ClientMap clients;

    try {
        installSignalHandler(SIGTERM);
        installSignalHandler(SIGINT);
        listener = makeListener(parsePort(argv[1]));
        poller = createPoller();
        poller->add(listener, InterestRead);
        std::cout << "PORT " << actualPort(listener) << std::endl;

        while (!stopRequested) {
            const std::vector<PollEvent> events = poller->wait(100);
            std::set<int> closing;

            for (std::size_t i = 0; i < events.size(); ++i) {
                const PollEvent &event = events[i];
                if (event.fd == listener) {
                    if (event.readable)
                        acceptAll(listener, *poller, clients);
                    continue;
                }

                ClientMap::iterator found = clients.find(event.fd);
                if (found == clients.end())
                    continue;

                Connection *connection = found->second;
                if (event.readable && !connection->closeAfterWrite())
                    connection->readReady();
                if (event.writable && !connection->dead())
                    connection->writeReady();

                if (event.error)
                    connection->markDead();
                else if (event.hangup)
                    connection->requestCloseAfterWrite();

                if (connection->dead()) {
                    closing.insert(event.fd);
                    continue;
                }

                int interest = 0;
                if (!connection->closeAfterWrite())
                    interest |= InterestRead;
                if (connection->wantsWrite())
                    interest |= InterestWrite;
                if (interest == 0)
                    closing.insert(event.fd);
                else
                    poller->update(event.fd, interest);
            }

            for (std::set<int>::const_iterator it = closing.begin();
                 it != closing.end(); ++it) {
                ClientMap::iterator found = clients.find(*it);
                if (found == clients.end())
                    continue;
                poller->remove(*it);
                Connection *connection = found->second;
                clients.erase(found);
                delete connection;
            }
        }

        destroyClients(poller, clients);
        poller->remove(listener);
        delete poller;
        poller = 0;
        ::close(listener);
        listener = -1;
        return 0;
    }
    catch (const std::exception &error) {
        std::cerr << "fatal: " << error.what() << '\n';
        destroyClients(poller, clients);
        delete poller;
        if (listener != -1)
            ::close(listener);
        return 1;
    }
}
