#include "TextBuffer.hpp"

#include <algorithm>
#include <cstring>
#include <new>
#include <stdexcept>

int TextBuffer::allocationCountdown_ = -1;
int TextBuffer::liveCount_ = 0;

// [Implementation 2-1] Allocation and string lifetime
// 생성이 끝난 객체만 liveCount_에 포함합니다. 할당 실패는 살아 있는 객체 수를 바꾸지 않습니다.
char *TextBuffer::allocate(std::size_t count) {
    if (allocationCountdown_ == 0)
        throw std::bad_alloc();
    if (allocationCountdown_ > 0)
        --allocationCountdown_;
    return new char[count];
}

TextBuffer::TextBuffer()
    : data_(allocate(1)), size_(0) {
    data_[0] = '\0';
    ++liveCount_;
}

TextBuffer::TextBuffer(const char *text)
    : data_(0), size_(text == 0 ? 0 : std::strlen(text)) {
    data_ = allocate(size_ + 1);
    if (size_ != 0)
        std::memcpy(data_, text, size_);
    data_[size_] = '\0';
    ++liveCount_;
}

TextBuffer::TextBuffer(const TextBuffer &other)
    : data_(0), size_(other.size_) {
    data_ = allocate(size_ + 1);
    std::memcpy(data_, other.data_, size_ + 1);
    ++liveCount_;
}

TextBuffer::~TextBuffer() {
    delete[] data_;
    --liveCount_;
}

// [Implementation 2-2] Copy assignment with rollback
// 후보 복사를 먼저 만들기 때문에 자기 대입과 할당 실패에도 기존 문자열이 보존됩니다.
TextBuffer &TextBuffer::operator=(const TextBuffer &other) {
    TextBuffer candidate(other);
    swap(candidate);
    return *this;
}

const char *TextBuffer::c_str() const {
    return data_;
}

std::size_t TextBuffer::size() const {
    return size_;
}

void TextBuffer::set(std::size_t index, char value) {
    if (index >= size_)
        throw std::out_of_range("TextBuffer::set");
    data_[index] = value;
}

void TextBuffer::swap(TextBuffer &other) throw() {
    std::swap(data_, other.data_);
    std::swap(size_, other.size_);
}

void TextBuffer::failAfter(int allocations) {
    allocationCountdown_ = allocations;
}

int TextBuffer::liveCount() {
    return liveCount_;
}
