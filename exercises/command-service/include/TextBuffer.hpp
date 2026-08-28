#ifndef COMMAND_SERVICE_TEXT_BUFFER_HPP
#define COMMAND_SERVICE_TEXT_BUFFER_HPP

#include <cstddef>

// [Implementation 2] Heap-backed text ownership
// TextBuffer만 문자열 메모리를 해제합니다. 복사본끼리는 메모리를 공유하지 않습니다.
class TextBuffer {
public:
    TextBuffer();
    explicit TextBuffer(const char *text);
    TextBuffer(const TextBuffer &other);
    ~TextBuffer();
    TextBuffer &operator=(const TextBuffer &other);

    const char *c_str() const;
    std::size_t size() const;
    void set(std::size_t index, char value);
    void swap(TextBuffer &other) throw();

    static void failAfter(int allocations);
    static int liveCount();

private:
    char *data_;
    std::size_t size_;
    static int allocationCountdown_;
    static int liveCount_;

    static char *allocate(std::size_t count);
};

#endif
