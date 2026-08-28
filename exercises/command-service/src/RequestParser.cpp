#include "RequestParser.hpp"
#include "Errors.hpp"

#include <sstream>

namespace {
void requireArity(const Request &request, std::size_t expected) {
    if (request.arguments.size() != expected)
        throw ParseError("invalid command arity");
}
}

// [Implementation 4] Whole-line command parsing
// 한 줄 전체를 읽은 뒤 지원하는 명령과 인자 수만 Request로 만듭니다.
Request RequestParser::parse(const std::string &line) const {
    Request request;
    std::istringstream input(line);
    if (!(input >> request.command))
        throw ParseError("empty request");

    std::string argument;
    while (input >> argument)
        request.arguments.push_back(argument);

    if (request.command == "PUT")
        requireArity(request, 2);
    else if (request.command == "GET" || request.command == "DELETE")
        requireArity(request, 1);
    else if (request.command == "COUNT" || request.command == "LIST" ||
             request.command == "QUIT")
        requireArity(request, 0);
    else
        throw ParseError("unsupported command");

    return request;
}
