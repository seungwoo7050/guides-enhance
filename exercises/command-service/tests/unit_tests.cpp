#include "Errors.hpp"
#include "Handler.hpp"
#include "RequestParser.hpp"
#include "ResponseFormatter.hpp"
#include "Router.hpp"
#include "Store.hpp"
#include "TextBuffer.hpp"

#include <cassert>
#include <iostream>
#include <new>
#include <string>

namespace {
bool parseFails(const RequestParser &parser, const std::string &line) {
    try {
        parser.parse(line);
    }
    catch (const ParseError &) {
        return true;
    }
    return false;
}
}

int main() {
    assert(TextBuffer::liveCount() == 0);
    {
        TextBuffer first("alpha");
        TextBuffer copy(first);
        copy.set(0, 'A');
        assert(std::string(first.c_str()) == "alpha");
        assert(std::string(copy.c_str()) == "Alpha");

        TextBuffer stable("stable");
        // 대입 전에 기존 메모리를 지우는 구현은 이 실패 뒤 값을 잃습니다.
        TextBuffer::failAfter(0);
        try {
            stable = first;
            assert(false);
        }
        catch (const std::bad_alloc &) {
        }
        TextBuffer::failAfter(-1);
        assert(std::string(stable.c_str()) == "stable");
    }
    assert(TextBuffer::liveCount() == 0);

    Store store(2);
    store.putNew("alpha", "one");
    std::string value;
    assert(store.get("alpha", value) && value == "one");

    bool conflict = false;
    try {
        store.putNew("alpha", "replacement");
    }
    catch (const ConflictError &) {
        conflict = true;
    }
    assert(conflict);
    assert(store.get("alpha", value) && value == "one");

    // 값 복사가 실패해도 key와 size가 먼저 반영되지 않는지 확인합니다.
    TextBuffer::failAfter(1);
    bool allocationFailed = false;
    try {
        store.putNew("beta", "two");
    }
    catch (const std::bad_alloc &) {
        allocationFailed = true;
    }
    TextBuffer::failAfter(-1);
    assert(allocationFailed);
    assert(store.size() == 1);
    assert(!store.get("beta", value));

    store.putNew("beta", "two");
    bool full = false;
    try {
        store.putNew("gamma", "three");
    }
    catch (const StoreFullError &) {
        full = true;
    }
    assert(full && store.size() == 2);

    const std::vector<StoreEntry> entries = store.entries();
    assert(entries.size() == 2);
    assert(entries[0].key == "alpha" && entries[1].key == "beta");

    RequestParser parser;
    assert(parser.parse("GET alpha").command == "GET");
    assert(parseFails(parser, ""));
    assert(parseFails(parser, "PUT only-key"));
    assert(parseFails(parser, "UNKNOWN"));

    Router router;
    assert(router.find("PUT") != 0);
    assert(router.find("LIST") != 0);
    assert(router.find("UNKNOWN") == 0);

    Request countRequest = parser.parse("COUNT");
    Response count = router.find("COUNT")->handle(countRequest, store);
    ResponseFormatter formatter;
    assert(formatter.format(count) == "COUNT 2");

    Request listRequest = parser.parse("LIST");
    Response listing = router.find("LIST")->handle(listRequest, store);
    assert(formatter.format(listing) == "alpha=one\nbeta=two");

    std::cout << "command-service unit tests: passed\n";
    return 0;
}
