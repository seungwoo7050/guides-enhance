#ifndef COMMAND_SERVICE_REQUEST_PARSER_HPP
#define COMMAND_SERVICE_REQUEST_PARSER_HPP

#include "Request.hpp"

#include <string>

class RequestParser {
public:
    Request parse(const std::string &line) const;
};

#endif
