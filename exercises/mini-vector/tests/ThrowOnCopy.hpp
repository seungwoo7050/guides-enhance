#ifndef THROW_ON_COPY_HPP
#define THROW_ON_COPY_HPP

#include <stdexcept>

class ThrowOnCopy {
public:
    static int live;
    static int copiesBeforeThrow;

    explicit ThrowOnCopy(int initialValue = 0) : value(initialValue) { ++live; }

    ThrowOnCopy(const ThrowOnCopy &other) : value(other.value) {
        if (copiesBeforeThrow == 0)
            throw std::runtime_error("copy failed");
        if (copiesBeforeThrow > 0)
            --copiesBeforeThrow;
        ++live;
    }

    ~ThrowOnCopy() { --live; }

    ThrowOnCopy &operator=(const ThrowOnCopy &other) {
        value = other.value;
        return *this;
    }

    int value;
};

#endif
