#ifndef COMMAND_SERVICE_RESPONSE_HPP
#define COMMAND_SERVICE_RESPONSE_HPP

#include "Store.hpp"

#include <cstddef>
#include <string>
#include <vector>

// [Implementation 5] Response values independent of text formatting
// handler는 출력 문자열을 만들지 않고 결과 종류와 값만 반환합니다.
struct Response {
    enum Code {
        Ok,
        Value,
        Deleted,
        NotFound,
        Count,
        Listing,
        Bye
    };

    Code code;
    std::string value;
    std::size_t count;
    std::vector<StoreEntry> entries;

    explicit Response(Code responseCode)
        : code(responseCode), value(), count(0), entries() {
    }
};

#endif
