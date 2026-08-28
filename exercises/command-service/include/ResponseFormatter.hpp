#ifndef COMMAND_SERVICE_RESPONSE_FORMATTER_HPP
#define COMMAND_SERVICE_RESPONSE_FORMATTER_HPP

#include "Response.hpp"

#include <string>

class ResponseFormatter {
public:
    std::string format(const Response &response) const;
};

#endif
