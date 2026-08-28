#ifndef COMMAND_SERVICE_REQUEST_HPP
#define COMMAND_SERVICE_REQUEST_HPP

#include <string>
#include <vector>

struct Request {
    std::string command;
    std::vector<std::string> arguments;
};

#endif
