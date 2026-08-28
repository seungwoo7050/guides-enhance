#ifndef COMMAND_SERVICE_ROUTER_HPP
#define COMMAND_SERVICE_ROUTER_HPP

#include "Handler.hpp"

#include <map>
#include <string>

class Router {
public:
    Router();
    ~Router();

    const Handler *find(const std::string &command) const;

private:
    Router(const Router &);
    Router &operator=(const Router &);

    void add(const std::string &command, Handler *handler);
    void clear();

    std::map<std::string, Handler *> handlers_;
};

#endif
