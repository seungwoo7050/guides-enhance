#ifndef COMMAND_SERVICE_HANDLER_HPP
#define COMMAND_SERVICE_HANDLER_HPP

#include "Request.hpp"
#include "Response.hpp"
#include "Store.hpp"

// [Implementation 6] Command handler base class and implementations
// Router는 구체 handler 타입을 몰라도 같은 handle 호출로 명령을 실행합니다.
class Handler {
public:
    virtual ~Handler() {}
    virtual Response handle(const Request &request, Store &store) const = 0;
};

class PutHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

class GetHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

class DeleteHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

class CountHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

class ListHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

class QuitHandler : public Handler {
public:
    Response handle(const Request &request, Store &store) const;
};

#endif
