#ifndef MINI_VECTOR_HPP
#define MINI_VECTOR_HPP

#include <algorithm>
#include <cstddef>
#include <memory>
#include <stdexcept>

// [Implementation 1] Raw storage, constructed size, and capacity
// 할당된 메모리와 생성이 끝난 원소를 구분합니다. size_까지만 실제 객체입니다.
template <class T>
class MiniVector {
public:
    typedef T value_type;
    typedef T *iterator;
    typedef const T *const_iterator;

    MiniVector()
        : data_(0), size_(0), capacity_(0), allocator_() {
    }

    // [Implementation 2] Deep copy, destruction, and copy-and-swap
    // 복사본을 먼저 완성하므로 대입 중 할당이 실패해도 기존 값은 남습니다.
    MiniVector(const MiniVector &other)
        : data_(0), size_(0), capacity_(0), allocator_() {
        copyFrom(other);
    }

    ~MiniVector() {
        destroyElements();
        if (data_ != 0)
            allocator_.deallocate(data_, capacity_);
    }

    MiniVector &operator=(MiniVector other) {
        swap(other);
        return *this;
    }

    void swap(MiniVector &other) throw() {
        std::swap(data_, other.data_);
        std::swap(size_, other.size_);
        std::swap(capacity_, other.capacity_);
    }

    // [Implementation 3] Checked element access and half-open iterators

    std::size_t size() const { return size_; }
    std::size_t capacity() const { return capacity_; }
    bool empty() const { return size_ == 0; }

    T &operator[](std::size_t index) { return data_[index]; }
    const T &operator[](std::size_t index) const { return data_[index]; }

    T &at(std::size_t index) {
        if (index >= size_)
            throw std::out_of_range("MiniVector::at");
        return data_[index];
    }

    const T &at(std::size_t index) const {
        if (index >= size_)
            throw std::out_of_range("MiniVector::at");
        return data_[index];
    }

    iterator begin() { return data_; }
    const_iterator begin() const { return data_; }
    iterator end() { return size_ == 0 ? data_ : data_ + size_; }
    const_iterator end() const { return size_ == 0 ? data_ : data_ + size_; }

    // [Implementation 4] Copy into new storage before replacing the old storage
    // 새 메모리에서 모든 복사가 끝난 뒤에만 기존 메모리를 교체합니다.
    void reserve(std::size_t requestedCapacity) {
        if (requestedCapacity <= capacity_)
            return;
        if (requestedCapacity > allocator_.max_size())
            throw std::length_error("MiniVector::reserve");

        T *candidate = allocator_.allocate(requestedCapacity);
        std::size_t built = 0;
        try {
            for (; built < size_; ++built)
                allocator_.construct(candidate + built, data_[built]);
        }
        catch (...) {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, requestedCapacity);
            throw;
        }
        replaceStorage(candidate, built, requestedCapacity);
    }

    // [Implementation 5] Grow without invalidating an aliased input value too early
    // value가 현재 원소를 가리킬 수 있으므로 추가 복사가 끝날 때까지 기존 메모리를 유지합니다.
    void push_back(const T &value) {
        if (size_ < capacity_) {
            allocator_.construct(data_ + size_, value);
            ++size_;
            return;
        }

        const std::size_t nextCapacity = growthCapacity();
        T *candidate = allocator_.allocate(nextCapacity);
        std::size_t built = 0;
        try {
            for (; built < size_; ++built)
                allocator_.construct(candidate + built, data_[built]);
            allocator_.construct(candidate + built, value);
            ++built;
        }
        catch (...) {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, nextCapacity);
            throw;
        }
        replaceStorage(candidate, built, nextCapacity);
    }

    void clear() {
        destroyElements();
        size_ = 0;
    }

private:
    T *data_;
    std::size_t size_;
    std::size_t capacity_;
    std::allocator<T> allocator_;

    std::size_t growthCapacity() const {
        if (capacity_ == 0)
            return 1;
        if (capacity_ > allocator_.max_size() / 2)
            throw std::length_error("MiniVector capacity overflow");
        return capacity_ * 2;
    }

    void destroyBuilt(T *memory, std::size_t count) {
        while (count != 0) {
            --count;
            allocator_.destroy(memory + count);
        }
    }

    void destroyElements() { destroyBuilt(data_, size_); }

    void replaceStorage(T *candidate, std::size_t candidateSize,
                        std::size_t candidateCapacity) {
        destroyElements();
        if (data_ != 0)
            allocator_.deallocate(data_, capacity_);
        data_ = candidate;
        size_ = candidateSize;
        capacity_ = candidateCapacity;
    }

    void copyFrom(const MiniVector &other) {
        if (other.size_ == 0)
            return;

        T *candidate = allocator_.allocate(other.size_);
        std::size_t built = 0;
        try {
            for (; built < other.size_; ++built)
                allocator_.construct(candidate + built, other.data_[built]);
        }
        catch (...) {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, other.size_);
            throw;
        }
        data_ = candidate;
        size_ = other.size_;
        capacity_ = other.size_;
    }
};

#endif
