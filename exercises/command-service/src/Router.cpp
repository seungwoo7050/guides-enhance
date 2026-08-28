#include "Router.hpp"

#include <stdexcept>
#include <utility>

// [Implementation 7] Own handlers and select by command
// 생성 중 등록이 실패하면 이미 만든 handler도 모두 삭제합니다.
Router::Router()
    : handlers_() {
    try {
        add("PUT", new PutHandler());
        add("GET", new GetHandler());
        add("DELETE", new DeleteHandler());
        add("COUNT", new CountHandler());
        add("LIST", new ListHandler());
        add("QUIT", new QuitHandler());
    }
    catch (...) {
        clear();
        throw;
    }
}

Router::~Router() {
    clear();
}

void Router::add(const std::string &command, Handler *handler) {
    if (handler == 0)
        throw std::invalid_argument("handler must not be null");

    const std::pair<std::map<std::string, Handler *>::iterator, bool> inserted =
        handlers_.insert(std::make_pair(command, handler));
    if (!inserted.second) {
        delete handler;
        throw std::logic_error("handler already registered");
    }
}

void Router::clear() {
    for (std::map<std::string, Handler *>::iterator it = handlers_.begin();
         it != handlers_.end(); ++it) {
        delete it->second;
    }
    handlers_.clear();
}

const Handler *Router::find(const std::string &command) const {
    const std::map<std::string, Handler *>::const_iterator found =
        handlers_.find(command);
    return found == handlers_.end() ? 0 : found->second;
}
