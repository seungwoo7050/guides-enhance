#include "ResponseFormatter.hpp"

#include <sstream>

std::string ResponseFormatter::format(const Response &response) const {
    std::ostringstream output;
    switch (response.code) {
    case Response::Ok:
        output << "OK";
        break;
    case Response::Value:
        output << "VALUE " << response.value;
        break;
    case Response::Deleted:
        output << "DELETED";
        break;
    case Response::NotFound:
        output << "NOT_FOUND";
        break;
    case Response::Count:
        output << "COUNT " << response.count;
        break;
    case Response::Listing:
        for (std::size_t i = 0; i < response.entries.size(); ++i) {
            if (i != 0)
                output << '\n';
            output << response.entries[i].key << '=' << response.entries[i].value;
        }
        break;
    case Response::Bye:
        output << "BYE";
        break;
    }
    return output.str();
}
