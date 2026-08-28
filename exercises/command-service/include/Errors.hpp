#ifndef COMMAND_SERVICE_ERRORS_HPP
#define COMMAND_SERVICE_ERRORS_HPP

#include <stdexcept>
#include <string>

// [Implementation 1] Failure types for parse, conflict, and capacity errors
// 호출자가 복구 방법을 고를 수 있도록 실패 원인을 별도 타입으로 구분합니다.
class ParseError : public std::runtime_error {
public:
    explicit ParseError(const std::string &message)
        : std::runtime_error(message) {
    }
};

class ConflictError : public std::runtime_error {
public:
    explicit ConflictError(const std::string &message)
        : std::runtime_error(message) {
    }
};

class StoreFullError : public std::runtime_error {
public:
    explicit StoreFullError(const std::string &message)
        : std::runtime_error(message) {
    }
};

#endif
